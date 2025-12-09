from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from data_processor import DataProcessor
from typing import Any
import numpy as np
import joblib
import h5py
import time
import os
import io

class AIModel:
    def __init__(self):
        self.model: Any = None
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.processor = DataProcessor()
        self.model_path = "data/model_weights.h5"
        self._load_or_init_model()
    
    def _load_or_init_model(self):
        """Загружает или инициализирует модель"""
        try:
            if os.path.exists(self.model_path):
                self.log_message("Попытка загрузки модели из файла")
                with h5py.File(self.model_path, 'r') as f:
                    if 'model' in f:
                        dataset = f['model']
                        if isinstance(dataset, h5py.Dataset):
                            loaded_void = dataset[()]
                            model_bytes = loaded_void.tobytes()
                            buffer = io.BytesIO(model_bytes)
                            self.model = joblib.load(buffer)
                            self.log_message("Модель успешно загружена из файла")
            else:
                self.log_message("Файл модели не найден, инициализация новой модели")
                self.model = RandomForestClassifier(n_estimators=100)
                self.log_message("Новая модель RandomForest инициализирована")
                
        except Exception as e:
            self.log_message(f"Ошибка загрузки модели: {e}")
            self.model = RandomForestClassifier(n_estimators=100)
            self.log_message("Создана новая модель после ошибки")
    
    def log_message(self, text):
        """Логирование сообщений"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - AI_MODEL - {text}"
        print(message)
        with open('bot.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')

    def save_model(self):
        """Сохраняет модель в HDF5"""
        if self.model:
            try:
                self.log_message("Сохранение модели в файл")
                buffer = io.BytesIO()
                joblib.dump(self.model, buffer)
                model_bytes = buffer.getvalue()
                with h5py.File(self.model_path, 'w') as f:
                    f.create_dataset('model', data=np.void(model_bytes))
                self.log_message("Модель успешно сохранена")
            except Exception as e:
                self.log_message(f"Ошибка сохранения модели: {e}")
        else:
            self.log_message("Модель не существует для сохранения")

    def analyze_sentiment(self, text: str) -> str:
        """Анализ тональности текста"""
        self.log_message(f"Анализ тональности текста: '{text[:50]}...'")
        positive_words = ['хорош', 'отличн', 'прекрасн', 'супер', 'класс', 'люблю']
        negative_words = ['плох', 'ужасн', 'грустн', 'ненавижу', 'скучн']
        text_lower = text.lower()
        pos = sum(1 for w in positive_words if w in text_lower)
        neg = sum(1 for w in negative_words if w in text_lower)
        sentiment = "Положительное" if pos > neg else "Отрицательное" if neg > pos else "Нейтральное"
        self.log_message(f"Тональность определена как: {sentiment} (позитивных: {pos}, негативных: {neg})")
        return sentiment

    def generate_response(self, text: str) -> str:
        """Генерация ответа на текст"""
        self.log_message(f"Генерация ответа на: '{text[:50]}...'")
        responses = {
            'привет': 'Привет! Как дела?',
            'как дела': 'У меня все отлично! А у тебя?',
            'пока': 'До свидания! Буду рад пообщаться снова!'
        }
        text_lower = text.lower()
        for k, v in responses.items():
            if k in text_lower:
                self.log_message(f"Найден стандартный ответ для ключа: '{k}'")
                return v
        self.log_message("Стандартный ответ не найден, возвращён общий ответ")
        return "Интересно! Расскажи мне больше об этом."

    def process_message(self, user_id: int, text: str) -> dict:
        """Обработка сообщения: сохранение, анализ, ответ"""
        self.log_message(f"Обработка сообщения от пользователя {user_id}: '{text[:50]}...'")
        
        try:
            self.log_message("Сохранение данных пользователя")
            save_result = self.processor.save_user_data(user_id, "message", text)
            if save_result:
                self.log_message("Данные пользователя сохранены")
            else:
                self.log_message("Ошибка сохранения данных пользователя")
            self.log_message("Анализ тональности")
            sentiment = self.analyze_sentiment(text)
            self.log_message("Генерация ответа")
            response = self.generate_response(text)
            self.log_message("AI анализ текста")
            ai_prediction = self.processor.analyze_with_ai(text)
            self.log_message("Получение статистики пользователя")
            stats = self.processor.get_user_stats(user_id)
            result = {
                "response": response,
                "sentiment": sentiment,
                "ai_prediction": ai_prediction,
                "stats": stats
            }
            self.log_message(f"Обработка сообщения завершена. Ответ: '{response[:50]}...'")
            return result
        except Exception as e:
            self.log_message(f"Ошибка обработки сообщения: {e}")
            return {
                "response": "Извините, произошла ошибка при обработке сообщения",
                "sentiment": "Неизвестно",
                "ai_prediction": "Ошибка",
                "stats": "Данные временно недоступны"
            }