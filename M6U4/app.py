from flask import Flask, request, jsonify, send_file, send_from_directory
from collections import defaultdict
from dotenv import load_dotenv
from ultralytics import YOLO
from flask_cors import CORS
from PIL import Image
import requests
import base64
import random
import spacy
import uuid
import json
import io
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from werkzeug.datastructures import FileStorage

load_dotenv()
app: Flask = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Создаём папки если их нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# ========== N-грамм модель (без ИИ) ==========
class NGramModel:
    def __init__(self, n: int = 5) -> None:
        self.n: int = n
        self.transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.trained: bool = False

    def train(self, text: str) -> None:
        if len(text) < self.n + 1:
            return
        for i in range(len(text) - self.n):
            context: str = text[i:i+self.n]
            next_char: str = text[i+self.n]
            self.transitions[context][next_char] += 1
        self.trained = True

    def generate(self, prompt: str, max_length: int = 200) -> str:
        if not self.trained or len(prompt) < self.n:
            return f"(Модель не обучена) Вы сказали: {prompt}"
        result: List[str] = list(prompt)
        for _ in range(max_length):
            context: str = ''.join(result[-self.n:])
            if context not in self.transitions:
                break
            choices: Dict[str, int] = self.transitions[context]
            next_char: str = random.choices(
                list(choices.keys()),
                weights=list(choices.values())
            )[0]
            result.append(next_char)
            if next_char in '.!?':
                break
        return ''.join(result)

# ========== БАЗА ЗНАНИЙ ==========
KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "tesla": {
        "type": "company",
        "founder": "Илон Маск",
        "founded": 2003,
        "products": ["электромобили", "солнечные панели", "батареи"],
        "headquarters": "Остин, Техас"
    },
    "elon musk": {
        "type": "person",
        "companies": ["Tesla", "SpaceX", "Neuralink", "The Boring Company"],
        "born": 1971,
        "nationality": "ЮАР, Канада, США"
    },
    "spacex": {
        "type": "company",
        "founder": "Илон Маск",
        "founded": 2002,
        "products": ["Falcon 9", "Starship", "Dragon"],
        "headquarters": "Хоторн, Калифорния"
    },
    "python": {
        "type": "technology",
        "creator": "Гвидо ван Россум",
        "year": 1991,
        "paradigm": ["объектно-ориентированный", "функциональный", "императивный"]
    },
    "deepseek": {
        "type": "company",
        "founder": "Лян Вэньфэн",
        "founded": 2023,
        "products": ["DeepSeek Chat", "DeepSeek Coder"],
        "headquarters": "Китай"
    }
}

# ========== ПРАВИЛА НАМЕРЕНИЙ ==========
INTENT_RULES: List[Dict[str, Any]] = [
    {
        "intent": "who_founded",
        "patterns": ["кто основал", "кто создал", "основатель", "founder", "who founded", "who created"],
        "entity_type": "ORG"
    },
    {
        "intent": "what_products",
        "patterns": ["что производит", "продукты", "чем занимается", "products", "what does", "what products"],
        "entity_type": "ORG"
    },
    {
        "intent": "where_headquarters",
        "patterns": ["где находится", "штаб-квартира", "офис", "headquarters", "located", "where is"],
        "entity_type": "ORG"
    },
    {
        "intent": "when_founded",
        "patterns": ["когда основана", "год основания", "founded", "established", "when was"],
        "entity_type": "ORG"
    },
    {
        "intent": "who_is",
        "patterns": ["кто такой", "расскажи о", "информация о", "who is", "tell me about"],
        "entity_type": "PER"
    },
    {
        "intent": "greeting",
        "patterns": ["привет", "здравствуй", "хай", "hello", "hi", "hey"],
        "entity_type": None
    },
    {
        "intent": "how_are_you",
        "patterns": ["как дела", "как ты", "how are you"],
        "entity_type": None
    }
]

