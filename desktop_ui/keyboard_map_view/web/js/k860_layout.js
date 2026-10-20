/*
 * Logitech ERGO K860 layout model.
 *
 * Design intuition
 * ----------------
 * 1. Every key is identified by its *physical* id, using the browser's
 *    KeyboardEvent.code names ("KeyG", "ShiftLeft", "ControlRight", ...).
 *    That is the same split the OS makes: `code` says WHERE the key is,
 *    `key` says WHAT character it produced. Left and right Shift are
 *    different places, so they are different codes, even though both
 *    produce the same "Shift" meaning.
 * 2. Geometry is written as a normal straight (ANSI) keyboard in "key
 *    units" (1u = one key pitch, ~19 mm), because that is easy to read and
 *    check. The K860's split is then a *transform*: each half is rotated
 *    ("splayed") a few degrees around the top of the split and pushed apart.
 *    Changing SPLAY_DEG or GAP_U reshapes the whole board.
 * 3. Each physical keycap gets one entry. The K860 has two space bars that
 *    both send "Space", so two caps share one code (ids SpaceL / SpaceR).
 *
 * Assumptions to check against the real board (all easy to edit below):
 *  - "6", "T", "G", "B" sit on the left half; "7", "Y", "H", "N" on the right.
 *  - Bottom row: Ctrl Fn Win Alt Space | Space Alt Menu Ctrl.
 *  - F-row split is F1-F6 left, F7-F12 right.
 */
