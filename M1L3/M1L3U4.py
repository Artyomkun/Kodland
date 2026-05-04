from aiogram import Dispatcher, types
from dotenv import load_dotenv
from ai_model import AIModel
from typing import Any
from gtts import gTTS
import tempfile
import time
import os

load_dotenv()

dp = Dispatcher()
ai_model = AIModel()

def log_message(text: str) -> None:
    """Логирование сообщений"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - TEXT_TO_SPEECH - {text}"
    print(message)
    with open('bot.log', 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def get_user_info(message: types.Message) -> str:
    """Получает информацию о пользователе для логов"""
    if not message.from_user:
        return "unknown"
    user = message.from_user
    return f"{user.id} ({user.username or 'no username'})"

@dp.message()
async def text_to_audio(message: types.Message):
    """Преобразование текста в аудио с AI анализом"""
    user_info = get_user_info(message)
    if not message.text or message.text.startswith('/'):
        log_message(f"Пропущено сообщение от {user_info}: команда или пустой текст")
        return
    text = message.text.strip()
    if len(text) > 500:
        log_message(f"Слишком длинный текст от {user_info}: {len(text)} символов")
        await message.answer("Текст слишком длинный. Максимум 500 символов.")
        return
    start_time = time.time()
    log_message(f"Запрос аудио от {user_info}: '{text[:50]}...' ({len(text)} символов)")
    temp_path = None
    try:
        log_message("Анализ текста с помощью AI...")
        ai_result = ai_model.process_message(message.from_user.id if message.from_user else 0, text)
        sentiment = ai_result['sentiment']
        ai_response = ai_result['response']
        log_message(f"AI анализ: тональность - {sentiment}")
        log_message("Создание аудио файла...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
        log_message("Генерация речи...")
        tts: Any = gTTS(text=text, lang='ru')
        tts.save(temp_path)
        log_message("Аудио файл создан")
        log_message("Отправка аудио пользователю...")
        with open(temp_path, 'rb') as audio:
            await message.answer_audio(
                types.BufferedInputFile(
                    audio.read(),
                    filename="audio.mp3"
                ),
                title="Озвученный текст",
                performer="Бот",
                caption=f"🎧 Озвученный текст ({len(text)} символов)\n Тональность: {sentiment}\n🤖 AI: {ai_response[:100]}..."
            )
        os.unlink(temp_path)
        log_message("Временный файл удален")
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        log_message(f"Аудио успешно отправлено {user_info} за {processing_time} секунд")
    except Exception as e:
        error_msg = f"Ошибка создания аудио для {user_info}: {e}"
        log_message(error_msg)
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                log_message("Временный файл удален после ошибки")
            except Exception as cleanup_error:
                log_message(f"Ошибка удаления временного файла: {cleanup_error}")
        await message.answer("Произошла ошибка при создании аудио. Попробуйте позже.")