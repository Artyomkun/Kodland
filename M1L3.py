import telebot
import os
import random
import string
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Получаем токен из переменной окружения
Token = os.getenv('TELEGRAM_BOT_TOKEN')
if Token is None:
    raise ValueError("Токен бота не найден в переменных окружения!")

# Создаем экземпляр бота
bot = telebot.TeleBot(Token)

# Функция генерации пароля
def gen_pass(pass_length):
    """
    Генерирует случайный пароль заданной длины.
    
    Args:
        pass_length (int): Длина генерируемого пароля
        
    Returns:
        str: Случайно сгенерированный пароль
    """
    elements = "+-/*!&$#?=@<>123456789"
    password = ""
    for i in range(pass_length):
        password += random.choice(elements)
    return password

# Улучшенная версия функции с буквами
def gen_pass_advanced(pass_length):
    """
    Генерирует случайный пароль с буквами, цифрами и символами.
    """
    elements = string.ascii_letters + string.digits + "+-/*!&$#?=@<>"
    password = ""
    for i in range(pass_length):
        password += random.choice(elements)
    return password

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
Привет! Я твой Telegram бот. 

Доступные команды:
/start - показать это сообщение
/hello - поздороваться
/bye - попрощаться
/password - сгенерировать пароль
/pass8 - сгенерировать пароль из 8 символов
/pass12 - сгенерировать пароль из 12 символов

Или просто напиши число - длину пароля!
"""
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['hello'])
def send_hello(message):
    bot.reply_to(message, "Привет! Как дела?")

@bot.message_handler(commands=['bye'])
def send_bye(message):
    bot.reply_to(message, "Пока! Удачи!")

@bot.message_handler(commands=['password'])
def send_password_info(message):
    bot.reply_to(message, "Напиши число от 6 до 20 - длину пароля, или используй команды:\n/pass8 - пароль из 8 символов\n/pass12 - пароль из 12 символов")

@bot.message_handler(commands=['pass8'])
def send_pass8(message):
    password = gen_pass_advanced(8)
    bot.reply_to(message, f"🔐 Ваш пароль (8 символов):\n`{password}`", parse_mode='Markdown')

@bot.message_handler(commands=['pass12'])
def send_pass12(message):
    password = gen_pass_advanced(12)
    bot.reply_to(message, f"🔐 Ваш пароль (12 символов):\n`{password}`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text.isdigit())
def generate_custom_password(message):
    length = int(message.text)
    if 6 <= length <= 20:
        password = gen_pass_advanced(length)
        bot.reply_to(message, f"🔐 Ваш пароль ({length} символов):\n`{password}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, "Пожалуйста, введите число от 6 до 20")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Не понимаю команду. Используйте /start для списка команд")

# Запускаем бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling()