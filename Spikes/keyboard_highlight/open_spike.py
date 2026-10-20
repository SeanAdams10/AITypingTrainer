"""Open one of the keyboard-highlight spikes in your browser with a key or text.

Examples (from the repo root):
    python Spikes/keyboard_highlight/open_spike.py 1 G
    python Spikes/keyboard_highlight/open_spike.py 2 "RCtrl+c" --tilt 5
    python Spikes/keyboard_highlight/open_spike.py 3 --text "\\frac{a}{b}" --shift opposite
    python Spikes/keyboard_highlight/open_spike.py 4 "{" --board forge

Why a launcher: on Windows, opening a file:// URL hands it to the shell, which
drops the "?key=G" part. Serving the folder on localhost keeps the query intact.
The server stops when you press Ctrl+C.
"""

import argparse
import functools
import http.server
import threading
import urllib.parse
import webbrowser
from pathlib import Path

PAGES = {"1": "1_flat_2d.html", "2": "2_tilted_3d.html", "3": "3_finger_guide.html", "4": "4_finger_guide.html"}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    # Windows can map .js/.css to odd types in the registry; pin them.
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".css": "text/css", ".html": "text/html"}

    def log_message(self, format: str, *args: object) -> None:  # keep the console quiet
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spike", choices=PAGES, help="1 = flat 2D, 2 = tilted 3D, 3 = finger guide, 4 = finger guide with --board")
    ap.add_argument("key", nargs="?", help='key, character or combo: g, G, "{", RCtrl+c, Enter')
    ap.add_argument("--text", help="step through a string one character at a time")
    ap.add_argument("--interval", type=int, help="ms per step for --text (default: wait until typed)")
    ap.add_argument("--shift", choices=["left", "right", "opposite"], help="which Shift capitals use")
    ap.add_argument("--board", choices=["k860", "forge"], help="spike 4: which keyboard (default k860)")
    ap.add_argument("--tilt", type=float, help="spike 2: degrees off top-down (default 5)")
    args = ap.parse_args()

    query = {k: v for k, v in {"key": args.key, "text": args.text, "interval": args.interval,
                               "shift": args.shift, "tilt": args.tilt, "board": args.board}.items() if v is not None}
    folder = Path(__file__).resolve().parent
    handler = functools.partial(QuietHandler, directory=str(folder))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/{PAGES[args.spike]}?{urllib.parse.urlencode(query)}"
    threading.Timer(0.3, webbrowser.open, (url,)).start()
    print(f"Serving {url}\nPress Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
