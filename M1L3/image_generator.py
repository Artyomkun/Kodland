from typing import Any, Dict, List, TypedDict, Optional, cast, TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import numpy as np
import traceback
import requests
import warnings
import time
import io
import os
import gc

if TYPE_CHECKING:
    from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
    from diffusers.models.unets.unet_2d_condition import UNet2DConditionModel
    from diffusers.models.autoencoders.autoencoder_kl import AutoencoderKL
    from diffusers.schedulers.scheduling_pndm import PNDMScheduler
    from transformers import CLIPTextModel, CLIPTokenizer

torch: Optional[Any] = None
StableDiffusionPipeline: Any = None
UNet2DConditionModel: Any = None
AutoencoderKL: Any = None
PNDMScheduler: Any = None
CLIPTextModel: Any = None
CLIPTokenizer: Any = None

diffusers_available = False
diffusers_error = ""

try:
    import torch
    from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
    from diffusers.models.unets.unet_2d_condition import UNet2DConditionModel
    from diffusers.models.autoencoders.autoencoder_kl import AutoencoderKL
    from diffusers.schedulers.scheduling_pndm import PNDMScheduler
    from transformers import CLIPTextModel, CLIPTokenizer
    diffusers_available = True
    diffusers_error = ""
except Exception as e:
    diffusers_available = False
    diffusers_error = str(e)

class LoraConfig(TypedDict):
    url: str
    trigger_word: str
    weight: float

