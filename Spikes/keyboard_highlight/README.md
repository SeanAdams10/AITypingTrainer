# Keyboard highlight spikes (Logitech ERGO K860)

Three ways to show "press this key" on a drawing of the K860, for the typing tutor.

| Spike | File | What it shows |
|---|---|---|
| 1 | `1_flat_2d.html` | Flat top-down board. Strike key filled amber, keys to hold pale amber. No animation. |
| 2 | `2_tilted_3d.html` | 3D board, 5° off top-down. The chord is pressed in a loop: hold keys go down, strike key goes down and up, hold keys release. Drag to look around, double-click to reset. |
| 3 | `3_finger_guide.html` | Finger guide: which finger, its home key, an animated path from home to the target, a pulsing glow, numbered hold/strike steps. |
| 4 | `4_finger_guide.html` | Spike 3 with a keyboard switch: `?board=k860` (default) or `?board=forge` for the CharaChorder Master Forge. |

All three also outline in blue whatever you are physically pressing, and the
text mode waits for you to type each character correctly (green/red flash in
spikes 2 and 3), so they already behave like a tiny drill.

## Run

No install. Python is only used to serve the folder.

```
python Spikes/keyboard_highlight/open_spike.py 1 G
python Spikes/keyboard_highlight/open_spike.py 2 g
python Spikes/keyboard_highlight/open_spike.py 2 "RCtrl+c" --tilt 4.5
python Spikes/keyboard_highlight/open_spike.py 3 --text "\frac{a}{b}"
python Spikes/keyboard_highlight/open_spike.py 3 G --shift opposite
python Spikes/keyboard_highlight/open_spike.py 4 "{" --board forge
```

Or open an HTML file directly and type into the box at the top.

### What you can ask to show

- A character: `g`, `G` (Left Shift + G), `{` (Left Shift + `[`), `\`, `^`
- A combo, with left/right named: `LShift+g`, `RShift+g`, `RCtrl+c`, `LCtrl+RAlt+x`, `Ctrl++`
- A named key: `Enter`, `Tab`, `Esc`, `Bksp`, `F5`, `Home`, `Space`, or any browser key code (`KeyG`, `Numpad5`)
- Any longer text: it steps through one character at a time

Parameters (URL or launcher): `key`, `text`, `interval` (ms per step, 0 = wait for you),
`shift` (`left` default, `right`, `opposite`), `tilt` and `travel` (spike 2), `ui=0` to hide the bar.

## How it is built

- `shared/k860_layout.js`: the board. Keys are written as a straight ANSI board in key units,
  then each half is rotated 6° around the top of the split and pushed apart. Change `SPLAY_DEG`,
  `GAP_U` or a row list to match the real board.
- `shared/keymap.js`: character → physical keys. A character is a key plus "needs Shift?";
  which Shift is a separate policy.
- `shared/app_shell.js`: parameters, control bar, text stepping, real-keyboard listening.
- `shared/svg_keyboard.js`: the 2D board as SVG (spikes 1 and 3).
- `vendor/three.min.js`: three.js r158 (MIT), for spike 2's WebGL. Vendored so it works offline.

Keys are identified by browser `KeyboardEvent.code` names (`ShiftLeft`, `ControlRight`, `KeyG`):
`code` is the physical key, `key` is the character it produced. That is what makes left and right
Shift/Ctrl distinct for free.

### The Master Forge (spike 4)

`shared/forge_layout.js` holds the 16 switches and the default M4 English layout, copied from
Device Manager's ABC, 123 and fx screens. On the Forge a character lives on a *direction* of a
switch, so the unit that gets highlighted is a (switch, direction) wedge, and the arrow shows which
way to push rather than where to travel. Only the aux switches and thumb 2 make a finger move,
and those get a travel arrow from the resting switch.

Layers are holds, just like Shift: hold a pinky outward for 123, hold the ③ key (right aux 1, south)
for fx, and hold a pinky inward for Shift. `@` is therefore 123 + Shift + the "2" slot, three
fingers at once. When the target is on another layer, the whole board relabels to that layer.
The halves sit 15° apart (`HALF_ANGLE = 7.5` each way).

Checked against the docs: `A` = left pinky east + right index west, `4` = right pinky east +
left middle east, `@` = both pinkies east + left index south.

### Embedding in the PySide6 app later

Each page exposes `window.KB.show("G")`, `KB.showText("abc", 0)` and `KB.clear()`. A
`QWebEngineView` can load the page and call those with `page().runJavaScript(...)`, with `ui=0` to hide the bar.

## Known limits

- Layout is from memory of the K860, not measured: check the 6 key (assumed left half),
  the bottom row (Ctrl fn Win Alt Space | Space Alt Menu Ctrl) and the F-row split.
- The Fn key never reaches software, and Windows keeps the Win key for itself, so those two
  cannot light up from live typing.
- US-ANSI character table only.
- Forge: switch positions are traced from Device Manager, not measured; the per-switch tilt the
  real device has is not drawn. On the 123 layer the arrow switch is really mouse scrolling,
  but it still shows arrows. Chords (e.g. both index fingers south for "the") are not shown.
- Spike 2 logs a three.js notice that the classic `three.min.js` build is deprecated; harmless for a spike.
