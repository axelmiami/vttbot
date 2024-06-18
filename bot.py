import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from telegram.error import NetworkError, RetryAfter, TimedOut
from config import TOKEN, ALLOWED_USERS, LOG_LEVEL_FILE, LOG_LEVEL_CONSOLE, LOG_FILE, LOG_FORMAT, LOG_ROTATION, \
    TEMP_DIR, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, MAX_FILE_SIZE, CHUNK_SIZE, OVERLAP_SECONDS
from utils import extract_audio_from_video, transcribe_audio, clean_up, convert_ogg_to_wav, ensure_temp_dir, \
    generate_unique_filename, convert_audio_to_wav, transcribe_large_audio, update_loading_message, send_long_message, \
    load_language_file, get_user_language, get_translation, transcribe_audio_with_retries

import shutil

# Configure logging with timed rotation
file_handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when=LOG_ROTATION, backupCount=5)
file_handler.setLevel(LOG_LEVEL_FILE)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL_CONSOLE)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Dictionary to track user messages and language preferences
user_message_count = {}
user_language_choice = {}
user_files_to_clean = {}
user_loading_message_id = {}
user_help_language_choice = {}


def set_bot_commands(updater):
    """Set bot commands with localized names."""
    commands = [
        BotCommand('help', get_translation(None, 'command_help', language_code=DEFAULT_LANGUAGE))
    ]
    updater.bot.set_my_commands(commands)


def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        update.message.reply_text(get_translation(user_id, "help_message", update=update))
    else:
        update.message.reply_text(get_translation(user_id, "not_authorized", update=update))


def help_command(update: Update, context: CallbackContext):
    """Handle the /help command."""
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        update.message.reply_text(get_translation(user_id, "not_authorized", update=update))
        return

    # Directly send the help message in the user's language
    update.message.reply_text(get_translation(user_id, "help_message", update=update))


