from PIL import Image, ImageEnhance, ImageFilter, ImageStat
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from typing import Optional, Tuple
from dotenv import load_dotenv
from datetime import datetime
import random
import asyncio
import math
import time
import io
import os

load_dotenv()

class GIF:
    def __init__(self):
        self.TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.TOKEN:
            print("Token not found")
            exit(1)
        self.bot = Bot(token=self.TOKEN)
        self.dp = Dispatcher()
        self.setup_handlers()
        self.optimization_settings = {
            'max_size': 400,
            'frame_count': 64,
        }
        self.session_stats = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'successful_gifs': 0,
            'failed_gifs': 0,
        }
        self.is_running = True

    def log_message(self, text):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - {text}"
        print(message)
        with open('bot.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')

    def format_processing_time(self, seconds: float) -> str:
        if seconds < 0.1:
            return f"{seconds * 1000:.0f} мс"
        elif seconds < 1:
            return f"{seconds * 1000:.1f} мс"
        elif seconds < 10:
            return f"{seconds:.2f} сек"
        else:
            return f"{seconds:.1f} сек"

    def setup_handlers(self):
        self.dp.message.register(self.start_handler, Command("gif"))
        self.dp.message.register(self.photo_to_gif_handler, lambda m: m.photo is not None)

    def analyze_image_style(self, image: Image.Image) -> str:
        stats = ImageStat.Stat(image)
        brightness = sum(stats.mean) / 3
        contrast = sum(stats.stddev) / 3
        r, g, b = stats.mean
        max_color = max(r, g, b)
        min_color = min(r, g, b)
        saturation = 0 if max_color == 0 else (max_color - min_color) / max_color
        grayscale = image.convert('L')
        hist = grayscale.histogram()
        total_pixels = sum(hist)
        dark_ratio = sum(hist[:64]) / total_pixels
        light_ratio = sum(hist[192:]) / total_pixels
        contrast_ratio = contrast / 128
        print(f"Анализ изображения:")
        print(f"Яркость: {brightness:.1f}")
        print(f"Контраст: {contrast:.1f}")
        print(f"Насыщенность: {saturation:.1f}")
        print(f"Темные тона: {dark_ratio:.1%}")
        print(f"Светлые тона: {light_ratio:.1%}")
        if contrast_ratio > 0.7 and saturation > 0.6:
            style = "cinematic"
            reason = "высокий контраст и насыщенные цвета"
        elif saturation < 0.3 and contrast_ratio < 0.4:
            style = "minimalist"
            reason = "приглушенные цвета и мягкий контраст"
        elif dark_ratio > 0.6:
            style = "cinematic"
            reason = "преобладание темных тонов"
        elif light_ratio > 0.6:
            style = "minimalist"
            reason = "преобладание светлых тонов"
        elif saturation > 0.5:
            style = "artistic"
            reason = "яркие и насыщенные цвета"
        else:
            style = "artistic"
            reason = "сбалансированная цветовая гамма"
        style_names = {
            "cinematic": "Кинематографический",
            "artistic": "Художественный", 
            "minimalist": "Минималистичный"
        }
        print(f"   Выбран стиль: {style_names[style]} ({reason})")
        return style

    def optimize_image_size(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        max_size = self.optimization_settings['max_size']
        if width > max_size or height > max_size:
            if width > height:
                new_height = int((max_size / width) * height)
                new_size = (max_size, new_height)
            else:
                new_width = int((max_size / height) * width)
                new_size = (new_width, max_size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        return image

    async def download_and_optimize_photo(self, file_id: str) -> Optional[Image.Image]:
        try:
            file = await self.bot.get_file(file_id)
            if file.file_path:
                photo_data = await self.bot.download_file(file.file_path)
                if photo_data:
                    image = Image.open(io.BytesIO(photo_data.read()))
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image = self.optimize_image_size(image)
                    return image
        except Exception as e:
            print(f"Ошибка загрузки фото: {e}")
        return None

    def safe_get_pixel(self, image: Image.Image, x: int, y: int) -> Tuple[int, int, int]:
        if 0 <= x < image.width and 0 <= y < image.height:
            pixel = image.getpixel((x, y))
            if isinstance(pixel, int):
                return (pixel, pixel, pixel)
            elif isinstance(pixel, tuple):
                if len(pixel) >= 3:
                    return (pixel[0], pixel[1], pixel[2])
                elif len(pixel) == 1:
                    return (pixel[0], pixel[0], pixel[0])
            return (0, 0, 0)
        return (0, 0, 0)

    def fast_wave_effect(self, image: Image.Image, frame: int, total_frames: int) -> Image.Image:
        progress = frame / total_frames
        width, height = image.size
        wave_strength = 5 * math.sin(progress * 4 * math.pi)
        wave_frame = image.copy()
        for y in range(0, height, 2):
            offset = int(wave_strength * math.sin(y / 20 + progress * 8))
            for x in range(0, width, 2):
                new_x = (x + offset) % width
                if 0 <= new_x < width:
                    pixel = self.safe_get_pixel(image, new_x, y)
                    wave_frame.putpixel((x, y), pixel)
                    if x + 1 < width:
                        wave_frame.putpixel((x + 1, y), pixel)
                    if y + 1 < height:
                        wave_frame.putpixel((x, y + 1), pixel)
                        if x + 1 < width:
                            wave_frame.putpixel((x + 1, y + 1), pixel)
        return wave_frame

    def fast_color_effect(self, image: Image.Image, frame: int, total_frames: int) -> Image.Image:
        progress = frame / total_frames
        enhancer = ImageEnhance.Color(image)
        saturation = 0.7 + 0.3 * math.sin(progress * 4 * math.pi)
        result = enhancer.enhance(saturation)
        enhancer = ImageEnhance.Brightness(result)
        brightness = 0.8 + 0.2 * math.cos(progress * 6 * math.pi)
        result = enhancer.enhance(brightness)
        return result

    def fast_zoom_effect(self, image: Image.Image, frame: int, total_frames: int) -> Image.Image:
        progress = frame / total_frames
        width, height = image.size
        scale = 0.8 + 0.4 * math.sin(progress * 2 * math.pi)
        new_width = int(width * scale)
        new_height = int(height * scale)
        if new_width <= 0 or new_height <= 0:
            return image
        scaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        result = Image.new('RGB', (width, height), 
                          (int(128 + 100 * math.sin(progress * 2 * math.pi)),
                           int(128 + 100 * math.cos(progress * 3 * math.pi)),
                           int(128 + 100 * math.sin(progress * 4 * math.pi))))
        x = (width - new_width) // 2
        y = (height - new_height) // 2
        if 0 <= x < width and 0 <= y < height:
            result.paste(scaled, (x, y))
        return result

    def fast_rotation_effect(self, image: Image.Image, frame: int, total_frames: int) -> Image.Image:
        progress = frame / total_frames
        angle = 15 * math.sin(progress * 4 * math.pi)
        return image.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)

    def fast_morph_effect(self, image: Image.Image, frame: int, total_frames: int) -> Image.Image:
        progress = frame / total_frames
        width, height = image.size
        result = image.copy()
        for y in range(0, height, 2):
            wave_x = int(10 * math.sin(progress * 6 * math.pi + y / 25))
            for x in range(0, width, 2):
                source_x = (x + wave_x) % width
                pixel = self.safe_get_pixel(image, source_x, y)
                result.putpixel((x, y), pixel)
        return result

    def cinematic_color_grade(self, image: Image.Image) -> Image.Image:
        tint = Image.new('RGB', image.size, (25, 20, 15))
        result = Image.blend(image, tint, 0.1)
        enhancer = ImageEnhance.Contrast(result)
        return enhancer.enhance(1.2)

    def artistic_color_enhance(self, image: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Color(image)
        result = enhancer.enhance(1.3)
        enhancer = ImageEnhance.Sharpness(result)
        return enhancer.enhance(1.1)

    def minimalist_simplify(self, image: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Color(image)
        result = enhancer.enhance(0.8)
        result = result.filter(ImageFilter.SMOOTH_MORE)
        return result

    def create_cinematic_gif(self, image: Image.Image) -> io.BytesIO:
        total_frames = self.optimization_settings['frame_count']
        frames = []
        base_image = self.cinematic_color_grade(image)
        for frame in range(total_frames):
            current_frame = base_image.copy()
            current_frame = self.fast_color_effect(current_frame, frame, total_frames)
            if frame % 3 == 0:
                current_frame = self.fast_wave_effect(current_frame, frame, total_frames)
            if frame % 4 == 0:
                current_frame = self.fast_zoom_effect(current_frame, frame, total_frames)
            if frame % 8 == 0:
                vintage = Image.new('RGB', image.size, (20, 15, 10))
                current_frame = Image.blend(current_frame, vintage, 0.05)
            frames.append(current_frame)
        return self._save_optimized_gif(frames)

    def create_artistic_gif(self, image: Image.Image) -> io.BytesIO:
        total_frames = self.optimization_settings['frame_count']
        frames = []
        base_image = self.artistic_color_enhance(image)
        for frame in range(total_frames):
            current_frame = base_image.copy()
            current_frame = self.fast_color_effect(current_frame, frame, total_frames)
            if frame % 2 == 0:
                current_frame = self.fast_morph_effect(current_frame, frame, total_frames)
            if frame % 3 == 0:
                current_frame = self.fast_rotation_effect(current_frame, frame, total_frames)
            if frame % 6 == 0:
                artistic_color = (
                    random.randint(100, 200),
                    random.randint(100, 200), 
                    random.randint(100, 200)
                )
                tint = Image.new('RGB', image.size, artistic_color)
                current_frame = Image.blend(current_frame, tint, 0.08)
            frames.append(current_frame)
        return self._save_optimized_gif(frames)

    def create_minimalist_gif(self, image: Image.Image) -> io.BytesIO:
        total_frames = self.optimization_settings['frame_count']
        frames = []
        base_image = self.minimalist_simplify(image)
        for frame in range(total_frames):
            current_frame = base_image.copy()
            if frame % 5 == 0:
                current_frame = self.fast_color_effect(current_frame, frame, total_frames)
            if frame % 8 == 0:
                current_frame = self.fast_zoom_effect(current_frame, frame, total_frames)
            if frame % 12 == 0:
                soft_tint = Image.new('RGB', image.size, (240, 240, 235))
                current_frame = Image.blend(current_frame, soft_tint, 0.03)
            frames.append(current_frame)
        return self._save_optimized_gif(frames)

    def _save_optimized_gif(self, frames: list) -> io.BytesIO:
        gif_bytes = io.BytesIO()
        frames[0].save(
            gif_bytes,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=50,
            loop=0,
            optimize=True,
            quality=80
        )
        gif_bytes.seek(0)
        return gif_bytes

    async def start_handler(self, message: types.Message):
        await message.answer(
            "Умный GIF Creator с AI-подбором стиля!\n\n"
            "Отправь фото - я проанализирую его и подберу идеальный стиль анимации!\n\n"
            "Автоматический анализ:\n"
            "• Кинематографический - для контрастных и темных фото\n"
            "• Художественный - для ярких и цветных фото\n"  
            "• Минималистичный - для светлых и нежных фото\n\n"
            "64 кадра • Интеллектуальный подбор • Быстрая обработка"
        )

    async def photo_to_gif_handler(self, message: types.Message):
        if not self.is_running:
            await message.answer("Бот завершает работу. Попробуйте позже.")
            return
        user = message.from_user
        if not user:
            await message.answer("Не удалось получить информацию о пользователе")
            return
        user_id = user.id
        request_id = f"REQ_{int(time.time())}_{random.randint(1000, 9999)}"
        self.session_stats['total_requests'] += 1
        print(f"Запрос {request_id} от пользователя {user_id}")
        processing_msg = await message.answer(
            f"Анализирую изображение...\n"
            f"{request_id}\n"
            f"Подбираю идеальный стиль..."
        )
        try:
            async with asyncio.timeout(45):
                photo_list = message.photo
                if not photo_list:
                    await message.answer("Не удалось получить фото")
                    self.session_stats['failed_gifs'] += 1
                    return
                photo = photo_list[-1]
                start_time = time.time()
                image = await self.download_and_optimize_photo(photo.file_id)
                if not image:
                    await message.answer("Ошибка загрузки фото")
                    self.session_stats['failed_gifs'] += 1
                    return
                download_time = time.time() - start_time
                formatted_download_time = self.format_processing_time(download_time)
                print(f"Фото загружено за {formatted_download_time}")
                await processing_msg.edit_text("Анализирую цвета и контраст...")
                selected_style = self.analyze_image_style(image)
                style_mapping = {
                    "cinematic": (self.create_cinematic_gif, "Кинематографический"),
                    "artistic": (self.create_artistic_gif, "Художественный"),
                    "minimalist": (self.create_minimalist_gif, "Минималистичный")
                }
                gif_creator, style_name = style_mapping[selected_style]
                style_reasons = {
                    "cinematic": "ваше фото имеет высокий контраст и насыщенные цвета, идеально для кинематографического стиля",
                    "artistic": "яркая цветовая гамма вашего фото отлично подходит для художественной обработки", 
                    "minimalist": "нежные тона и мягкий контраст вашего фото идеальны для минималистичного стиля"
                }
                reason = style_reasons[selected_style]
                await processing_msg.edit_text(
                    f"Стиль подобран: {style_name}\n"
                    f"Создаю 64 кадра...\n"
                    f"{reason}"
                )
                start_process_time = time.time()
                gif_bytes = await asyncio.get_event_loop().run_in_executor(
                    None, gif_creator, image
                )
                process_time = time.time() - start_process_time
                formatted_process_time = self.format_processing_time(process_time)
                print(f"GIF создан за {formatted_process_time}")
                await processing_msg.edit_text("Отправляю результат...")
                file_size = len(gif_bytes.getvalue()) / 1024
                await message.answer_animation(
                    types.BufferedInputFile(
                        gif_bytes.getvalue(),
                        filename=f"smart_{request_id}.gif"
                    ),
                    caption=(
                        f"Умная GIF-анимация готова!\n"
                        f"Стиль: {style_name}\n"
                        f"Кадры: 64 | Размер: {file_size:.1f}KB\n"
                        f"Обработка: {formatted_process_time}\n"
                        f"{reason}\n"
                        f"{request_id}"
                    )
                )
                await processing_msg.delete()
                self.session_stats['successful_gifs'] += 1
                print(f"Успешно создан GIF в стиле {style_name} для {request_id}")

        except asyncio.TimeoutError:
            await message.answer("Время обработки истекло. Попробуйте с меньшим изображением.")
            self.session_stats['failed_gifs'] += 1
            print(f"Таймаут для запроса {request_id}")
        except Exception as e:
            await message.answer("Ошибка при создании GIF")
            self.session_stats['failed_gifs'] += 1
            print(f"Ошибка для {request_id}: {e}")
            try:
                await processing_msg.delete()
            except:
                pass

    async def shutdown(self):
        print("\nЗавершение работы бота...")
        self.is_running = False
        await self.bot.session.close()
        uptime = datetime.now() - self.session_stats['start_time']
        hours, remainder = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"Итоги работы сессии:")
        print(f"   Время работы: {int(hours)}ч {int(minutes)}м {int(seconds)}с")
        print(f"   Всего запросов: {self.session_stats['total_requests']}")
        print(f"   Успешных GIF: {self.session_stats['successful_gifs']}")
        print(f"   Ошибок: {self.session_stats['failed_gifs']}")
        print("Бот завершил работу")

