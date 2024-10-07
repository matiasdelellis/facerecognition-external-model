import os

bind = f"[::]:{os.getenv('PORT', '5000')}"
accesslog = "-"
access_log_format = "%(h)s %(l)s %(u)s %(t)s '%(r)s' %(s)s %(b)s in %(M)sms"  # noqa: E501

workers = int(os.getenv("GUNICORN_WORKERS", 1))
threads = int(os.getenv("GUNICORN_WORKERS", 1))

reload = bool("false")

timeout = int(os.getenv("REQ_TIMEOUT", 300))

def on_starting(server):
    # Check image folder
    folder_path = "images"
    if not os.path.exists(folder_path):
        server.log.debug("Creating directory for temporary files.")
        os.mkdir(folder_path)
    # Clean old files if exists.
    server.log.debug("Cleaning up old temporary files.")
    for filename in os.listdir(folder_path):
        os.unlink(os.path.join(folder_path, filename))
