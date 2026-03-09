# KNPS Reservation Auto-Notification System

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange.svg)](https://supabase.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)](https://core.telegram.org/bots/api)

A real-time monitoring system for Korea National Park Service (KNPS) campsite availability that sends Telegram notifications based on user-defined filters and cooldown periods.

> 🌐 **Language**: [한국어](README.md) | **English**

## 🚀 Features

- **Real-time Monitoring**: Continuously checks KNPS campsite availability
- **Smart Notifications**: Telegram alerts based on customizable filters
- **Cooldown Management**: Prevents notification spam with configurable cooldown periods
- **Web Dashboard**: Neobrutalist UI for managing settings and viewing availability
- **Automated Testing**: Comprehensive test suite with pytest
- **Local Development**: Docker-based Supabase for local development
- **Multi-date Range Support**: Filter availability by custom date ranges

## 🏗️ Architecture

```
knps-reservation/
├── backend/          # Python/Flask API server & Core Logic
│   ├── app.py        # API Entry point & Router
│   ├── db.py         # Supabase interface (Settings & History)
│   ├── scraper.py    # KNPS API interaction logic
│   └── notifier.py   # Telegram notification service
├── frontend/         # Web-based settings dashboard
│   └── index.html    # Vanilla JS + Tailwind CSS UI
└── supabase/         # Database migrations & configuration
```

## 🛠️ Tech Stack

### Backend
- **Python 3.13+** - Core programming language
- **Flask** - Web framework for API endpoints
- **Supabase** - PostgreSQL database with real-time capabilities
- **Requests** - HTTP client for KNPS API interactions
- **Telegram Bot API** - Notification delivery

### Frontend
- **Vanilla JavaScript** - No framework dependencies
- **Tailwind CSS** - Utility-first CSS framework
- **Neobrutalist Design** - Bold, functional UI design

### DevOps
- **Docker** - Local Supabase development
- **pytest** - Comprehensive testing framework
- **Playwright** - End-to-end browser testing

## 📦 Installation

### Prerequisites
- Python 3.13 or higher
- Node.js 18+ (for Supabase CLI)
- Docker (for local Supabase)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Backend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd knps-reservation
```

2. Set up Python environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `config.ini` file in the project root:
```ini
[telegram]
bot_token = YOUR_TELEGRAM_BOT_TOKEN
chat_id = YOUR_TELEGRAM_CHAT_ID

[supabase]
url = YOUR_SUPABASE_URL
key = YOUR_SUPABASE_ANON_KEY
```

### Database Setup

1. Start local Supabase:
```bash
cd supabase
supabase start
```

2. Apply migrations:
```bash
supabase db reset
```

### Frontend Setup

The frontend is a single HTML file with no build step. Simply open `frontend/index.html` in a browser.

## 🚀 Usage

### Starting the Application

1. Start the backend server:
```bash
cd backend
python app.py
```

2. Open the frontend dashboard:
- Navigate to `http://localhost:5000` (backend serves the frontend)
- Or open `frontend/index.html` directly in your browser

### Configuration

1. **Telegram Settings**:
   - Obtain a bot token from [@BotFather](https://t.me/botfather)
   - Get your chat ID by messaging your bot
   - Add both to `config.ini`

2. **Filter Settings**:
   - Select parks to monitor
   - Choose facility types (auto-camping, caravan, etc.)
   - Set cooldown period (days between notifications)
   - Define date range for availability checks

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get current user settings |
| POST | `/api/settings` | Update user settings |
| POST | `/api/check` | Manual availability check (TEST prefix) |
| GET | `/api/history` | Get notification history |


## 🧪 Testing

### Running Tests

```bash
cd backend
pytest
```

### Test Coverage

- **Unit Tests**: Database operations, scraping logic, notification formatting
- **Integration Tests**: Flask endpoints, Telegram notifications
- **End-to-End Tests**: Browser automation with Playwright

### Test Structure

```
backend/tests/
├── test_db.py          # Database operation tests
├── test_scraper.py     # Scraping logic tests
├── test_notifier.py    # Notification formatting tests
└── test_integration.py # Integration tests
```

## 📊 Database Schema

### Tables

#### `user_settings`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (Primary Key) | Unique identifier |
| parks | JSONB | Array of park names to monitor |
| facility_types | JSONB | Array of facility types to check |
| cooldown_days | INTEGER | Days between notifications |
| start_date | DATE | Start date for availability checks |
| end_date | DATE | End date for availability checks |
| created_at | TIMESTAMP | Record creation time |

#### `notification_history`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (Primary Key) | Unique identifier |
| identifier | TEXT | Unique notification key (YYYYMMDD_Park_Facility) |
| sent_at | TIMESTAMP | When notification was sent |
| park_name | TEXT | Park name |
| facility_type | TEXT | Facility type |
| available_dates | JSONB | Array of available dates |

#### `system_status`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (Primary Key) | Unique identifier |
| last_check_at | TIMESTAMP | Last system check time |
| updated_at | TIMESTAMP | Last update time |

## 🔧 Deployment

### Production Considerations

1. **Environment Variables**: Use production Supabase credentials
2. **Process Management**: Use gunicorn or similar WSGI server
3. **Cron Jobs**: Schedule regular checks using system cron or Celery
4. **Monitoring**: Implement logging and health checks
5. **Security**: Keep Telegram tokens and Supabase keys secure

### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with comprehensive tests
4. Submit a pull request

### Code Style

- Follow existing patterns in the codebase
- Add tests for new functionality
- Update documentation for API changes
- Use descriptive commit messages

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Korea National Park Service for providing the campsite availability API
- Supabase for the excellent PostgreSQL platform
- Telegram for the Bot API


