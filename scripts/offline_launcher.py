"""Serve an unpacked Traceback recorded demo on localhost using Python alone."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Choose a port from 0 to 65535.")
    directory = Path(__file__).resolve().parent
    if not (directory / "index.html").is_file():
        parser.error(
            "Run START_DEMO.py from the unpacked offline-demo archive. For the source project, use ./start.sh."
        )
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/vtt", ".vtt")
    mimetypes.add_type("font/ttf", ".ttf")

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    try:
        server = ThreadingHTTPServer(
            ("127.0.0.1", args.port), partial(Handler, directory=str(directory))
        )
    except OSError as exc:
        parser.exit(
            1, f"Could not open localhost port {args.port}: {exc}. Try --port 8001.\n"
        )
    with server:
        print(
            f"Traceback recorded demo: http://127.0.0.1:{server.server_port}",
            flush=True,
        )
        print(
            "Recorded pipeline outputs and local packet verification. No model inference service. Press Ctrl+C to stop.",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nDemo stopped.")


if __name__ == "__main__":
    main()
