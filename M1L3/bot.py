from image_generator import ImageGenerator, LightImageGenerator
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from gtts import gTTS
from GIF import GIF
import tempfile
import asyncio
import random
import string
import time
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")

bot = Bot(token=TOKEN)
dp = Dispatcher()
gif_creator = GIF()
light_gen = LightImageGenerator()
image_gen = ImageGenerator()
gif_creator.bot = bot

user_states = {}

def log_message(text: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - {text}"
    print(message)
    with open('bot.log', 'a', encoding='utf-8') as f:
        f.write(message + '\n')

async def get_user_info(message: types.Message) -> str:
    """Получает информацию о пользователе для логов"""
    if not message.from_user:
        return "неизвестно"
    user = message.from_user
    return f"{user.id} ({user.username or 'нет имени'})"

async def gen_pass(length: int) -> str:
    """Генерация пароля указанной длины"""
    chars = string.ascii_letters + string.digits + "+-/*!&$#?=@<>"
    password = ''.join(random.choice(chars) for _ in range(length))
    return password

async def validate_text(text: str) -> tuple[bool, str]:
    """Проверяет текст на валидность"""
    if not text or len(text.strip()) == 0:
        return False, "Текст не может быть пустым"
    
    if len(text.strip()) < 3:
        return False, "Текст слишком короткий (минимум 3 символа)"
    
    if len(text) > 500:
        return False, "Текст слишком длинный (максимум 500 символов)"
    forbidden_patterns = ['http://', 'https://', '@', '#!/']
    for pattern in forbidden_patterns:
        if pattern in text.lower():
            return False, "Текст содержит недопустимые элементы"
    
    return True, ""

async def set_bot_commands(bot: Bot):
    """Установка команд меню для бота"""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="gif", description="Создать GIF из фото"),
        BotCommand(command="image", description="Создать изображение"),
        BotCommand(command="audio", description="Озвучить текст"),
        BotCommand(command="pass8", description="Пароль 8 символов"),
        BotCommand(command="pass12", description="Пароль 12 символов"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="heh", description="Повторить 'he' N раз")
    ]
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
    log_message("Команды меню установлены")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_info = await get_user_info(message)
    log_message(f"Команда START от {user_info}")
    await message.answer("Привет! Используй команды из меню")

@dp.message(Command("gif"))
async def gif_info_handler(message: types.Message):
    user_info = await get_user_info(message)
    log_message(f"Команда GIF запрошена пользователем {user_info}")
    await message.answer("Отправь несколько фото для создания GIF")
    await gif_creator.start_handler(message)

@dp.message(Command("image"))
async def image_command_handler(message: types.Message):
    """Обработчик команды /image - переводит в режим ожидания текста"""
    user_info = await get_user_info(message)
    log_message(f"Команда IMAGE получена от {user_info}")
    
    if not message.from_user:
        await message.answer("Ошибка: не удалось определить пользователя")
        return
    user_id = message.from_user.id
    user_states[user_id] = "waiting_for_image_text"
    
    await message.answer("Опиши что хочешь увидеть на изображении. Будь конкретным!\n\nПримеры:\n• 'Красный спортивный автомобиль на фоне гор'\n• 'Кот в костюме супергероя на крыше'\n• 'Фантастический город будущего с летающими машинами'")

@dp.message(Command("audio"))
async def audio_command_handler(message: types.Message):
    """Обработчик команды /audio - переводит в режим ожидания текста"""
    user_info = await get_user_info(message)
    log_message(f"Команда AUDIO получена от {user_info}")
    
    if not message.from_user:
        await message.answer("Ошибка: не удалось определить пользователя")
        return
    user_id = message.from_user.id
    user_states[user_id] = "waiting_for_audio_text"
    
    await message.answer("Напиши текст для озвучки:")


