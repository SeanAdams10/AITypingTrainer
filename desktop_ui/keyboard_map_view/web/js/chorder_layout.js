/*
 * CharaChorder devices: Master Forge (M4G), CharaChorder One (CC1) and
 * CharaChorder Two (CC2). One model, three device descriptions.
 *
 * Design intuition
 * ----------------
 * On a normal keyboard a character lives on a KEY and your finger travels to
 * it. On a CharaChorder each finger owns one switch and mostly stays there;
 * a character lives on a DIRECTION of that switch (north, east, south, west,
 * or a press down into the device). So the unit we highlight is a "slot" =
 * (switch, direction), and the guide shows a push direction, not a trip.
 *
 * Layers work like Shift: hold a pinky outward for the 123 layer (A2), hold
 * the fx access for the fx layer (A3), hold a pinky inward for Shift. So "@"
 * is Shift + 123 + the "2" slot: three fingers at once.
 *
 * The three devices share that logic. What differs is data:
 *  - where the switches sit and what the body looks like,
 *  - the default layout (Forge: "M4 English"; CC1/CC2: "CC English"),
 *  - how you reach fx (Forge: the ③ key; CC1/CC2: press a pinky down).
 *
 * Directions: N = away from you, S = toward you, E/W = screen right/left,
 * D = press down. For the left hand east is inward; for the right, west.
 */
