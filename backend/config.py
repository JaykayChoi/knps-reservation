from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment():
    backend_dir = Path(__file__).resolve().parent
    load_dotenv(backend_dir.parent / '.env')
    load_dotenv(backend_dir / '.env', override=True)


@dataclass(frozen=True)
class AppConfig:
    check_probability: float = 0.2
    history_retention_days: int = 31

    @classmethod
    def from_env(cls, environ=None):
        if environ is None:
            load_environment()
        environ = os.environ if environ is None else environ
        try:
            probability = float(environ.get('CHECK_PROBABILITY', '0.2'))
        except ValueError:
            probability = 0.2
        return cls(check_probability=max(0.0, min(1.0, probability)))
