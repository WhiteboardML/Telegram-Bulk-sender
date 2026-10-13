import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging


class SessionManager:
    """Manages per-run session directories and metadata persistence."""
    
    def __init__(self, sessions_dir: str = os.path.join('data', 'sessions')):
        self.sessions_dir = os.path.abspath(sessions_dir)
        self.current_session_id: Optional[str] = None
        self.current_session_path: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        
        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            self.logger.debug(f"SessionManager initialized with sessions_dir: {self.sessions_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create sessions directory: {e}")
        
    def create_session(self) -> str:
        """Create a new timestamped session directory and set it as active."""
        self.current_session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_session_path = os.path.join(self.sessions_dir, self.current_session_id)
        
        os.makedirs(self.current_session_path, exist_ok=True)
        self.logger.info(f"Created session: {self.current_session_id}")
        return self.current_session_id
        
    def get_session_path(self, filename: str) -> str:
        """Get the absolute path for a file inside the current active session directory."""
        if not self.current_session_path:
            raise ValueError("No active session created. Call create_session() first.")
        return os.path.join(self.current_session_path, filename)
        
    def save_session_metadata(self, metadata: Dict) -> None:
        """Save session execution metadata to metadata.json."""
        if not self.current_session_path:
            self.logger.warning("Attempted to save metadata without an active session.")
            return
            
        metadata_path = self.get_session_path('metadata.json')
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Session metadata saved to {metadata_path}")
        except Exception as e:
            self.logger.error(f"Failed to save session metadata: {e}")
            
    def list_sessions(self) -> List[str]:
        """List all available session IDs sorted by newest first."""
        if not os.path.exists(self.sessions_dir):
            return []
        entries = [
            d for d in os.listdir(self.sessions_dir)
            if os.path.isdir(os.path.join(self.sessions_dir, d))
        ]
        return sorted(entries, reverse=True)