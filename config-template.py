import logging

# Telegram Bot Token
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Allowed Users
ALLOWED_USERS = [463688781, 1587264049] # Replace with actual user IDs

# Temporary Files Directory
TEMP_DIR = 'temp_files'

# Supported Languages
SUPPORTED_LANGUAGES = {
    'en-US': 'English',
    'pl-PL': 'Polski',
    'ru-RU': 'Русский',
}
DEFAULT_LANGUAGE = 'en-US'

# Max size of video file
MAX_FILE_SIZE = 49 * 1024 * 1024 # 50 MB

# Chunk size in seconds
CHUNK_SIZE = 30 # for example, 30 seconds

# Number of seconds to capture from the previous chunk
OVERLAP_SECONDS = 10 # for example, 10 seconds

# Logging Configuration
LOG_LEVEL_FILE = logging.INFO
LOG_LEVEL_CONSOLE = logging.ERROR
LOG_FILE = 'logs/bot.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_ROTATION = 'midnight'