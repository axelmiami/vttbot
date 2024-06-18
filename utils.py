import os
import subprocess
from datetime import datetime
import logging
import json
import time
import speech_recognition as sr
from config import TEMP_DIR, DEFAULT_LANGUAGE, CHUNK_SIZE, OVERLAP_SECONDS
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def ensure_temp_dir(temp_dir):
    """Ensure the temporary directory exists."""
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        logger.debug(f"Created temporary directory {TEMP_DIR}")


def generate_unique_filename(user_id, message_id, extension, temp_dir):
    """Generate a unique filename based on user ID, message ID, and current timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(temp_dir, f"{user_id}_{message_id}_{timestamp}.{extension}")
    logger.debug(f"Generated unique filename {filename}")
    return filename


def convert_ogg_to_wav(ogg_path, wav_path):
    """Convert OGG file to WAV format."""
    command = f"ffmpeg -y -i {ogg_path} {wav_path}"
    subprocess.run(command, shell=True, check=True)
    logger.debug(f"Converted {ogg_path} to {wav_path}")


def extract_audio_from_video(video_path, audio_path):
    """Extract audio from a video file."""
    command = f"ffmpeg -y -i {video_path} {audio_path}"
    subprocess.run(command, shell=True, check=True)
    logger.debug(f"Extracted audio from {video_path} to {audio_path}")


def convert_audio_to_wav(audio_path, wav_path):
    """Convert audio file to WAV format."""
    command = f"ffmpeg -y -i {audio_path} {wav_path}"
    subprocess.run(command, shell=True, check=True)
    logger.debug(f"Converted {audio_path} to {wav_path}")


def transcribe_audio(audio_path, language=DEFAULT_LANGUAGE):
    """Transcribe audio file to text using Google Speech Recognition."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)
    text = recognizer.recognize_google(audio, language=language)
    logger.debug(f"Transcribed audio from {audio_path} with language {language}")
    return text


def clean_up(files):
    """Clean up temporary files."""
    for file in files:
        if os.path.exists(file):
            os.remove(file)
            logger.debug(f"Removed file {file}")
        else:
            logger.warning(f"File {file} not found for cleanup")


def transcribe_large_audio(audio_path, language, chunk_size=CHUNK_SIZE, overlap_seconds=OVERLAP_SECONDS, update=None,
                           context=None, user_loading_message_id=None):
    """Transcribe large audio files by splitting them into chunks."""
    audio = AudioSegment.from_wav(audio_path)
    chunk_length_ms = chunk_size * 1000  # pydub works in milliseconds
    overlap_length_ms = overlap_seconds * 1000

    recognizer = sr.Recognizer()

    for i in range(0, len(audio), chunk_length_ms - overlap_length_ms):
        if i == 0:
            chunk = audio[i:i + chunk_length_ms]
        else:
            chunk = audio[i - overlap_length_ms:i + chunk_length_ms - overlap_length_ms]
        chunk_path = f"{audio_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")

        try:
            logger.debug(f"Transcribing chunk {chunk_path}")
            with sr.AudioFile(chunk_path) as source:
                audio_data = recognizer.record(source)
                chunk_text = recognizer.recognize_google(audio_data, language=language)
                send_long_message(update, chunk_text)
                update_loading_message(update, context, user_loading_message_id)
        except Exception as e:
            logger.error(f"Failed to transcribe chunk {chunk_path}: {str(e)}")
            raise
        finally:
            os.remove(chunk_path)

    # Remove the loading message after processing is complete
    if update and user_loading_message_id.get(update.message.chat_id):
        context.bot.delete_message(chat_id=update.message.chat_id,
                                   message_id=user_loading_message_id.pop(update.message.chat_id))


def send_long_message(update, text):
    """Send a long message by splitting it into parts if it exceeds the Telegram limit."""
    TELEGRAM_MESSAGE_LIMIT = 4096
    for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
        update.message.reply_text(text[i:i + TELEGRAM_MESSAGE_LIMIT])


def update_loading_message(update, context, user_loading_message_id):
    """Update the loading message by deleting the previous one and creating a new one."""
    chat_id = update.message.chat_id
    if chat_id in user_loading_message_id:
        try:
            context.bot.delete_message(
                chat_id=chat_id,
                message_id=user_loading_message_id.pop(chat_id)
            )
        except Exception as e:
            logger.error(f"Failed to delete loading message: {str(e)}")
    message = update.message.reply_text("Processing audio...")
    user_loading_message_id[chat_id] = message.message_id


def load_language_file(language_code):
    """Load the language file based on the provided language code."""
    lang_file_path = os.path.join('lang', f'{language_code}.json')
    try:
        with open(lang_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        # Try to load the language file without the regional code
        base_language_code = language_code.split('-')[0]
        lang_file_path = os.path.join('lang', f'{base_language_code}.json')
        try:
            with open(lang_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"Language file {lang_file_path} not found. Loading default language file.")
            default_lang_file_path = os.path.join('lang', f'{DEFAULT_LANGUAGE}.json')
            with open(default_lang_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)


def get_user_language(update):
    """Get the user's language preference or default to the language set in Telegram."""
    language_code = update.message.from_user.language_code or DEFAULT_LANGUAGE
    # Ensure the language code is in the format xx-XX
    if '-' not in language_code:
        language_code = f"{language_code}-{language_code.upper()}"
    return language_code


def get_translation(user_id, key, update=None, language_code=None, **kwargs):
    """Retrieve the translated text for the given key and user language."""
    if language_code:
        language = language_code
    else:
        language = get_user_language(update)
    lang_data = load_language_file(language)
    return lang_data.get(key, load_language_file(DEFAULT_LANGUAGE).get(key, key)).format(**kwargs)


def transcribe_audio_with_retries(audio_path, language, retries=3, delay=5, update=None, context=None,
                                  user_loading_message_id=None):
    """Attempt to transcribe audio with retries in case of failure."""
    for attempt in range(retries):
        try:
            logger.debug(f"Attempt {attempt + 1} to transcribe audio {audio_path}")
            text = transcribe_audio(audio_path, language)
            send_long_message(update, text)
            return
        except Exception as e:
            logger.error(f"Transcription attempt {attempt + 1} failed: {str(e)}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                update.message.reply_text(get_translation(None, "transcription_failed", update=update, error=str(e)))
                raise
