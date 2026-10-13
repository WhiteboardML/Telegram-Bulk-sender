import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Application configuration and directory management."""
    
    # Root and Directory Paths
    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
    
    # Load environment variables from .env in project root
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

    # Telegram API Credentials
    _raw_api_id = os.getenv("API_ID", "").strip()
    API_ID: Optional[int] = int(_raw_api_id) if _raw_api_id.isdigit() else None
    API_HASH: Optional[str] = os.getenv("API_HASH", "").strip() or None

    # Storage and Runtime Directories
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
    MEDIA_DIR = os.path.join(DATA_DIR, 'media')
    LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
    TELETHON_SESSIONS_DIR = os.path.join(PROJECT_ROOT, 'sessions')

    # Safety & Human Mimicry Settings
    SAFE_DAILY_LIMIT: int = 50
    MIN_DELAY: float = 10.0          # Minimum jitter delay between individual messages (seconds)
    MAX_DELAY: float = 25.0          # Maximum jitter delay between individual messages (seconds)
    BATCH_PAUSE_INTERVAL: int = 15   # Take a longer human break every N messages
    BATCH_PAUSE_MIN: float = 60.0    # Minimum batch pause in seconds (1 minute)
    BATCH_PAUSE_MAX: float = 120.0   # Maximum batch pause in seconds (2 minutes)
    SAFE_BATCH_SIZE: int = 1

    # File Paths
    DATABASE_FILE = os.path.join(DATA_DIR, 'contacts_database.json')
    CONTACTS_CSV = os.path.join(DATA_DIR, 'contacts.csv')
    LOG_FILE = os.path.join(LOGS_DIR, 'telegram_messenger.log')
    REPORT_FILE = os.path.join(DATA_DIR, 'messaging_report.json')
    SAMPLE_CSV = os.path.join(DATA_DIR, 'contacts_sample.csv')

    # Telethon Session Settings
    SESSION_NAME = 'bulk_messenger'
    SESSION_PATH = os.path.join(TELETHON_SESSIONS_DIR, f'{SESSION_NAME}.session')

    # Default Message Template with Spintax
    DEFAULT_TEMPLATE = (
        "{Hello|Hi|Hey} {first_name}! "
        "{Hope you are doing well|Hope you are having a productive day|Reaching out with a quick update}. "
        "This is an automated campaign message from Bulk Messenger."
    )

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary project runtime directories if they do not exist."""
        for directory in [cls.DATA_DIR, cls.SESSIONS_DIR, cls.MEDIA_DIR, cls.LOGS_DIR, cls.TELETHON_SESSIONS_DIR]:
            os.makedirs(directory, exist_ok=True)

    @classmethod
    def validate_credentials(cls) -> bool:
        """Check if valid Telegram API credentials are configured."""
        return bool(cls.API_ID and cls.API_HASH and cls.API_HASH != 'your_api_hash')


if __name__ == "__main__":
    Config.ensure_directories()
    print("Project File Paths:")
    print(f"DATABASE_FILE: {Config.DATABASE_FILE}")
    print(f"CONTACTS_CSV:  {Config.CONTACTS_CSV}")
    print(f"MEDIA_DIR:     {Config.MEDIA_DIR}")
    print(f"LOG_FILE:      {Config.LOG_FILE}")
    print(f"REPORT_FILE:   {Config.REPORT_FILE}")
    print(f"SAMPLE_CSV:    {Config.SAMPLE_CSV}")
    print(f"SESSION_PATH:  {Config.SESSION_PATH}")
    print("\nAPI Credentials configured:", Config.validate_credentials())