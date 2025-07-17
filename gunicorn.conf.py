import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8050')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('WEB_CONCURRENCY', multiprocessing.cpu_count()))
worker_class = 'sync'
worker_connections = 1000
timeout = 60
keepalive = 2

# Restart workers after this many requests, to help with memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = 'info'
accesslog = '-'
errorlog = '-'

# Process naming
proc_name = 'renewable-portfolio-dashboard'

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Memory optimizations
preload_app = True
worker_tmp_dir = '/dev/shm'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190 