"""Open spike 5, the 3D CharaChorder Master Forge with joystick switches.

Examples (from the repo root):
    python Spikes/keyboard_highlight/open_forge_3d.py
    python Spikes/keyboard_highlight/open_forge_3d.py "{"
    python Spikes/keyboard_highlight/open_forge_3d.py --text "\\frac{a}{b}" --joined
    python Spikes/keyboard_highlight/open_forge_3d.py --wiggle --fps

Why it serves the repo root rather than the spike folder: the page reuses the
Forge layout, key map and control bar from desktop_ui/keyboard_map_view/web,
so the server has to reach both folders. The server stops on Ctrl+C.
"""

import argparse
import functools
import http.server
import threading
import urllib.parse
import webbrowser
from pathlib import Path

PAGE = "Spikes/keyboard_highlight/5_forge_3d.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    # Windows can map .js/.css to odd types in the registry; pin them.
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".css": "text/css", ".html": "text/html"}

    def log_message(self, format: str, *args: object) -> None:  # keep the console quiet
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("key", nargs="?", help='character or key: a, G, "{", Enter')
    ap.add_argument("--text", help="step through a string one character at a time")
    ap.add_argument("--interval", type=int, help="ms per step for --text (default: wait until typed)")
    ap.add_argument("--shift", choices=["left", "right", "opposite"], help="which Shift capitals use")
    ap.add_argument("--joined", action="store_true", help="halves clipped together")
    ap.add_argument("--wiggle", action="store_true", help="push every switch round once on load")
    ap.add_argument("--no-led", action="store_true", help="LED pods off")
    ap.add_argument("--fps", action="store_true", help="show ms per frame")
    args = ap.parse_args()

    query = {k: v for k, v in {"key": args.key, "text": args.text, "interval": args.interval,
                               "shift": args.shift}.items() if v is not None}
    for flag, name, value in ((args.joined, "joined", "1"), (args.wiggle, "wiggle", "1"),
                              (args.no_led, "led", "0"), (args.fps, "fps", "1")):
        if flag:
            query[name] = value
    root = Path(__file__).resolve().parents[2]
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/{PAGE}?{urllib.parse.urlencode(query)}"
    threading.Timer(0.3, webbrowser.open, (url,)).start()
    print(f"Serving {url}\nPress Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
