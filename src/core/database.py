import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from src.utils.session_manager import SessionManager


class ContactDatabase:
    """Manages persistent contact memory, CSV ingestion, dynamic custom fields, and session snapshots."""
    
    def __init__(self, file_path: str = 'contacts_database.json', session_manager: Optional['SessionManager'] = None):
        self.file_path = os.path.abspath(file_path)
        self.session_manager = session_manager
        self.contacts: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
        
    def load_from_file(self) -> None:
        """Load contacts from persistent JSON database file."""
        if not os.path.exists(self.file_path):
            self.logger.info(f"Database file not found at {self.file_path}. Starting with empty memory.")
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.contacts.update(loaded)
            self.logger.info(f"Persistent database loaded: {len(self.contacts)} total contacts in memory.")
        except json.JSONDecodeError:
            self.logger.error("Corrupted JSON encountered in database file; maintaining current memory.")
        except Exception as e:
            self.logger.error(f"Error loading database from {self.file_path}: {e}")
            
    def save_to_file(self) -> None:
        """Save contacts to persistent JSON file and active session folder."""
        try:
            parent_dir = os.path.dirname(self.file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Persistent database saved: {len(self.contacts)} contacts.")
        except Exception as e:
            self.logger.error(f"Error saving database to {self.file_path}: {e}")
        
        # Save snapshot into active session directory if present
        if self.session_manager and self.session_manager.current_session_path:
            try:
                session_contacts_path = self.session_manager.get_session_path('contacts.json')
                with open(session_contacts_path, 'w', encoding='utf-8') as f:
                    json.dump(self.contacts, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Session contact snapshot saved to {session_contacts_path}")
            except Exception as e:
                self.logger.error(f"Error saving session contacts snapshot: {e}")
            
    def add_contact(self, phone: Optional[str] = None, username: Optional[str] = None, 
                    user_id: Optional[int] = None, first_name: Optional[str] = None, 
                    last_name: Optional[str] = None, **custom_fields) -> str:
        """Add or merge a contact in memory, preserving custom template attributes."""
        # Use user_id as primary key if available, else phone or username
        key = str(user_id) if user_id else (phone or (f"@{username.lstrip('@')}" if username else None))
        if not key:
            raise ValueError("Contact must have at least one identifier (user_id, phone, or username).")
        
        if key not in self.contacts:
            self.contacts[key] = {}
            
        contact = self.contacts[key]
        if phone:
            contact['phone'] = phone
        if username:
            contact['username'] = username.lstrip('@')
        if user_id:
            contact['user_id'] = int(user_id)
        if first_name:
            contact['first_name'] = first_name
        if last_name:
            contact['last_name'] = last_name

        # Store any additional custom attributes (e.g., company, title, product)
        for k, v in custom_fields.items():
            if v is not None and str(v).strip():
                contact[k] = str(v).strip()
            
        contact['last_updated'] = datetime.now().isoformat()
        return key

    def update_contact(self, key: str, user_id: Optional[int] = None,
                       username: Optional[str] = None, phone: Optional[str] = None,
                       first_name: Optional[str] = None, last_name: Optional[str] = None,
                       **custom_fields) -> None:
        """Enrich an existing contact with newly resolved Telegram identifiers and custom data."""
        if key not in self.contacts:
            existing_key = self._find_key_by_identifier(key)
            target_key = existing_key or key
            if target_key not in self.contacts:
                self.contacts[target_key] = {}
        else:
            target_key = key

        contact = self.contacts[target_key]
        if user_id:
            contact['user_id'] = int(user_id)
        if username:
            contact['username'] = username.lstrip('@')
        if phone:
            contact['phone'] = phone
        if first_name:
            contact['first_name'] = first_name
        if last_name:
            contact['last_name'] = last_name

        for k, v in custom_fields.items():
            if v is not None and str(v).strip():
                contact[k] = str(v).strip()
            
        contact['last_updated'] = datetime.now().isoformat()
        self.logger.debug(f"Contact '{target_key}' enriched with resolved data: {contact}")

    def _find_key_by_identifier(self, identifier: str) -> Optional[str]:
        """Search in-memory contacts for a matching user_id, username, or phone."""
        clean_id = str(identifier).strip()
        for k, v in self.contacts.items():
            if str(v.get('user_id')) == clean_id:
                return k
            if v.get('username') and v['username'].lower() == clean_id.lstrip('@').lower():
                return k
            if v.get('phone') and v['phone'] == clean_id:
                return k
        return None
        
    def get_contact(self, key: str) -> Optional[Dict]:
        """Retrieve a contact dictionary by its key or any identifier alias."""
        if key in self.contacts:
            return self.contacts[key]
        matching_key = self._find_key_by_identifier(key)
        if matching_key:
            return self.contacts[matching_key]
        return None
        
    def get_all_contacts(self) -> Dict[str, Dict]:
        """Get all stored contacts."""
        return self.contacts
        
    def get_contact_keys(self) -> List[str]:
        """Get list of all contact keys."""
        return list(self.contacts.keys())
        
    def load_from_csv(self, csv_file: str) -> Dict[str, Dict]:
        """Ingest contacts and custom metadata columns from CSV file into memory."""
        ingested_count = 0
        if not os.path.exists(csv_file):
            self.logger.warning(f"CSV file not found: {csv_file}")
            return {}
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user_id_raw = row.get('user_id', '').strip()
                    user_id = int(user_id_raw) if user_id_raw.isdigit() else None
                    phone = row.get('phone', '').strip() or None
                    username = row.get('username', '').strip() or None
                    full_name = row.get('name', '').strip()
                    name_parts = full_name.split() if full_name else []
                    first_name = name_parts[0] if name_parts else None
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else None

                    # Extract any custom fields for template personalization
                    custom_fields = {
                        k: v.strip() for k, v in row.items()
                        if k and k not in ['name', 'username', 'user_id', 'phone'] and v and v.strip()
                    }

                    if user_id or phone or username:
                        self.add_contact(
                            phone=phone,
                            username=username,
                            user_id=user_id,
                            first_name=first_name,
                            last_name=last_name,
                            name=full_name,
                            **custom_fields
                        )
                        ingested_count += 1
                        
            self.logger.info(f"Loaded {ingested_count} contacts with metadata from CSV: {csv_file}")
        except Exception as e:
            self.logger.error(f"Error loading CSV {csv_file}: {e}")
            
        return self.contacts