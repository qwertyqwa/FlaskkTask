import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app import create_app
from app.db import ensure_initial_users
from app.db import init_db


@pytest.fixture()
def app(tmp_path):
    test_db = tmp_path / "test.sqlite3"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(test_db),
        }
    )
    with app.app_context():
        init_db()
        ensure_initial_users()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
