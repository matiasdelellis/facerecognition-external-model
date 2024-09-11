import os

bind = f"[::]:{os.getenv('PORT', '5000')}"
accesslog = "-"
access_log_format = "%(h)s %(l)s %(u)s %(t)s '%(r)s' %(s)s %(b)s '%(f)s' '%(a)s' in %(D)sµs"  # noqa: E501

workers = int(os.getenv("GUNICORN_WORKERS", 1))
threads = int(os.getenv("GUNICORN_WORKERS", 1))

reload = bool("false")

timeout = int(os.getenv("REQ_TIMEOUT", 300))
