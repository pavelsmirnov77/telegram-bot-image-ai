import requests
import io
from PIL import Image
import telebot
import os
from dotenv import load_dotenv
from googletrans import Translator
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
translator = Translator()

saved_images = {}

def translate_to_english(text):
    language = translator.detect(text).lang
    if language == 'ru':
        translated_text = translator.translate(text, src='ru', dest='en').text
    else:
        translated_text = text
    return translated_text

def query(payload):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        error_message = f"Ошибка {response.status_code}: {response.text}"
        print(error_message)
        return None, error_message
    return response.content, None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправьте мне текст, и я сгенерирую изображение.")

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

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id

    if call.data == "save_image":
        if user_id in saved_images:
            image_data = saved_images[user_id]
            bio = io.BytesIO(image_data)
            bio.name = "image.png"
            bot.send_document(user_id, bio)
            bot.answer_callback_query(call.id, "Изображение сохранено!")
        else:
            bot.answer_callback_query(call.id, "Изображение не найдено для сохранения.")

if __name__ == "__main__":
    bot.polling()