RESPONSE_TEMPLATES: Dict[str, str] = {
    "who_founded": "{entity} основал {founder}.",
    "what_products": "{entity} производит: {products}.",
    "where_headquarters": "Штаб-квартира {entity} находится в {headquarters}.",
    "when_founded": "{entity} основана в {founded} году.",
    "who_is": "{entity} — {info}.",
    "greeting": "Привет! Я rule-based ассистент. Спроси меня о компаниях или людях из моей базы знаний.",
    "how_are_you": "Я алгоритм, у меня нет чувств, но я работаю исправно!",
    "not_found": "Я не знаю о {entity}. Попробуй спросить о Tesla, SpaceX, Elon Musk или Python.",
    "no_entity": "Я не понял, о ком или о чём ты спрашиваешь. Уточни, пожалуйста.",
    "no_intent": "Я не понял вопрос. Спроси, например: 'Кто основал Tesla?' или 'Где находится SpaceX?'"
}

# ========== МОДЕЛИ ==========
print("🔄 Загружаю YOLOv10m...")
yolo_model: YOLO = YOLO("yolov10m.pt")
print("✅ YOLO готов")

print("🔄 Загружаю spaCy модели...")
# Базовые модели с векторами (быстрые)
model_path_nlp_en_lg: Path = Path("/mnt/d/Kodland/M6U4/.venv/lib/python3.13/site-packages/en_core_web_lg")
model_path_en_core_web_trf: Path = Path("/mnt/d/Kodland/M6U4/.venv/lib/python3.13/site-packages/en_core_web_trf")
model_path_ru_lg: Path = Path("/mnt/d/Kodland/M6U4/.venv/lib/python3.13/site-packages/ru_core_news_lg")

nlp_en_lg: spacy.Language = spacy.load(model_path_nlp_en_lg)
print("✅ en_core_web_lg загружена")

# Попытка загрузить трансформерные модели (самые точные)
nlp_en: spacy.Language
nlp_ru: spacy.Language
nlp_en_trf: Optional[spacy.Language] = None
nlp_ru_trf: Optional[spacy.Language] = None

try:
    import spacy_transformers
    nlp_en_trf = spacy.load(model_path_en_core_web_trf)
    nlp_en = nlp_en_trf
    print("✅ Английская трансформерная модель загружена")
except Exception as e:
    nlp_en = nlp_en_lg
    print(f"⚠️ Английская трансформерная модель не найдена, используется lg: {e}")

try:
    nlp_ru = spacy.load(model_path_ru_lg)
    print("✅ ru_core_news_lg загружена")
except Exception as e:
    nlp_ru = spacy.load("ru_core_news_sm")
    print(f"⚠️ Используется ru_core_news_sm: {e}")

# Проверяем, используем ли мы трансформеры
if nlp_en_trf:
    print("🎯 Используется en_core_web_trf (Transformers)")
else:
    print("🎯 Используется en_core_web_lg (Vectors)")

print("✅ spaCy готов")

print("🔄 Инициализация N-грамм модели...")
ngram_model: NGramModel = NGramModel(n=5)
training_text: str = """
Привет. Как дела? Я работаю в компании Тесла. Илон Маск основатель.
Hello. How are you? I work at Tesla. Elon Musk is the founder.
"""
ngram_model.train(training_text)
print("✅ N-грамм модель готова")

# ========== ХРАНИЛИЩЕ ЧАТОВ ==========
chats: Dict[str, List[Dict[str, Any]]] = {}

