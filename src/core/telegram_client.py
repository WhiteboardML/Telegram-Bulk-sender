import asyncio
import os
import logging
from typing import Optional, Union
from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberBannedError, PhoneNumberInvalidError, 
    UsernameNotOccupiedError, UserPrivacyRestrictedError,
    FloodWaitError, PeerFloodError, UserNotMutualContactError
)
from telethon.tl.types import User


class TelegramClientWrapper:
    """Wrapper around Telethon's TelegramClient with managed lifecycle, entity resolution, and rich media dispatch."""
    
    def __init__(self, api_id: Union[int, str], api_hash: str, 
                 session_name: str = 'bulk_messenger', sessions_dir: str = 'sessions'):
        if not api_id or not api_hash:
            raise ValueError("Both api_id and api_hash must be provided to initialize TelegramClientWrapper.")
            
        self.api_id = int(api_id) if str(api_id).strip().isdigit() else api_id
        self.api_hash = str(api_hash).strip()
        self.sessions_dir = os.path.abspath(sessions_dir)
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        session_path = os.path.join(self.sessions_dir, session_name)
        self.client = TelegramClient(session_path, self.api_id, self.api_hash)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized Telegram client with session path: {session_path}.session")
        
    async def start(self) -> None:
        """Start and authenticate the Telegram client."""
        await self.client.start()
        self.logger.info("Telegram client started and authenticated successfully.")
        
    async def stop(self) -> None:
        """Disconnect the Telegram client gracefully."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.logger.info("Telegram client disconnected.")
            
    async def get_user_info(self, identifier: Union[str, int]) -> Optional[User]:
        """Resolve a Telegram User entity by user_id, @username, or phone number."""
        try:
            # If numeric string, convert to int for ID lookup
            if isinstance(identifier, str) and identifier.isdigit():
                identifier = int(identifier)

            entity = await self.client.get_entity(identifier)
            if isinstance(entity, User):
                return entity
            self.logger.warning(f"Entity found for {identifier} is not a User (type: {type(entity).__name__}).")
                
        except (PhoneNumberInvalidError, UsernameNotOccupiedError, ValueError) as e:
            self.logger.warning(f"Could not resolve Telegram user for identifier '{identifier}': {e}")
        except Exception as e:
            self.logger.error(f"Error fetching user info for '{identifier}': {e}")
            
        return None
        
    async def send_message(self, user: User, message: str, media_path: Optional[str] = None) -> None:
        """
        Send a text message or rich media file (photo, document, video, audio) with an optional caption.
        """
        if media_path and os.path.isfile(media_path):
            self.logger.info(f"Dispatching rich media ({os.path.basename(media_path)}) to user {user.id}")
            await self.client.send_file(user, media_path, caption=message)
        else:
            await self.client.send_message(user, message)