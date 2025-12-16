from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask import redirect
from flask import url_for

from app import admin
from app import auth
from app import notifications
from app import stats
from app import tickets
from app.db import close_db
from app.db import ensure_initial_users
from app.db import init_app as init_db_app
from app.db import init_db as init_schema


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        DATABASE=str(Path(app.instance_path) / "app.sqlite3"),
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    init_db_app(app)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_schema()
        ensure_initial_users()

    app.register_blueprint(auth.bp)
    app.register_blueprint(tickets.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(admin.bp)

    auth.register_error_handlers(app)

    @app.route("/")
    def index():
        return redirect(url_for("tickets.list_tickets"))

    return app
