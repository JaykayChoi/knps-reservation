from types import SimpleNamespace

import app as app_module
from config import AppConfig
from services.checks import CheckSummary


def test_web_runner_excludes_ktx_provider(monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, 'create_supabase_client', lambda: object())
    monkeypatch.setattr(app_module, 'MonitorRepository', lambda client: object())
    monkeypatch.setattr(app_module, 'HistoryRepository', lambda client: object())
    monkeypatch.setattr(app_module, 'CatalogRepository',
                        lambda client: SimpleNamespace(list=lambda *args: []))
    monkeypatch.setattr(app_module, 'StatusRepository',
                        lambda client: SimpleNamespace(record_check=lambda now: None))
    monkeypatch.setattr(app_module, 'MaintenanceService',
                        lambda *args: SimpleNamespace(run=lambda: None))

    class RecordingChecks:
        def __init__(self, *args):
            pass

        def run(self, **kwargs):
            calls.append(kwargs)
            return CheckSummary()

    monkeypatch.setattr(app_module, 'CheckService', RecordingChecks)
    dependencies = app_module.build_dependencies(AppConfig())

    dependencies.runner.run_check()

    assert calls[0]['categories'] == {'knps', 'moduparking'}
