import os

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Wrapped in ASGIStaticFilesHandler so /admin/'s static assets keep working
# in dev now that the app is served by uvicorn instead of `runserver`
# (which handles static files itself under WSGI).
application = ASGIStaticFilesHandler(get_asgi_application())
