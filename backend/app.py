import logging
import random
from dataclasses import dataclass

from flask import Flask
from flask_cors import CORS

from api.checks import blueprint as checks_blueprint
from api.errors import register_error_handlers
from api.search import blueprint as search_blueprint
from api.settings import blueprint as settings_blueprint
from config import AppConfig
from domain.clock import Clock, KST
from notifications.telegram import TelegramSender
from providers.registry import default_registry
from repositories.catalogs import CatalogRepository
from repositories.client import DatabaseUnavailable, create_supabase_client
from repositories.history import HistoryRepository
from repositories.monitors import MonitorRepository
from repositories.status import StatusRepository
from services.checks import CheckService
from services.jobs import CheckRunner, MaintenanceService
from services.notifications import NotificationService

logger = logging.getLogger(__name__)


@dataclass
class Dependencies:
    monitors: object
    history: object
    catalogs: object
    status: object
    runner: object
    maintenance: object
    station_loader: object
    search_knps: object


class UnavailableRepository:
    def __getattr__(self, _name):
        def unavailable(*_args, **_kwargs):
            raise DatabaseUnavailable('Supabase is not configured')
        return unavailable


def build_dependencies(config=None):
    config = config or AppConfig.from_env()
    clock = Clock()
    try:
        client = create_supabase_client()
        monitors = MonitorRepository(client)
        history = HistoryRepository(client)
        catalogs = CatalogRepository(client)
        status = StatusRepository(client)
    except DatabaseUnavailable:
        monitors = history = catalogs = status = UnavailableRepository()
    providers = default_registry(catalogs)
    notifications = NotificationService(monitors, history, TelegramSender(), clock.now)
    checks = CheckService(monitors, providers, notifications, clock.now)
    maintenance = MaintenanceService(history, clock.now, config.history_retention_days)
    def run_check(*, is_test=False):
        try:
            maintenance.run()
        except Exception:
            logger.exception('Monitor maintenance failed')
        current = clock.now().astimezone(KST)
        allow_knps = current.hour in (0, 1) or random.random() < config.check_probability
        summary = checks.run(is_test=is_test, allow_knps=allow_knps,
                             categories={'knps', 'moduparking'})
        try:
            status.record_check(clock.now())
        except Exception:
            logger.exception('Could not record check completion')
        logger.info('Monitor check complete: %s', summary.as_dict())
        return summary
    runner = CheckRunner(run_check)
    from providers import knps, ktx
    return Dependencies(monitors, history, catalogs, status, runner, maintenance,
                        ktx.fetch_stations, knps.fetch_reservations)


def create_app(test_config=None, dependencies=None):
    application = Flask(__name__, static_folder='../frontend', static_url_path='')
    application.config.from_mapping(test_config or {})
    CORS(application)
    application.extensions['dependencies'] = dependencies or build_dependencies()
    application.register_blueprint(settings_blueprint)
    application.register_blueprint(checks_blueprint)
    application.register_blueprint(search_blueprint)
    register_error_handlers(application)

    @application.get('/')
    def index():
        return application.send_static_file('index.html')

    return application


app = create_app()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5000)