def get_or_create_chat(chat_id: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
    if chat_id and chat_id in chats:
        return chat_id, chats[chat_id]
    new_id: str = str(uuid.uuid4())[:8]
    chats[new_id] = []
    return new_id, chats[new_id]

def detect_language(text: str) -> str:
    return 'ru' if re.search('[а-яА-Я]', text) else 'en'

# ========== ЛОГИКА АССИСТЕНТА ==========
def detect_intent(text: str, entities: List[Dict[str, str]]) -> Tuple[str, Optional[str]]:
    text_lower: str = text.lower()
    for rule in INTENT_RULES:
        if any(pattern in text_lower for pattern in rule["patterns"]):
            if rule["entity_type"]:
                for ent in entities:
                    if ent["type"] == rule["entity_type"]:
                        return rule["intent"], ent["text"].lower()
            else:
                return rule["intent"], None
    if entities:
        return "general_query", entities[0]["text"].lower()
    return "unknown", None

def find_in_knowledge_base(entity_name: str) -> Optional[Dict[str, Any]]:
    normalized: str = entity_name.lower().strip()
    if normalized in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[normalized]
    for key, value in KNOWLEDGE_BASE.items():
        if normalized in key or key in normalized:
            return value
    return None

def build_response(intent: str, entity: Optional[str], entity_data: Optional[Dict[str, Any]]) -> str:
    if intent == "greeting":
        return RESPONSE_TEMPLATES["greeting"]
    if intent == "how_are_you":
        return RESPONSE_TEMPLATES["how_are_you"]
    if intent == "unknown" and not entity:
        return RESPONSE_TEMPLATES["no_intent"]
    if not entity_data:
        return RESPONSE_TEMPLATES["not_found"].format(entity=entity or "этом")
    if intent == "who_founded":
        founder: str = entity_data.get("founder", "неизвестно")
        return RESPONSE_TEMPLATES["who_founded"].format(entity=entity.capitalize(), founder=founder)
    if intent == "what_products":
        products: str = ", ".join(entity_data.get("products", ["неизвестно"]))
        return RESPONSE_TEMPLATES["what_products"].format(entity=entity.capitalize(), products=products)
    if intent == "where_headquarters":
        hq: str = entity_data.get("headquarters", "неизвестно")
        return RESPONSE_TEMPLATES["where_headquarters"].format(entity=entity.capitalize(), headquarters=hq)
    if intent == "when_founded":
        founded: Any = entity_data.get("founded", "неизвестно")
        return RESPONSE_TEMPLATES["when_founded"].format(entity=entity.capitalize(), founded=founded)
    if intent == "who_is":
        if entity_data.get("type") == "person":
            info: str = f"родился в {entity_data.get('born', 'неизвестно')}, известен как {', '.join(entity_data.get('companies', ['неизвестно']))}"
        else:
            info = entity_data.get("type", "неизвестно")
        return RESPONSE_TEMPLATES["who_is"].format(entity=entity.capitalize(), info=info)
    return f"Я знаю о {entity}: {json.dumps(entity_data, ensure_ascii=False)}"

def process_message(text: str) -> Dict[str, Any]:
    lang: str = detect_language(text)
    nlp: spacy.Language = nlp_ru if lang == 'ru' else nlp_en
    doc: spacy.tokens.Doc = nlp(text)
    entities: List[Dict[str, str]] = []
    for ent in doc.ents:
        entities.append({"text": ent.text, "type": ent.label_})
    intent, target_entity = detect_intent(text, entities)
    kb_data: Optional[Dict[str, Any]] = None
    if target_entity:
        kb_data = find_in_knowledge_base(target_entity)
    response: str = build_response(intent, target_entity, kb_data)
    return {
        "response": response,
        "entities": entities,
        "intent": intent,
        "target_entity": target_entity,
        "kb_data": kb_data,
        "model_used": "transformers" if (lang == 'en' and nlp_en_trf) or (lang == 'ru' and nlp_ru_trf) else "vectors"
    }

# ========== МАРШРУТЫ ==========
@app.route("/")
def index() -> Any:
    return send_from_directory("static", "index.html")

@app.route("/chat", methods=["POST"])
def chat() -> Any:
    data: Dict[str, Any] = request.json
    text: str = data.get("message", "")
    chat_id: Optional[str] = data.get("chat_id")
    
    if not text:
        return jsonify({"error": "No text"}), 400
    
    # Получаем или создаём чат
    chat_id, messages = get_or_create_chat(chat_id)
    
    # Сохраняем сообщение пользователя
    messages.append({
        "role": "user",
        "content": text,
        "timestamp": __import__('time').time()
    })
    
    # Обрабатываем сообщение
    result: Dict[str, Any] = process_message(text)
    
    # Сохраняем ответ ассистента
    messages.append({
        "role": "assistant",
        "content": result["response"],
        "timestamp": __import__('time').time()
    })
    
    return jsonify({
        "response": result["response"],
        "chat_id": chat_id,
        "analysis": {
            "entities": result["entities"],
            "intent": result["intent"],
            "target": result["target_entity"],
            "model_used": result["model_used"]
        }
    })

@app.route("/sync-chat", methods=["POST"])
def sync_chat() -> Any:
    """Синхронизация сообщений чата с фронтендом"""
    data: Dict[str, Any] = request.json
    chat_id: Optional[str] = data.get("chat_id")
    messages: List[Dict[str, Any]] = data.get("messages", [])
    
    if chat_id:
        chats[chat_id] = messages
        return jsonify({"status": "ok", "chat_id": chat_id})
    
    return jsonify({"error": "No chat_id"}), 400

@app.route("/chat/history/<chat_id>", methods=["GET"])
def get_chat_history(chat_id: str) -> Any:
    """Получение истории конкретного чата"""
    if chat_id in chats:
        return jsonify({
            "chat_id": chat_id,
            "messages": chats[chat_id]
        })
    return jsonify({"error": "Chat not found"}), 404

@app.route("/chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id: str) -> Any:
    """Удаление чата"""
    if chat_id in chats:
        del chats[chat_id]
        return jsonify({"status": "ok"})
    return jsonify({"error": "Chat not found"}), 404

@app.route("/train", methods=["POST"])
def train_ngram() -> Any:
    data: Dict[str, Any] = request.json
    text: str = data.get("text", "")
    if text:
        ngram_model.train(text)
        return jsonify({"status": "ok", "message": f"Обучено на {len(text)} символах"})
    return jsonify({"error": "No text"}), 400

@app.route("/detect", methods=["POST"])
def detect() -> Any:
    file: Optional[FileStorage] = request.files.get("image")
    if not file:
        return jsonify({"error": "No image"}), 400
    img: Image.Image = Image.open(file.stream)
    results: List[Any] = yolo_model(img)
    detections: List[Dict[str, Any]] = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "class": yolo_model.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": box.xyxy[0].tolist()
            })
    img_with_boxes: Any = results[0].plot()
    img_pil: Image.Image = Image.fromarray(img_with_boxes[..., ::-1])
    buffered: io.BytesIO = io.BytesIO()
    img_pil.save(buffered, format="JPEG")
    img_base64: str = base64.b64encode(buffered.getvalue()).decode()
    return jsonify({
        "detections": detections,
        "annotated_image": f"data:image/jpeg;base64,{img_base64}"
    })

