from typing import Any, Dict, List, Callable, Optional, Tuple
import urllib.parse
import requests
import logging
import random

logger = logging.getLogger(__name__)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def search_kitsu(category: str, query: str) -> Dict[str, Any]:
    """Расширенный поиск с несколькими попытками"""
    attempts: List[Callable[[], Optional[str]]] = [
        lambda: f'filter[name]={urllib.parse.quote(query)}',
        lambda: f'filter[text]={urllib.parse.quote(query)}',
        lambda: f'filter[name]={urllib.parse.quote(query.split()[0])}' if ' ' in query else None
    ]
    
    for attempt in attempts:
        filter_param = attempt()
        try:
            if not filter_param:
                continue
                
            url = f'https://kitsu.io/api/edge/{category}?{filter_param}'
            logger.info(f"Попытка запроса: {url}")
            
            headers = {
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('data'):
                logger.info(f"Успешный запрос с фильтром: {filter_param}")
                return data
                
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Неудачная попытка с фильтром: {filter_param}")
            continue
        except Exception as e:
            logger.warning(f"Ошибка в попытке: {e}")
            continue
    
    return {'data': []}

def search_kitsu_alternative(category: str, query: str) -> Dict[str, Any]:
    """Альтернативный метод поиска через общий поиск"""
    try:
        # Используем другой endpoint для поиска
        encoded_query = urllib.parse.quote(query)
        url = f'https://kitsu.io/api/edge/{category}?filter[name]={encoded_query}'
        
        logger.info(f"Альтернативный запрос к API: {url}")
        
        headers = {
            'Accept': 'application/vnd.api+json',
            'Content-Type': 'application/vnd.api+json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except Exception as e:
        logger.error(f"Ошибка в альтернативном поиске: {e}")
        return {'data': []}    

def format_anime_result(attributes: Dict[str, Any]) -> str:
    """Форматирует информацию об аниме с дополнительными данными"""
    title = attributes.get('titles', {}).get('en', attributes.get('canonicalTitle', 'Без названия'))
    rating = attributes.get('averageRating', 'Нет рейтинга')
    episodes = attributes.get('episodeCount', '?')
    status = attributes.get('status', 'Неизвестно')
    popularity = attributes.get('popularityRank', 'Неизвестно')
    description = (attributes.get('synopsis', 'Нет описания')[:250] + '...') if attributes.get('synopsis') else 'Нет описания'
    
    # Определяем эмодзи для статуса
    status_emoji = {
        'current': '🟢',
        'finished': '✅', 
        'upcoming': '🟡',
        'tba': '🟠'
    }.get(status, '⚪')
    
    return (f"🎌 <b>{title}</b>\n"
            f"⭐ <b>Рейтинг:</b> {rating}\n"
            f"📊 <b>Эпизодов:</b> {episodes}\n"
            f"{status_emoji} <b>Статус:</b> {status}\n"
            f"🔥 <b>Популярность:</b> #{popularity}\n"
            f"📖 <b>Описание:</b> {description}")

def format_manga_result(attributes: Dict[str, Any]) -> str:
    """Форматирует информацию о манге"""
    title = attributes.get('titles', {}).get('en', attributes.get('canonicalTitle', 'Без названия'))
    rating = attributes.get('averageRating', 'Нет рейтинга')
    chapters = attributes.get('chapterCount', '?')
    volumes = attributes.get('volumeCount', '?')
    status = attributes.get('status', 'Неизвестно')
    description = (attributes.get('synopsis', 'Нет описания')[:200] + '...') if attributes.get('synopsis') else 'Нет описания'
    
    return (f"📚 <b>Манга:</b> {title}\n"
            f"⭐ <b>Рейтинг:</b> {rating}\n"
            f"📑 <b>Глав:</b> {chapters}\n"
            f"📗 <b>Томов:</b> {volumes}\n"
            f"📈 <b>Статус:</b> {status}\n"
            f"📖 <b>Описание:</b> {description}")

def format_character_result(attributes: Dict[str, Any]) -> str:
    """Форматирует информацию о персонаже"""
    name = attributes.get('names', {}).get('en', attributes.get('canonicalName', 'Без имени'))
    description = (attributes.get('description', 'Нет описания')[:300] + '...') if attributes.get('description') else 'Нет описания'
    
    return (f"🎭 <b>Персонаж:</b> {name}\n"
            f"📖 <b>Описание:</b> {description}")

def format_person_result(attributes: Dict[str, Any]) -> str:
    """Форматирует информацию о человеке"""
    name = attributes.get('names', {}).get('en', attributes.get('canonicalName', 'Без имени'))
    birthday = attributes.get('birthday', 'Неизвестно')
    
    return (f"👤 <b>Имя:</b> {name}\n"
            f"🎂 <b>День рождения:</b> {birthday}")
    
def search_anime_advanced(query: str) -> Dict[str, Any]:
    """Продвинутый поиск аниме с несколькими стратегиями"""
    encoded_query = urllib.parse.quote(query)
    
    strategies: List[Optional[str]] = [
        f'https://kitsu.io/api/edge/anime?filter[text]={encoded_query}',
        f'https://kitsu.io/api/edge/anime?filter[text]={encoded_query}&page[limit]=10',
        f'https://kitsu.io/api/edge/anime?filter[text]={encoded_query}&sort=popularityRank' if len(query) > 3 else None
    ]
    
    all_results: List[Dict[str, Any]] = []
    
    for url in strategies:
        if not url:
            continue
            
        try:
            logger.info(f"Попытка поиска: {url}")
            headers = {
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('data'):
                all_results.extend(data['data'])
                
        except Exception as e:
            logger.warning(f"Ошибка в стратегии поиска: {e}")
            continue
    
    unique_results: Dict[str, Any] = {}
    for item in all_results:
        item_id = item['id']
        if item_id not in unique_results:
            unique_results[item_id] = item
    
    return {'data': list(unique_results.values())}

def find_best_anime_match(results: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    """Находит наиболее релевантный результат для запроса"""
    if not results:
        return None
    
    query_lower = query.lower()
    scored_results: List[Tuple[int, Dict[str, Any]]] = []
    
    for item in results:
        attributes = item['attributes']
        title_en = attributes.get('titles', {}).get('en', '').lower()
        title_jp = attributes.get('titles', {}).get('ja_jp', '').lower()
        canonical_title = attributes.get('canonicalTitle', '').lower()
        
        score = 0
        
        if title_en == query_lower:
            score += 100
        elif title_jp == query_lower:
            score += 90
        elif query_lower in title_en:
            score += 50
        elif canonical_title == query_lower:
            score += 80
        elif query_lower in canonical_title:
            score += 40
        popularity_rank = attributes.get('popularityRank')
        if popularity_rank is not None and popularity_rank < 1000:
            score += 20
        elif popularity_rank is not None and popularity_rank < 5000:
            score += 10
        rating_rank = attributes.get('ratingRank')
        if rating_rank is not None and rating_rank < 1000:
            score += 15
        scored_results.append((score, item))
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    return scored_results[0][1] if scored_results else results[0] 

def get_dog_image() -> str:
    """Получает случайное изображение собаки"""
    try:
        url = 'https://random.dog/woof.json'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('url', '')
    except Exception as e:
        logger.error(f"Error getting dog image: {e}")
        return ''

def get_fox_image() -> str:
    """Получает случайное изображение лисы"""
    try:
        url = 'https://randomfox.ca/floof/'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('image', '')
    except Exception as e:
        logger.error(f"Error getting fox image: {e}")
        return ''

def get_pokemon_info(pokemon_name: str) -> Dict[str, Any]:
    """Получает информацию о покемоне"""
    try:
        url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting pokemon info: {e}")
        raise

def get_random_pokemon() -> Dict[str, Any]:
    """Получает случайного покемона"""
    try:
        pokemon_id = random.randint(1, 1010) 
        url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_id}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting random pokemon: {e}")
        raise

def format_pokemon_result(pokemon_data: Dict[str, Any]) -> str:
    """Форматирует информацию о покемоне"""
    name = pokemon_data['name'].title()
    pokemon_id = pokemon_data['id']
    height = pokemon_data['height'] / 10
    weight = pokemon_data['weight'] / 10 
    types = [t['type']['name'].title() for t in pokemon_data['types']]
    types_str = ', '.join(types)
    abilities = [a['ability']['name'].title() for a in pokemon_data['abilities'][:3]]
    abilities_str = ', '.join(abilities)
    stats: Dict[str, int] = {}
    for stat in pokemon_data['stats']:
        stat_name = stat['stat']['name']
        stats[stat_name] = stat['base_stat']
    
    return (f"⚡ <b>Pokémon:</b> {name} #{pokemon_id}\n"
            f"📏 <b>Height:</b> {height}m\n"
            f"⚖️ <b>Weight:</b> {weight}kg\n"
            f"🎯 <b>Type:</b> {types_str}\n"
            f"💪 <b>Abilities:</b> {abilities_str}\n"
            f"❤️ <b>HP:</b> {stats.get('hp', 0)}\n"
            f"⚔️ <b>Attack:</b> {stats.get('attack', 0)}\n"
            f"🛡️ <b>Defense:</b> {stats.get('defense', 0)}")