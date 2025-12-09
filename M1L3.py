from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
import random
import string
import time

def log_message(text):
    """Логирование сообщений"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - BOT - {text}"
    print(message)
    with open('bot.log', 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def get_user_info(message: types.Message) -> str:
    """Получает информацию о пользователе для логов"""
    if not message.from_user:
        return "unknown"
    user = message.from_user
    return f"{user.id} ({user.username or 'no username'})"

def gen_pass(length: int) -> str:
    """Генерация пароля указанной длины"""
    chars = string.ascii_letters + string.digits + "+-/*!&$#?=@<>"
    password = ''.join(random.choice(chars) for _ in range(length))
    log_message(f"Сгенерирован пароль длины {length}")
    return password

async def generate_password(message: types.Message, default_length: int):
    """Общая функция для генерации пароля"""
    user_info = get_user_info(message)
    if not message.text:
        await message.answer("Ошибка: сообщение не содержит текста")
        return
    
    parts = message.text.split()
    if len(parts) > 1:
        try:
            length = int(parts[1])
            length = max(4, min(length, 50))
            pwd = gen_pass(length)
            await message.answer(f"Пароль ({length} символов):\n`{pwd}`", parse_mode="Markdown")
            log_message(f"Пароль {length} символов сгенерирован для {user_info}")
        except ValueError:
            pwd = gen_pass(default_length)
            await message.answer(f"Пароль ({default_length} символов):\n`{pwd}`\n\n*Используйте число для изменения длины*", parse_mode="Markdown")
            log_message(f"Пароль {default_length} символов сгенерирован для {user_info}")
    else:
        pwd = gen_pass(default_length)
        await message.answer(f"Пароль ({default_length} символов):\n`{pwd}`", parse_mode="Markdown")
        log_message(f"Пароль {default_length} символов сгенерирован для {user_info}")

dp = Dispatcher()

@dp.message(Command("pass8"))
async def pass8(message: types.Message):
    """Генерация пароля из 8 символов"""
    user_info = get_user_info(message)
    log_message(f"Команда /pass8 от пользователя {user_info}")
    try:
        pwd = gen_pass(8)
        await message.answer(f"Пароль (8):\n`{pwd}`", parse_mode="Markdown")
        log_message(f"Пароль отправлен пользователю {user_info}")
    except Exception as e:
        error_msg = f"Ошибка генерации пароля для {user_info}: {e}"
        log_message(error_msg)
        await message.answer("Произошла ошибка при генерации пароля")

@dp.message(Command("pass12"))
async def pass12(message: types.Message):
    """Генерация пароля из 12 символов"""
    user_info = get_user_info(message)
    log_message(f"Команда /pass12 от пользователя {user_info}")
    try:
        pwd = gen_pass(12)
        await message.answer(f"Пароль (12):\n`{pwd}`", parse_mode="Markdown")
        log_message(f"Пароль отправлен пользователю {user_info}")
    except Exception as e:
        error_msg = f"Ошибка генерации пароля для {user_info}: {e}"
        log_message(error_msg)
        await message.answer("Произошла ошибка при генерации пароля")

@dp.message(F.text.regexp(r'^\d+$'))
async def custom_pass(message: types.Message):
    """Генерация пароля произвольной длины"""
    user_info = get_user_info(message)
    if not message.text:  
        log_message(f"Пустое сообщение от {user_info}")
        return
    try:
        length = int(message.text)
        log_message(f"Запрос кастомного пароля от {user_info}: длина {length}")
        
        if 6 <= length <= 20:
            pwd = gen_pass(length)
            await message.answer(f"Пароль ({length}):\n`{pwd}`", parse_mode="Markdown")
            log_message(f"Кастомный пароль отправлен {user_info}: длина {length}")
        else:
            log_message(f"Некорректная длина от {user_info}: {length}")
            await message.answer("Число от 6 до 20")
    except ValueError:
        error_msg = f"Ошибка преобразования числа от {user_info}: '{message.text}'"
        log_message(error_msg)
        await message.answer("Пожалуйста, введите число")
    except Exception as e:
        error_msg = f"Неизвестная ошибка у {user_info}: {e}"
        log_message(error_msg)
        await message.answer("Произошла ошибка при генерации пароля")