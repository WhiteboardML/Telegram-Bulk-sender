import json
import os
from typing import Dict, List, Optional
from src.messaging.template_engine import TemplateEngine


def main_menu() -> str:
    """Display interactive main menu and prompt for selection."""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                   TELEGRAM BULK MESSENGER                        ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                  ║
    ║  1. Run bulk messaging campaign (Spintax, Templates, Media)      ║
    ║  2. Create sample CSV file (data/contacts_sample.csv)            ║
    ║  3. View session history                                         ║
    ║  4. Show setup instructions                                      ║
    ║  5. Exit                                                         ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    return input("Enter choice (1-5): ").strip()


def get_template_input(default_template: str, sample_contacts: Optional[List[Dict]] = None) -> str:
    """Prompt user for a message template with spintax support and show live previews."""
    print("\n" + "=" * 65)
    print("MESSAGE TEMPLATE CONFIGURATION")
    print("=" * 65)
    print("Variables: {first_name}, {last_name}, {name}, {username}, {phone}, {user_id}")
    print("Spintax:   {Hello|Hi|Greetings} or {option1|option2|...}")
    print(f"\nDefault Template:\n  \"{default_template}\"\n")
    
    custom = input("Enter custom template (or press Enter to use default): ").strip()
    template = custom if custom else default_template
    
    # Generate live preview
    sample = sample_contacts[0] if sample_contacts else {'first_name': 'Alex', 'name': 'Alex Smith', 'username': 'alex_tele'}
    print("\n" + "-" * 65)
    print("LIVE TEMPLATE PREVIEW (3 Variations for sample contact):")
    for i in range(1, 4):
        rendered = TemplateEngine.render_template(template, sample)
        print(f"  Variation {i}: \"{rendered}\"")
    print("-" * 65 + "\n")
    
    return template


def get_media_attachment_input(default_media_dir: str = 'data/media') -> Optional[str]:
    """Prompt user for an optional rich media attachment (image, PDF, document, video)."""
    print("=" * 65)
    print("RICH MEDIA ATTACHMENT (Optional)")
    print("=" * 65)
    print("Supported: Images (.jpg, .png), Documents (.pdf, .docx), Audio, Video")
    print(f"You can provide an absolute path or relative to project root.")
    
    # Check if files exist in data/media
    if os.path.isdir(default_media_dir):
        files = [f for f in os.listdir(default_media_dir) if not f.startswith('.')]
        if files:
            print(f"Files found in {default_media_dir}: {', '.join(files[:5])}")

    media_input = input("Enter media file path (or press Enter for text-only): ").strip()
    if not media_input:
        return None
        
    resolved_path = os.path.abspath(media_input)
    if not os.path.isfile(resolved_path):
        # Also check inside data/media
        alt_path = os.path.join(default_media_dir, media_input)
        if os.path.isfile(alt_path):
            resolved_path = os.path.abspath(alt_path)
        else:
            print(f"[!] Warning: Media file not found at '{media_input}'. Proceeding text-only.")
            return None
            
    file_size_mb = os.path.getsize(resolved_path) / (1024 * 1024)
    print(f"[✓] Media attachment verified: {os.path.basename(resolved_path)} ({file_size_mb:.2f} MB)\n")
    return resolved_path


def show_session_history(session_manager) -> None:
    """Display summary of recent sessions recorded in data/sessions/."""
    if not session_manager:
        print("\nSession manager is not available.\n")
        return

    sessions = session_manager.list_sessions()
    if not sessions:
        print("\nNo historical sessions found.\n")
        return
        
    print(f"\nFound {len(sessions)} recorded session(s) (showing up to 10 most recent):")
    print("-" * 65)
    
    for i, session_id in enumerate(sessions[:10], 1):
        metadata_path = os.path.join(session_manager.sessions_dir, session_id, 'metadata.json')
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                success = metadata.get('successful_sends', 'N/A')
                failed = metadata.get('failed_sends', 'N/A')
                total = metadata.get('processed_contacts', metadata.get('total_contacts', 'N/A'))
                start_time = metadata.get('start_time', 'N/A')
                media = metadata.get('media_attached')
                media_str = f" | Media: {media}" if media else ""
                print(f" {i}. Session: {session_id} [{start_time}]")
                print(f"    Delivered: {success} | Failed: {failed} | Total: {total}{media_str}")
                print()
                continue
            except Exception:
                pass
                
        print(f" {i}. Session: {session_id} (metadata unavailable)")
    print("-" * 65 + "\n")


