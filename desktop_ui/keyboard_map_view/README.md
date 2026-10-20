# Keyboard Map View

An on-screen keyboard that shows what to press next, which finger presses it,
and what you are physically pressing right now.

| board   | keyboard                                   |
|---------|--------------------------------------------|
| `k860`  | Logitech ERGO K860                         |
| `forge` | CharaChorder Master Forge (M4 English)     |
| `cc1`   | CharaChorder One (CC English)              |
| `cc2`   | CharaChorder Two (CC English)              |

## Try it

    python -m desktop_ui.keyboard_map_view.keyboard_map_view --board forge --key "{"
    python -m desktop_ui.keyboard_map_view.keyboard_map_view --board k860 --text "\frac{a}{b}"
    python -m desktop_ui.keyboard_map_view.keyboard_map_view --board forge --joined --key T

## Embed it

    from desktop_ui.keyboard_map_view import KeyboardMapView
    view = KeyboardMapView(board="forge", shift="opposite")
    view.show_key("G")          # or "RCtrl+c", "{", "Enter"
    view.show_text("x^{2}")     # steps through; waits for each correct keystroke
    view.set_board("cc2")

Calls made before the page has loaded are queued.

## How it works

- `web/` is plain HTML/SVG/JS with no build step and no network access.
- Each key is a live SVG element, so highlighting a key only changes a CSS
  class. The glow and arrow animations are CSS, so nothing runs per frame.
- `js/keymap.js` maps a character to physical keys (`G` = ShiftLeft + KeyG),
  with the Shift side as a separate policy.
- `js/chorder_layout.js` maps a character to CharaChorder (switch, direction)
  slots. It holds the 123 layer (pinky outward), fx and Shift (pinky inward)
  as needed.
- `js/forge_plan.js` is the Master Forge seen from straight above, generated
  from the CAD-based 3D model in spike 5 (`Spikes/keyboard_highlight`) by
  `tools/make_forge_plan.py`. A top-down view keeps left-right and front-back
  and only drops height, so switch positions and every panel outline are the
  real ones; height only decides which panel is painted over which. Rerun the
  script (needs `shapely`) if the 3D model changes.
- `index.html?board=...` picks the board script. The Python widget hosts the
  page in a `QWebEngineView` and calls `window.KB`.

## Known assumptions

- CC1/CC2 123 and fx layers are assumed to match the Forge's M4 layout.
- Forge: drawn from CharaChorder's CAD (github.com/CharaChorder/CAD-CAM,
  licence CharaChorder BY-SA-CR: non-commercial, credit, share alike). Caps
  are drawn larger than the real 12.5 mm so labels stay readable. The thumb
  switches sit on a steep facet, so their rosettes are turned to the way
  "up the slope" points from above (assumed to be their N).
- CC1/CC2 bodies are traced from top-down photos. CharaChorder switch spacing is widened
  (about 1.45x on CC1/CC2) so the drawn switches never overlap. Per-switch tilt is not drawn.
- The Forge can be drawn apart (cable only) or joined (bracket): `?joined=1`.
