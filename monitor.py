import json
import asyncio
import time
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import Channel
from config import *

client = TelegramClient('monitor_session', API_ID, API_HASH)

last_messages = {}
sent_messages = set()

def load_json_file(filename, default=None):
    """Загрузка данных из JSON файла"""
    if default is None:
        default = {}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json_file(filename, data):
    """Сохранение данных в JSON файл"""
    with open(filename, 'w') as f:
        json.dump(data, f)

def load_last_messages():
    """Загрузка последних обработанных сообщений из файла"""
    return load_json_file(LAST_MESSAGES_FILE)

def load_sent_messages():
    """Загрузка хешей отправленных сообщений"""
    data = load_json_file(SENT_MESSAGES_FILE, {"messages": []})
    return set(data["messages"])

def save_sent_messages():
    """Сохранение хешей отправленных сообщений"""
    save_json_file(SENT_MESSAGES_FILE, {"messages": list(sent_messages)})

def load_last_run_time():
    """Загрузка времени последнего запуска"""
    data = load_json_file(LAST_RUN_FILE, {"last_run": 0})
    return data["last_run"]

def save_last_run_time():
    """Сохранение времени текущего запуска"""
    save_json_file(LAST_RUN_FILE, {"last_run": int(time.time())})

def save_last_messages():
    """Сохранение последних обработанных сообщений в файл"""
    save_json_file(LAST_MESSAGES_FILE, last_messages)

def get_message_hash(message):
    """Создание уникального хеша сообщения"""
    return f"{message.chat_id}_{message.id}_{message.text}"

import re

def clean_text(text):
    """Очистка текста от эмодзи и специальных символов"""
    # Удаляем эмодзи и другие специальные символы
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # эмодзи-смайлики
        u"\U0001F300-\U0001F5FF"  # символы и пиктограммы
        u"\U0001F680-\U0001F6FF"  # транспорт и символы
        u"\U0001F1E0-\U0001F1FF"  # флаги
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def contains_keywords(text):
    """Проверка наличия ключевых слов в тексте"""
    if not text:
        return False
    
    clean_message = clean_text(text)
    text_lower = clean_message.lower()
    
    found_keywords = []
    for keyword in KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            found_keywords.append(keyword)
    
    if found_keywords:
        print(f"Найдены ключевые слова: {', '.join(found_keywords)}")
        print(f"В тексте: {text[:200]}...") 
        return True
    return False

async def find_channel_by_title(title):
    """Поиск канала по его отображаемому имени"""
    async for dialog in client.iter_dialogs():
        if dialog.is_channel and dialog.title == title:
            return dialog.entity
    return None

async def get_channel_entity(channel):
    """Получение сущности канала по разным форматам идентификации"""
    try:
        if isinstance(channel, str):
            if channel.startswith(('https://t.me/', 't.me/')) or channel.startswith('@'):
                return await client.get_entity(channel)
            else:
                entity = await find_channel_by_title(channel)
                if entity:
                    return entity
                print(f"Канал '{channel}' не найден по названию")
                return None
        return await client.get_entity(channel)
    except Exception as e:
        print(f"Ошибка при получении канала {channel}: {str(e)}")
        return None

async def check_old_messages():
    """Проверка сообщений с момента последнего запуска"""
    print("Проверяю пропущенные сообщения...")
    
    last_run = load_last_run_time()
    
    if last_run == 0:
        print("Первый запуск, начинаем мониторинг с текущего момента")
        return
    
    last_run_time = datetime.fromtimestamp(last_run)
    print(f"Проверяю сообщения с {last_run_time}")
    
    for channel in CHANNELS:
        try:
            channel_entity = await get_channel_entity(channel)
            if channel_entity and isinstance(channel_entity, Channel):
                messages = await client.get_messages(
                    channel_entity,
                    limit=None,
                    offset_date=last_run_time
                )
                
                for message in messages:
                    if not message.text:
                        continue
                        
                    if contains_keywords(message.text):
                        await forward_message(message)
                        
                if messages:
                    last_messages[str(channel_entity.id)] = messages[0].id
        except Exception as e:
            print(f"Ошибка при проверке канала {channel}: {str(e)}")
    
    save_last_messages()
    print("Проверка пропущенных сообщений завершена")

async def forward_message(message):
    """Пересылка сообщения в целевую группу"""
    print("\nПроверка сообщения на пересылку:")
    print(f"Текст сообщения: {message.text[:200]}...")  
    
    message_hash = get_message_hash(message)
    if message_hash in sent_messages:
        print("Это сообщение уже было отправлено ранее")
        return
    
    try:
        try:
            target = await client.get_entity(TARGET_GROUP)
        except ValueError:
            target = None
            async for dialog in client.iter_dialogs():
                if dialog.id == int(TARGET_GROUP):
                    target = dialog.entity
                    break
            
            if not target:
                raise ValueError(f"Не удалось найти группу с ID {TARGET_GROUP}")
        
        await client.forward_messages(target, message)
        print(f"Сообщение переслано: {message.text[:100]}...")
        
        sent_messages.add(message_hash)
        save_sent_messages()
        
    except Exception as e:
        print(f"Ошибка при пересылке сообщения: {str(e)}")

@client.on(events.NewMessage(chats=CHANNELS))
async def handle_new_message(event):
    """Обработка новых сообщений"""
    if not event.text:
        return
        
    if contains_keywords(event.text):
        await forward_message(event.message)
        
    channel_id = str(event.chat_id)
    last_messages[channel_id] = event.message.id
    save_last_messages()

async def check_periodically():
    """Периодическая проверка сообщений"""
    while True:
        try:
            for channel in CHANNELS:
                channel_entity = await get_channel_entity(channel)
                if channel_entity and isinstance(channel_entity, Channel):
                    messages = await client.get_messages(channel_entity, limit=50)
                    for message in messages:
                        if not message.text:
                            continue
                        if contains_keywords(message.text):
                            await forward_message(message)
            
            save_last_run_time()
            save_sent_messages()
            
            print(f"Следующая проверка через {CHECK_INTERVAL} секунд...")
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Ошибка при проверке: {str(e)}")
            await asyncio.sleep(10)  

async def main():
    """Основная функция"""
    global last_messages, sent_messages
    
    print("Запуск мониторинга...")
    last_messages = load_last_messages()
    sent_messages = load_sent_messages()
    
    if CHECK_OLD_MESSAGES:
        await check_old_messages()
    
    save_last_run_time()
    save_sent_messages()
    
    print(f"Начинаю периодический мониторинг (каждые {CHECK_INTERVAL // 60} минут)...")
    await check_periodically()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
