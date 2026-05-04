"""ideogram.py — Модуль для работы с ZIP-архивом от Ideogram."""
from __future__ import annotations

import io
import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Final

import keras
import numpy as np
import numpy.typing as npt
from PIL import Image

from ai_model import AIModel
from data_processor import DataProcessor, ModelWeightsProcessor
from keras.src.saving.saving_api import load_model

IMG_SIZE: Final[int] = 224
EXTRACT_DIR: Final[str] = "ideogram_extracted"


class IdeogramModel:
    """Загрузчик и инференсер для моделей из ZIP-архива Ideogram."""

    __slots__ = (
        "_zip_path",
        "_model",
        "_labels",
        "_is_loaded",
        "_weights_processor",
        "_data_processor",
        "_ai_model",
    )

    def __init__(self, zip_path: str = "converted_keras.zip") -> None:
        self._zip_path: str = zip_path
        self._model: keras.Model | None = None
        self._labels: list[str] = []
        self._is_loaded: bool = False
        self._weights_processor = ModelWeightsProcessor()
        self._data_processor = DataProcessor()
        self._ai_model = AIModel()

    def load(self) -> bool:
        """Загружает модель из ZIP и подготавливает систему."""
        try:
            if not os.path.exists(self._zip_path):
                self._log(f"ZIP-архив не найден: {self._zip_path}")
                return False

            if os.path.exists(EXTRACT_DIR):
                shutil.rmtree(EXTRACT_DIR)

            with zipfile.ZipFile(self._zip_path, "r") as zf:
                zf.extractall(EXTRACT_DIR)
            self._log(f"Архив {self._zip_path} распакован")

            labels_path = Path(EXTRACT_DIR) / "labels.txt"
            if labels_path.exists():
                self._labels = labels_path.read_text(encoding="utf-8").splitlines()
                self._log(f"Загружено {len(self._labels)} меток")

            model_path = next(
                (
                    Path(root) / f
                    for root, _, files in os.walk(EXTRACT_DIR)
                    for f in files
                    if f.endswith((".h5", ".hdf5", ".keras"))
                ),
                None,
            )

            if model_path is None:
                self._log("Модель не найдена в архиве")
                return False

            self._model = load_model(
                str(model_path),
                custom_objects={"DepthwiseConv2D": self._fixed_depthwise_conv2d},
                compile=False,
            )
            self._log(f"Модель загружена: {model_path.name}")
            self._is_loaded = True
            return True
        except Exception as exc:
            self._log(f"Ошибка загрузки: {exc}")
            return False

    @staticmethod
    def _fixed_depthwise_conv2d(**kwargs: Any) -> keras.layers.DepthwiseConv2D:
        kwargs.pop("groups", None)
        return keras.layers.DepthwiseConv2D(**kwargs)

    async def predict(self, image_bytes: bytes) -> tuple[str, float]:
        """Предсказывает класс изображения."""
        if not self._is_loaded and not self.load():
            return "Модель не загружена", 0.0

        if self._model is None:
            return "Модель отсутствует", 0.0

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image = image.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS)

            img_array: npt.NDArray[np.float32] = (
                np.array(image, dtype=np.float32) / 255.0
            )
            img_array = np.expand_dims(img_array, axis=0)

            predictions: npt.NDArray[np.float32] = self._model.predict(
                img_array, verbose=0
            )
            predicted_idx = int(np.argmax(predictions[0]))
            confidence = float(predictions[0][predicted_idx])

            class_name = (
                self._labels[predicted_idx]
                if predicted_idx < len(self._labels)
                else f"Класс {predicted_idx}"
            )
            return class_name, confidence
        except Exception as exc:
            self._log(f"Ошибка предсказания: {exc}")
            return "Ошибка", 0.0

    def process_and_predict(self, user_id: int, text: str) -> dict[str, Any]:
        """Обрабатывает данные пользователя и делает AI-предсказание."""
        return {
            "user_id": user_id,
            "text": text,
            "prediction": self._data_processor.analyze_with_ai(text),
            "sentiment": self._ai_model.analyze_sentiment(text),
            "response": self._ai_model.generate_response(text),
            "model_info": self._weights_processor.get_model_info(),
        }

    @staticmethod
    def _log(text: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - IDEOGRAM - {text}"
        print(message)
        with open("bot.log", "a", encoding="utf-8") as f:
            f.write(message + "\n")

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def cleanup(self) -> None:
        if os.path.exists(EXTRACT_DIR):
            shutil.rmtree(EXTRACT_DIR)