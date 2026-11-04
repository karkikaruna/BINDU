"""Start the BINDU backend with one short command:  python run.py

Put this file in the backend/ folder (next to the app/ folder).
Optional flags:  python run.py --port 9000   |   python run.py --no-reload
"""
import argparse

import uvicorn

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--no-reload", action="store_true")
args = parser.parse_args()

uvicorn.run("app.main:app", host=args.host, port=args.port, reload=not args.no_reload)