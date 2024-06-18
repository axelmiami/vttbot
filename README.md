# Voice to Text Bot

This bot is designed to convert voice messages, videos, and audio files into text. It supports multiple languages and can work with various types of media files, including voice messages, video notes, videos, and audio files.

## Features

- **/start Command**: Greets the user and provides information about the bot.
- **/help Command**: Provides help information about the bot.
- **Message Handling**: The bot accepts voice messages, video notes, videos, and audio files, converts them to text, and sends the text back to the user.
- **Language Selection**: If multiple languages are supported, the bot offers the user a choice of language for transcription.
- **Handling Large Files**: The bot splits large audio files into chunks and transcribes them piece by piece.

## How to Use

1. **Start the Bot**: Use the `/start` command to begin interacting with the bot.
2. **Get Help**: Use the `/help` command to get detailed information about the bot's functionalities.
3. **Send a Message or File**: Send a voice message, video note, video, or audio file to the bot.
4. **Choose Language**: If prompted, select the language for transcription.
5. **Receive Text**: The bot will process the file and send back the transcribed text.

## Installation

To run this bot, follow these steps:

1. **Clone the Repository**:
    ```bash
    https://github.com/axelmiami/vttbot
    cd voicetotextbot
    ```

2. **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Configuration**:
    - Create a `config.py` file with the following content:
    ```python
    TOKEN = 'your-telegram-bot-token'
    ALLOWED_USERS = [123456789] # List of allowed user IDs
    LOG_LEVEL_FILE = 'DEBUG'
    LOG_LEVEL_CONSOLE = 'INFO'
    LOG_FILE = 'bot.log'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_ROTATION = 'midnight'
    TEMP_DIR = 'temp'
    SUPPORTED_LANGUAGES = {'en-US': 'English', 'ru-RU': 'Russian', 'pl-PL': 'Polish'}
    DEFAULT_LANGUAGE = 'en-US'
    MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB
    CHUNK_SIZE = 30 # 30 seconds
    OVERLAP_SECONDS = 10 # 10 seconds
    ```

5. **Run the Bot**:
    ```bash
    python bot.py
    ```

## Configuration

- **TOKEN**: Your Telegram bot token.
- **ALLOWED_USERS**: List of user IDs allowed to interact with the bot.
- **LOG_LEVEL_FILE**: Logging level for the log file.
- **LOG_LEVEL_CONSOLE**: Logging level for the console.
- **LOG_FILE**: Path to the log file.
- **LOG_FORMAT**: Format for log messages.
- **LOG_ROTATION**: Log rotation policy.
- **TEMP_DIR**: Directory for temporary files.
- **SUPPORTED_LANGUAGES**: Dictionary of supported languages.
- **DEFAULT_LANGUAGE**: Default language for transcription.
- **MAX_FILE_SIZE**: Maximum file size allowed for processing.
- **CHUNK_SIZE**: Chunk size in seconds for splitting large audio files.
- **OVERLAP_SECONDS**: Number of seconds to capture from the previous chunk.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Python Telegram Bot](https://github.com/axelmiami/vttbot)
- [SpeechRecognition](https://github.com/Uberi/speech_recognition)
- [pydub](https://github.com/jiaaro/pydub)
- [FFmpeg](https://ffmpeg.org/)

## Contact

For any questions or suggestions, please contact [axel.miami@gmqil.com](mailto:axel.miami@gmail.com).
```
