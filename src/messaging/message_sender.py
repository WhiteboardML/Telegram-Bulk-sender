import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union, TYPE_CHECKING
from telethon.errors import (
    PhoneNumberBannedError, PhoneNumberInvalidError, 
    UsernameNotOccupiedError, UserPrivacyRestrictedError,
    FloodWaitError, PeerFloodError, UserNotMutualContactError
)

from src.messaging.template_engine import TemplateEngine

if TYPE_CHECKING:
    from src.core.database import ContactDatabase
    from src.core.telegram_client import TelegramClientWrapper


class MessageSender:
    """Dispatches personalized spintax messages and rich media to contacts with randomized jitter delays."""
    
    def __init__(self, telegram_client: 'TelegramClientWrapper', contact_database: 'ContactDatabase'):
        self.telegram_client = telegram_client
        self.contact_database = contact_database
        self.successful_sends: List[Dict] = []
        self.failed_contacts: List[Dict] = []
        self.logger = logging.getLogger(__name__)
        
    def reset_tracking(self) -> None:
        """Reset success and failure tracking lists before a new campaign."""
        self.successful_sends = []
        self.failed_contacts = []
        
    async def send_to_single_contact(self, contact_key: str, message_text: str, 
                                   media_path: Optional[str] = None, delay: float = 5.0) -> bool:
        """
        Send a personalized message and optional media file to a single contact,
        attempting fallback identifiers in priority order.
        """
        contact = self.contact_database.get_contact(contact_key) or {}
        identifiers = self._get_contact_identifiers(contact, contact_key)
        
        self.logger.info(f"Processing '{contact_key}' with {len(identifiers)} candidate(s): {identifiers}")
        
        for i, identifier in enumerate(identifiers, 1):
            identifier_type = self._get_identifier_type(identifier)
            self.logger.info(f"  Attempt {i}/{len(identifiers)}: using {identifier_type} ({identifier})")
            
            try:
                success = await self._attempt_send(
                    contact_key=contact_key,
                    identifier=identifier,
                    identifier_type=identifier_type,
                    message=message_text,
                    media_path=media_path
                )
                if success:
                    await asyncio.sleep(delay)
                    return True
                    
            except FloodWaitError as e:
                self.logger.warning(f"Telegram FloodWait: pausing {e.seconds}s before retrying.")
                if await self._handle_flood_wait(contact_key, identifier, identifier_type, message_text, media_path, e):
                    await asyncio.sleep(delay)
                    return True
                    
            except PeerFloodError as e:
                self.logger.error(
                    f"PeerFloodError on {contact_key}. "
                    "Telegram has flagged this account for sending messages to non-contacts: "
                    f"{e}"
                )
                self.failed_contacts.append({
                    'contact_key': contact_key,
                    'identifier': identifier,
                    'identifier_type': identifier_type,
                    'error': 'PeerFloodError: Account restricted by Telegram',
                    'timestamp': datetime.now().isoformat()
                })
                break  # Stop trying further identifiers to protect the account
                
            except (UserPrivacyRestrictedError, UserNotMutualContactError) as e:
                self._handle_privacy_error(contact_key, identifier, identifier_type, e)
                continue
                
            except (PhoneNumberBannedError, PhoneNumberInvalidError) as e:
                self._handle_phone_error(contact_key, identifier, identifier_type, e)
                continue
                
            except Exception as e:
                self.logger.error(f"Error sending via {identifier_type} ({identifier}): {e}")
                continue
                
        # All candidate identifiers failed
        self._handle_all_failed(contact_key, identifiers)
        await asyncio.sleep(delay)
        return False
        
    def _get_contact_identifiers(self, contact: Dict, contact_key: str) -> List[Union[int, str]]:
        """Extract available identifiers: user_id -> @username -> phone -> contact_key."""
        identifiers: List[Union[int, str]] = []
        
        # Priority 1: User ID
        if contact.get('user_id'):
            identifiers.append(int(contact['user_id']))
            
        # Priority 2: Telegram Username
        if contact.get('username'):
            username = str(contact['username']).lstrip('@')
            identifiers.append(f"@{username}")
            
        # Priority 3: Phone Number
        if contact.get('phone'):
            identifiers.append(str(contact['phone']).strip())
            
        # Fallback: Original key
        if contact_key not in identifiers and str(contact_key) not in [str(x) for x in identifiers]:
            if str(contact_key).isdigit():
                identifiers.append(int(contact_key))
            else:
                identifiers.append(str(contact_key))
            
        return identifiers
        
    def _get_identifier_type(self, identifier: Union[str, int]) -> str:
        """Classify identifier as user_id, username, or phone."""
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            return "user_id"
        elif str(identifier).startswith("@"):
            return "username"
        else:
            return "phone"
            
    async def _attempt_send(self, contact_key: str, identifier: Union[str, int], 
                            identifier_type: str, message: str, media_path: Optional[str] = None) -> bool:
        """Attempt to resolve entity and dispatch text or rich media."""
        user_info = await self.telegram_client.get_user_info(identifier)
        
        if not user_info:
            self.logger.warning(f"Could not resolve Telegram entity for {identifier_type}: {identifier}")
            return False
            
        await self.telegram_client.send_message(user_info, message, media_path=media_path)
        
        # Enrich persistent contact database with newly resolved attributes
        self.contact_database.update_contact(
            key=contact_key,
            user_id=user_info.id,
            username=getattr(user_info, 'username', None),
            phone=getattr(user_info, 'phone', None),
            first_name=getattr(user_info, 'first_name', None),
            last_name=getattr(user_info, 'last_name', None)
        )
        
        self.successful_sends.append({
            'contact_key': contact_key,
            'identifier_used': identifier,
            'identifier_type': identifier_type,
            'user_id': user_info.id,
            'username': getattr(user_info, 'username', None),
            'message_sent': message,
            'media_attached': os.path.basename(media_path) if media_path else None,
            'timestamp': datetime.now().isoformat()
        })
        
        media_tag = f" [Attachment: {os.path.basename(media_path)}]" if media_path else ""
        self.logger.info(f"SUCCESS: Delivered to '{contact_key}' via {identifier_type} (ID: {user_info.id}){media_tag}")
        return True
            
    async def _handle_flood_wait(self, contact_key: str, identifier: Union[str, int], 
                                 identifier_type: str, message: str, media_path: Optional[str], 
                                 error: FloodWaitError) -> bool:
        """Wait for Telegram flood duration and retry the delivery once."""
        self.logger.warning(f"Waiting {error.seconds}s due to Telegram FloodWait...")
        await asyncio.sleep(error.seconds)
        
        try:
            return await self._attempt_send(contact_key, identifier, identifier_type, message, media_path)
        except Exception as e:
            self.logger.error(f"Retry after FloodWait failed for {contact_key}: {e}")
            return False
            
    def _handle_privacy_error(self, contact_key: str, identifier: Union[str, int], 
                              identifier_type: str, error: Exception) -> None:
        """Handle privacy settings preventing direct messaging."""
        self.logger.warning(f"Privacy restriction for {identifier}: {error}")
        self.failed_contacts.append({
            'contact_key': contact_key,
            'identifier': identifier,
            'identifier_type': identifier_type,
            'error': f'Privacy restricted ({type(error).__name__})',
            'timestamp': datetime.now().isoformat()
        })
        
    def _handle_phone_error(self, contact_key: str, identifier: Union[str, int], 
                            identifier_type: str, error: Exception) -> None:
        """Handle invalid or banned phone numbers."""
        self.logger.warning(f"Phone error for {identifier}: {error}")
        self.failed_contacts.append({
            'contact_key': contact_key,
            'identifier': identifier,
            'identifier_type': identifier_type,
            'error': f'Phone error: {str(error)}',
            'timestamp': datetime.now().isoformat()
        })
        
    def _handle_all_failed(self, contact_key: str, identifiers: List) -> None:
        """Record failure when all fallback candidate identifiers have been exhausted."""
        self.logger.error(f"All candidate identifiers failed for contact: {contact_key}")
        self.failed_contacts.append({
            'contact_key': contact_key,
            'error': f'All {len(identifiers)} fallback identifiers failed',
            'tried_identifiers': [str(ident) for ident in identifiers],
            'timestamp': datetime.now().isoformat()
        })
        
    async def send_bulk_messages(self, contacts: List[str], template: str, 
                               safety_manager=None, media_path: Optional[str] = None, 
                               fixed_delay: Optional[float] = None) -> Dict:
        """
        Dispatch dynamic spintax messages and optional rich media sequentially 
        with randomized jitter delays and human batch breaks.
        """
        self.logger.info(f"Starting bulk campaign to {len(contacts)} recipients with dynamic templates & spintax.")
        if media_path:
            self.logger.info(f"Rich media attachment enabled: {media_path}")
            
        self.reset_tracking()
        
        for i, contact_key in enumerate(contacts, 1):
            contact_data = self.contact_database.get_contact(contact_key) or {}
            
            # 1. Render personalized spintax message for this specific contact
            personalized_message = TemplateEngine.render_template(template, contact_data)
            
            # 2. Determine jitter delay
            if safety_manager:
                current_delay = safety_manager.get_jitter_delay()
            else:
                current_delay = fixed_delay if fixed_delay is not None else 5.0
                
            self.logger.info(f"[{i}/{len(contacts)}] Sending to '{contact_key}' (Jitter delay: {current_delay:.2f}s)")
            await self.send_to_single_contact(
                contact_key=contact_key,
                message_text=personalized_message,
                media_path=media_path,
                delay=current_delay
            )
            
            # 3. Check for human batch break
            if safety_manager and safety_manager.should_take_batch_pause(i) and i < len(contacts):
                pause_time = safety_manager.get_batch_pause_duration()
                self.logger.info(
                    f"Taking a human batch pause of {pause_time:.1f}s after {i} messages to protect account..."
                )
                print(f"\n[⏸] Human batch break: pausing {pause_time:.1f}s to avoid spam flags...")
                await asyncio.sleep(pause_time)
                print("[▶] Resuming messaging...\n")
                
        total = len(contacts)
        successful = len(self.successful_sends)
        failed = len(self.failed_contacts)
        success_rate = (successful / total * 100.0) if total > 0 else 0.0
        
        summary = {
            'total_contacts': total,
            'successful_sends': successful,
            'failed_sends': failed,
            'success_rate': success_rate,
            'media_attached': os.path.basename(media_path) if media_path else None
        }
        
        self.logger.info(f"Campaign complete: {successful}/{total} successful ({success_rate:.1f}%)")
        return summary