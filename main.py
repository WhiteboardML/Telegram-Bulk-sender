import asyncio
import os
import sys
from datetime import datetime

from config.config import Config
from src.core.database import ContactDatabase
from src.core.telegram_client import TelegramClientWrapper
from src.messaging.message_sender import MessageSender
from src.reporting.reporter import Reporter
from src.utils.logger import setup_logging
from src.utils.safety_manager import SafetyManager
from src.utils.session_manager import SessionManager
from src.utils.ui import (
    create_sample_csv,
    get_media_attachment_input,
    get_template_input,
    get_user_confirmation,
    main_menu,
    setup_instructions,
    show_session_history,
)


class TelegramBulkMessenger:
    """Main orchestrator for Telegram bulk messaging operations."""
    
    def __init__(self):
        self.config = Config()
        self.config.ensure_directories()
        
        self.logger = setup_logging(self.config.LOG_FILE)
        self.session_manager = SessionManager(self.config.SESSIONS_DIR)
        self.database = ContactDatabase(self.config.DATABASE_FILE, self.session_manager)
        
        self.safety_manager = SafetyManager(
            daily_limit=self.config.SAFE_DAILY_LIMIT, 
            min_delay=self.config.MIN_DELAY,
            max_delay=self.config.MAX_DELAY,
            batch_pause_interval=self.config.BATCH_PAUSE_INTERVAL,
            batch_pause_min=self.config.BATCH_PAUSE_MIN,
            batch_pause_max=self.config.BATCH_PAUSE_MAX
        )
        self.reporter = Reporter(self.config.REPORT_FILE, self.session_manager)
        
        self.telegram_client = None
        self.message_sender = None
        
        if self.config.validate_credentials():
            self.telegram_client = TelegramClientWrapper(
                api_id=self.config.API_ID, 
                api_hash=self.config.API_HASH, 
                session_name=self.config.SESSION_NAME,
                sessions_dir=self.config.TELETHON_SESSIONS_DIR
            )
            self.message_sender = MessageSender(self.telegram_client, self.database)
        
    async def run_bulk_messaging(self) -> None:
        """Run the end-to-end bulk messaging pipeline with Spintax, templates, and rich media."""
        if not self.telegram_client or not self.message_sender:
            print("\n[!] Telegram API credentials are not properly configured.")
            print("    Please check your .env file or choose option 4 for setup instructions.\n")
            return

        # 1. Load persistent contact memory
        self.database.load_from_file()

        # 2. Check if contacts CSV file exists
        if not os.path.exists(self.config.CONTACTS_CSV):
            print(f"\n[!] Contacts file not found at: {self.config.CONTACTS_CSV}")
            print(f"    Create a CSV with columns: name,username,user_id,phone")
            print(f"    You can generate a sample via Menu Option 2.\n")
            return

        # 3. Ingest and merge CSV contacts
        self.database.load_from_csv(self.config.CONTACTS_CSV)
        all_contacts = self.database.get_contact_keys()
        
        if not all_contacts:
            print("\n[!] No valid contacts found in CSV. Please verify file format.\n")
            return
            
        print(f"\nLoaded {len(all_contacts)} contact(s) into memory.")
        
        # 4. Apply safety constraints (quota)
        safe_contacts = self.safety_manager.limit_contacts(all_contacts)
        
        # 5. Configure dynamic template with Spintax
        sample_contacts = [self.database.get_contact(k) for k in safe_contacts[:3]]
        template = get_template_input(self.config.DEFAULT_TEMPLATE, sample_contacts)
        
        # 6. Configure optional rich media attachment
        media_path = get_media_attachment_input(self.config.MEDIA_DIR)
        
        # 7. User confirmation & runtime estimate
        if not get_user_confirmation(len(safe_contacts), self.config.MIN_DELAY, 
                                     self.config.MAX_DELAY, template, media_path):
            print("\nOperation cancelled by user.\n")
            return
            
        session_id = self.session_manager.create_session()
        self.logger.info(f"Starting bulk messaging session: {session_id}")
        
        try:
            print("\nConnecting to Telegram...")
            await self.telegram_client.start()
            
            print(f"Dispatching campaign to {len(safe_contacts)} recipients...")
            summary = await self.message_sender.send_bulk_messages(
                contacts=safe_contacts,
                template=template,
                safety_manager=self.safety_manager,
                media_path=media_path
            )
            
            # 8. Record metadata & generate reports
            metadata = {
                'session_id': session_id,
                'start_time': datetime.now().isoformat(),
                'total_contacts': len(all_contacts),
                'processed_contacts': len(safe_contacts),
                'successful_sends': len(self.message_sender.successful_sends),
                'failed_sends': len(self.message_sender.failed_contacts),
                'template_used': template,
                'media_attached': os.path.basename(media_path) if media_path else None,
                'min_delay': self.config.MIN_DELAY,
                'max_delay': self.config.MAX_DELAY,
                'success_rate': summary.get('success_rate', 0.0)
            }
            self.session_manager.save_session_metadata(metadata)
            
            self.reporter.generate_report(
                self.message_sender.successful_sends,
                self.message_sender.failed_contacts
            )
            
            self.reporter.print_summary(
                summary,
                self.message_sender.successful_sends,
                self.message_sender.failed_contacts
            )
            
            # 9. Persist enriched contact database
            self.database.save_to_file()
            print(f"Session {session_id} completed. Reports and contact memory saved.\n")
            
        except Exception as e:
            self.logger.error(f"Error during bulk messaging run: {e}", exc_info=True)
            print(f"\n[✗] An error occurred during messaging: {e}\n")
        finally:
            if self.telegram_client:
                await self.telegram_client.stop()


async def main() -> None:
    """Application CLI entry point."""
    messenger = TelegramBulkMessenger()
    
    while True:
        try:
            choice = main_menu()
            
            if choice == '1':
                await messenger.run_bulk_messaging()
            elif choice == '2':
                create_sample_csv(messenger.config.SAMPLE_CSV)
            elif choice == '3':
                show_session_history(messenger.session_manager)
            elif choice == '4':
                setup_instructions()
            elif choice == '5':
                print("\nGoodbye!\n")
                break
            else:
                print("\nInvalid choice. Please enter a number between 1 and 5.\n")
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting application...")
            break


if __name__ == "__main__":
    asyncio.run(main())