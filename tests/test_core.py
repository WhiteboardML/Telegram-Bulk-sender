import asyncio
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

from config.config import Config
from src.core.database import ContactDatabase
from src.messaging.message_sender import MessageSender
from src.messaging.template_engine import TemplateEngine
from src.reporting.reporter import Reporter
from src.utils.safety_manager import SafetyManager
from src.utils.session_manager import SessionManager


class TestTelegramBulkMessenger(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.test_dir, 'data')
        self.sessions_dir = os.path.join(self.data_dir, 'sessions')
        self.db_file = os.path.join(self.data_dir, 'contacts_database.json')
        self.report_file = os.path.join(self.data_dir, 'messaging_report.json')
        os.makedirs(self.sessions_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_config_paths_and_directory_creation(self):
        Config.ensure_directories()
        self.assertTrue(os.path.isdir(Config.DATA_DIR))
        self.assertTrue(os.path.isdir(Config.LOGS_DIR))
        self.assertTrue(os.path.isdir(Config.TELETHON_SESSIONS_DIR))
        self.assertTrue(os.path.isdir(Config.MEDIA_DIR))

    def test_session_manager(self):
        sm = SessionManager(sessions_dir=self.sessions_dir)
        session_id = sm.create_session()
        self.assertIsNotNone(session_id)
        self.assertTrue(os.path.isdir(sm.current_session_path))
        
        meta = {'test': 'data', 'count': 42}
        sm.save_session_metadata(meta)
        
        meta_file = sm.get_session_path('metadata.json')
        self.assertTrue(os.path.isfile(meta_file))
        with open(meta_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        self.assertEqual(loaded['count'], 42)
        
        sessions = sm.list_sessions()
        self.assertIn(session_id, sessions)

    def test_reporter_generation_and_session_save(self):
        sm = SessionManager(sessions_dir=self.sessions_dir)
        sm.create_session()
        
        reporter = Reporter(file_path=self.report_file, session_manager=sm)
        successful = [{'contact_key': '123', 'user_id': 123, 'identifier_type': 'user_id'}]
        failed = [{'contact_key': '456', 'error': 'Privacy restricted'}]
        
        report = reporter.generate_report(successful, failed)
        
        self.assertEqual(report['summary']['total_successful'], 1)
        self.assertEqual(report['summary']['total_failed'], 1)
        
        self.assertTrue(os.path.isfile(self.report_file))
        session_report = sm.get_session_path('report.json')
        self.assertTrue(os.path.isfile(session_report))

    def test_safety_manager_limits_and_jitter(self):
        safety = SafetyManager(
            daily_limit=5, 
            min_delay=10.0, 
            max_delay=20.0,
            batch_pause_interval=2,
            batch_pause_min=30.0,
            batch_pause_max=60.0
        )
        contacts = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7']
        limited = safety.limit_contacts(contacts)
        self.assertEqual(len(limited), 5)
        
        # Jitter delay bounds
        for _ in range(10):
            delay = safety.get_jitter_delay()
            self.assertGreaterEqual(delay, 10.0)
            self.assertLessEqual(delay, 20.0)
            
        # Batch pause check
        self.assertFalse(safety.should_take_batch_pause(1))
        self.assertTrue(safety.should_take_batch_pause(2))
        self.assertFalse(safety.should_take_batch_pause(3))
        self.assertTrue(safety.should_take_batch_pause(4))
        
        pause = safety.get_batch_pause_duration()
        self.assertGreaterEqual(pause, 30.0)
        self.assertLessEqual(pause, 60.0)

    def test_spintax_and_template_engine(self):
        # 1. Basic spintax
        spintax_template = "{Hello|Hi|Hey}"
        options = {"Hello", "Hi", "Hey"}
        for _ in range(20):
            res = TemplateEngine.spin_text(spintax_template)
            self.assertIn(res, options)

        # 2. Nested spintax
        nested_template = "{A|{B|C}}"
        nested_options = {"A", "B", "C"}
        for _ in range(20):
            res = TemplateEngine.spin_text(nested_template)
            self.assertIn(res, nested_options)

        # 3. Dynamic variable replacement
        contact = {
            'first_name': 'John',
            'name': 'John Doe',
            'username': 'johndoe',
            'company': 'Google'
        }
        template = "{Hello|Hi} {first_name} from {company}! Your handle is {username}."
        rendered = TemplateEngine.render_template(template, contact)
        self.assertTrue(rendered.startswith("Hello John from Google!") or rendered.startswith("Hi John from Google!"))
        self.assertIn("@johndoe", rendered)

    def test_contact_database_with_custom_metadata(self):
        sm = SessionManager(sessions_dir=self.sessions_dir)
        sm.create_session()
        db = ContactDatabase(file_path=self.db_file, session_manager=sm)
        
        # Add contact with custom metadata fields
        key = db.add_contact(
            username='alice', 
            phone='+1234567890',
            company='OpenAI',
            role='Engineer'
        )
        contact = db.get_contact(key)
        self.assertEqual(contact['company'], 'OpenAI')
        self.assertEqual(contact['role'], 'Engineer')
        
        # CSV loading with custom columns
        csv_path = os.path.join(self.test_dir, 'contacts_custom.csv')
        csv_content = (
            "name,username,user_id,phone,company,plan\n"
            "Bob Smith,bob_smith,,+111222333,Tesla,Premium\n"
        )
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
            
        db.load_from_csv(csv_path)
        bob = db.get_contact('+111222333')
        self.assertIsNotNone(bob)
        self.assertEqual(bob.get('company'), 'Tesla')
        self.assertEqual(bob.get('plan'), 'Premium')

    def test_message_sender_with_media_and_template(self):
        mock_client = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 123456
        mock_user.username = 'alex_user'
        mock_user.phone = '+123456789'
        mock_user.first_name = 'Alex'
        mock_user.last_name = 'V'
        
        mock_client.get_user_info = AsyncMock(return_value=mock_user)
        mock_client.send_message = AsyncMock(return_value=None)
        
        # Create dummy media file
        media_file = os.path.join(self.test_dir, 'sample_flyer.pdf')
        with open(media_file, 'wb') as f:
            f.write(b'%PDF-1.4 dummy content')
            
        db = ContactDatabase(file_path=self.db_file)
        key = db.add_contact(username='alex_user', first_name='Alex')
        
        sender = MessageSender(mock_client, db)
        template = "{Hello|Greetings} {first_name}!"
        
        async def run_bulk():
            return await sender.send_bulk_messages(
                contacts=[key],
                template=template,
                media_path=media_file,
                fixed_delay=0.01
            )
            
        summary = asyncio.run(run_bulk())
        self.assertEqual(summary['total_contacts'], 1)
        self.assertEqual(summary['successful_sends'], 1)
        self.assertEqual(summary['media_attached'], 'sample_flyer.pdf')
        
        # Verify send_message was called with media_path
        mock_client.send_message.assert_called_once()
        args, kwargs = mock_client.send_message.call_args
        self.assertEqual(kwargs.get('media_path'), media_file)
        self.assertTrue(args[1].startswith("Hello Alex!") or args[1].startswith("Greetings Alex!"))


if __name__ == '__main__':
    unittest.main()