(function (global) {
  'use strict';

  const SPLAY_DEG = 6;   // rotation of each half; rows slope down toward the middle
  const GAP_U = 0.9;     // extra horizontal gap between the halves (key units)
  const PIVOT = { x: 7.25, y: 1.25 }; // top of the split, the hinge point

  const Y = { fn: 0, num: 1.25, top: 2.25, home: 3.25, bottom: 4.25, space: 5.25 };

  // A row is a list of [code, label, width, shiftedLabel] or a bare number = gap.
  const LEFT_ROWS = [
    [Y.fn, 0, [['Escape', 'Esc', 1], 0.25, ['F1', 'F1', 1], ['F2', 'F2', 1], ['F3', 'F3', 1],
      ['F4', 'F4', 1], ['F5', 'F5', 1], ['F6', 'F6', 1]]],
    [Y.num, 0, [['Backquote', '`', 1, '~'], ['Digit1', '1', 1, '!'], ['Digit2', '2', 1, '@'],
      ['Digit3', '3', 1, '#'], ['Digit4', '4', 1, '$'], ['Digit5', '5', 1, '%'], ['Digit6', '6', 1, '^']]],
    [Y.top, 0, [['Tab', 'Tab', 1.5], ['KeyQ', 'Q', 1], ['KeyW', 'W', 1], ['KeyE', 'E', 1],
      ['KeyR', 'R', 1], ['KeyT', 'T', 1]]],
    [Y.home, 0, [['CapsLock', 'Caps', 1.75], ['KeyA', 'A', 1], ['KeyS', 'S', 1], ['KeyD', 'D', 1],
      ['KeyF', 'F', 1], ['KeyG', 'G', 1]]],
    [Y.bottom, 0, [['ShiftLeft', 'Shift', 2.25], ['KeyZ', 'Z', 1], ['KeyX', 'X', 1], ['KeyC', 'C', 1],
      ['KeyV', 'V', 1], ['KeyB', 'B', 1]]],
    [Y.space, 0, [['ControlLeft', 'Ctrl', 1.25], ['Fn', 'fn', 1.25], ['MetaLeft', 'Win', 1.25],
      ['AltLeft', 'Alt', 1.25], ['Space', '', 2.25, null, 'SpaceL']]],
  ];

  const RIGHT_ROWS = [
    [Y.fn, 8.5, [['F7', 'F7', 1], ['F8', 'F8', 1], ['F9', 'F9', 1], ['F10', 'F10', 1],
      ['F11', 'F11', 1], ['F12', 'F12', 1]]],
    [Y.num, 7, [['Digit7', '7', 1, '&'], ['Digit8', '8', 1, '*'], ['Digit9', '9', 1, '('],
      ['Digit0', '0', 1, ')'], ['Minus', '-', 1, '_'], ['Equal', '=', 1, '+'], ['Backspace', 'Bksp', 2]]],
    [Y.top, 6.5, [['KeyY', 'Y', 1], ['KeyU', 'U', 1], ['KeyI', 'I', 1], ['KeyO', 'O', 1],
      ['KeyP', 'P', 1], ['BracketLeft', '[', 1, '{'], ['BracketRight', ']', 1, '}'],
      ['Backslash', '\\', 1.5, '|']]],
    [Y.home, 6.75, [['KeyH', 'H', 1], ['KeyJ', 'J', 1], ['KeyK', 'K', 1], ['KeyL', 'L', 1],
      ['Semicolon', ';', 1, ':'], ['Quote', "'", 1, '"'], ['Enter', 'Enter', 2.25]]],
    [Y.bottom, 7.25, [['KeyN', 'N', 1], ['KeyM', 'M', 1], ['Comma', ',', 1, '<'],
      ['Period', '.', 1, '>'], ['Slash', '/', 1, '?'], ['ShiftRight', 'Shift', 2.75]]],
    [Y.space, 7.25, [['Space', '', 3.25, null, 'SpaceR'], ['AltRight', 'Alt', 1.5],
      ['ContextMenu', 'Menu', 1.5], ['ControlRight', 'Ctrl', 1.5]]],
  ];

  // Nav cluster and number pad stay straight; x is relative to the block start.
  const NAV_ROWS = [
    [Y.fn, 0, [['PrintScreen', 'PrtSc', 1], ['ScrollLock', 'ScrLk', 1], ['Pause', 'Pause', 1]]],
    [Y.num, 0, [['Insert', 'Ins', 1], ['Home', 'Home', 1], ['PageUp', 'PgUp', 1]]],
    [Y.top, 0, [['Delete', 'Del', 1], ['End', 'End', 1], ['PageDown', 'PgDn', 1]]],
    [Y.bottom, 1, [['ArrowUp', '↑', 1]]],
    [Y.space, 0, [['ArrowLeft', '←', 1], ['ArrowDown', '↓', 1], ['ArrowRight', '→', 1]]],
  ];
  const PAD_ROWS = [
    [Y.num, 0, [['NumLock', 'Num', 1], ['NumpadDivide', '/', 1], ['NumpadMultiply', '*', 1],
      ['NumpadSubtract', '-', 1]]],
    [Y.top, 0, [['Numpad7', '7', 1], ['Numpad8', '8', 1], ['Numpad9', '9', 1], ['NumpadAdd', '+', 1, null, null, 2]]],
    [Y.home, 0, [['Numpad4', '4', 1], ['Numpad5', '5', 1], ['Numpad6', '6', 1]]],
    [Y.bottom, 0, [['Numpad1', '1', 1], ['Numpad2', '2', 1], ['Numpad3', '3', 1],
      ['NumpadEnter', 'Ent', 1, null, null, 2]]],
    [Y.space, 0, [['Numpad0', '0', 2], ['NumpadDecimal', '.', 1]]],
  ];

  // Touch-typing finger for each key. LP = left pinky ... LT = left thumb.
  const FINGERS = {
    LP: ['Escape', 'F1', 'Backquote', 'Digit1', 'Tab', 'KeyQ', 'CapsLock', 'KeyA', 'ShiftLeft', 'KeyZ',
      'ControlLeft', 'Fn', 'MetaLeft'],
    LR: ['F2', 'Digit2', 'KeyW', 'KeyS', 'KeyX'],
    LM: ['F3', 'Digit3', 'KeyE', 'KeyD', 'KeyC'],
    LI: ['F4', 'F5', 'F6', 'Digit4', 'Digit5', 'Digit6', 'KeyR', 'KeyT', 'KeyF', 'KeyG', 'KeyV', 'KeyB'],
    LT: ['AltLeft', 'SpaceL'],
    RT: ['SpaceR', 'AltRight', 'Numpad0'],
    RI: ['F7', 'Digit7', 'KeyY', 'KeyU', 'KeyH', 'KeyJ', 'KeyN', 'KeyM', 'NumLock', 'Numpad7', 'Numpad4', 'Numpad1',
      'ArrowLeft'],
    RM: ['F8', 'Digit8', 'KeyI', 'KeyK', 'Comma', 'NumpadDivide', 'Numpad8', 'Numpad5', 'Numpad2',
      'ArrowUp', 'ArrowDown'],
    RR: ['F9', 'Digit9', 'KeyO', 'KeyL', 'Period', 'NumpadMultiply', 'Numpad9', 'Numpad6', 'Numpad3',
      'NumpadDecimal', 'ArrowRight'],
    RP: ['F10', 'F11', 'F12', 'Digit0', 'Minus', 'Equal', 'Backspace', 'KeyP', 'BracketLeft', 'BracketRight',
      'Backslash', 'Semicolon', 'Quote', 'Enter', 'Slash', 'ShiftRight', 'ContextMenu', 'ControlRight',
      'NumpadSubtract', 'NumpadAdd', 'NumpadEnter'],
  };
  // Where each finger rests. Numpad keys use a separate numpad home row.
  const HOME = { LP: 'KeyA', LR: 'KeyS', LM: 'KeyD', LI: 'KeyF', LT: 'SpaceL',
    RT: 'SpaceR', RI: 'KeyJ', RM: 'KeyK', RR: 'KeyL', RP: 'Semicolon' };
  const PAD_HOME = { RI: 'Numpad4', RM: 'Numpad5', RR: 'Numpad6', RP: 'NumpadAdd', RT: 'Numpad0' };
  const FINGER_NAMES = { LP: 'left pinky', LR: 'left ring', LM: 'left middle', LI: 'left index',
    LT: 'left thumb', RT: 'right thumb', RI: 'right index', RM: 'right middle', RR: 'right ring',
    RP: 'right pinky' };

  function rotate(px, py, deg) {
    const a = deg * Math.PI / 180;
    const dx = px - PIVOT.x, dy = py - PIVOT.y;
    return { x: PIVOT.x + dx * Math.cos(a) - dy * Math.sin(a), y: PIVOT.y + dx * Math.sin(a) + dy * Math.cos(a) };
  }

  function expandRows(rows, half, xBase) {
    const keys = [];
    for (const [y, x0, defs] of rows) {
      let x = xBase + x0;
      for (const d of defs) {
        if (typeof d === 'number') { x += d; continue; }
        const [code, label, w, shiftLabel, id, h] = d;
        const hh = h || 1;
        keys.push({ id: id || code, code, label, shiftLabel: shiftLabel || null, half,
          x: x + w / 2, y: y + hh / 2, w, h: hh, angle: 0 });
        x += w;
      }
    }
    return keys;
  }

  function build(opts) {
    const splay = (opts && opts.splay != null) ? opts.splay : SPLAY_DEG;
    const gap = (opts && opts.gap != null) ? opts.gap : GAP_U;
    const keys = [];
    // Left half: rotate clockwise around the split hinge.
    for (const k of expandRows(LEFT_ROWS, 'L', 0)) {
      const p = rotate(k.x, k.y, splay);
      keys.push(Object.assign(k, { x: p.x - gap / 2, y: p.y, angle: splay }));
    }
    // Right half: rotate the other way, push right by the gap.
    for (const k of expandRows(RIGHT_ROWS, 'R', 0)) {
      const p = rotate(k.x, k.y, -splay);
      keys.push(Object.assign(k, { x: p.x + gap / 2, y: p.y, angle: -splay }));
    }
    // Straight blocks sit to the right of the right half's furthest corner.
    let maxX = -Infinity;
    for (const k of keys) for (const c of corners(k, 0)) maxX = Math.max(maxX, c.x);
    const navX = maxX + 0.6;
    keys.push(...expandRows(NAV_ROWS, 'X', navX));
    keys.push(...expandRows(PAD_ROWS, 'X', navX + 3.5));

    // Shift everything so the top-left is at (margin, margin).
    const m = 0.6;
    let minX = Infinity, minY = Infinity, mx = -Infinity, my = -Infinity;
    for (const k of keys) for (const c of corners(k, 0)) {
      minX = Math.min(minX, c.x); minY = Math.min(minY, c.y);
      mx = Math.max(mx, c.x); my = Math.max(my, c.y);
    }
    for (const k of keys) { k.x += m - minX; k.y += m - minY; }
    const pivotShift = { x: m - minX, y: m - minY };

    const byId = {}, byCode = {};
    for (const k of keys) {
      byId[k.id] = k;
      (byCode[k.code] = byCode[k.code] || []).push(k);
    }
    const fingerOf = {};
    for (const f in FINGERS) for (const id of FINGERS[f]) fingerOf[id] = f;
    for (const k of keys) {
      k.finger = fingerOf[k.id] || fingerOf[k.code] || null;
      if (k.finger) {
        const home = k.code.startsWith('Num') ? PAD_HOME[k.finger] : HOME[k.finger];
        k.home = home || null;
      }
    }
    const halves = {};
    for (const h of ['L', 'R', 'X']) halves[h] = keys.filter(k => k.half === h);
    return {
      keys, byId, byCode, halves,
      width: mx - minX + 2 * m, height: my - minY + 2 * m,
      splay, gap,
      leftPivot: { x: PIVOT.x - gap / 2 + pivotShift.x, y: PIVOT.y + pivotShift.y },
      rightPivot: { x: PIVOT.x + gap / 2 + pivotShift.x, y: PIVOT.y + pivotShift.y },
      fingerNames: FINGER_NAMES,
    };
  }

  // Corners of a key rectangle, optionally grown by `pad` on every side.
  function corners(k, pad) {
    const a = k.angle * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    const hw = k.w / 2 + pad, hh = k.h / 2 + pad;
    return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([dx, dy]) =>
      ({ x: k.x + dx * c - dy * s, y: k.y + dx * s + dy * c }));
  }

  // Convex hull (monotone chain). Used to draw each half's plastic body:
  // the hull of all key corners, grown by a margin, is a believable case outline.
  function hull(points) {
    const p = points.slice().sort((a, b) => a.x - b.x || a.y - b.y);
    const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
    const lower = [], upper = [];
    for (const pt of p) {
      while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], pt) <= 0) lower.pop();
      lower.push(pt);
    }
    for (let i = p.length - 1; i >= 0; i--) {
      const pt = p[i];
      while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], pt) <= 0) upper.pop();
      upper.push(pt);
    }
    upper.pop(); lower.pop();
    return lower.concat(upper);
  }

  function bodyOutline(keys, pad) {
    const pts = [];
    for (const k of keys) pts.push(...corners(k, pad));
    return hull(pts);
  }

  // Palm rest under one half: a rectangle that follows the half's rotation.
  function palmRest(layout, half) {
    const ks = layout.halves[half];
    const angle = half === 'L' ? layout.splay : -layout.splay;
    const a = angle * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    const piv = half === 'L' ? layout.leftPivot : layout.rightPivot;
    // Work in the half's un-rotated frame, then rotate back.
    const local = ks.map(k => { const dx = k.x - piv.x, dy = k.y - piv.y;
      return { x: dx * c + dy * s, y: -dx * s + dy * c }; });
    const minX = Math.min(...local.map(p => p.x)), maxX = Math.max(...local.map(p => p.x));
    const maxY = Math.max(...local.map(p => p.y));
    const x0 = minX + 0.2, x1 = maxX - 0.2, y0 = maxY + 1.0, y1 = maxY + 3.2;
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([x, y]) =>
      ({ x: piv.x + x * c - y * s, y: piv.y + x * s + y * c }));
  }

  // The K860's palm rest is one cushion under both halves.
  function palmOutline(layout) { return hull(palmRest(layout, 'L').concat(palmRest(layout, 'R'))); }

  global.K860 = { build, corners, hull, bodyOutline, palmRest, palmOutline, FINGER_NAMES };
})(typeof window !== 'undefined' ? window : globalThis);
