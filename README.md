# 📩 Telegram Bulk Messenger

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Asyncio](https://img.shields.io/badge/Concurrency-Asyncio-informational.svg?logo=python&logoColor=white)](https://docs.python.org/3/library/asyncio.html)
[![Telethon](https://img.shields.io/badge/Protocol-Telethon%20MTProto-blueviolet.svg)](https://github.com/LonamiWebs/Telethon)
[![Tests](https://img.shields.io/badge/Unit%20Tests-7%2F7%20Passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modular, anti-ban Telegram outreach tool written in Python using [Telethon](https://github.com/LonamiWebs/Telethon). It allows you to reliably send personalized bulk messages and media files to contacts from CSV files while keeping your Telegram account safe through Spintax variations, randomized human delays, and contact fallback resolution.

---

## Overview

When automating outreach on Telegram, basic scripts quickly run into rate limits or get accounts restricted. Telegram's spam algorithms easily spot automation patterns:
1. **Identical Message Text:** Sending the exact same message body to 30+ recipients triggers duplicate content detection.
2. **Fixed Timers:** Pausing for an exact interval (e.g., exactly 5.0 seconds every single time) looks like an obvious bot.
3. **Missing or Incomplete Contacts:** Some contacts only have a phone number, others only have an `@username`, and usernames often change. If one identifier fails, simple scripts give up.

I built this project to solve these exact problems. It introduces:
- **Spintax message variation** so every recipient gets a uniquely phrased message.
- **Randomized human pacing** with automated rest breaks to mimic real user behavior.
- **Multi-step contact fallback** that checks User ID $\to$ Username $\to$ Phone number, and saves resolved IDs to a local database for future runs.
- **Rich media attachments** (PDFs, flyers, photos) with personalized captions.
- **Detailed session reports** so you have a complete audit trail of every send.

---

## Technology Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Core programming language, using type hinting and modern standard libraries. |
| **Telethon (`1.40.0`)** | Interacts directly with Telegram's MTProto binary protocol over TCP as a user client. |
| **`asyncio`** | Asynchronous event loop for non-blocking network I/O and graceful pacing. |
| **`python-dotenv`** | Securely loads Telegram API keys from a local `.env` file (12-Factor App methodology). |
| **Regex (`re`)** | Evaluates Spintax syntax recursively to support both simple and nested choices. |
| **Flat JSON & CSV** | Lightweight local data storage for contact caching, session history, and reports. |
| **`unittest`** | Automated unit test suite with asynchronous mocks (`AsyncMock`) to test delivery logic. |

---

## How It Works (Architecture)

The codebase is organized with clear separation of concerns:

```
                            +-----------------------+
                            |   data/contacts.csv   |
                            +-----------+-----------+
                                        |
                                        v
                               [ ContactDatabase ] <---+ (Caches resolved IDs)
                                        |              |
                                        v              |
 [ TemplateEngine ] ---> [ Rendered Spintax Message ]  |
 [ Media Attachment ] -> [ Rich Media Dispatcher ]     |
                                        |              |
                                        v              |
                                [ SafetyManager ]      |
                           (Random Delays & Pauses)    |
                                        |              |
                                        v              |
                         [ TelegramClientWrapper ] ----+
                            (Telethon MTProto)
                                        |
                 +----------------------+----------------------+
                 |                      |                      |
                 v                      v                      v
           [ user_id ]            [ @username ]          [ Phone # ]
        (Direct & Fast)         (Resolve Entity)       (Lookup Phone)
                 \                      |                      /
                  +---------------------+---------------------+
                                        |
                                        v
                          [ Reporter & SessionManager ]
                          (Session logs & JSON reports)
```

---

## Key Features

### 1. Spintax & Dynamic Template Engine
* **File:** `src/messaging/template_engine.py`
* **How it helps:** Instead of sending the same text to everyone, you write templates using Spintax format:
  ```text
  {Hello|Hi|Hey} {first_name}! {Hope you are having a productive week|Reaching out regarding} {company}.
  ```
* Supports nested Spintax (e.g., `{Hello|{Hi|Hey}}`).
* Automatically substitutes `{first_name}`, `{last_name}`, `{name}`, `{username}`, and `{phone}`, plus any custom columns in your CSV (like `{company}` or `{role}`).
* Displays **live preview variations** in the terminal so you can verify how messages look before launching a campaign.

### 2. Randomized Human Pacing & Batch Breaks
* **File:** `src/utils/safety_manager.py`
* **How it helps:** Fixed intervals scream "bot" to spam filters.
* Replaces static timers with randomized delays between `MIN_DELAY` ($10\text{s}$) and `MAX_DELAY` ($25\text{s}$).
* Automatically takes a 1–2 minute rest pause every 15 messages to let network connection buffers settle.

### 3. Rich Media Support
* **Files:** `src/core/telegram_client.py` & `src/messaging/message_sender.py`
* **How it helps:** Plain text often gets low response rates.
* Allows you to attach collateral:
  - Images (`.png`, `.jpg`, `.webp`)
  - Documents & brochures (`.pdf`, `.docx`)
  - Audio & video files
* The recipient receives the file with the personalized, spun message as its caption.

### 4. Smart Contact Fallback & Memory
* **Files:** `src/core/database.py` & `src/messaging/message_sender.py`
* **How it helps:** Client contact lists are often messy or incomplete.
* Tries multiple ways to find the user in priority order:
  1. **User ID:** The numeric Telegram ID (fastest and immune to username changes).
  2. **@username:** Public handle lookup.
  3. **Phone Number:** Lookup by international phone number.
* When a user is resolved, their permanent `user_id` is automatically saved back to `data/contacts_database.json`, making all future sends faster and more reliable.

### 5. Platform Safety & Error Recovery
* **`FloodWaitError`:** When Telegram temporarily rate-limits an account, the script catches the error, sleeps for the exact requested number of seconds, and retries.
* **`PeerFloodError`:** If Telegram restricts an account from messaging non-contacts, the runner immediately halts to protect the account from a permanent ban.
* **`UserPrivacyRestrictedError`:** Gracefully logs when a user has restricted DMs from non-mutual contacts and moves to the next person without crashing.

---

## Project Structure

```
Bulk-messenger/
├── config/
│   ├── __init__.py
│   └── config.py                  # Pacing parameters, paths, and credential validator
├── data/
│   ├── contacts_sample.csv        # Sample CSV template with custom columns
│   ├── contacts.csv               # Your recipient list (ignored in git)
│   ├── contacts_database.json     # Persistent contact memory cache (ignored in git)
│   ├── media/                     # Storage folder for PDF/image attachments
│   ├── messaging_report.json      # Cumulative send report (ignored in git)
│   └── sessions/                  # Timestamped per-run audit logs (ignored in git)
├── logs/
│   └── telegram_messenger.log     # Runtime log file
├── sessions/                      # SQLite-backed Telethon session files (ignored in git)
├── src/
│   ├── core/
│   │   ├── database.py            # Contact storage, enrichment & CSV ingestion
│   │   └── telegram_client.py     # Telethon client wrapper & media sending
│   ├── messaging/
│   │   ├── message_sender.py      # Fallback resolution, dispatch loop & error handling
│   │   └── template_engine.py     # Regex-based Spintax parser & placeholder replacer
│   ├── reporting/
│   │   └── reporter.py            # JSON report generator and console dashboards
│   └── utils/
│       ├── logger.py              # UTF-8 file and console logging
│       ├── safety_manager.py      # Jitter delay calculation, batch pauses, limits
│       ├── session_manager.py     # Creates and manages per-run session folders
│       └── ui.py                  # Interactive CLI menu, live preview, user confirmation
├── tests/
│   ├── __init__.py
│   └── test_core.py               # Automated unit tests (7 passing tests)
├── .env.example                   # Template for Telegram API credentials
├── .gitignore                     # Git ignore rules
├── main.py                        # Application entry point
├── requirements.txt               # Pinned Python dependencies
└── README.md                      # Documentation
```

---

## Setup & Usage

### Prerequisites
- Python 3.10 or higher
- A Telegram account
- Telegram API credentials (`API_ID` and `API_HASH`) from [my.telegram.org/apps](https://my.telegram.org/apps)

### 1. Clone the Repository
```bash
git clone https://github.com/WhiteboardML/Telegram-Bulk-sender.git
cd Telegram-Bulk-sender
```

### 2. Set Up a Virtual Environment
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate       # On macOS / Linux
# or .venv\Scripts\activate    # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Credentials
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your credentials:
```env
API_ID=12345678
API_HASH=your_32_character_api_hash
```

### 5. Prepare Contacts
Create `data/contacts.csv` (or use Option 2 in the menu to create a sample file). You can include standard columns plus any custom metadata:
```csv
name,username,user_id,phone,company
John Doe,john_doe,123456789,+1234567890,Google
Alice Smith,alice_smith,,+1987654321,DeepMind
Bob Johnson,,,+1122334455,MIT
```

### 6. Run the Script
```bash
python main.py
```

```
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
```

---

## Automated Testing

The project includes unit tests covering the template engine, contact memory, safety delays, and mock message sending.

Run the test suite with:
```bash
python -m unittest discover tests
```

Output:
```text
Ran 7 tests in 0.016s

OK
```

---

## License

This project is licensed under the [MIT License](LICENSE).
