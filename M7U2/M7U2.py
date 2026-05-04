from aiogram.types import BotCommand, BotCommandScopeDefault, Message
from M1L3.tm import TeachableMachineRuntime
from aiogram import Bot, Dispatcher, types
from typing import Any, Coroutine, cast
from M1L3.ideogram import IdeogramModel
from aiogram.filters import Command
from dotenv import load_dotenv
from M1L3.cv import detector
import logging
import asyncio
import time
import os

load_dotenv()

logger = logging.getLogger(__name__)

TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден")

bot = Bot(token=TOKEN) 
dp = Dispatcher()
tm_model = TeachableMachineRuntime("project2.tm")
ideogram_model = IdeogramModel("converted_keras.zip")
tm_model.load_project()

def log_message(text: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - {text}"
    print(message)
    with open('bot.log', 'a', encoding='utf-8') as f:
        f.write(message + '\n')

async def set_bot_commands(bot: Bot) -> None:
    """Установка команд меню для бота"""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="detect", description="🔍 Детекция объектов на фото"),
        BotCommand(command="tm", description="🤖 Teachable Machine"),
        BotCommand(command="ideogram", description="🎨 Ideogram анализ фото"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
    log_message("Команды меню установлены")

def command_caption_filter(command: str, message: Message) -> bool:
    if not message.caption:
        return False
    text: str = message.caption.strip().lower()
    return text.startswith(f"/{command}")

def detect_caption_filter(message: Message) -> bool:
    return command_caption_filter("detect", message)

def ideogram_caption_filter(message: Message) -> bool:
    return command_caption_filter("ideogram", message)

@dp.message(Command("detect"))
@dp.message(detect_caption_filter)
async def detect_command(message: types.Message) -> None:
    """Детекция объектов на фото: /detect"""
    source_message = None
    if message.reply_to_message and message.reply_to_message.photo:
        source_message = message.reply_to_message
    elif message.photo:
        source_message = message

    if source_message is None or not source_message.photo:
        await message.answer("Ответь на фото командой /detect или прикрепи фото к сообщению с командой.")
        return
    
    await message.answer("🔍 Анализирую изображение...")
    
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: не удалось определить пользователя")
            return
        user_id: int = message.from_user.id

        photo = source_message.photo[-1]
        file = await bot.get_file(photo.file_id)
        if file.file_path is None:
            await message.answer("❌ Ошибка: путь к файлу отсутствует")
            return
        image_bytes = await bot.download_file(file.file_path)
        if image_bytes is None:
            await message.answer("❌ Ошибка: не удалось скачать файл")
            return
        if isinstance(image_bytes, (bytes, bytearray)):
            payload: bytes = bytes(image_bytes)
        else:
            payload = image_bytes.read()
        photo_file, caption = await detector.detect_and_format_telegram(payload, user_id)
        await message.answer_photo(photo_file, caption=caption)
    except Exception as e:
        logger.error(f"Ошибка детекции: {e}")
        await message.answer("❌ Ошибка при анализе изображения")

@dp.message(Command("ideogram"))
@dp.message(ideogram_caption_filter)
async def ideogram_handler(message: types.Message) -> None:
    """Обработчик Ideogram"""
    source_message = None
    if message.reply_to_message and message.reply_to_message.photo:
        source_message = message.reply_to_message
    elif message.photo:
        source_message = message

    if source_message is None or not source_message.photo:
        await message.answer("📸 Ответь на фото командой /ideogram или прикрепи фото к сообщению с командой.")
        return
    
    await message.answer("🎨 Ideogram анализирует...")
    
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: не удалось определить пользователя")
            return

        photo = source_message.photo[-1]
        file = await bot.get_file(photo.file_id)
        if file.file_path is None:
            await message.answer("❌ Ошибка: путь к файлу отсутствует")
            return
        image_bytes = await bot.download_file(file.file_path)
        if image_bytes is None:
            await message.answer("❌ Ошибка: не удалось скачать файл")
            return
        if isinstance(image_bytes, (bytes, bytearray)):
            payload: bytes = bytes(image_bytes)
        else:
            payload = image_bytes.read()

        class_name, confidence = await ideogram_model.predict(payload)
        
        await message.answer(
            f"🎯 Результат Ideogram:\n"
            f"📌 Класс: {class_name}\n"
            f"📊 Уверенность: {confidence:.1%}"
        )
    except Exception as e:
        logger.error(f"Ошибка Ideogram: {e}")
        await message.answer("❌ Ошибка при анализе")

@dp.message(Command("tm"))
async def detect_with_tm_command(message: types.Message) -> None:
    """Детекция объектов с помощью Teachable Machine: /tm"""
    # Проверяем, что ответили на фото
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.answer("📸 Ответь на фото командой /tm")
        return
    
    await message.answer("🤖 Teachable Machine анализирует изображение...")
    
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: не удалось определить пользователя")
            return

        # Скачиваем фото из Telegram
        photo = message.reply_to_message.photo[-1]
        file = await bot.get_file(photo.file_id)
        if file.file_path is None:
            await message.answer("❌ Ошибка: путь к файлу отсутствует")
            return
        image_bytes = await bot.download_file(file.file_path)
        if image_bytes is None:
            await message.answer("❌ Ошибка: не удалось скачать файл")
            return
        if isinstance(image_bytes, (bytes, bytearray)):
            image_payload: bytes = bytes(image_bytes)
        else:
            image_payload = image_bytes.read()

        # Предсказание
        class_name, confidence = await tm_model.predict_image(image_payload)
        
        # Отправляем результат
        await message.answer(
            f"🎯 Результат детекции (Teachable Machine):\n"
            f"📌 Класс: {class_name}\n"
            f"📊 Уверенность: {confidence:.1%}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка TM: {e}")
        await message.answer("❌ Ошибка при анализе изображения")

async def shutdown(bot: Bot, dp: Dispatcher) -> None:
    print("\nЗавершение работы бота...")
    await asyncio.gather(
        return_exceptions=True
    )

async def main() -> None:
    log_message("Бот запускается...")
    print("Бот запускается...")
    
    try:
        await set_bot_commands(bot)
        log_message("Команды бота успешно установлены")
        log_message("Бот успешно запущен")
        start_polling_method = getattr(dp, "start_polling")
        poll_task: Coroutine[Any, Any, None] = cast(Coroutine[Any, Any, None], start_polling_method(bot))
        await poll_task
        if ideogram_model.load():
            log_message("Ideogram модель загружена")
        else:
            log_message("⚠️ Ideogram модель не загружена")
    except (KeyboardInterrupt, asyncio.CancelledError):
        log_message("Бот остановлен по прерыванию")
        print("\nБот остановлен")
    except Exception as e:
        log_message(f"Бот упал с ошибкой: {e}")
        print(f"Бот упал с ошибкой: {e}")
    finally:
        log_message("Бот выключается...")
        await shutdown(bot, dp)
        log_message("Выключение бота завершено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем")