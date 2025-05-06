import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE = os.getenv('PHONE')

# ID группы куда пересылать сообщения
TARGET_GROUP = "Кавички убираем"

# Ключевые слова для поиска (используем маленькие буквы)
KEYWORDS = [
    'слово1',
    'слово2',
    'слово3',
    'слово4',
    'слово5',
    'слово6',
    'и тд...'
]

# Список каналов для мониторинга
# Можно использовать:
# - Полные ссылки: 'https://t.me/ktroom'
# - Короткие имена: '@ktroom'
# - ID каналов: '-1001234567890'
# - Точные названия каналов: 'KTroom | Уцінені товари'
CHANNELS = [
    'Канал1', 
    'Канал2',
    'Канал3',

]

LAST_MESSAGES_FILE = 'last_messages.json'

LAST_RUN_FILE = 'last_run.json'

SENT_MESSAGES_FILE = 'sent_messages.json'

# Интервал проверки в секундах (5 минут = 300 секунд)
CHECK_INTERVAL = 300

# Всегда проверяем сообщения с момента последнего запуска
CHECK_OLD_MESSAGES = True