@app.route("/proxy-image")
def proxy_image() -> Any:
    url: Optional[str] = request.args.get("url")
    if not url:
        return jsonify({"error": "URL required"}), 400
    try:
        resp: requests.Response = requests.get(url, stream=True, timeout=10)
        return send_file(io.BytesIO(resp.content),
                        mimetype=resp.headers.get("Content-Type", "image/jpeg"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ner", methods=["POST"])
def ner() -> Any:
    data: Dict[str, Any] = request.json
    text: str = data.get("text", "")
    if not text:
        return jsonify({"error": "No text"}), 400
    lang: str = detect_language(text)
    nlp: spacy.Language = nlp_ru if lang == 'ru' else nlp_en
    doc: spacy.tokens.Doc = nlp(text)
    entities: List[Dict[str, str]] = []
    for ent in doc.ents:
        entities.append({"text": ent.text, "type": ent.label_})
    
    # Добавляем информацию о модели
    model_used: str = "transformers" if (lang == 'en' and nlp_en_trf) or (lang == 'ru' and nlp_ru_trf) else "vectors"
    
    return jsonify({
        "entities": entities,
        "language": lang,
        "model_used": model_used
    })

@app.route("/clear-chat", methods=["POST"])
def clear_chat() -> Any:
    data: Dict[str, Any] = request.json
    chat_id: Optional[str] = data.get("chat_id")
    if chat_id in chats:
        chats[chat_id] = []
    return jsonify({"status": "ok"})

@app.route("/chats", methods=["GET"])
def list_chats() -> Any:
    return jsonify({"chats": {cid: len(msgs) for cid, msgs in chats.items()}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)