async def generate_image(message: types.Message, text: str):
    """Генерация изображения по тексту"""
    user_info = await get_user_info(message)
    log_message(f"Генерация изображения для {user_info}: '{text[:50]}...'")
    
    await message.answer("Создаю изображение... Это может занять несколько секунд")
    
    try:
        if not message.from_user:
            await message.answer("Ошибка: не удалось определить пользователя")
            return
            
        user_id = message.from_user.id
        clean_text = ' '.join(text.split())
        image_bytes = image_gen.auto_generate(clean_text, str(user_id), save_to_disk=True)
        if image_bytes and image_bytes.getbuffer().nbytes > 1000: 
            await message.answer_photo(
                types.BufferedInputFile(
                    image_bytes.getvalue(),
                    filename=f"image_{user_id}.png"
                ),
                caption=f"Изображение по запросу: {clean_text}"
            )
            log_message(f"Изображение успешно создано для {user_info}")
        else:
            await message.answer("Не удалось создать изображение. Попробуй другой запрос.")
            log_message(f"Ошибка: пустое или маленькое изображение для {user_info}")
        
    except Exception as e:
        error_msg = f"Ошибка генерации изображения для {user_info}: {e}"
        log_message(error_msg)
        await message.answer("Произошла ошибка при создании изображения. Попробуй другой запрос или повтори позже.")

async def generate_audio(message: types.Message, text: str):
    """Генерация аудио по тексту"""
    user_info = await get_user_info(message)
    log_message(f"Генерация аудио для {user_info}: '{text[:50]}...'")
    
    await message.answer("Создаю аудио...")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
        tts: gTTS = gTTS(text=text, lang='ru')
        tts.save(temp_path)
        if os.path.getsize(temp_path) > 0:
            with open(temp_path, 'rb') as audio:
                await message.answer_audio(
                    types.BufferedInputFile(
                        audio.read(),
                        filename="audio.mp3"
                    ),
                    title="Озвученный текст",
                    performer="Бот"
                )
            log_message(f"Аудио успешно создано для {user_info}")
        else:
            await message.answer("Не удалось создать аудио")
            log_message(f"Ошибка: пустой аудиофайл для {user_info}")
            
        os.unlink(temp_path)
        
    except Exception as e:
        error_msg = f"Ошибка создания аудио для {user_info}: {e}"
        log_message(error_msg)
        await message.answer("Произошла ошибка при создании аудио")

@dp.message(Command("pass8"))
async def pass8(message: types.Message):
    """Обработчик команды /pass8"""
    user_info = await get_user_info(message)
    log_message(f"Команда PASS8 обработана для {user_info}")
    
    if not message.text:
        await message.answer("Ошибка: сообщение не содержит текста")
        return
    
    parts = message.text.split()
    if len(parts) > 1:
        try:
            length = int(parts[1])
            length = max(4, min(length, 50))
            pwd = await gen_pass(length)
            await message.answer(f"Пароль ({length} символов):\n`{pwd}`", parse_mode="Markdown")
            log_message(f"Пароль {length} символов сгенерирован для {user_info}")
        except ValueError:
            pwd = await gen_pass(8)
            await message.answer(f"Пароль (8 символов):\n`{pwd}`\n\n*Примечание: для изменения длины используйте /pass8 <число>*", parse_mode="Markdown")
            log_message(f"Пароль 8 символов сгенерирован для {user_info} (неверный параметр)")
    else:
        pwd = await gen_pass(8)
        await message.answer(f"Пароль (8 символов):\n`{pwd}`", parse_mode="Markdown")
        log_message(f"Пароль 8 символов сгенерирован для {user_info}")

@dp.message(Command("pass12"))
async def pass12(message: types.Message):
    user_info = await get_user_info(message)
    log_message(f"Пароль 12 символов запрошен пользователем {user_info}")
    if not message.text:
        await message.answer("Ошибка: сообщение не содержит текста")
        return
    
    parts = message.text.split()
    if len(parts) > 1:
        try:
            length = int(parts[1])
            length = max(4, min(length, 50))
            pwd = await gen_pass(length)
            await message.answer(f"Пароль ({length} символов):\n`{pwd}`", parse_mode="Markdown")
            log_message(f"Пароль {length} символов сгенерирован для {user_info}")
        except ValueError:
            pwd = await gen_pass(12)
            await message.answer(f"Пароль (12 символов):\n`{pwd}`\n\n*Примечание: для изменения длины используйте /pass12 <число>*", parse_mode="Markdown")
            log_message(f"Пароль 12 символов сгенерирован для {user_info} (неверный параметр)")
    else:
        pwd = await gen_pass(12)
        await message.answer(f"Пароль (12 символов):\n`{pwd}`", parse_mode="Markdown")
        log_message(f"Пароль 12 символов сгенерирован для {user_info}")

