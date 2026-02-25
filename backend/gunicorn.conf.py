import os

# Bind to the PORT environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker configuration
workers = 2
worker_class = 'sync'
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'knps-reservation'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (not needed for Render)
# keyfile = None
# certfile = None

# Server hooks
def on_starting(server):
    server.log.info("Starting KNPS Reservation Monitor")

def when_ready(server):
    server.log.info(f"Server is ready. Listening on: {bind}")

def on_exit(server):
    server.log.info("Server shutting down")