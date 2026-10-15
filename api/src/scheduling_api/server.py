"""The app instance uvicorn serves:  uv run uvicorn scheduling_api.server:app"""

from .main import create_app

app = create_app()