def handle_message(update: Update, context: CallbackContext):
    """Handle incoming messages, including voice, video, and document files."""
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    if user_id not in ALLOWED_USERS:
        update.message.reply_text(get_translation(user_id, "not_authorized", update=update))
        user_message_count[user_id] = user_message_count.get(user_id, 0) + 1
        if user_message_count[user_id] > 5:
            update.message.reply_text(get_translation(user_id, "blocked_for_spamming", update=update))
            return
        return

    ensure_temp_dir(TEMP_DIR)

    if update.message.voice or update.message.video_note or update.message.video or update.message.document or update.message.audio:
        file = update.message.voice or update.message.video_note or update.message.video or update.message.document or update.message.audio

        # Log the file size before checking
        logger.debug(f"Received file with size: {file.file_size} bytes")

        # Check the file size
        if file.file_size > MAX_FILE_SIZE:
            file_type = "voice message" if update.message.voice else \
                "video note" if update.message.video_note else \
                    "video" if update.message.video else \
                        "document" if update.message.document else \
                            "audio"
            update.message.reply_text(
                get_translation(user_id, "file_too_big", update=update, file_type=file_type,
                                file_size=file.file_size / (1024 * 1024))
            )
            return

        file_extension = "oga" if update.message.voice else "mp4" if update.message.video or (
                update.message.document and update.message.document.mime_type.startswith('video/')) else "oga"
        file_path = generate_unique_filename(user_id, message_id, file_extension, TEMP_DIR)
        audio_path = generate_unique_filename(user_id, message_id, "wav", TEMP_DIR)

        # Initialize the list of files to clean for this user
        if user_id not in user_files_to_clean:
            user_files_to_clean[user_id] = []

        # Add files to the list for cleanup
        user_files_to_clean[user_id].extend([file_path, audio_path])

        try:
            # Check free disk space
            total, used, free = shutil.disk_usage("/")
            if free < file.file_size:
                update.message.reply_text(get_translation(user_id, "not_enough_space", update=update))
                clean_up(user_files_to_clean.pop(user_id, []))
                return

            # Log before downloading the file
            logger.debug(f"Attempting to download file to {file_path}")

            # Download the file as a document if its size exceeds 20 MB
            if file.file_size > 20 * 1024 * 1024:
                file.get_file().download(custom_path=file_path)
            else:
                file.get_file().download(custom_path=file_path)
            logger.debug(f"Downloaded file to {file_path}")

            if update.message.voice or (update.message.document and update.message.document.mime_type == 'audio/ogg'):
                ogg_path = file_path
                convert_ogg_to_wav(ogg_path, audio_path)
                logger.debug(f"Converted {ogg_path} to {audio_path}")
            elif update.message.video or update.message.video_note or (
                    update.message.document and update.message.document.mime_type.startswith('video/')):
                extract_audio_from_video(file_path, audio_path)
                logger.debug(f"Extracted audio from {file_path} to {audio_path}")
            elif update.message.document and update.message.document.mime_type.startswith('audio/'):
                # Handle other audio files
                convert_audio_to_wav(file_path, audio_path)
                logger.debug(f"Converted {file_path} to {audio_path}")
            elif update.message.audio:
                # Handle audio files sent as audio
                convert_audio_to_wav(file_path, audio_path)
                logger.debug(f"Converted {file_path} to {audio_path}")
            else:
                update.message.reply_text(get_translation(user_id, "unsupported_file", update=update))
                return

            # If multiple languages are supported, offer the user to choose a language
            if len(SUPPORTED_LANGUAGES) > 1:
                user_language_choice[user_id] = audio_path
                keyboard = [
                    [InlineKeyboardButton(lang_name, callback_data=lang_code) for lang_code, lang_name in
                     SUPPORTED_LANGUAGES.items()]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(get_translation(user_id, 'choose_language_transcription', update=update),
                                          reply_markup=reply_markup)
            else:
                # If only one language is supported, use it
                language = DEFAULT_LANGUAGE
                transcribe_audio_with_retries(audio_path, language=language, update=update, context=context,
                                              user_loading_message_id=user_loading_message_id)
                clean_up(user_files_to_clean.pop(user_id, []))
                logger.debug(f"Cleaned up files for user {user_id}")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            update.message.reply_text(get_translation(user_id, "error_occurred", update=update, error=str(e)))
            clean_up(user_files_to_clean.pop(user_id, []))
    else:
        update.message.reply_text(get_translation(user_id, "unsupported_file", update=update))


def button(update: Update, context: CallbackContext):
    """Handle button clicks for language selection."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data.startswith('help_'):
        language = data.split('_')[1]
        lang_data = load_language_file(language)
        help_message = lang_data.get('help_message', 'Help message not found.')
        query.edit_message_text(text=help_message)
        user_help_language_choice.pop(user_id, None)
    else:
        language = data
        audio_path = user_language_choice.pop(user_id, None)

        if audio_path:
            try:
                # Remove language selection buttons
                query.edit_message_text(text=get_translation(user_id, "processing_audio", update=query,
                                                             language=SUPPORTED_LANGUAGES[language]))
                transcribe_audio_with_retries(audio_path, language=language, update=query, context=context,
                                              user_loading_message_id=user_loading_message_id)
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                query.edit_message_text(text=get_translation(user_id, "error_occurred", update=query, error=str(e)))
            finally:
                # Clean up files only after all operations are complete
                clean_up(user_files_to_clean.pop(user_id, []))
                logger.debug(f"Cleaned up files for user {user_id}")
        else:
            try:
                query.edit_message_text(text=get_translation(user_id, "no_audio_found", update=query))
            except telegram.error.BadRequest as e:
                logger.error(f"Failed to edit message: {str(e)}")


def main():
    """Main function to start the bot."""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.voice | Filters.video | Filters.video_note | Filters.document | Filters.audio,
                                  handle_message))
    dp.add_handler(CallbackQueryHandler(button))

    # Set bot commands with localized names
    set_bot_commands(updater)

    while True:
        try:
            updater.start_polling()
            updater.idle()
        except NetworkError as e:
            logger.error(f"Network error occurred: {str(e)}. Retrying in 5 seconds...")
            time.sleep(5)
        except RetryAfter as e:
            logger.error(f"Flood control exceeded. Retry in {e.retry_after} seconds...")
            time.sleep(e.retry_after)
        except TimedOut as e:
            logger.error(f"Request timed out: {str(e)}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}. Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == '__main__':
    main()
