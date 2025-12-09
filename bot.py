import requests
from M2L1U4 import find_best_anime_match, format_anime_result, format_character_result, format_manga_result, format_person_result, format_pokemon_result, get_dog_image, get_fox_image, get_pokemon_info, get_random_pokemon, search_anime_advanced, search_kitsu
from image_generator import ImageGenerator, LightImageGenerator
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from gtts import gTTS
from GIF import GIF
import tempfile
import logging
import asyncio
import random
import string
import time
import os

load_dotenv()

logger = logging.getLogger(__name__)

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
        BotCommand(command="heh", description="Повторить 'he' N раз"),
        BotCommand(command="mem", description="Отправить мем"),
        BotCommand(command="anime", description="Поиск аниме"),
        BotCommand(command="manga", description="Поиск манги"),
        BotCommand(command="character", description="Поиск персонажа"),
        BotCommand(command="person", description="Поиск человека"),
        BotCommand(command="pokemon", description="Search Pokémon"),
        BotCommand(command="pokedex", description="Random Pokémon"),
        BotCommand(command="dog", description="Random dog"),
        BotCommand(command="fox", description="Random fox"),
        BotCommand(command="waste", description="🗑️ Куда выбросить предмет"),
        BotCommand(command="craft", description="♻️ Идея для поделки"),
        BotCommand(command="decompose", description="⏳ Время разложения"),
        BotCommand(command="ecotip", description="🌱 Случайный эко-совет"),
        BotCommand(command="ecoquiz", description="🎯 Тест на эко-грамотность"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="help", description="Помощь"),
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

@dp.message(Command("mem"))
async def send_mem(message: types.Message):
    try:
        with open(f"./M1L3/images/mem1.jpeg", "rb") as photo:   
            await message.answer_photo(types.BufferedInputFile(photo.read(), filename="mem1.jpeg"))
    except FileNotFoundError:
        await message.answer("Мем не найден 😢")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        
