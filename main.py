import os

from app import create_app


def main() -> None:
    app = create_app()
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)


if __name__ == "__main__":
    main()

