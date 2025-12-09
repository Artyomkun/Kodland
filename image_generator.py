from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import numpy as np
import requests
import torch
import time
import io
import os

class ImageGenerator:
    def __init__(self):
        self.output_dir = "generated_images"
        os.makedirs(self.output_dir, exist_ok=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self.lora_adapters = {}
        self.models_cache_dir = "D:/huggingface_cache"
        self.loras_dir = "D:/lora_models"
        os.makedirs(self.models_cache_dir, exist_ok=True)
        os.makedirs(self.loras_dir, exist_ok=True)

        # Модели для загрузки по приоритету
        models_to_try = [
            "bguisard/stable-diffusion-nano-2-1",
            "alvarobaron/dog-sd-xl",
            "black-forest-labs/FLUX.1-schnell",
            "sd_xl_base_1.0.safetensors"
        ]

        self.high_quality_params = {
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
            "output_type": "pil"
        }

        self.standard_params = {
            "num_inference_steps": 20,
            "guidance_scale": 7.0,
            "width": 512,
            "height": 512,
            "output_type": "pil"
        }


        self.lora_configs = {
            "anime": {
                "url": "https://huggingface.co/Linaqruf/pastel-anime-xl-lora/blob/main/pastel-anime-xl-latest.safetensors",
                "trigger_word": "anime style",
                "weight": 0.8
            },
            "pixel_art": {
                "url": "https://huggingface.co/nerijs/pixel-art-xl/resolve/main/pixel-art-xl.safetensors",
                "trigger_word": "pixel art",
                "weight": 0.9
            },
            "watercolor": {
                "url": "https://huggingface.co/bguisard/stable-diffusion-nano-2-1",
                "trigger_word": "watercolor painting",
                "weight": 0.7
            },
            "realistic": {
                "url": "https://huggingface.co/DervlexVenice/sdxl_offset_example_lora-sdxl/blob/main/SDXL_Offset_Example_Lora_137511.safetensors",
                "trigger_word": "photorealistic",
                "weight": 0.8
            }
        }
        # Безопасная загрузка модели
        self._load_base_model_safe(models_to_try)
        self._load_lora_adapters()


    def _load_base_model_safe(self, models_to_try):
        if self.device == "cuda":
            torch.cuda.empty_cache()

        for model_id in models_to_try:
            try:
                self.log_message(f"🔄 Пробуем загрузить: {model_id}")
                self.log_message(f"📁 Кэш моделей: {self.models_cache_dir}")

                self.pipeline = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    cache_dir=self.models_cache_dir,
                    safety_checker=None,
                    requires_safety_checker=False,
                    low_cpu_mem_usage=True, 
                    local_files_only=True
                ).to(torch.float16 if self.device == "cuda" else torch.float32).to(self.device)

                self.log_message(f"✅ Успешно загружена: {model_id}")
                return
            except Exception as e:
                self.log_message(f"❌ Не удалось загрузить: {model_id} - {e}")
        self.log_message("⚠️ Не удалось загрузить ни одну модель!")

    def _load_lora_adapters(self):
        if self.pipeline is None:
            self.log_message("⚠️ Пропускаем загрузку LoRA: базовая модель не загружена")
            return

        for lora_name, config in self.lora_configs.items():
            try:
                lora_path = self._download_lora(config["url"], lora_name)
                if lora_path and os.path.exists(lora_path):
                    self.log_message(f"📁 LoRA файл найден: {lora_path}")
                    self.lora_adapters[lora_name] = config
                    self.log_message(f"✅ LoRA {lora_name} загружен (конфиг сохранен)")
                else:
                    self.log_message(f"⚠️ LoRA файл не найден: {lora_name}")
            except Exception as e:
                self.log_message(f"❌ Ошибка загрузки LoRA {lora_name}: {e}")

    def _download_lora(self, url, lora_name):
        """Скачивание LoRA файла"""
        try:
            local_path = os.path.join(self.loras_dir, f"{lora_name}.safetensors")
            
            if not os.path.exists(local_path):
                self.log_message(f"📥 Скачиваю LoRA: {lora_name}")
                self.log_message(f"📁 Сохраняю в: {local_path}")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.log_message(f"✅ LoRA сохранен: {local_path}")
            else:
                self.log_message(f"📁 LoRA уже существует: {local_path}")
            
            return local_path
        except Exception as e:
            self.log_message(f"❌ Ошибка скачивания LoRA: {e}")
            return None

    def _enhance_prompt_for_quality(self, prompt: str) -> str:
        """Усиление промпта для максимального качества"""
        quality_enhancers = [
            "masterpiece, best quality, ultra detailed, 8K",
            "sharp focus, professional photography",
            "intricate details, highly detailed",
            "cinematic lighting, perfect composition"
        ]
        
        return f"{prompt}, {', '.join(quality_enhancers)}"

    def _enhance_prompt(self, prompt: str) -> str:
        """Улучшает промпт для точной генерации животных"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['кот', 'кошка', 'кошк', 'cat']):
            return ("a cute domestic cat, feline, whiskers, cat eyes, cat nose, "
                    "fur, pet cat, sitting, realistic photo, high quality, "
                    "detailed fur, beautiful cat face")
        
        elif any(word in prompt_lower for word in ['собак', 'пёс', 'dog']):
            return ("a cute domestic dog, canine, dog eyes, dog nose, "
                    "fur, pet dog, sitting, realistic photo, high quality, "
                    "detailed fur, friendly dog face")
        
        elif any(word in prompt_lower for word in ['белк', 'squirrel']):
            return ("a cute squirrel, rodent, bushy tail, small animal, "
                    "realistic photo, high quality, detailed fur")
        
        else:
            return f"{prompt}, realistic, high quality, detailed"

    def generate_high_quality(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        """Генерация с акцентом на максимальное качество"""
        if not self.pipeline:
            return self.auto_generate(prompt, user_id, save_to_disk)
        
        try:
            enhanced_prompt = self._enhance_prompt_for_quality(prompt)
            
            # Усиленный негативный промпт для избежания артефактов
            negative_prompt = (
                "blurry, low quality, worst quality, jpeg artifacts, "
                "deformed, malformed, mutated, disfigured, bad anatomy, "
                "watermark, signature, text, username, cartoon, anime"
            )

            self.log_message(f"🎨 Генерация HQ: {enhanced_prompt}")
            
            with torch.no_grad():
                result = self.pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt,
                    **self.high_quality_params
                )
                
                image = self._safe_extract_image(result)
            
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG', quality=100)
            img_bytes.seek(0)
            
            if save_to_disk:
                filename = f"hq_{user_id}_{datetime.now().strftime('%H%M%S')}.png"
                filepath = os.path.join(self.output_dir, filename)
                image.save(filepath, format='PNG', quality=100)
                self.log_message(f"💾 HQ изображение сохранено: {filepath}")
            
            self.log_message("✅ Изображение премиум-качества создано!")
            return img_bytes
            
        except Exception as e:
            self.log_message(f"❌ Ошибка HQ генерации: {e}")
            return self.generate_with_ai(prompt, user_id, save_to_disk)

    def auto_generate(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        """Всегда использует режим максимального качества"""
        prompt_lower = prompt.lower()
        
        if self.pipeline:
            self.log_message("🎯 Приоритет: КАЧЕСТВО (режим HQ)")
            return self.generate_high_quality(prompt, user_id, save_to_disk)
        
        # Если модель не загрузилась - простая генерация с улучшенным качеством
        self.log_message("🎨 Используется простая генерация с улучшенным качеством")
        
        if any(word in prompt_lower for word in ['лого', 'логотип', 'бренд', 'brand', 'logo']):
            return self.generate_logo_hq(prompt, user_id, save_to_disk)
        elif any(word in prompt_lower for word in ['иконк', 'icon', 'app', 'приложен']):
            return self.generate_icon_hq(prompt, user_id, save_to_disk)
        elif any(word in prompt_lower for word in ['персонаж', 'character', 'герой', 'человек', 'лицо']):
            return self.generate_character_hq(prompt, user_id, save_to_disk)
        elif any(word in prompt_lower for word in ['архитектур', 'здан', 'building', 'дом', 'арх']):
            return self.generate_architecture_hq(prompt, user_id, save_to_disk)
        elif any(word in prompt_lower for word in ['интерфейс', 'ui', 'ux', 'скрин', 'экран', 'app']):
            return self.generate_ui_screen_hq(prompt, user_id, save_to_disk)
        elif any(word in prompt_lower for word in ['обложк', 'cover', 'album', 'дизайн']):
            return self.generate_cover_hq(prompt, user_id, save_to_disk)
        else:
            return self.generate_abstract_art_hq(prompt, user_id, save_to_disk)

    def generate_with_ai(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        """Стандартная AI генерация"""
        if not self.pipeline:
            return self.auto_generate(prompt, user_id, save_to_disk)
        
        try:
            enhanced_prompt = self._enhance_prompt(prompt)
            self.log_message(f"🤖 AI генерация: {enhanced_prompt}")
            
            negative_prompt = (
                "squirrel, rodent, rabbit, bear, monkey, deformed, ugly, "
                "bad anatomy, disfigured, poor quality, extra limbs, mutation"
            )

            with torch.no_grad():
                result = self.pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt,
                    **self.standard_params
                )
                
                image = self._safe_extract_image(result)
            
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            if save_to_disk:
                filename = f"ai_{user_id}_{datetime.now().strftime('%H%M%S')}.png"
                filepath = os.path.join(self.output_dir, filename)
                image.save(filepath)
                self.log_message(f"💾 Изображение сохранено: {filepath}")
            
            self.log_message("✅ AI изображение создано!")
            return img_bytes
            
        except Exception as e:
            self.log_message(f"❌ Ошибка AI генерации: {e}")
            import traceback
            self.log_message(f"🔍 Детали: {traceback.format_exc()}")
            return self.auto_generate(prompt, user_id, save_to_disk)

    def generate_with_lora(self, prompt: str, user_id: str, lora_style=None, save_to_disk: bool = True) -> io.BytesIO:
        """Генерация с автоматическим или ручным выбором LoRA"""
        if self.pipeline is None:
            return self.auto_generate(prompt, user_id, save_to_disk)
        
        try:
            if not lora_style:
                lora_style = self._auto_detect_lora_style(prompt)
            
            enhanced_prompt = prompt
            lora_weight = 0.8 
            
            if lora_style and lora_style in self.lora_configs:
                trigger_word = self.lora_configs[lora_style]["trigger_word"]
                enhanced_prompt = f"{prompt}, {trigger_word}"
                lora_weight = self.lora_configs[lora_style]["weight"]
                self.log_message(f"🎨 Применен LoRA стиль: {lora_style} с весом {lora_weight}")
            
            self.log_message(f"🤖 AI генерация с LoRA: {enhanced_prompt}")
            
            negative_prompt = "deformed, ugly, bad anatomy, disfigured, poor quality, extra limbs"
            
            with torch.no_grad():
                cross_attention_kwargs = None
                if lora_style and lora_style in self.lora_adapters:
                    cross_attention_kwargs = {"scale": lora_weight}
                
                result = self.pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=20,
                    guidance_scale=7.5,
                    width=512,
                    height=512,
                    output_type="pil",
                    cross_attention_kwargs=cross_attention_kwargs
                )
                image = self._safe_extract_image(result)
            
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            if save_to_disk:
                style_suffix = f"_{lora_style}" if lora_style else ""
                filename = f"lora{style_suffix}_{user_id}_{datetime.now().strftime('%H%M%S')}.png"
                filepath = os.path.join(self.output_dir, filename)
                image.save(filepath)
                self.log_message(f"💾 Изображение сохранено: {filepath}")
            
            self.log_message("✅ Изображение с LoRA создано!")
            return img_bytes
            
        except Exception as e:
            self.log_message(f"❌ Ошибка генерации с LoRA: {e}")
            import traceback
            self.log_message(f"🔍 Детали ошибки: {traceback.format_exc()}")
            return self.auto_generate(prompt, user_id, save_to_disk)

    def _auto_detect_lora_style(self, prompt):
        """Автоматическое определение подходящего LoRA стиля"""
        prompt_lower = prompt.lower()
        
        style_mappings = {
            "anime": ["anime", "manga", "японск", "аниме"],
            "pixel_art": ["pixel", "пиксель", "8bit", "16bit", "ретро игр"],
            "watercolor": ["акварель", "watercolor", "акварельн"],
            "realistic": ["реалистич", "realistic", "фото", "photo"]
        }
        
        for lora_name, keywords in style_mappings.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return lora_name
        return None

    # HQ методы для простой генерации
    def generate_abstract_art_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "СТАНДАРТ", (100, 150, 200), save_to_disk)
        
    def generate_logo_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "ЛОГОТИП", (255, 100, 100), save_to_disk)

    def generate_icon_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "ИКОНКА", (100, 255, 100), save_to_disk)

    def generate_character_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "ПЕРСОНАЖ", (100, 100, 255), save_to_disk)

    def generate_architecture_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "АРХИТЕКТУРА", (255, 200, 100), save_to_disk)

    def generate_ui_screen_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "UI/UX", (100, 200, 255), save_to_disk)

    def generate_cover_hq(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image_hq(prompt, user_id, "ОБЛОЖКА", (200, 100, 255), save_to_disk)

    # Старые методы для обратной совместимости
    def generate_abstract_art(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "СТАНДАРТ", (100, 150, 200), save_to_disk)
        
    def generate_logo(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "ЛОГОТИП", (255, 100, 100), save_to_disk)

    def generate_icon(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "ИКОНКА", (100, 255, 100), save_to_disk)

    def generate_character(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "ПЕРСОНАЖ", (100, 100, 255), save_to_disk)

    def generate_architecture(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "АРХИТЕКТУРА", (255, 200, 100), save_to_disk)

    def generate_ui_screen(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "UI/UX", (100, 200, 255), save_to_disk)

    def generate_cover(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        return self._generate_styled_image(prompt, user_id, "ОБЛОЖКА", (200, 100, 255), save_to_disk)    

    def _generate_styled_image_hq(self, prompt: str, user_id: str, style: str, color: tuple, save_to_disk: bool = True) -> io.BytesIO:
        """Улучшенная генерация стилизованных изображений с высоким качеством"""
        try:
            # Большое разрешение для качества
            img = Image.new('RGB', (1024, 1024), color=color)
            draw = ImageDraw.Draw(img)
            
            # Детальная градиентная заливка
            for i in range(1024):
                r = min(255, color[0] + int((i / 1024) * 100))
                g = min(255, color[1] + int((i / 1024) * 80))
                b = min(255, color[2] + int((i / 1024) * 60))
                draw.line([(0, i), (1024, i)], fill=(r, g, b))
            
            # Улучшенная типографика
            try:
                font_large = ImageFont.truetype("arial.ttf", 42) if os.path.exists("arial.ttf") else None
                font_medium = ImageFont.truetype("arial.ttf", 28) if os.path.exists("arial.ttf") else None
                font_small = ImageFont.truetype("arial.ttf", 20) if os.path.exists("arial.ttf") else None
            except:
                font_large = font_medium = font_small = None
            
            # Профессиональное текстовое оформление
            text_elements = [
                (f"🎨 {prompt}", (80, 300), (255, 255, 255), font_large),
                (f"✨ {style} • ВЫСОКОЕ КАЧЕСТВО", (80, 360), (255, 255, 0), font_medium),
                (f"👤 ID: {user_id}", (80, 410), (200, 200, 255), font_small),
                (f"🔄 AI Генерация Premium", (80, 450), (200, 255, 200), font_small),
                (f"🕒 {datetime.now().strftime('%H:%M:%S')}", (80, 490), (255, 200, 200), font_small)
            ]
            
            for text, position, color, font in text_elements:
                if font:
                    draw.text(position, text, fill=color, font=font)
                else:
                    draw.text(position, text, fill=color)
            
            # Детальные декоративные элементы
            draw.rectangle([30, 30, 994, 994], outline=(255, 255, 255), width=4)
            draw.rectangle([60, 60, 964, 964], outline=(255, 255, 255), width=2)
            
            # Сложные геометрические элементы
            for i in range(0, 1024, 64):
                draw.ellipse([i, 100, i+20, 120], outline=(255, 255, 255, 128))
                draw.ellipse([i, 700, i+20, 720], outline=(255, 255, 255, 128))
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True, quality=95)
            img_bytes.seek(0)
            
            if save_to_disk:
                filename = f"hq_{style.lower()}_{user_id}_{datetime.now().strftime('%H%M%S')}.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath, format='PNG', optimize=True, quality=95)
                self.log_message(f"💾 HQ изображение сохранено: {filepath}")
            
            self.log_message(f"✅ Создано HQ {style} изображение: {prompt}")
            return img_bytes
            
        except Exception as e:
            self.log_message(f"❌ Ошибка HQ генерации {style}: {e}")
            return self._create_error_image(str(e))

    def _generate_styled_image(self, prompt: str, user_id: str, style: str, color: tuple, save_to_disk: bool = True) -> io.BytesIO:
        """Общая функция для создания стилизованных изображений (старая версия)"""
        try:
            img = Image.new('RGB', (512, 512), color=color)
            draw = ImageDraw.Draw(img)
            
            for i in range(512):
                r = min(255, color[0] + int((i / 512) * 50))
                g = min(255, color[1] + int((i / 512) * 50))
                b = min(255, color[2] + int((i / 512) * 50))
                draw.line([(0, i), (512, i)], fill=(r, g, b))
            
            draw.text((50, 180), f"🎨 {prompt}", fill=(255, 255, 255))
            draw.text((50, 220), f"✨ {style}", fill=(255, 255, 0))
            draw.text((50, 250), f"👤 ID: {user_id}", fill=(200, 200, 255))
            draw.text((50, 280), "🔄 AI Генерация", fill=(200, 255, 200))
            
            draw.rectangle([20, 20, 492, 492], outline=(255, 255, 255), width=3)
            draw.rectangle([40, 40, 472, 472], outline=(255, 255, 255), width=1)
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            if save_to_disk:
                filename = f"{style.lower()}_{user_id}_{datetime.now().strftime('%H%M%S')}.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
                self.log_message(f"Изображение сохранено: {filepath}")
            
            self.log_message(f"✅ Создано {style} изображение: {prompt}")
            return img_bytes
            
        except Exception as e:
            self.log_message(f"Ошибка генерации {style}: {e}")
            return self._create_error_image(str(e))

    def _safe_extract_image(self, result):
        """Безопасное извлечение и конвертация изображения в PIL"""
        try:
            if hasattr(result, 'images') and result.images:
                img = result.images[0]
            elif isinstance(result, (list, tuple)) and result:
                img = result[0]
            else:
                raise ValueError("Не удалось извлечь изображение из результата")
            
            if not isinstance(img, Image.Image):
                img = self._convert_to_pil(img)
            
            return img
            
        except Exception as e:
            self.log_message(f"❌ Ошибка при извлечении изображения: {e}")
            raise

    def _convert_to_pil(self, image_data):
        """Конвертирует различные форматы изображений в PIL Image"""
        if isinstance(image_data, Image.Image):
            return image_data
        
        elif isinstance(image_data, torch.Tensor):
            image_data = image_data.squeeze(0).detach().cpu()
            if image_data.dim() == 3:
                image_data = image_data.permute(1, 2, 0)
            image_np = image_data.numpy()
            
            if image_np.max() <= 1.0:
                image_np = (image_np * 255).astype(np.uint8)
            else:
                image_np = image_np.astype(np.uint8)
                
            return Image.fromarray(image_np)
        
        elif isinstance(image_data, np.ndarray):
            if image_data.dtype in [np.float32, np.float64]:
                image_data = (image_data * 255).astype(np.uint8)
            return Image.fromarray(image_data)
        
        else:
            raise TypeError(f"Неподдерживаемый тип изображения: {type(image_data)}")

    def _create_error_image(self, error_msg: str = ""):
        """Создает изображение с сообщением об ошибке"""
        img = Image.new('RGB', (512, 512), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 502, 502], outline=(255, 0, 0), width=3)
        draw.text((50, 200), "Ошибка генерации", fill=(255, 0, 0))
        if error_msg:
            draw.text((50, 250), error_msg[:50], fill=(255, 0, 0))
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes

    def log_message(self, text):
        """Логирование сообщений"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - IMAGE_GENERATOR - {text}"
        print(message)
        with open('bot.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')