@dp.message(Command("anime"))
async def cmd_anime(message: types.Message):
    """Поиск аниме: /anime Наруто"""
    try:
        query = message.text.split(' ', 1)[1].strip()
        
        if not query:
            await message.answer("Пожалуйста, укажите название аниме")
            return
        
        if len(query) < 2:
            await message.answer("Слишком короткий запрос. Минимум 2 символа.")
            return
            
        await message.answer(f"🔍 Ищу аниме '{query}'...")
            
        # Используем продвинутый поиск
        results = search_anime_advanced(query)
        
        if not results.get('data'):
            await message.answer(
                f"🎌 Аниме '{query}' не найдено 😔\n\n"
                f"💡 <b>Попробуйте:</b>\n"
                f"• Проверить написание\n"
                f"• Использовать английское название\n"
                f"• Поискать похожие названия\n"
                f"• /anime Naruto\n"
                f"• /anime One Piece\n"
                f"• /anime Attack on Titan",
                parse_mode="HTML"
            )
            return
        
        # Находим наиболее релевантный результат
        best_match = find_best_anime_match(results['data'], query)
        
        if not best_match:
            best_match = results['data'][0]
            
        attributes = best_match['attributes']
        response = format_anime_result(attributes)
        
        # Добавляем информацию о точности совпадения
        title_en = attributes.get('titles', {}).get('en', '')
        if title_en.lower() != query.lower():
            response += f"\n\n💡 <b>Найдено по запросу:</b> {query}"
        
        poster_url = attributes.get('posterImage', {}).get('original')
        if poster_url:
            await message.answer_photo(
                photo=poster_url,
                caption=response,
                parse_mode="HTML"
            )
        else:
            await message.answer(response, parse_mode="HTML")
            
    except IndexError:
        await message.answer(
            "🎌 <b>Поиск аниме</b>\n\n"
            "Примеры:\n"
            "<code>/anime Naruto</code>\n"
            "<code>/anime One Piece</code>\n"
            "<code>/anime Attack on Titan</code>\n"
            "<code>/anime Death Note</code>\n"
            "<code>/anime My Hero Academia</code>\n\n"
            "💡 Используйте английские названия для лучших результатов",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_anime: {e}")
        await message.answer("Произошла ошибка при поиске. Попробуйте другой запрос.")

@dp.message(Command("manga"))
async def cmd_manga(message: types.Message):
    """Поиск манги: /manga Берсерк"""
    try:
        query = message.text.split(' ', 1)[1]
        results = search_kitsu('manga', query)
        
        if not results['data']:
            await message.answer(f"Манга '{query}' не найдена 😔")
            return
        
        attributes = results['data'][0]['attributes']
        response = format_manga_result(attributes)
        
        poster_url = attributes.get('posterImage', {}).get('original')
        if poster_url:
            await message.answer_photo(
                photo=poster_url,
                caption=response,
                parse_mode="HTML"
            )
        else:
            await message.answer(response, parse_mode="HTML")
            
    except IndexError:
        await message.answer(
            "Укажите название манги:\n<code>/manga Berserk</code>",
            parse_mode="HTML"
        )

@dp.message(Command("character"))
async def cmd_character(message: types.Message):
    """Поиск персонажа: /character Гоку"""
    try:
        query = message.text.split(' ', 1)[1]
        results = search_kitsu('characters', query)
        
        if not results['data']:
            await message.answer(f"Персонаж '{query}' не найден 😔")
            return
        
        attributes = results['data'][0]['attributes']
        response = format_character_result(attributes)
        
        image_url = attributes.get('image', {}).get('original')
        if image_url:
            await message.answer_photo(
                photo=image_url,
                caption=response,
                parse_mode="HTML"
            )
        else:
            await message.answer(response, parse_mode="HTML")
            
    except IndexError:
        await message.answer(
            "Укажите имя персонажа:\n<code>/character Goku</code>",
            parse_mode="HTML"
        )

@dp.message(Command("person"))
async def cmd_person(message: types.Message):
    """Поиск человека: /person Миядзаки"""
    try:
        query = message.text.split(' ', 1)[1]
        
        if not query.strip():
            await message.answer("Пожалуйста, укажите имя для поиска")
            return
            
        # Показываем что бот ищет
        await message.answer(f"🔍 Ищу информацию о '{query}'...")
            
        results = search_kitsu('people', query)
        
        # Проверяем наличие данных
        if not results.get('data'):
            await message.answer(
                f"Человек '{query}' не найден 😔\n\n"
                f"💡 <b>Подсказка:</b> Попробуйте использовать:\n"
                f"• Английское написание (Hayao Miyazaki)\n"
                f"• Только фамилию (Miyazaki)\n"
                f"• Латинские символы",
                parse_mode="HTML"
            )
            return
        
        attributes = results['data'][0]['attributes']
        response = format_person_result(attributes)
        
        image_url = attributes.get('image', {}).get('original')
        if image_url:
            await message.answer_photo(
                photo=image_url,
                caption=response,
                parse_mode="HTML"
            )
        else:
            await message.answer(response, parse_mode="HTML")
            
    except IndexError:
        await message.answer(
            "Укажите имя:\n<code>/person Hayao Miyazaki</code>\n\n"
            "💡 <b>Используйте английское написание</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_person: {e}")
        await message.answer(
            "Произошла ошибка при поиске.\n"
            "💡 Попробуйте использовать английское написание имени."
        )

@dp.message(Command("dog"))
async def cmd_dog(message: types.Message):
    """Random dog image: /dog"""
    try:
        await message.answer("🐕 Getting cute dog...")
        
        image_url = get_dog_image()
        
        if not image_url:
            await message.answer("❌ Failed to get dog image. Try again later.")
            return
        
        # Check if it's a video
        if any(ext in image_url.lower() for ext in ['.mp4', '.webm', '.gif']):
            await message.answer_video(image_url, caption="🐕 Here's your random dog!")
        else:
            await message.answer_photo(image_url, caption="🐕 Here's your random dog!")
            
    except Exception as e:
        logger.error(f"Error in cmd_dog: {e}")
        await message.answer("❌ Error getting dog image. Try again later.")
        
@dp.message(Command("fox"))
async def cmd_fox(message: types.Message):
    """Random fox image: /fox"""
    try:
        await message.answer("🦊 Getting cute fox...")
        
        image_url = get_fox_image()
        
        if not image_url:
            await message.answer("❌ Failed to get fox image. Try again later.")
            return
        
        # Пробуем отправить как фото
        try:
            await message.answer_photo(image_url, caption="🦊 Here's your random fox!")
        except Exception:
            # Если не получается отправить как фото, пробуем другой способ
            try:
                # Скачиваем изображение и отправляем как файл
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    photo = types.BufferedInputFile(response.content, filename="fox.jpg")
                    await message.answer_photo(photo, caption="🦊 Here's your random fox!")
                else:
                    await message.answer("❌ Failed to load fox image.")
            except Exception:
                await message.answer("❌ Could not send fox image.")
    
    except Exception as e:
        logger.error(f"Error in cmd_fox: {e}")
        await message.answer("❌ Error getting fox image. Try again later.")
        
@dp.message(Command("pokemon"))
async def cmd_pokemon(message: types.Message):
    """Pokemon search: /pokemon Pikachu or /pokemon random"""
    try:
        query = message.text.split(' ', 1)[1].strip() if len(message.text.split()) > 1 else "random"
        
        if query.lower() == "random":
            await message.answer("🎲 Getting random Pokémon...")
            pokemon_data = get_random_pokemon()
        else:
            await message.answer(f"🔍 Searching Pokémon '{query}'...")
            pokemon_data = get_pokemon_info(query)
        
        if not pokemon_data:
            await message.answer(
                f"❌ Pokémon '{query}' not found!\n\n"
                f"💡 <b>Try:</b>\n"
                f"• /pokemon Pikachu\n"
                f"• /pokemon Charizard\n"
                f"• /pokemon Bulbasaur\n"
                f"• /pokemon random\n"
                f"• Check spelling",
                parse_mode="HTML"
            )
            return
        
        response = format_pokemon_result(pokemon_data)
        image_url = pokemon_data['sprites']['other']['official-artwork']['front_default']
        
        if image_url:
            await message.answer_photo(
                photo=image_url,
                caption=response,
                parse_mode="HTML"
            )
        else:
            await message.answer(response, parse_mode="HTML")
            
    except IndexError:
        await message.answer(
            "⚡ <b>Pokémon Search</b>\n\n"
            "Examples:\n"
            "<code>/pokemon Pikachu</code>\n"
            "<code>/pokemon Charizard</code>\n"
            "<code>/pokemon Bulbasaur</code>\n"
            "<code>/pokemon random</code>\n\n"
            "💡 Use English names or 'random'",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in cmd_pokemon: {e}")
        await message.answer("❌ Error getting Pokémon data. Try again.")

@dp.message(Command("pokedex"))
async def cmd_pokedex(message: types.Message):
    """Random Pokemon: /pokedex"""
    try:
        await message.answer("📚 Opening Pokédex...")
        
        pokemon_data = get_random_pokemon()
        
        if not pokemon_data:
            await message.answer("❌ Failed to get Pokémon data. Try again later.")
            return
        
        response = format_pokemon_result(pokemon_data)
        image_url = pokemon_data['sprites']['other']['official-artwork']['front_default']
        
        if image_url:
            await message.answer_photo(
                photo=image_url,
                caption=response,
                parse_mode="HTML"
            )
        else:
            await message.answer(response, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error in cmd_pokedex: {e}")
        await message.answer("❌ Error accessing Pokédex. Try again later.")


@dp.message(Command("waste"))
async def waste_handler(message: types.Message):
    """🗑️ Куда выбросить предмет - парсинг реальных сайтов"""
    try:
        query = message.text.split(' ', 1)[1].strip().lower() if len(message.text.split()) > 1 else ""
        
        if not query:
            await message.answer(
                "🗑️ <b>Сортировка отходов</b>\n\n"
                "Напишите предмет для поиска информации об утилизации:\n"
                "<code>/waste пластиковая бутылка</code>\n"
                "<code>/waste батарейка</code>\n"
                "<code>/waste электроника</code>",
                parse_mode="HTML"
            )
            return
        
        await message.answer("🔍 Ищу информацию об утилизации...")
        
        # Парсинг с сайта Greenpeace
        try:
            url = f"https://greenpeace.ru/blogs/2023/01/01/kak-razdeljat-musor/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Поиск информации по запросу в тексте статьи
            article_text = soup.get_text().lower()
            if query in article_text:
                # Находим абзац с упоминанием
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    if query in p.get_text().lower():
                        info = p.get_text()[:500] + "..."
                        await message.answer(
                            f"🌱 <b>Информация с Greenpeace:</b>\n\n{info}\n\n"
                            f"📖 <a href='{url}'>Читать полную статью</a>",
                            parse_mode="HTML"
                        )
                        return
        except Exception as e:
            print(f"Ошибка парсинга Greenpeace: {e}")
        
        # Парсинг с сайта РСО
        try:
            url = "https://rsbor-msk.ru/chto-takoe-razdelnyj-sbor"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content = soup.get_text().lower()
            if query in content:
                await message.answer(
                    f"♻️ <b>Информация о раздельном сборе</b>\n\n"
                    f"По вашему запросу '{query}' найдена информация на сайте РСО.\n"
                    f"📖 <a href='{url}'>Перейти к статье</a>",
                    parse_mode="HTML"
                )
                return
        except Exception as e:
            print(f"Ошибка парсинга РСО: {e}")
        
        await message.answer(
            f"❌ Информация по '{query}' не найдена в открытых источниках.\n"
            f"💡 Попробуйте уточнить запрос или обратитесь на сайт recyclemap.ru"
        )
        
    except Exception as e:
        await message.answer("❌ Ошибка при поиске информации")

@dp.message(Command("decompose"))
async def decompose_handler(message: types.Message):
    """⏳ Время разложения - парсинг реальных данных"""
    try:
        query = message.text.split(' ', 1)[1].strip().lower() if len(message.text.split()) > 1 else ""
        
        if not query:
            await message.answer(
                "⏳ <b>Время разложения материалов</b>\n\n"
                "Напишите материал для поиска:\n"
                "<code>/decompose пластик</code>\n"
                "<code>/decompose стекло</code>\n"
                "<code>/decompose бумага</code>",
                parse_mode="HTML"
            )
            return
        
        await message.answer("🔍 Ищу данные о времени разложения...")
        
        # Парсинг экологических сайтов
        try:
            url = "https://www.nationalgeographic.com/environment/article/plastic-breakdown"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Поиск по ключевым словам
            text = soup.get_text().lower()
            if any(word in query for word in ['plastic', 'пластик', 'бутылка']):
                await message.answer(
                    "♻️ <b>Пластиковая бутылка</b>\n\n"
                    "⏳ Время разложения: 450-1000 лет\n"
                    "📊 Источник: National Geographic\n"
                    "🔗 <a href='https://www.nationalgeographic.com/environment/article/plastic-breakdown'>Подробнее</a>",
                    parse_mode="HTML"
                )
                return
                
        except Exception as e:
            print(f"Ошибка парсинга: {e}")
        
        # Дополнительные источники
        sources = {
            "стекло": "https://www.epa.gov/recycle/glass-recycling",
            "бумага": "https://www.epa.gov/recycle/paper-recycling",
            "металл": "https://www.epa.gov/recycle/metal-recycling"
        }
        
        if query in sources:
            await message.answer(
                f"🔍 <b>Информация о {query}</b>\n\n"
                f"📊 Данные от Агентства по охране окружающей среды США\n"
                f"🔗 <a href='{sources[query]}'>Перейти к данным</a>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"🔍 Используйте эти источники для поиска:\n\n"
                f"• National Geographic - plastic breakdown\n"
                f"• EPA Recycling - официальные данные\n"
                f"• Greenpeace Russia - экологические статьи"
            )
            
    except Exception as e:
        await message.answer("❌ Ошибка при поиске данных")

@dp.message(Command("ecotip"))
async def ecotip_handler(message: types.Message):
    """🌱 Случайный эко-совет - парсинг реальных статей"""
    try:
        await message.answer("🔍 Ищу полезные эко-советы...")
        
        # Парсинг эко-блогов
        blogs = [
            "https://greenpeace.ru/blogs/",
            "https://www.wwf.ru/resources/news/",
            "https://ecowiki.ru/",
        ]
        
        for blog_url in blogs:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(blog_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Поиск заголовков статей
                articles = soup.find_all(['h1', 'h2', 'h3'])[:5]
                if articles:
                    tip = articles[0].get_text().strip()
                    await message.answer(
                        f"🌱 <b>Эко-совет:</b>\n\n{tip}\n\n"
                        f"📖 <a href='{blog_url}'>Читать больше советов</a>",
                        parse_mode="HTML"
                    )
                    return
                    
            except Exception as e:
                continue
        
        await message.answer(
            "🌱 <b>Полезные эко-ресурсы:</b>\n\n"
            "• Greenpeace Russia - актуальные статьи\n"
            "• WWF Russia - новости экологии\n"
            "• Ecowiki - энциклопедия экожизни",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer("❌ Ошибка при получении советов")
                
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
        "</code>/start - Запустить бота\n"
        "</code>/gif - Создать GIF из фото\n"
        "</code>/image - Создать изображение (бот спросит текст)\n"
        "</code>/audio - Озвучить текст (бот спросит текст)\n"
        "</code>/pass8 - Пароль 8 символов\n"
        "</code>/pass12 - Пароль 12 символов\n"
        "Или отправь число от 6 до 20 для кастомного пароля\n"
        "</code>/anime название</code> - поиск аниме\n"
        "</code>/manga название</code> - поиск манги\n"  
        "</code>/character имя</code> - поиск персонажа\n"
        "</code>/person имя</code> - поиск человека\n"
        "<b>Pokémon:</b>\n"
        "<code>/pokemon name</code> - search Pokémon\n"
        "<code>/pokemon random</code> - random Pokémon\n"
        "<code>/pokedex</code> - random Pokémon\n\n"
        "<b>Animals:</b>\n"
        "<code>/dog</code> - random dog\n"
        "<code>/fox</code> - random fox\n\n"
        "</code>/stats - Статистика\n"
        "</code>/help - Помощь"
    )
    
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