import os

from supabase import Client, create_client


class DatabaseUnavailable(RuntimeError):
    pass


def create_supabase_client(environ=None) -> Client:
    environ = os.environ if environ is None else environ
    url, key = environ.get('SUPABASE_URL'), environ.get('SUPABASE_KEY')
    if not url or not key:
        raise DatabaseUnavailable('Supabase is not configured')
    return create_client(url, key)
