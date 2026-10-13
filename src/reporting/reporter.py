import json
import os
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from src.utils.session_manager import SessionManager


class Reporter:
    """Handles messaging report generation, persistence, and console summary presentation."""
    
    def __init__(self, file_path: str = 'messaging_report.json', session_manager: Optional['SessionManager'] = None):
        self.file_path = os.path.abspath(file_path)
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
        
    def generate_report(self, successful_sends: List[Dict], failed_contacts: List[Dict]) -> Dict:
        """Generate and persist a detailed messaging report."""
        report = {
            'summary': {
                'total_successful': len(successful_sends),
                'total_failed': len(failed_contacts),
                'total_processed': len(successful_sends) + len(failed_contacts),
                'report_generated': datetime.now().isoformat()
            },
            'successful_sends': successful_sends,
            'failed_contacts': failed_contacts
        }
        
        # Save cumulative / main report
        try:
            report_dir = os.path.dirname(self.file_path)
            if report_dir:
                os.makedirs(report_dir, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Report saved to {self.file_path}")
        except Exception as e:
            self.logger.error(f"Error saving report to {self.file_path}: {e}")
            
        # Save session-specific report if session is active
        if self.session_manager and self.session_manager.current_session_path:
            try:
                session_report_path = self.session_manager.get_session_path('report.json')
                with open(session_report_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                self.logger.info(f"Session report saved to {session_report_path}")
            except Exception as e:
                self.logger.error(f"Error saving session report: {e}")

        return report
        
    def print_summary(self, summary: Dict, successful_sends: List[Dict], 
                      failed_contacts: List[Dict]) -> None:
        """Print a structured summary of messaging operations to the console."""
        print(f"\n{'='*55}")
        print(f"               MESSAGING SUMMARY")
        print(f"{'='*55}")
        print(f"  Total Contacts Processed : {summary.get('total_contacts', 0)}")
        print(f"  Successful Deliveries    : {summary.get('successful_sends', 0)}")
        print(f"  Failed Deliveries        : {summary.get('failed_sends', 0)}")
        success_rate = summary.get('success_rate', 0.0)
        print(f"  Success Rate             : {success_rate:.1f}%")
        if summary.get('media_attached'):
            print(f"  Media Attachment         : {summary.get('media_attached')}")
        print(f"{'='*55}")
        
        if successful_sends:
            preview_count = min(5, len(successful_sends))
            print(f"\n[✓] SUCCESSFUL SENDS (Showing {preview_count} of {len(successful_sends)}):")
            for i, send in enumerate(successful_sends[:preview_count], 1):
                identifier = send.get('identifier_used', 'N/A')
                id_type = send.get('identifier_type', 'N/A')
                user_id = send.get('user_id', 'N/A')
                media = f" [File: {send.get('media_attached')}]" if send.get('media_attached') else ""
                print(f"  {i}. {send.get('contact_key', 'Unknown')} [{id_type}: {identifier}] -> User ID: {user_id}{media}")
        
        if failed_contacts:
            preview_count = min(5, len(failed_contacts))
            print(f"\n[✗] FAILED SENDS (Showing {preview_count} of {len(failed_contacts)}):")
            for i, fail in enumerate(failed_contacts[:preview_count], 1):
                contact_key = fail.get('contact_key', 'Unknown')
                error_msg = fail.get('error', 'Unknown error')
                print(f"  {i}. {contact_key} -> {error_msg}")
        print(f"{'='*55}\n")