@dp.message(Command("heh"))
async def send_heh(message: types.Message):
    if not message.text:
        await message.reply("Не удалось обработать сообщение")
        return
    
    parts = message.text.split()
    count_heh = int(parts[1]) if len(parts) > 1 else 5
    await message.reply("he" * count_heh)

@dp.message(lambda message: message.text and message.text.isdigit())
async def custom_pass(message: types.Message):
    user_info = await get_user_info(message)
    if not message.text:
        return
    length = int(message.text)
    log_message(f"Кастомный пароль запрошен пользователем {user_info}: длина {length}")
    if 6 <= length <= 20:
        pwd = await gen_pass(length)
        await message.answer(f"Пароль ({length} символов):\n`{pwd}`", parse_mode="Markdown")
        log_message(f"Кастомный пароль сгенерирован для {user_info}: длина {length}")
    else:
        log_message(f"Неверная длина пароля от {user_info}: {length}")
        await message.answer("Число от 6 до 20")

@dp.message(lambda message: message.photo is not None)
async def photo_handler(message: types.Message):
    user_info = await get_user_info(message)
    log_message(f"Фото получено от {user_info} для создания GIF")
    await gif_creator.photo_to_gif_handler(message)

@dp.message(Command("stats"))
async def stats_handler(message: types.Message):
    user_info = await get_user_info(message)
    log_message(f"Статистика запрошена пользователем {user_info}")
    
    from datetime import datetime
    stats = gif_creator.session_stats
    uptime = datetime.now() - stats['start_time']
    hours, remainder = divmod(uptime.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    success_rate = (stats['successful_gifs'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
    await message.answer(
        f"Статистика:\n"
        f"Время работы: {int(hours)}ч {int(minutes)}м {int(seconds)}с\n"
        f"Запросов: {stats['total_requests']}\n"
        f"Успешных GIF: {stats['successful_gifs']}\n"
        f"Ошибок: {stats['failed_gifs']}\n"
        f"Эффективность: {success_rate:.1f}%"
    )

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    user_info = await get_user_info(message)
    log_message(f"Помощь запрошена пользователем {user_info}")
    await message.answer(
        "Команды:\n"
        "/start - Запустить бота\n"
        "/gif - Создать GIF из фото\n"
        "/image - Создать изображение (бот спросит текст)\n"
        "/audio - Озвучить текст (бот спросит текст)\n"
        "/pass8 - Пароль 8 символов\n"
        "/pass12 - Пароль 12 символов\n"
        "Или отправь число от 6 до 20 для кастомного пароля\n"
        "/stats - Статистика\n"
        "/help - Помощь"
    )

@dp.message()
async def text_handler(message: types.Message):
    """Универсальный обработчик всех сообщений"""
    if not message.text or not message.from_user:
        return
    user_info = await get_user_info(message)
    text = message.text.strip()
    if text.startswith('/'):
        log_message(f"Команда {text} получена от {user_info}")
        return
    await message.answer(f"Вы написали: {text}")
    
async def main():
    os.environ['HF_HOME'] = 'D:/.cache/huggingface'
    log_message("Бот запускается...")
    print("Бот запускается...")
    
    try:
        await set_bot_commands(bot)
        log_message("Команды бота успешно установлены")
        log_message("Бот успешно запущен")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        log_message("Бот остановлен по KeyboardInterrupt")
        print("\nБот остановлен")
    except Exception as e:
        log_message(f"Бот упал с ошибкой: {e}")
        print(f"Бот упал с ошибкой: {e}")
    finally:
        log_message("Бот выключается...")
        await gif_creator.shutdown()
        log_message("Выключение бота завершено")

if __name__ == "__main__":
    asyncio.run(main())