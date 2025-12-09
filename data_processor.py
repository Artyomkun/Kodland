from typing import Optional, Tuple, Any, Dict
from datetime import datetime
import pandas as pd
import numpy as np
import time
import json
import h5py
import os

class ModelWeightsProcessor:
    def __init__(self, weights_path: str = "data/model_weights.h5"):
        self.weights_path = weights_path
        self._ensure_weights_file()
    
    def _ensure_weights_file(self):
        """Создает файл с весами если его нет"""
        try:
            with h5py.File(self.weights_path, 'a') as f:
                if 'neural_network' not in f:
                    self._initialize_weights(f)
        except Exception as e:
            print(f"Ошибка создания файла весов: {e}")
    
    def _initialize_weights(self, f: Any):
        """Инициализирует веса модели"""
        nn_group = f.create_group('neural_network')
        nn_group.create_dataset('layer1/weights', data=np.random.randn(100, 64).astype(np.float32))
        nn_group.create_dataset('layer1/biases', data=np.zeros(64).astype(np.float32))
        nn_group.create_dataset('layer2/weights', data=np.random.randn(64, 10).astype(np.float32))
        nn_group.create_dataset('layer2/biases', data=np.zeros(10).astype(np.float32))
        vocab_group = f.create_group('vocabulary')
        vocab = {
            'привет': 1, 'пока': 2, 'фото': 3, 'бот': 4, 'команда': 5,
            'статистика': 6, 'анализ': 7, 'помощь': 8, 'спасибо': 9, 'хорошо': 10
        }
        for word, idx in vocab.items():
            vocab_group.attrs[word] = idx
        f.attrs['model_name'] = 'telegram_bot'
        f.attrs['version'] = '1.0'
        f.attrs['created'] = datetime.now().isoformat()
        f.attrs['input_shape'] = json.dumps([100])
        f.attrs['output_classes'] = 10
    
    def log_message(self, text): 
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - {text}"
        print(message)
        with open('bot.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')
            
    def get_weights(self, layer_name: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Получает веса указанного слоя"""
        try:
            with h5py.File(self.weights_path, 'r') as f:
                weights_path = f'neural_network/{layer_name}/weights'
                biases_path = f'neural_network/{layer_name}/biases'
                if weights_path in f and biases_path in f:
                    weights_dataset = f[weights_path]
                    biases_dataset = f[biases_path]
                    
                    weights = np.array(weights_dataset)
                    biases = np.array(biases_dataset)
                    return weights, biases
                else:
                    print(f"Пути не найдены: {weights_path}, {biases_path}")
                    return None, None
        except Exception as e:
            print(f"Ошибка получения весов: {e}")
            return None, None
    
    def predict(self, text: str) -> str:
        """Простое предсказание на основе текста"""
        try:
            with h5py.File(self.weights_path, 'r') as f:
                if 'vocabulary' not in f:
                    return "Словарь не найден"
                vocab_group = f['vocabulary']
                vocab = {}
                for key in vocab_group.attrs:
                    vocab[key] = vocab_group.attrs[key]
                words = str(text).lower().split()
                score = sum(1 for word in words if word in vocab)
                categories = [
                    'приветствие', 'прощание', 'медиа', 'команда', 
                    'статистика', 'анализ', 'помощь', 'благодарность', 
                    'положительный', 'другое'
                ]
                category_idx = min(score, len(categories) - 1)
                return categories[category_idx]
        except Exception as e:
            return f"Ошибка предсказания: {e}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Информация о модели"""
        try:
            with h5py.File(self.weights_path, 'r') as f:
                vocab_size = 0
                if 'vocabulary' in f:
                    vocab_group = f['vocabulary']
                    vocab_size = len(vocab_group.attrs)
                
                info = {
                    'name': f.attrs.get('model_name', 'Unknown'),
                    'version': f.attrs.get('version', 'Unknown'),
                    'created': f.attrs.get('created', 'Unknown'),
                    'vocabulary_size': vocab_size
                }
                return info
        except Exception as e:
            return {'error': f'Модель не доступна: {e}'}

class DataProcessor:
    def __init__(self, hdf5_path: str = "data/user_data.h5", weights_path: str = "data/model_weights.h5"):
        self.hdf5_path = hdf5_path
        self.weights_path = weights_path
        self._ensure_data_directory()
        self.weights_processor = ModelWeightsProcessor(weights_path)
    
    def _ensure_data_directory(self):
        """Создает папку для данных если её нет"""
        os.makedirs(os.path.dirname(self.hdf5_path), exist_ok=True)
    
    def log_message(self, text): 
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - {text}"
        print(message)
        with open('bot.log', 'a', encoding='utf-8') as f:
            f.write(message + '\n')
            
    def save_user_data(self, user_id: int, action_type: str, data: Optional[str] = None) -> bool:
        """Сохраняет данные пользователя в HDF5"""
        try:
            timestamp = datetime.now().isoformat()
            
            user_data = {
                'user_id': user_id,
                'timestamp': timestamp,
                'action_type': action_type,
                'data': str(data) if data else '',
                'message_length': len(data) if data else 0
            }
            new_data = pd.DataFrame([user_data])
            with pd.HDFStore(self.hdf5_path, mode='a') as store:
                if 'user_actions' in store:
                    existing_data = store['user_actions']
                    updated_data = pd.concat([existing_data, new_data], ignore_index=True)
                    store.put('user_actions', updated_data, format='table')
                else:
                    store.put('user_actions', new_data, format='table')
            return True
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
            return False
    
    def get_user_data(self, user_id: int) -> pd.DataFrame:
        """Получает данные конкретного пользователя"""
        try:
            with pd.HDFStore(self.hdf5_path, mode='r') as store:
                if 'user_actions' in store:
                    data = store['user_actions']
                    user_data = data[data['user_id'] == user_id]
                    return pd.DataFrame(user_data)
        except Exception as e:
            print(f"Ошибка чтения данных: {e}")
        return pd.DataFrame()
    
    def get_all_data(self) -> pd.DataFrame:
        """Получает все данные"""
        try:
            with pd.HDFStore(self.hdf5_path, mode='r') as store:
                if 'user_actions' in store:
                    data = store['user_actions']
                    return pd.DataFrame(data) 
        except Exception as e:
            print(f"Ошибка чтения всех данных: {e}")
        return pd.DataFrame()
    
    def get_user_stats(self, user_id: int) -> str:
        """Статистика пользователя"""
        user_data = self.get_user_data(user_id)
        
        if user_data.empty:
            return "Данных пока нет"
        
        try:
            stats = {
                'total_messages': len(user_data),
                'first_activity': user_data['timestamp'].min(),
                'last_activity': user_data['timestamp'].max(),
                'avg_message_length': user_data['message_length'].mean()
            }
            
            return (
                f"Сообщений: {stats['total_messages']}\n"
                f"Первая активность: {stats['first_activity'][:10]}\n"
                f"Последняя активность: {stats['last_activity'][:16]}\n"
                f"Средняя длина сообщения: {stats['avg_message_length']:.1f} симв."
            )
        except Exception as e:
            return f"Ошибка расчета статистики: {e}"
    
    def analyze_with_ai(self, text: str) -> str:
        """Анализ текста с помощью AI модели"""
        return self.weights_processor.predict(text)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Информация о AI модели"""
        return self.weights_processor.get_model_info()