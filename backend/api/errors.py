class ServiceUnavailable(RuntimeError):
    pass


def register_error_handlers(app):
    from repositories.client import DatabaseUnavailable
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(ServiceUnavailable)
    def unavailable(error):
        return {'error': str(error)}, 503

    app.register_error_handler(DatabaseUnavailable, unavailable)

    @app.errorhandler(Exception)
    def unexpected(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception('Unhandled API error')
        return {'error': 'Internal server error'}, 500