class ImageGenerator:
    def __init__(self):
        self.device = "cuda" if diffusers_available and torch is not None and torch.cuda.is_available() else "cpu"
        self.models_cache_dir = "D:/huggingface_cache"
        os.makedirs(self.models_cache_dir, exist_ok=True)
        self.output_dir = "generated_images"
        os.makedirs(self.output_dir, exist_ok=True)
        self.loras_dir = "D:/lora_models"
        os.makedirs(self.loras_dir, exist_ok=True)
        self.lora_adapters: Dict[str, Any] = {}
        self.pipeline: Optional[Any] = None
        self.current_model_id = None
        self.torch_available = diffusers_available
        self.hf_token: Optional[str] = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

        if self.hf_token:
            self.log_message("🔑 HF token найден, будет использоваться для загрузки моделей")
            os.environ["HUGGINGFACE_TOKEN"] = self.hf_token
        else:
            self.log_message("⚠️ HF token отсутствует — загрузка моделей будет анонимной")

        os.environ.setdefault("HF_HOME", self.models_cache_dir)
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

        models_to_try = [
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/sd-turbo",
            "bguisard/stable-diffusion-nano-2-1",
        ]

        self.model_params: Dict[str, Dict[str, Any]] = {
            "runwayml/stable-diffusion-v1-5": {
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512,
            },
            "stabilityai/sd-turbo": {
                "num_inference_steps": 4,
                "guidance_scale": 0.0,
                "width": 512,
                "height": 512,
            },
            "bguisard/stable-diffusion-nano-2-1": {
                "num_inference_steps": 20,
                "guidance_scale": 7.0,
                "width": 512,
                "height": 512,
            }
        }

        self.high_quality_params: Dict[str, Any] = {
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
            "output_type": "pil"
        }

        self.standard_params: Dict[str, Any] = {
            "num_inference_steps": 20,
            "guidance_scale": 7.0,
            "width": 512,
            "height": 512,
            "output_type": "pil"
        }

        self.lora_configs: Dict[str, Dict[str, Any]] = {
            "anime": {
                "url": "https://huggingface.co/Linaqruf/pastel-anime-xl-lora/resolve/main/pastel-anime-xl-latest.safetensors",
                "trigger_word": "anime style",
                "weight": 0.8
            },
            "pixel_art": {
                "url": "https://huggingface.co/nerijs/pixel-art-xl/resolve/main/pixel-art-xl.safetensors",
                "trigger_word": "pixel art",
                "weight": 0.9
            },
            "realistic": {
                "url": "https://huggingface.co/bdsqlsz/SDXL-Consists-Model-Lora-Collection/resolve/main/sdxl-flash-lora_rank1.safetensors",
                "trigger_word": "photorealistic, detailed, sharp focus",
                "weight": 0.8
            }
        }

        self.current_model_id = None
        if diffusers_available:
            self._load_base_model_safe(models_to_try)
            self._load_lora_adapters()
        else:
            self.log_message(f"⚠️ Diffusers/Torch unavailable: {diffusers_error}")
            self.log_message("💡 Будет использоваться упрощённая генерация без модели")

    def _cache_model_parts(self, model_id: str) -> None:
        """Кеширует компоненты модели локально."""
        self.log_message(f"📦 Кеширование модели: {model_id}")
        if not diffusers_available:
            self.log_message("⚠️ Отмена кеширования: diffusers недоступен")
            return
        assert torch is not None
        try:
            model_dtype = torch.float16 if self.device == "cuda" else torch.float32
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="The `local_dir_use_symlinks` argument is deprecated and ignored in `hf_hub_download`.*",
                    category=UserWarning,
                )
                self._load_component(CLIPTokenizer, model_id, subfolder="tokenizer")
                self._load_component(CLIPTextModel, model_id, subfolder="text_encoder", torch_dtype=model_dtype, low_cpu_mem_usage=True)
                self._load_component(AutoencoderKL, model_id, subfolder="vae", torch_dtype=model_dtype, low_cpu_mem_usage=True)
                self._load_component(UNet2DConditionModel, model_id, subfolder="unet", torch_dtype=model_dtype, low_cpu_mem_usage=True)

            scheduler_loaded = False
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="The `local_dir_use_symlinks` argument is deprecated and ignored in `hf_hub_download`.*",
                        category=UserWarning,
                    )
                    if PNDMScheduler is not None:
                        getattr(PNDMScheduler, "from_pretrained")(model_id, subfolder="scheduler", low_cpu_mem_usage=True)
                        scheduler_loaded = True
            except Exception as scheduler_error:
                self.log_message(f"⚠️ Scheduler не загрузился для {model_id}: {scheduler_error}")

            if scheduler_loaded:
                self.log_message(f"✅ Кеширование завершено: {model_id}")
            else:
                self.log_message(f"✅ Кеширование основных весов завершено: {model_id} (scheduler пропущен)")
            
        except Exception as e:
            self.log_message(f"⚠️ Не удалось закешировать {model_id}: {e}")
            self.log_message(f"🔍 Трассировка: {traceback.format_exc()}")
        finally:
            gc.collect()

    def _get_hf_auth_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.hf_token:
            kwargs["use_auth_token"] = self.hf_token
        return kwargs

    def _load_component(self, component_cls: Any, model_id: str, **kwargs: Any) -> Any:
        kwargs = {**kwargs, **self._get_hf_auth_kwargs()}
        try:
            return getattr(component_cls, "from_pretrained")(model_id, **kwargs)
        except Exception as first_error:
            message = str(first_error)
            if any(marker in message for marker in ("client has been closed", "getaddrinfo failed", "Connection refused", "Name or service not known")):
                self.log_message(f"⚠️ Сетевая ошибка при загрузке {model_id}: {message}")
                self.log_message("ℹ️ Пробую загрузить компонент из локального кеша")
                kwargs["local_files_only"] = True
                kwargs.pop("use_auth_token", None)
                return getattr(component_cls, "from_pretrained")(model_id, **kwargs)
            raise

    def _cache_remaining_model_candidates(self, candidates: List[str], active_model_id: str) -> None:
        self.log_message(f"ℹ️ Начинаю кеширование остальных моделей-кандидатов после выбора {active_model_id}")
        for model_id in candidates:
            if model_id == active_model_id:
                continue
            try:
                self._cache_model_parts(model_id)
            except Exception:
                self.log_message(f"⚠️ Пропускаю кеширование {model_id} после ошибки")

    def _load_base_model_safe(self, models_to_try: List[str]) -> None:
        if not diffusers_available:
            return
        assert torch is not None, "PyTorch недоступен"
        for model_id in models_to_try:
            try:
                self.log_message(f"🔄 Пробуем загрузить по частям: {model_id}")
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="The `local_dir_use_symlinks` argument is deprecated and ignored in `hf_hub_download`.*",
                        category=UserWarning,
                    )
                    tokenizer: Any = self._load_component(CLIPTokenizer, model_id, subfolder="tokenizer", local_files_only=True)
                    text_encoder: Any = self._load_component(CLIPTextModel, model_id, subfolder="text_encoder", torch_dtype=torch.float32, local_files_only=True)
                    vae: Any = self._load_component(AutoencoderKL, model_id, subfolder="vae", torch_dtype=torch.float32, local_files_only=True)
                    unet: Any = self._load_component(UNet2DConditionModel, model_id, subfolder="unet", torch_dtype=torch.float32, local_files_only=True)
                    if PNDMScheduler is None:
                        raise RuntimeError("Scheduler unavailable")
                    scheduler: Any = self._load_component(PNDMScheduler, model_id, subfolder="scheduler", local_files_only=True)
                self.pipeline = StableDiffusionPipeline(
                    vae=vae,
                    text_encoder=text_encoder,
                    tokenizer=tokenizer,
                    unet=unet,
                    scheduler=scheduler,
                    safety_checker=None,
                    feature_extractor=None,
                    requires_safety_checker=False,
                )

                assert self.pipeline is not None, "Не удалось создать пайплайн"

                if self.device == "cuda":
                    self.pipeline.enable_model_cpu_offload()
                    if hasattr(self.pipeline, "vae") and hasattr(self.pipeline.vae, "enable_slicing"):
                        self.pipeline.vae.enable_slicing()
                    else:
                        self.pipeline.enable_vae_slicing()
                    self.pipeline.enable_attention_slicing()
                    self.log_message("✅ CPU Offload + VAE Slicing включены")
                
                self.current_model_id = model_id
                self.log_message(f"✅ Успешно загружена по частям: {model_id}")
                self.log_message("ℹ️ Пропускаем кеширование остальных моделей — это снижает расход памяти и предотвращает MemoryError")
                return
                
            except Exception as e:
                self.log_message(f"❌ Не удалось загрузить {model_id}: {e}")
                self.log_message(f"🔍 Трассировка: {traceback.format_exc()}")
                if self.pipeline is not None:
                    self.pipeline = None
                if hasattr(torch, "cuda"):
                    torch.cuda.empty_cache()
        
        self.log_message("⚠️ Не удалось загрузить ни одну модель!")

    def _load_lora_adapters(self):
        if self.pipeline is None:
            self.log_message("⚠️ Пропускаем загрузку LoRA: базовая модель не загружена")
            return

        loaded: List[str] = []
        missing: List[str] = []
        for lora_name, config in self.lora_configs.items():
            try:
                lora_path = self._download_lora(config["url"], lora_name)
                if lora_path and os.path.exists(lora_path):
                    self.log_message(f"📁 LoRA файл найден: {lora_path}")
                    self.lora_adapters[lora_name] = {
                        "url": config["url"],
                        "trigger_word": config["trigger_word"],
                        "weight": config["weight"],
                    }
                    loaded.append(lora_name)
                    self.log_message(f"✅ LoRA {lora_name} загружен (конфиг сохранен)")
                else:
                    missing.append(lora_name)
                    self.log_message(f"⚠️ LoRA файл не найден: {lora_name}")
            except Exception as e:
                missing.append(lora_name)
                self.log_message(f"❌ Ошибка загрузки LoRA {lora_name}: {e}")

        existing_files = [f for f in os.listdir(self.loras_dir) if f.lower().endswith('.safetensors')]
        self.log_message(f"ℹ️ Содержимое папки LoRA ({self.loras_dir}): {', '.join(existing_files) if existing_files else 'пусто'}")
        if loaded:
            self.log_message(f"✅ Загруженные LoRA: {', '.join(sorted(loaded))}")
        if missing:
            self.log_message(f"⚠️ Не найдены/не загружены LoRA: {', '.join(sorted(missing))}")

    def _download_lora(self, url: str, lora_name: str) -> str:
        """Скачивание LoRA файла"""
        try:
            local_path = os.path.join(self.loras_dir, f"{lora_name}.safetensors")
            self.log_message(f"🔧 Проверка LoRA для '{lora_name}' в {local_path}")
            
            if not os.path.exists(local_path):
                self.log_message(f"📥 Скачиваю LoRA: {lora_name}")
                self.log_message(f"📁 Сохраняю в: {local_path}")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                self.log_message(f"✅ LoRA сохранен: {local_path}")
            else:
                self.log_message(f"📁 LoRA уже существует: {local_path}")
            
            return local_path
        except Exception as e:
            self.log_message(f"❌ Ошибка скачивания LoRA: {e}")
            raise

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
            
            negative_prompt = (
                "blurry, low quality, worst quality, jpeg artifacts, "
                "deformed, malformed, mutated, disfigured, bad anatomy, "
                "watermark, signature, text, username, cartoon, anime"
            )

            self.log_message(f"🎨 Генерация HQ: {enhanced_prompt}")
            
            raw_params = self.model_params.get(str(self.current_model_id), self.high_quality_params)
            assert torch is not None

            with torch.no_grad():
                result = self.pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt if "turbo" not in str(self.current_model_id).lower() else None,
                    output_type="pil",
                    height=int(raw_params.get("height", 512)),
                    width=int(raw_params.get("width", 512)),
                    num_inference_steps=int(raw_params.get("num_inference_steps", 25)),
                    guidance_scale=float(raw_params.get("guidance_scale", 7.5)),
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
            return self._create_error_image(f"Генерация не удалась: {str(e)[:100]}")

    def auto_generate(self, prompt: str, user_id: str, save_to_disk: bool = True) -> io.BytesIO:
        """Всегда использует режим максимального качества"""
        prompt_lower = prompt.lower()
        
        if self.pipeline:
            self.log_message("🎯 Приоритет: КАЧЕСТВО (режим HQ)")
            return self.generate_high_quality(prompt, user_id, save_to_disk)
        
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

            raw_params = self.model_params.get(str(self.current_model_id), self.standard_params)
            assert torch is not None

            with torch.no_grad():
                result = self.pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt if "turbo" not in str(self.current_model_id).lower() else None,
                    output_type="pil",
                    height=int(raw_params.get("height", 512)),
                    width=int(raw_params.get("width", 512)),
                    num_inference_steps=int(raw_params.get("num_inference_steps", 20)),
                    guidance_scale=float(raw_params.get("guidance_scale", 7.0)),
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
            self.log_message(f"🔍 Детали: {traceback.format_exc()}")
            return self.auto_generate(prompt, user_id, save_to_disk)

    def generate_with_lora(self, prompt: str, user_id: str, lora_style: str, save_to_disk: bool = True) -> io.BytesIO:
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
            
            raw_params = self.model_params.get(str(self.current_model_id), self.standard_params)
            assert torch is not None

            with torch.no_grad():
                cross_attention_kwargs = None
                if lora_style and lora_style in self.lora_adapters:
                    cross_attention_kwargs = {"scale": lora_weight}
                
                result = self.pipeline(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt if "turbo" not in str(self.current_model_id).lower() else None,
                    output_type="pil",
                    height=int(raw_params.get("height", 512)),
                    width=int(raw_params.get("width", 512)),
                    num_inference_steps=int(raw_params.get("num_inference_steps", 20)),
                    guidance_scale=float(raw_params.get("guidance_scale", 7.0)),
                    cross_attention_kwargs=cross_attention_kwargs,
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
            self.log_message(f"🔍 Детали ошибки: {traceback.format_exc()}")
            return self.auto_generate(prompt, user_id, save_to_disk)

    def _auto_detect_lora_style(self, prompt: str) -> str:
        """Автоматическое определение подходящего LoRA стиля"""
        prompt_lower = prompt.lower()
        
        style_mappings = {
            "anime": ["anime", "manga", "японск", "аниме"],
            "pixel_art": ["pixel", "пиксель", "8bit", "16bit", "ретро игр"],
            "realistic": ["реалистич", "realistic", "фото", "photo"]
        }
        
        for lora_name, keywords in style_mappings.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return lora_name
        raise

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

    def _generate_styled_image(self, prompt: str, user_id: str, style: str, color: tuple[int, int, int], save_to_disk: bool = True) -> io.BytesIO:
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

    def _generate_styled_image_hq(self, prompt: str, user_id: str, style: str, color: tuple[int, int, int], save_to_disk: bool = True) -> io.BytesIO:
        """Улучшенная генерация стилизованных изображений с высоким качеством"""
        try:
            img = Image.new('RGB', (1024, 1024), color=color)
            draw = ImageDraw.Draw(img)
            
            for i in range(1024):
                r = min(255, color[0] + int((i / 1024) * 100))
                g = min(255, color[1] + int((i / 1024) * 80))
                b = min(255, color[2] + int((i / 1024) * 60))
                draw.line([(0, i), (1024, i)], fill=(r, g, b))
            
            try:
                font_large = ImageFont.truetype("arial.ttf", 42) if os.path.exists("arial.ttf") else None
                font_medium = ImageFont.truetype("arial.ttf", 28) if os.path.exists("arial.ttf") else None
                font_small = ImageFont.truetype("arial.ttf", 20) if os.path.exists("arial.ttf") else None
            except:
                font_large = font_medium = font_small = None
            
            text_elements = [
                (f"🎨 {prompt}", (80, 300), (255, 255, 255), font_large),
                (f"✨ {style} • ВЫСОКОЕ КАЧЕСТВО", (80, 360), (255, 255, 0), font_medium),
                (f"👤 ID: {user_id}", (80, 410), (200, 200, 255), font_small),
                (f"🔄 AI Генерация Premium", (80, 450), (200, 255, 200), font_small),
                (f"🕒 {datetime.now().strftime('%H:%M:%S')}", (80, 490), (255, 200, 200), font_small)
            ]
            
            for text, position, color_text, font in text_elements:
                if font:
                    draw.text(position, text, fill=color_text, font=font)
                else:
                    draw.text(position, text, fill=color_text)
            
            draw.rectangle([30, 30, 994, 994], outline=(255, 255, 255), width=4)
            draw.rectangle([60, 60, 964, 964], outline=(255, 255, 255), width=2)
            
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

    def _safe_extract_image(self, result: Any) -> Image.Image:
        """Безопасное извлечение и конвертация изображения в PIL"""
        try:
            if hasattr(result, 'images') and result.images:
                raw = result.images[0]
            elif isinstance(result, (list, tuple)) and result:
                raw: Any = cast(Any, result[0])
            else:
                raise ValueError("Не удалось извлечь изображение из результата")
            
            if isinstance(raw, Image.Image):
                return raw
            
            return self._convert_to_pil(raw)
            
        except Exception as e:
            self.log_message(f"❌ Ошибка при извлечении изображения: {e}")
            raise

    def _convert_to_pil(self, image_data: Any) -> Image.Image:
        """Конвертирует различные форматы изображений в PIL Image"""
        if isinstance(image_data, Image.Image):
            return image_data
        
        elif diffusers_available and torch is not None and isinstance(image_data, torch.Tensor):
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
            ndarray_image = cast(np.ndarray, image_data)
            if ndarray_image.dtype in [np.float32, np.float64]:
                ndarray_image = (ndarray_image * 255).astype(np.uint8)
            return Image.fromarray(ndarray_image)
        
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

    def log_message(self, text: str) -> None:
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

    def log_message(self, text: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - LIGHT_GENERATOR - {text}"
        print(message)