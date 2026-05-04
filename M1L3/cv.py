"""
Модуль детекции объектов YOLOv10m с интеграцией aiogram.
Использует CPU/CUDA в зависимости от доступности.
"""
from typing import Any, List, Optional, Tuple
from aiogram.types import BufferedInputFile
from ultralytics import YOLO
from PIL import Image
import logging
import torch
import time
import io
import os

logger = logging.getLogger(__name__)

# Пороги детекции
CONFIDENCE_THRESHOLD: float = 0.5
IOU_THRESHOLD: float = 0.45

def log_message(text: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - {text}"
    print(message)
    with open('bot.log', 'a', encoding='utf-8') as f:
        f.write(message + '\n')

class YOLODetector:
    """Детектор объектов на основе YOLOv10m."""
    
    def __init__(self, model_path: str = "yolov10m.pt"):
        self.model_path = model_path
        self.model: Optional[Any] = None
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self) -> None:
        try:
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
            else:
                self.model = YOLO("yolov10m.pt")
            
            self.model.to(self._device)
            log_message(f"YOLO загружена на {self._device}")
        except Exception as e:
            log_message(f"Ошибка загрузки модели: {e}")
            raise
    
    async def detect_objects(
        self, 
        image_bytes: bytes,
        classes: Optional[List[int]] = None,
        conf: float = CONFIDENCE_THRESHOLD,
        iou: float = IOU_THRESHOLD,
    ) -> Tuple[bytes, List[dict[str, Any]]]:
        """Детектирует объекты на изображении."""
        if self.model is None:
            raise RuntimeError("Модель не загружена")
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            results: Any = self.model.predict(
                source=image,
                conf=conf,
                iou=iou,
                classes=classes,
                device=self._device,
                verbose=False,
            )
            detections: List[dict[str, Any]] = []
            result: Any = results[0]
            if getattr(result, "boxes", None) is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names.get(class_id, "unknown")
                    
                    detections.append({
                        "bbox": (x1, y1, x2, y2),
                        "confidence": confidence,
                        "class": class_name,
                        "class_id": class_id,
                    })
            
            annotated_plot = result.plot()
            annotated_image = Image.fromarray(annotated_plot[..., ::-1])
            output_buffer = io.BytesIO()
            annotated_image.save(output_buffer, format="JPEG", quality=85)
            annotated_bytes = output_buffer.getvalue()
            
            logger.info(f"Обнаружено {len(detections)} объектов")
            return annotated_bytes, detections
            
        except Exception as e:
            logger.error(f"Ошибка детекции: {e}")
            raise
    
    async def detect_and_format_telegram(
        self,
        image_bytes: bytes,
        user_id: int,
        classes: Optional[List[int]] = None,
    ) -> Tuple[BufferedInputFile, str]:
        """Детектирует объекты и возвращает результат для Telegram."""
        annotated_bytes, detections = await self.detect_objects(
            image_bytes, classes=classes,
        )
        
        if detections:
            lines = [f"🔍 Обнаружено {len(detections)} объектов:"]
            for det in detections[:10]:
                conf_percent = det["confidence"] * 100
                lines.append(
                    f"• {det['class']}: {conf_percent:.1f}% "
                    f"({det['bbox'][0]:.0f},{det['bbox'][1]:.0f})"
                )
            caption = "\n".join(lines)
        else:
            caption = "🔍 Объекты не обнаружены"
        
        photo = BufferedInputFile(
            annotated_bytes,
            filename=f"detection_{user_id}.jpg",
        )
        
        return photo, caption
    
    @property
    def is_loaded(self) -> bool:
        """Проверяет, загружена ли модель."""
        return self.model is not None
    
    @property
    def device(self) -> str:
        """Возвращает устройство вычислений."""
        return self._device

detector = YOLODetector()