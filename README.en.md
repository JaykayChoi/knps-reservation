# KNPS Reservation Auto-Notification System

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange.svg)](https://supabase.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)](https://core.telegram.org/bots/api)

A real-time monitoring system for Korea National Park Service (KNPS) campsite availability that sends Telegram notifications based on user-defined filters and cooldown periods.

> 🌐 **Language**: [한국어](README.md) | **English**

## 🚀 Features

- **Monitor categories**: Select KNPS, Parking or KTX by clicking or dragging a category button at the top of the setting editor. Each setting monitors one category.
- **KTX alerts**: Select stations, one travel date, an inclusive departure-time window, and any combination of general, special and standing availability. Availability is for one adult; purchase tickets on Korail.

### Category migration and KTX setup

Before deploying, apply `supabase/migrations/20260921120000_setting_categories_ktx.sql`
after the previous migrations to the existing database (back it up first).
It adds the `setting_category` enum (`knps`, `moduparking`, `ktx`) and `ktx_options`.
Then apply `20260921160000_remove_ktx_status.sql`. Existing rows with parking lots get a separate
Parking row and their `MONTHLY` history moves to that row. KNPS filters/history
remain in the original row; activation, Telegram configuration and cooldown are
preserved. Splitting can exceed the normal ten-setting creation limit without
losing data. Review the resulting rows and deactivate unwanted KNPS monitors.

Install `backend/requirements.txt`; KTX searches are anonymous and need no Korail
account. The station picker uses Korail's official station list and does not allow
free-text station names. The adapter uses a [pinned korail2 client](https://github.com/dhfhfk/korail2/tree/4b134266fff097ea0fd54e9f760cb128b6c8f878)
for read-only searches. Upstream changes and network errors are reported as failed checks.

Keep the scheduler calling `/api/check`. KTX and Parking bypass the KNPS
probability gate. KTX runs in a background thread; the response includes
`ktx.status` (`queued`, `running`, `no_active_settings`). There is no persisted KTX
status endpoint or refresh panel.
**Test Now sends real Telegram messages**, including delayed KTX messages; it is
not a dry run. The adapter never reserves tickets.

Use a persistent Python server with **one worker process**, for example
`gunicorn --workers 1 --threads 4 app:app` from `backend/`. Do not use multiple
replicas or request-lifetime/serverless hosting: overlap protection is per process.
Requests have connection/read timeouts; searches have a 40-page safety limit
(narrow the time window if exceeded). KTX history distinguishes date, route,
train number, departure time and seat class, and is written only after successful
delivery. Seats found by one check are combined into one Telegram message and split
only above 20 items to stay within message limits. Cooldown 0 repeats alerts; the
existing midnight history reset still applies.

Settings APIs accept `category` and `ktx_options`. Partial updates preserve
the category; switching categories clears unrelated filters. KTX options:

```json
{"departure":"서울","departure_code":"0001","arrival":"부산","arrival_code":"0020","date":"2026-10-01","start_time":"08:00","end_time":"18:00","seat_classes":["general","special","standing"]}
```

Legacy `seat_class` settings remain valid and are mapped to equivalent checkboxes by
the server and UI. Existing rows are not rewritten during deployment.

Offline browser check: `npx playwright test tests/categories.spec.ts` (all requests
intercepted). From `backend/`, run `python -m pytest tests --ignore=tests/test_integration.py`
and `python -m pytest tests/test_integration.py -k "not telegram_test_notification"`.

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

### Notification history at midnight

Apply `supabase/migrations/20260921_truncate_notification_history.sql` before deploying this backend change. A `/api/check` request received during 00:00:00–00:00:59 KST truncates `notification_history` before checking availability. The database function rejects calls outside that minute. Settings with `cooldown_days` set to `0` send notifications without inserting history rows.


