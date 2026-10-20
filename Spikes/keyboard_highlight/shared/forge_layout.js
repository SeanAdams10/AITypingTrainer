/*
 * CharaChorder Master Forge (M4G) model: 16 five-way switches, default
 * "M4 English" layout, from Sean's Device Manager screenshots (ABC, 123, fx).
 *
 * Design intuition
 * ----------------
 * On a normal keyboard a character lives on a KEY and your finger travels to
 * it. On the Forge each finger owns one switch and never leaves it; a
 * character lives on a DIRECTION of that switch (north, east, south, west).
 * So the unit we highlight is a "slot" = (switch, direction), and the
 * finger guide shows a push direction instead of a trip across the board.
 * Only the two aux switches (under ring and middle) and thumb 2 need the
 * finger to move off its resting switch.
 *
 * Layers work like Shift: hold a pinky outward for the 123 layer (A2), hold
 * the ③ key for the fx layer (A3), hold a pinky inward for Shift. So "@" is
 * Shift + 123-layer + the "2" slot: three fingers at once.
 *
 * Directions: N = away from you, S = toward you, E/W = screen right/left.
 * For the left hand east is inward; for the right hand west is inward.
 */
(function (global) {
  'use strict';

  const HALF_ANGLE = 7.5;   // each half is turned this much, so 15 degrees between them

  // Switch positions in "switch units" (1 = one switch diameter), traced from
  // Device Manager, which lays the switches out as they sit on the device.
  // finger: who presses it; home: the switch that finger rests on.
  const SWITCHES = {
    L: [
      { id: 'pinky', x: 0.62, y: 1.62, finger: 'LP', w: 1.1 },
      { id: 'ring', x: 1.70, y: 1.07, finger: 'LR' },
      { id: 'middle', x: 2.80, y: 1.07, finger: 'LM' },
      { id: 'index', x: 3.86, y: 1.62, finger: 'LI' },
      { id: 'aux1', x: 1.72, y: 2.17, finger: 'LR', home: 'ring' },
      { id: 'aux2', x: 2.72, y: 2.17, finger: 'LM', home: 'middle' },
      { id: 'thumb1', x: 3.62, y: 2.98, finger: 'LT' },
      { id: 'thumb2', x: 3.08, y: 3.95, finger: 'LT', home: 'thumb1' },
    ],
  };
  // The right half is the mirror image.
  SWITCHES.R = SWITCHES.L.map(s => Object.assign({}, s, { x: -s.x, finger: 'R' + s.finger[1] }));

  // Layer tables: [switch, N, E, S, W]. Names in {} are special keys.
  const A1 = {
    L: { pinky: ['{alt}', '{shift}', '{mirror}', '{num}'], ring: ['{ctrl}', "'", 'u', ','],
      middle: ['{del}', 'i', 'o', '.'], index: ['{bksp}', 'r', 'e', ' '],
      aux1: ['=', '/', '{esc}', '{numpad}'], aux2: ['{up}', '{right}', '{down}', '{left}'],
      thumb1: ['v', 'k', 'c', 'm'], thumb2: ['?', 'w', 'z', 'g'] },
    R: { pinky: ['{alt}', '{num}', '{mirror}', '{shift}'], ring: ['{ctrl}', ';', 's', 'y'],
      middle: ['{tab}', 'j', 'n', 'l'], index: ['{enter}', ' ', 't', 'a'],
      aux1: ['-', '{numpad}', '{fx}', '\\'], aux2: ['{up}', '{right}', '{down}', '{left}'],
      thumb1: ['p', 'h', 'd', 'f'], thumb2: ['x', '{dup}', 'q', 'b'] },
  };
  const A2 = {
    L: { ring: [null, '`', '|', '='], middle: [null, '4', '5', '6'], index: [null, '1', '2', '3'],
      aux1: [null, '{end}', null, '{home}'], thumb1: ['8', '7', '0', '9'], thumb2: [null, 'w', ']', '['] },
    R: { ring: [null, ';', 's', '='], middle: [null, '6', '5', '4'], index: [null, '3', '2', '1'],
      thumb1: ['8', '9', '0', '7'], thumb2: ['x', '[', ']', 'b'] },
  };
  const A3 = {
    L: { middle: [null, 'F4', 'F5', 'F6'], index: [null, 'F1', 'F2', 'F3'],
      thumb1: ['F8', 'F7', 'F10', 'F9'], thumb2: ['F11', null, null, 'F12'] },
    R: { middle: [null, 'F6', 'F5', 'F4'], index: [null, 'F3', 'F2', 'F1'],
      thumb1: ['F8', 'F9', 'F10', 'F7'], thumb2: ['F11', 'F12', null, null] },
  };
  const DIRS = ['N', 'E', 'S', 'W'];
  const SPECIAL = { alt: 'Alt', shift: '⇧', mirror: '◁▷', num: '②', ctrl: 'Ctrl', del: 'Del',
    bksp: '⌫', esc: 'Esc', numpad: '∷', up: '↑', right: '→', down: '↓', left: '←',
    tab: '⇥', enter: '↵', fx: '③', dup: 'dup', end: 'End', home: 'Home' };
  // Browser key names that the specials produce, so live typing can light them.
  const SPECIAL_KEY = { bksp: 'Backspace', del: 'Delete', esc: 'Escape', tab: 'Tab', enter: 'Enter',
    up: 'ArrowUp', right: 'ArrowRight', down: 'ArrowDown', left: 'ArrowLeft', end: 'End', home: 'Home' };

  function label(v) {
    if (v == null) return '';
    if (v === ' ') return '␣';
    const m = /^\{(\w+)\}$/.exec(v);
    return m ? SPECIAL[m[1]] : v;
  }

  function build() {
    const switches = [], byId = {};
    for (const half of ['L', 'R']) {
      const list = SWITCHES[half];
      const cx = list.reduce((a, s) => a + s.x, 0) / list.length;
      const cy = list.reduce((a, s) => a + s.y, 0) / list.length;
      // Left half turns clockwise, right half anticlockwise: the halves open
      // toward you like forearms coming in from the elbows.
      const ang = half === 'L' ? HALF_ANGLE : -HALF_ANGLE;
      const a = ang * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
      const offset = half === 'L' ? -3.3 : 3.3;   // where each half's centre sits
      for (const sw of list) {
        const dx = sw.x - cx, dy = sw.y - cy;
        const o = { id: half + '.' + sw.id, half, name: sw.id, finger: sw.finger,
          home: sw.home ? half + '.' + sw.home : null, w: sw.w || 1, angle: ang,
          x: offset + dx * c - dy * s, y: 2.4 + dx * s + dy * c, slots: {} };
        for (const [layer, table] of [['A1', A1], ['A2', A2], ['A3', A3]]) {
          const row = table[half][sw.id];
          o.slots[layer] = DIRS.map((d, i) => row ? row[i] : null);
        }
        switches.push(o); byId[o.id] = o;
      }
    }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const s of switches) {
      minX = Math.min(minX, s.x - s.w / 2); maxX = Math.max(maxX, s.x + s.w / 2);
      minY = Math.min(minY, s.y - 0.5); maxY = Math.max(maxY, s.y + 0.5);
    }
    const m = 0.7;
    for (const s of switches) { s.x += m - minX; s.y += m - minY; }
    return { switches, byId, width: maxX - minX + 2 * m, height: maxY - minY + 2 * m, label, DIRS,
      fingerNames: global.K860 ? K860.FINGER_NAMES : {} };
  }

  // Find where a value lives: [{sw, dir, layer}], base layer first.
  function find(layout, value) {
    const hits = [];
    for (const layer of ['A1', 'A2', 'A3']) for (const sw of layout.switches) {
      sw.slots[layer].forEach((v, i) => { if (v === value) hits.push({ sw, dir: DIRS[i], layer }); });
    }
    return hits;
  }

  // The pinky pushes that act as modifiers.
  const SHIFT = { L: ['L.pinky', 'E'], R: ['R.pinky', 'W'] };
  const NUM = { L: ['L.pinky', 'W'], R: ['R.pinky', 'E'] };
  const other = h => (h === 'L' ? 'R' : 'L');

  const NAMED = { enter: '{enter}', tab: '{tab}', esc: '{esc}', escape: '{esc}', bksp: '{bksp}',
    backspace: '{bksp}', del: '{del}', delete: '{del}', up: '{up}', down: '{down}', left: '{left}',
    right: '{right}', home: '{home}', end: '{end}', space: ' ', ctrl: '{ctrl}', alt: '{alt}',
    shift: '{shift}' };
  for (let i = 1; i <= 12; i++) NAMED['f' + i] = 'F' + i;

  /*
   * resolve(layout, spec, {shift}) -> { title, char, steps: [{sw, dir, verb, what}] }
   * Shift policy matches the K860 one: left / right / opposite (to the
   * striking hand). The 123 layer uses the pinky on the other hand from the
   * strike, as in the docs ("4" = right pinky east + left middle east).
   */
  function resolve(layout, spec, opts) {
    if (spec == null || spec === '') return null;
    let value = spec;
    if (spec.length > 1) {
      const n = NAMED[spec.toLowerCase()];
      if (n == null) return { text: Array.from(spec) };
      value = n;
    }
    if (value === '\n') value = '{enter}';
    if (value === '\t') value = '{tab}';
    const policy = (opts && opts.shift) || 'left';

    let needShift = false;
    let hits = find(layout, value);
    if (!hits.length && value.length === 1 && global.KeyMap) {
      // Not on any layer as-is: is it the shifted form of something that is?
      const info = KeyMap.CHAR[value];
      if (info && info.shift) {
        const base = Object.keys(KeyMap.CHAR).find(c => KeyMap.CHAR[c].code === info.code && !KeyMap.CHAR[c].shift);
        hits = find(layout, base);
        needShift = hits.length > 0;
      }
    }
    if (!hits.length) return { title: '“' + spec + '” is not on the M4 English layout', char: null, steps: [] };

    const hit = hits[0];
    const strikeHand = hit.sw.half;
    const steps = [];
    const used = new Set();
    function hold(pair, what) {
      used.add(pair[0]);
      steps.push({ sw: layout.byId[pair[0]], dir: pair[1], verb: 'hold', what });
    }
    if (hit.layer === 'A2') hold(NUM[other(strikeHand)], '123 layer');
    if (hit.layer === 'A3') hold(['R.aux1', 'S'], 'fx layer');
    if (needShift) {
      let hand = policy === 'right' ? 'R' : policy === 'opposite' ? other(strikeHand) : 'L';
      if (used.has(SHIFT[hand][0])) hand = other(hand);   // one pinky cannot push two ways at once
      hold(SHIFT[hand], 'Shift');
    }
    steps.push({ sw: hit.sw, dir: hit.dir, verb: 'strike', layer: hit.layer, what: label(hit.sw.slots[hit.layer][DIRS.indexOf(hit.dir)]) });
    const shown = { ' ': 'space' }[value] || label(value);
    const char = spec.length === 1 ? spec : null;
    return { title: (char ? '“' + shown + '”' : shown) + '  =  ' +
      steps.map(s => s.what).join(' + '), char, steps };
  }

  // Which slots to light while you type on the real device.
  function liveSlots(layout, code, key) {
    if (code === 'ShiftLeft') return [['L.pinky', 'E']];
    if (code === 'ShiftRight') return [['R.pinky', 'W']];
    if (code === 'ControlLeft') return [['L.ring', 'N']];
    if (code === 'ControlRight') return [['R.ring', 'N']];
    if (code === 'AltLeft') return [['L.pinky', 'N']];
    if (code === 'AltRight') return [['R.pinky', 'N']];
    let v = key;
    for (const k in SPECIAL_KEY) if (SPECIAL_KEY[k] === key) v = '{' + k + '}';
    if (key === 'Enter') v = '{enter}';
    let hits = find(layout, v).filter(h => h.layer === 'A1' || h.layer === 'A2');
    if (!hits.length && key && key.length === 1 && global.KeyMap) {
      const info = KeyMap.CHAR[key];
      if (info) {
        const base = Object.keys(KeyMap.CHAR).find(c => KeyMap.CHAR[c].code === info.code && !KeyMap.CHAR[c].shift);
        hits = find(layout, base);
      }
    }
    return hits.slice(0, 1).map(h => [h.sw.id, h.dir]);
  }

  global.Forge = { build, resolve, liveSlots, HALF_ANGLE };
})(typeof window !== 'undefined' ? window : globalThis);
