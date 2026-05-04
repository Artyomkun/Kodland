"""Рантайм для проекта Teachable Machine (.tm)."""
from typing import List, Tuple, Any, Optional
from importlib import import_module
from PIL import Image
import numpy as np
import logging
import zipfile
import shutil
import time
import os
import io

logger = logging.getLogger(__name__)

def log_message(text: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - {text}"
    print(message)
    with open('bot.log', 'a', encoding='utf-8') as f:
        f.write(message + '\n')
        
class TeachableMachineRuntime:
    """Загрузчик проектов Teachable Machine."""
    
    def __init__(self, project_path: str = "project2.tm"):
        self.project_path = project_path
        self.extract_dir: str = "ideogram_extracted" 
        self.extract_path = "tm_extracted"
        self.model: Optional[Any] = None
        self.labels: List[str] = []
        self.input_shape: Tuple[int, int] = (224, 224)
        self.is_loaded: bool = False

    def load_project(self) -> bool:
        """Извлекает проект .tm и загружает модель Keras + labels.txt."""
        try:
            if not os.path.exists(self.project_path):
                logger.error(f"Файл проекта не найден: {self.project_path}")
                return False

            if os.path.exists(self.extract_path):
                shutil.rmtree(self.extract_path)
            
            with zipfile.ZipFile(self.project_path, 'r') as zip_ref:
                zip_ref.extractall(self.extract_path)
            logger.info(f"Проект {self.project_path} извлечён в {self.extract_path}")

            labels_file: Optional[str] = None
            for entry in os.walk(self.extract_dir):
                root = entry[0]
                files = entry[2]
                if "labels.txt" in files:
                    labels_file = os.path.join(root, "labels.txt")
                    break

            if labels_file is not None and os.path.exists(str(labels_file)):
                with open(str(labels_file), 'r', encoding='utf-8') as f:
                    file_content: str = f.read()
                    self.labels = [line.strip() for line in file_content.splitlines()]
                log_message(f"Загружено {len(self.labels)} меток")

            model_file = None
            for root, model_file, files in os.walk(self.extract_path):
                for file in files:
                    if file.endswith(('.h5', '.hdf5', '.keras')):
                        model_file = os.path.join(root, file)
                        break
                if model_file:
                    break

            if not model_file:
                saved_model_root = None
                for root, saved_model_root, files in os.walk(self.extract_path):
                    if 'saved_model.pb' in files:
                        saved_model_root = root
                        break
                if saved_model_root:
                    model_file = saved_model_root

            if not model_file:
                extracted_files: List[str] = []
                for root, extracted_files, files in os.walk(self.extract_path):
                    for file in files:
                        extracted_files.append(os.path.relpath(os.path.join(root, file), self.extract_path))
                logger.error(
                    "Модель Keras не найдена в проекте. "
                    f"Папка извлечения: {self.extract_path}. "
                    f"Найдено файлов: {len(extracted_files)}. "
                    f"Примеры: {', '.join(extracted_files[:10])}"
                )
                return False

            try:
                tf: Any = import_module("tensorflow")
            except ImportError:
                logger.error("TensorFlow не установлен. Установите")
                return False

            self.model = tf.keras.models.load_model(model_file)
            logger.info(f"Модель Keras загружена из {model_file}")

            self.is_loaded = True
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки проекта: {e}")
            return False

    async def predict_image(self, image_bytes: bytes) -> Tuple[str, float]:
        """Делает предсказание для одного изображения."""
        if not self.is_loaded:
            if not self.load_project():
                return "Ошибка загрузки модели", 0.0

        try:
            assert self.model is not None
            model = self.model
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image = image.resize(self.input_shape, Image.Resampling.LANCZOS)
            img_array = np.array(image, dtype=np.float32) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            predictions = model.predict(img_array, verbose=0)
            predicted_class_idx = int(np.argmax(predictions[0]))
            confidence = float(predictions[0][predicted_class_idx])
            if predicted_class_idx < len(self.labels):
                class_name = self.labels[predicted_class_idx]
            else:
                class_name = f"Класс {predicted_class_idx}"

            return class_name, confidence

        except Exception as e:
            logger.error(f"Ошибка предсказания: {e}")
            return f"Ошибка: {e}", 0.0

    def cleanup(self):
        """Удаляет временные файлы после извлечения проекта."""
        if os.path.exists(self.extract_path):
            shutil.rmtree(self.extract_path)