def get_user_confirmation(contacts_count: int, min_delay: float, max_delay: float, 
                           template: str, media_path: Optional[str] = None) -> bool:
    """Prompt user for confirmation before initiating bulk messaging."""
    avg_delay = (min_delay + max_delay) / 2.0
    est_min = (contacts_count * min_delay) / 60.0
    est_max = (contacts_count * max_delay) / 60.0
    
    print(f"\n{'='*65}")
    print(f"CAMPAIGN CONFIRMATION & SAFETY PACING")
    print(f"{'='*65}")
    print(f"  Recipients to message : {contacts_count}")
    print(f"  Random Jitter Pacing  : {min_delay:.1f}s - {max_delay:.1f}s (Average: {avg_delay:.1f}s)")
    print(f"  Estimated Duration    : {est_min:.1f} - {est_max:.1f} minutes")
    if media_path:
        print(f"  Media Attachment      : {os.path.basename(media_path)}")
    else:
        print(f"  Media Attachment      : None (Text-only)")
    print(f"{'='*65}")
    
    confirm = input("\nProceed with campaign? (y/N): ").lower().strip()
    return confirm == 'y'


def setup_instructions() -> None:
    """Display step-by-step setup and configuration guide."""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                       SETUP INSTRUCTIONS                         ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                  ║
    ║ 1. Install dependencies:                                         ║
    ║    pip install -r requirements.txt                               ║
    ║                                                                  ║
    ║ 2. Obtain Telegram API credentials:                             ║
    ║    - Visit https://my.telegram.org/apps                          ║
    ║    - Log in and create an application                            ║
    ║    - Note your API ID (integer) and API HASH (string)            ║
    ║                                                                  ║
    ║ 3. Configure .env file in project root:                          ║
    ║    API_ID=12345678                                               ║
    ║    API_HASH=your_32_char_api_hash_here                           ║
    ║                                                                  ║
    ║ 4. Prepare your contacts in data/contacts.csv:                   ║
    ║    name,username,user_id,phone,company                           ║
    ║    John Doe,john_doe,,+1234567890,Google                         ║
    ║                                                                  ║
    ║ 5. (Optional) Place attachments into data/media/                 ║
    ║                                                                  ║
    ║ 6. Launch application:                                           ║
    ║    python main.py                                                ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)


def create_sample_csv(file_path: str = os.path.join('data', 'contacts_sample.csv')) -> bool:
    """Generate a template contacts.csv file with standard and custom fields."""
    sample_data = (
        "name,username,user_id,phone,company\n"
        "John Doe,john_doe,123456789,+1234567890,Acme Corp\n"
        "Alice Smith,alice_smith,,+1987654321,Tech Innovations\n"
        "Bob Johnson,,,+1122334455,Global Media\n"
        "Carol White,carol_white,987654321,,Fintech Labs\n"
        "Mike Brown,,555666777,+1999888777,Design Co\n"
        "Sarah Davis,sarah_d,111222333,,Cloud Solutions\n"
    )
    
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_data)
        print(f"\n[✓] Sample CSV created: {file_path}")
        print("    You can copy this to 'data/contacts.csv' and populate with your recipients.\n")
        return True
    except Exception as e:
        print(f"\n[✗] Error creating sample CSV: {e}\n")
        return False
