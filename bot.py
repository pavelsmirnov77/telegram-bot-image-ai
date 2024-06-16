import requests
import io
from PIL import Image
import telebot
import os
from dotenv import load_dotenv
from googletrans import Translator
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading

load_dotenv()

API_URL = os.getenv("API_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ROTATE_TOKEN_URL = os.getenv("ROTATE_TOKEN_URL")
COOKIE = os.getenv("COOKIE")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
translator = Translator()

saved_images = {}

API_TOKEN = None

def refresh_token():
    global API_TOKEN
    
    rotate_token_url = ROTATE_TOKEN_URL
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": COOKIE
    }

    try:
        response = requests.post(rotate_token_url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        if response.status_code == 200:
            new_token = response.json().get("token")
            if new_token:
                API_TOKEN = new_token
                print("Новый токен успешно получен")
            else:
                print("Не удалось получить новый токен. Ответ не содержит token")
        else:
            print(f"Не удалось обновить токен. Код ошибки: {response.status_code}, Тело ответа: {response.text}")
    except Exception as e:
        print(f"Ошибка при запросе на обновление токена: {e}")

def periodic_token_refresh(interval):
    refresh_token()
    threading.Timer(interval, periodic_token_refresh, [interval]).start()

def translate_to_english(text):
    language = translator.detect(text).lang
    if language == 'ru':
        translated_text = translator.translate(text, src='ru', dest='en').text
    else:
        translated_text = text
    return translated_text

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    generate_button = InlineKeyboardButton("Генерация изображения", callback_data="generate_image")
    author_button = InlineKeyboardButton("Об авторе", callback_data="author_info")
    markup.row(generate_button)
    markup.row(author_button)
    bot.reply_to(message, "Привет! Выберите действие из меню:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "generate_image":
        bot.send_message(call.message.chat.id, "Отправьте мне описание, и я нарисую по нему изображение.")
    elif call.data == "author_info":
        github_link = "https://github.com/pavelsmirnov77/telegram-bot-image-ai"
        bot.send_message(call.message.chat.id, f"Автор: Смирнов Павел\nGitHub: {github_link}")
    elif call.data == "save_image":
        user_id = call.message.chat.id
        if user_id in saved_images:
            image_data = saved_images[user_id]
            bio = io.BytesIO(image_data)
            bio.name = "image.png"
            bot.send_document(user_id, bio)
            bot.answer_callback_query(call.id, "Изображение сохранено!")
        else:
            bot.answer_callback_query(call.id, "Изображение не найдено для сохранения.")


def query(payload):
    global API_TOKEN
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        error_message = f"Ошибка {response.status_code}: {response.text}"
        print(error_message)
        return None, error_message
    return response.content, None

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text
    user_name = message.from_user.username
    user_id = message.chat.id

    print(f"Пользователь: {user_name}, Запрос: {user_input}")
    translated_input = translate_to_english(user_input)
    bot.reply_to(message, f"Генерация изображения...")

    image_bytes, error_message = query({"inputs": translated_input})

    if image_bytes:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            bio = io.BytesIO()
            bio.name = f"{user_input}.png"
            image.save(bio, 'PNG')
            bio.seek(0)

            saved_images[user_id] = bio.getvalue()

            markup = InlineKeyboardMarkup()
            save_button = InlineKeyboardButton("Сохранить 🖼️", callback_data="save_image")
            markup.add(save_button)

            bot.send_photo(message.chat.id, photo=bio, reply_markup=markup)
        except Exception as e:
            bot.reply_to(message, f"Ошибка при открытии изображения: {e}")
    else:
        bot.reply_to(message, f"Не удалось получить изображение. {error_message}")

if __name__ == "__main__":
    periodic_token_refresh(300) 
    bot.polling()
