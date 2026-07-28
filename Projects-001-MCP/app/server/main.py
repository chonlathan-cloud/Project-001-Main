"""Cloud Run ASGI entry point."""

from app.config.settings import get_settings
from app.server.factory import create_app

app = create_app(get_settings())