class LightImageGenerator:
    """Облегченная версия - ТОЛЬКО простая генерация"""
    def __init__(self):
        self.output_dir = "generated_images"
        os.makedirs(self.output_dir, exist_ok=True)
        self.log_message("💡 Легкий генератор готов (только простая генерация)")

    def generate_abstract_art(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        """Простая генерация для легкого генератора"""
        try:
            img = Image.new('RGB', (400, 300), color=(70, 130, 180))
            draw = ImageDraw.Draw(img)
            draw.text((50, 120), f"🎨 {prompt}", fill=(255, 255, 255))
            draw.text((50, 150), "💡 Легкая генерация", fill=(255, 255, 0))
            draw.text((50, 180), f"👤 {user_id}", fill=(200, 200, 255))
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            if save_to_disk:
                filename = f"simple_{user_id}_{datetime.now().strftime('%H%M%S')}.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
            
            self.log_message(f"✅ Создано простое изображение: {prompt}")
            return img_bytes
            
        except Exception as e:
            self.log_message(f"Ошибка простой генерации: {e}")
            return self._create_error_image(str(e))

    def _create_error_image(self, error_msg: str = ""):
        img = Image.new('RGB', (400, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 350, 250], outline=(255, 0, 0), width=3)
        draw.text((100, 130), "Ошибка генерации", fill=(255, 0, 0))
        if error_msg:
            draw.text((80, 160), error_msg[:30], fill=(255, 0, 0))
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes

    def log_message(self, text):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - LIGHT_GENERATOR - {text}"
        print(message)