(function (global) {
  'use strict';

  const DIRS = ['N', 'E', 'S', 'W', 'D'];

  // ---- layouts --------------------------------------------------------------
  // Rows are [N, E, S, W, D]; missing entries mean "nothing there".
  // Names in {} are special keys.

  // Master Forge, "M4 English", from Device Manager (ABC, 123, fx screens).
  const M4 = {
    A1: {
      L: { pinky: ['{alt}', '{shift}', '{mirror}', '{num}'], ring: ['{ctrl}', "'", 'u', ','],
        middle: ['{del}', 'i', 'o', '.'], index: ['{bksp}', 'r', 'e', ' '],
        aux1: ['=', '/', '{esc}', '{numpad}'], aux2: ['{up}', '{right}', '{down}', '{left}'],
        thumb1: ['v', 'k', 'c', 'm'], thumb2: ['?', 'w', 'z', 'g'] },
      R: { pinky: ['{alt}', '{num}', '{mirror}', '{shift}'], ring: ['{ctrl}', ';', 's', 'y'],
        middle: ['{tab}', 'j', 'n', 'l'], index: ['{enter}', ' ', 't', 'a'],
        aux1: ['-', '{numpad}', '{fx}', '\\'], aux2: ['{up}', '{right}', '{down}', '{left}'],
        thumb1: ['p', 'h', 'd', 'f'], thumb2: ['x', '{dup}', 'q', 'b'] },
    },
    A2: {
      L: { ring: [null, '`', '|', '='], middle: [null, '4', '5', '6'], index: [null, '1', '2', '3'],
        aux1: [null, '{end}', null, '{home}'], thumb1: ['8', '7', '0', '9'], thumb2: [null, 'w', ']', '['] },
      R: { ring: [null, ';', 's', '='], middle: [null, '6', '5', '4'], index: [null, '3', '2', '1'],
        thumb1: ['8', '9', '0', '7'], thumb2: ['x', '[', ']', 'b'] },
    },
    A3: {
      L: { middle: [null, 'F4', 'F5', 'F6'], index: [null, 'F1', 'F2', 'F3'],
        thumb1: ['F8', 'F7', 'F10', 'F9'], thumb2: ['F11', null, null, 'F12'] },
      R: { middle: [null, 'F6', 'F5', 'F4'], index: [null, 'F3', 'F2', 'F1'],
        thumb1: ['F8', 'F9', 'F10', 'F7'], thumb2: ['F11', 'F12', null, null] },
    },
  };

  // CC1 / CC2, "CC English" base layer, from the dot i/o screenshot (CC1 view).
  // The 123 and fx layers are assumed to match M4 English switch for switch
  // (M4 English was derived from CC English: the Forge moved thumb 3's keys
  // to aux 1). Pinky press-down is the fx access on these devices.
  const CC = {
    A1: {
      L: { pinky: ['{alt}', '{shift}', '{mirror}', '{num}', '{fx}'], ring: ['{ctrl}', "'", 'u', ','],
        middle: ['{del}', 'i', 'o', '.'], index: ['{bksp}', 'r', 'e', ' '],
        thumb1: ['v', 'k', 'c', 'm'], thumb2: ['{click}', 'w', 'z', 'g'],
        thumb3: ['-', '/', '{esc}', '{win}'],
        mouse: ['{mup}', '{mright}', '{mdown}', '{mleft}'], arrow: ['{up}', '{right}', '{down}', '{left}'] },
      R: { pinky: ['{alt}', '{num}', '{mirror}', '{shift}', '{fx}'], ring: ['{ctrl}', ';', 's', 'y'],
        middle: ['{tab}', 'j', 'n', 'l'], index: ['{enter}', ' ', 't', 'a'],
        thumb1: ['p', 'h', 'd', 'f'], thumb2: ['x', '{dup}', 'q', 'b'],
        thumb3: ['?', '{win}', '{esc}', '{rclick}'],
        mouse: ['{mup}', '{mright}', '{mdown}', '{mleft}'], arrow: ['{up}', '{right}', '{down}', '{left}'] },
    },
    A2: {
      L: Object.assign({}, M4.A2.L, { thumb3: M4.A2.L.aux1, aux1: undefined }),
      R: Object.assign({}, M4.A2.R),
    },
    A3: M4.A3,
  };

  // ---- devices --------------------------------------------------------------
  // Switch positions are for the LEFT half in switch pitches (x right, y
  // toward you); the right half is mirrored. home: the switch that finger
  // rests on, when it is not this one.

  // The Forge is drawn from its 3D model, not traced. forge_plan.js is the
  // CAD-based 3D Forge from spike 5 projected straight down (see
  // tools/make_forge_plan.py): every folded panel, the frame, the rails and
  // where each cap top sits. A top-down view keeps x and the front-back
  // distance and only loses height, so positions here are the real ones, in
  // switch pitches (18 mm). Each half is turned and placed exactly as the 3D
  // view does it, so the two views agree switch for switch.
  const PLAN = global.FORGE_PLAN || { switches: {}, shapes: [], pivot: { x: 0, y: 0 } };
  const FORGE_FINGERS = [
    // id, finger, the switch that finger rests on when it is not this one
    ['pinky', 'P'], ['ring', 'R'], ['middle', 'M'], ['index', 'I'],
    ['aux1', 'R', 'ring'], ['aux2', 'M', 'middle'], ['thumb1', 'T'], ['thumb2', 'T', 'thumb1'],
  ];
  const FORGE = {
    name: 'CharaChorder Master Forge',
    halfAngle: 7.5,          // halves 15 degrees apart
    offset: 4.2,             // half the distance between the two halves
    pivot: PLAN.pivot,
    fxAccess: () => ['R.aux1', 'S'],
    layout: M4,
    // rot: which way the switch's "north" points from above, relative to the
    // half. Deck switches point straight back; the thumb switches sit on a
    // steep facet facing the other half, so "up the slope" points outward.
    switches: FORGE_FINGERS.map(([id, finger, home]) => Object.assign({ id, finger, home },
      PLAN.switches[id] || { x: 0, y: 0 })),
    shapes: PLAN.shapes,
    // Left half carries the CharaChorder mark, right half the Forge mark, on the
    // flat logo face. The Forge mark is CharaChorder's own artwork (a mask).
    logo: PLAN.logo && Object.assign({ L: 'cc', R: 'forge' }, PLAN.logo),
    forgeMask: PLAN.forgeMask,
    // Separate halves are joined only by a USB-C cable from the inner back corner.
    cable: PLAN.cable,
    // Or clip them together, as the 3D view does: the halves move in and a
    // black bridge bar across the middle (under both halves) holds them.
    joined: { offset: 3.32, shapes: [['bracket', [[[1.4, -0.3], [3.6, -0.3], [3.6, 0.3], [1.4, 0.3]]]]] },
  };

  // CC1 and CC2 share a shape: a round dome per half, joined by a centre bar
  // that carries a cable pod. Positions are measured from top-down photos and
  // spread out by about 1.45x so the drawn switches never overlap (real caps
  // sit at different heights, so they can overlap in a plan view). Back row:
  // ring, middle. Front row: mouse (ring's second switch), arrow (middle's),
  // index. The pinky sits out at the top-outer edge, and the three thumb
  // switches run down the inner edge.
  const CC_SWITCHES = [
    { id: 'pinky', x: 1.65, y: 1.52, finger: 'P', w: 1.1 },
    { id: 'ring', x: 3.47, y: 0.74, finger: 'R' },
    { id: 'middle', x: 5.32, y: 0.74, finger: 'M' },
    { id: 'index', x: 6.79, y: 1.69, finger: 'I' },
    { id: 'mouse', x: 3.65, y: 1.78, finger: 'R', home: 'ring' },
    { id: 'arrow', x: 5.4, y: 1.78, finger: 'M', home: 'middle' },
    { id: 'thumb1', x: 7.06, y: 3.83, finger: 'T' },
    { id: 'thumb2', x: 6.36, y: 5.28, finger: 'T', home: 'thumb1' },
    { id: 'thumb3', x: 5.66, y: 6.41, finger: 'T', home: 'thumb1' },
  ];
  const CC_BODY = {
    halfAngle: 0, offset: 6.75, pivot: { x: 4.3, y: 4.0 },
    fxAccess: hand => [hand + '.pinky', 'D'],
    layout: CC,
    dome: { x: 4.3, y: 4.0, rx: 3.9, ry: 3.6 },
    // Centre bar between the domes, level with the front finger row; the
    // cable from each dome's inner jack runs to the pod in its middle.
    bar: { y: 2.95, h: 1.3 },
    cable: { x: 7.75, y: 2.75 },
    shapes: [],
  };

  // CC1: glossy black domes, silver caps, brushed aluminium bar.
  const CC1 = Object.assign({}, CC_BODY, { name: 'CharaChorder One (CC1)', switches: CC_SWITCHES });

  // CC2: matte black domes and caps, black bar; the pinky switch is wider.
  const CC2 = Object.assign({}, CC_BODY, { name: 'CharaChorder Two (CC2)',
    switches: CC_SWITCHES.map(s => (s.id === 'pinky' ? Object.assign({}, s, { w: 1.3 }) : s)) });

  const DEVICES = { forge: FORGE, cc1: CC1, cc2: CC2 };

  // ---- labels -----------------------------------------------------------------
  const SPECIAL = { alt: 'Alt', shift: '⇧', mirror: '◁▷', num: '②', ctrl: 'Ctrl', del: 'Del',
    bksp: '⌫', esc: 'Esc', numpad: '∷', up: '↑', right: '→', down: '↓', left: '←',
    tab: '⇥', enter: '↵', fx: '③', dup: 'dup', end: 'End', home: 'Home', win: 'Win',
    click: 'Click', rclick: 'R-Clk', mup: '⇡', mright: '⇢', mdown: '⇣', mleft: '⇠' };
  const SPECIAL_KEY = { bksp: 'Backspace', del: 'Delete', esc: 'Escape', tab: 'Tab', enter: 'Enter',
    up: 'ArrowUp', right: 'ArrowRight', down: 'ArrowDown', left: 'ArrowLeft', end: 'End', home: 'Home' };
  const FINGER_NAMES = { LP: 'left pinky', LR: 'left ring', LM: 'left middle', LI: 'left index',
    LT: 'left thumb', RT: 'right thumb', RI: 'right index', RM: 'right middle', RR: 'right ring',
    RP: 'right pinky' };

  function label(v) {
    if (v == null) return '';
    if (v === ' ') return '␣';
    const m = /^\{(\w+)\}$/.exec(v);
    return m ? SPECIAL[m[1]] : v;
  }

  // ---- geometry ---------------------------------------------------------------
  // opts.joined: draw the halves clipped together, on boards that allow it.
  function build(deviceName, opts) {
    const dev = DEVICES[deviceName] || FORGE;
    const joined = !!(opts && opts.joined && dev.joined);
    const offset = joined ? dev.joined.offset : dev.offset;
    const switches = [], byId = {}, shapes = [], domes = [], cableEnds = [], logos = [];
    for (const half of ['L', 'R']) {
      const sign = half === 'L' ? 1 : -1;
      // Left half turns clockwise, right half anticlockwise: the halves open
      // toward you like forearms coming in from the elbows.
      const ang = sign * dev.halfAngle;
      const a = ang * Math.PI / 180, c = Math.cos(a), sn = Math.sin(a);
      // Left-half plan point -> board point (mirror for the right half, turn, place).
      const place = (x, y) => {
        const dx = sign * (x - dev.pivot.x), dy = y - dev.pivot.y;
        return { x: -sign * offset + dx * c - dy * sn, y: 3 + dx * sn + dy * c };
      };
      // Joining pieces go under both halves, so they show only in the gap.
      // A shape is [class, rings, fill]: several rings make holes (drawn even-odd).
      const placeShape = ([cls, rings, fill]) => [cls, rings.map(r => r.map(([x, y]) => place(x, y))), fill];
      if (joined) for (const sh of dev.joined.shapes) shapes.unshift(placeShape(sh));
      for (const sh of dev.shapes) shapes.push(placeShape(sh));
      if (dev.dome) domes.push(Object.assign(place(dev.dome.x, dev.dome.y), { rx: dev.dome.rx, ry: dev.dome.ry }));
      if (dev.cable && !joined) cableEnds.push(place(dev.cable.x, dev.cable.y));
      if (dev.logo) logos.push(Object.assign(place(dev.logo.x, dev.logo.y), { kind: dev.logo[half], angle: ang,
        size: dev.logo.size }));
      for (const sw of dev.switches) {
        const p = place(sw.x, sw.y);
        const o = { id: half + '.' + sw.id, half, name: sw.id, finger: half + sw.finger,
          home: sw.home ? half + '.' + sw.home : null, w: sw.w || 1, angle: ang + sign * (sw.rot || 0),
          turn: sign * (sw.rot || 0), x: p.x, y: p.y, slots: {} };
        for (const layer of ['A1', 'A2', 'A3']) {
          const row = (dev.layout[layer][half] || {})[sw.id];
          o.slots[layer] = DIRS.map((d, i) => (row && row[i] != null ? row[i] : null));
        }
        switches.push(o); byId[o.id] = o;
      }
    }
    // Bounds over everything that gets drawn.
    const pts = [];
    for (const s of switches) pts.push({ x: s.x - 0.55 * s.w, y: s.y - 0.55 }, { x: s.x + 0.55 * s.w, y: s.y + 0.55 });
    for (const [, rings] of shapes) for (const r of rings) pts.push(...r);
    for (const d of domes) pts.push({ x: d.x - d.rx, y: d.y - d.ry }, { x: d.x + d.rx, y: d.y + d.ry });
    for (const e of cableEnds) pts.push({ x: e.x, y: e.y - 0.9 });
    const minX = Math.min(...pts.map(p => p.x)), maxX = Math.max(...pts.map(p => p.x));
    const minY = Math.min(...pts.map(p => p.y)), maxY = Math.max(...pts.map(p => p.y));
    const m = 0.45;
    const shift = p => { p.x += m - minX; p.y += m - minY; };
    switches.forEach(shift); shapes.forEach(([, rings]) => rings.forEach(r => r.forEach(shift))); domes.forEach(shift);
    cableEnds.forEach(shift); logos.forEach(shift);
    const bar = dev.bar && domes.length === 2 ?
      { x1: domes[0].x, x2: domes[1].x, y: domes[0].y + dev.bar.y - dev.dome.y, h: dev.bar.h } : null;
    return { device: deviceName in DEVICES ? deviceName : 'forge', dev, name: dev.name, switches, byId, shapes,
      domes, bar, cableEnds, logos, joined,
      width: maxX - minX + 2 * m, height: maxY - minY + 2 * m, label, DIRS, fingerNames: FINGER_NAMES };
  }

  // ---- what to press ------------------------------------------------------------
  // Find where a value lives: [{sw, dir, layer}], base layer first.
  function find(layout, value) {
    const hits = [];
    for (const layer of ['A1', 'A2', 'A3']) for (const sw of layout.switches) {
      sw.slots[layer].forEach((v, i) => { if (v === value) hits.push({ sw, dir: DIRS[i], layer }); });
    }
    return hits;
  }

  // The pinky pushes that act as modifiers (same on all three devices).
  const SHIFT = { L: ['L.pinky', 'E'], R: ['R.pinky', 'W'] };
  const NUM = { L: ['L.pinky', 'W'], R: ['R.pinky', 'E'] };
  const other = h => (h === 'L' ? 'R' : 'L');

  const NAMED = { enter: '{enter}', tab: '{tab}', esc: '{esc}', escape: '{esc}', bksp: '{bksp}',
    backspace: '{bksp}', del: '{del}', delete: '{del}', up: '{up}', down: '{down}', left: '{left}',
    right: '{right}', home: '{home}', end: '{end}', space: ' ', ctrl: '{ctrl}', alt: '{alt}',
    shift: '{shift}', win: '{win}' };
  for (let i = 1; i <= 12; i++) NAMED['f' + i] = 'F' + i;

  // The unshifted character on the same US key ("{" -> "["), or null.
  function unshifted(ch) {
    const info = global.KeyMap && KeyMap.CHAR[ch];
    if (!info || !info.shift) return null;
    return Object.keys(KeyMap.CHAR).find(c => KeyMap.CHAR[c].code === info.code && !KeyMap.CHAR[c].shift) || null;
  }

  /*
   * resolve(layout, spec, {shift}) -> { title, char, steps: [{sw, dir, verb, what, layer}] }
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
    if (!hits.length && value.length === 1) {
      // Not on any layer as-is: is it the shifted form of something that is?
      const base = unshifted(value);
      if (base) { hits = find(layout, base); needShift = hits.length > 0; }
    }
    if (!hits.length) {
      return { title: '“' + spec + '” is not on the ' + layout.name + ' default layout', char: null, steps: [] };
    }

    const hit = hits[0];
    const strikeHand = hit.sw.half;
    const steps = [];
    const used = new Set();
    function hold(pair, what) {
      used.add(pair[0]);
      steps.push({ sw: layout.byId[pair[0]], dir: pair[1], verb: 'hold', what });
    }
    if (hit.layer === 'A2') hold(NUM[other(strikeHand)], '123 layer');
    if (hit.layer === 'A3') hold(layout.dev.fxAccess(other(strikeHand)), 'fx layer');
    if (needShift) {
      let hand = policy === 'right' ? 'R' : policy === 'opposite' ? other(strikeHand) : 'L';
      if (used.has(SHIFT[hand][0])) hand = other(hand);   // one pinky cannot push two ways at once
      hold(SHIFT[hand], 'Shift');
    }
    steps.push({ sw: hit.sw, dir: hit.dir, verb: 'strike', layer: hit.layer,
      what: label(hit.sw.slots[hit.layer][DIRS.indexOf(hit.dir)]) });
    const shown = { ' ': 'space' }[value] || label(value);
    const char = spec.length === 1 ? spec : null;
    return { title: (char ? '“' + shown + '”' : shown) + '  =  ' + steps.map(s => s.what).join(' + '),
      char, steps };
  }

  // Which slots to light while you type on the real device.
  function liveSlots(layout, code, key) {
    const MODS = { ShiftLeft: ['L.pinky', 'E'], ShiftRight: ['R.pinky', 'W'], ControlLeft: ['L.ring', 'N'],
      ControlRight: ['R.ring', 'N'], AltLeft: ['L.pinky', 'N'], AltRight: ['R.pinky', 'N'] };
    if (MODS[code]) return [MODS[code]];
    let v = key;
    for (const k in SPECIAL_KEY) if (SPECIAL_KEY[k] === key) v = '{' + k + '}';
    let hits = find(layout, v).filter(h => h.layer !== 'A3' || /^F\d+$/.test(v));
    if (!hits.length && key && key.length === 1) {
      const base = unshifted(key);
      if (base) hits = find(layout, base);
    }
    return hits.slice(0, 1).map(h => [h.sw.id, h.dir]);
  }

  global.Chorder = { build, resolve, liveSlots, DEVICES };
})(typeof window !== 'undefined' ? window : globalThis);
