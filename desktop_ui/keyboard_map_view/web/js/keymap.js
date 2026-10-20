/*
 * Turns what you want to show ("g", "G", "{", "RCtrl+c", "Enter") into the
 * physical keys to highlight.
 *
 * Design intuition
 * ----------------
 * A character is not a key. "G" is two physical keys held together
 * (a Shift + the G key); "{" is Shift + the "[" key. So the mapping is:
 *
 *     character  ->  { code of the key it lives on, needs Shift? }
 *
 * and *which* Shift to use is a separate policy, not part of the character:
 *   - "left"     always Left Shift (what Sean asked for: G = Left Shift + g)
 *   - "right"    always Right Shift
 *   - "opposite" the touch-typing rule: use the Shift on the other hand
 *                from the key, so G (left hand) gets Right Shift. One hand
 *                holds Shift while the other strikes, which avoids
 *                stretching one hand across both keys.
 * Keeping the policy separate means the tutor can switch teaching styles
 * without touching the character table.
 *
 * The table is US-ANSI. Explicit combos like "RShift+g" or "LCtrl+RAlt+x"
 * bypass the policy and show exactly what you named.
 */
(function (global) {
  'use strict';

  const CHAR = {}; // char -> { code, shift }
  for (let i = 0; i < 26; i++) {
    const lo = String.fromCharCode(97 + i), up = lo.toUpperCase();
    CHAR[lo] = { code: 'Key' + up, shift: false };
    CHAR[up] = { code: 'Key' + up, shift: true };
  }
  const SHIFTED_DIGITS = ')!@#$%^&*(';
  for (let d = 0; d <= 9; d++) {
    CHAR[String(d)] = { code: 'Digit' + d, shift: false };
    CHAR[SHIFTED_DIGITS[d]] = { code: 'Digit' + d, shift: true };
  }
  const PAIRS = [['Backquote', '`', '~'], ['Minus', '-', '_'], ['Equal', '=', '+'],
    ['BracketLeft', '[', '{'], ['BracketRight', ']', '}'], ['Backslash', '\\', '|'],
    ['Semicolon', ';', ':'], ['Quote', "'", '"'], ['Comma', ',', '<'], ['Period', '.', '>'],
    ['Slash', '/', '?']];
  for (const [code, plain, shifted] of PAIRS) {
    CHAR[plain] = { code, shift: false };
    CHAR[shifted] = { code, shift: true };
  }
  CHAR[' '] = { code: 'Space', shift: false };
  CHAR['\n'] = { code: 'Enter', shift: false };
  CHAR['\t'] = { code: 'Tab', shift: false };

  const MODIFIERS = {
    shift: 'ShiftLeft', lshift: 'ShiftLeft', leftshift: 'ShiftLeft', shiftleft: 'ShiftLeft',
    rshift: 'ShiftRight', rightshift: 'ShiftRight', shiftright: 'ShiftRight',
    ctrl: 'ControlLeft', control: 'ControlLeft', lctrl: 'ControlLeft', leftctrl: 'ControlLeft',
    controlleft: 'ControlLeft',
    rctrl: 'ControlRight', rightctrl: 'ControlRight', controlright: 'ControlRight',
    alt: 'AltLeft', lalt: 'AltLeft', leftalt: 'AltLeft', altleft: 'AltLeft',
    ralt: 'AltRight', rightalt: 'AltRight', altright: 'AltRight', altgr: 'AltRight',
    win: 'MetaLeft', meta: 'MetaLeft', super: 'MetaLeft', cmd: 'MetaLeft', metaleft: 'MetaLeft',
    fn: 'Fn',
  };
  const NAMED = {
    esc: 'Escape', escape: 'Escape', enter: 'Enter', return: 'Enter', tab: 'Tab', space: 'Space',
    backspace: 'Backspace', bksp: 'Backspace', caps: 'CapsLock', capslock: 'CapsLock',
    del: 'Delete', delete: 'Delete', ins: 'Insert', insert: 'Insert', home: 'Home', end: 'End',
    pgup: 'PageUp', pageup: 'PageUp', pgdn: 'PageDown', pagedown: 'PageDown',
    up: 'ArrowUp', down: 'ArrowDown', left: 'ArrowLeft', right: 'ArrowRight',
    menu: 'ContextMenu', apps: 'ContextMenu', prtsc: 'PrintScreen', printscreen: 'PrintScreen',
    plus: '+', minus: '-',
  };
  for (let i = 1; i <= 12; i++) NAMED['f' + i] = 'F' + i;

  const MOD_LABEL = { ShiftLeft: 'Left Shift', ShiftRight: 'Right Shift', ControlLeft: 'Left Ctrl',
    ControlRight: 'Right Ctrl', AltLeft: 'Left Alt', AltRight: 'Right Alt', MetaLeft: 'Win', Fn: 'Fn' };
  const IS_MOD = new Set(Object.keys(MOD_LABEL));

  function keyLabel(layout, code) {
    if (MOD_LABEL[code]) return MOD_LABEL[code];
    const caps = layout.byCode[code];
    if (!caps) return code;
    if (code === 'Space') return 'Space';
    return caps[0].label;
  }

  function shiftFor(layout, code, policy) {
    if (policy === 'right') return 'ShiftRight';
    if (policy === 'opposite') {
      const k = layout.byCode[code] && layout.byCode[code][0];
      return k && k.half === 'L' ? 'ShiftRight' : 'ShiftLeft';
    }
    return 'ShiftLeft';
  }

  // One token -> { code, char?, shift? } or null.
  function token(layout, t) {
    if (t.length === 1 && CHAR[t]) return Object.assign({ char: t }, CHAR[t]);
    const low = t.toLowerCase();
    if (MODIFIERS[low]) return { code: MODIFIERS[low], shift: false };
    if (NAMED[low]) {
      const n = NAMED[low];
      return n.length === 1 ? Object.assign({ char: n }, CHAR[n]) : { code: n, shift: false };
    }
    // Raw KeyboardEvent.code names also work: "KeyG", "Numpad5", "ShiftRight".
    for (const c in layout.byCode) if (c.toLowerCase() === low) return { code: c, shift: false };
    return null;
  }

  /*
   * resolve(layout, spec, {shift: 'left'|'right'|'opposite'})
   *   -> { codes, main, mods, title }   for a single key / combo
   *   -> { text: [...] }                 when spec is a multi-character string
   *   -> null                            for empty input
   */
  function resolve(layout, spec, opts) {
    if (spec == null || spec === '') return null;
    const policy = (opts && opts.shift) || 'left';
    let parts = null;
    if (spec.length > 1 && spec.includes('+')) {
      // "Ctrl++" means Ctrl and the "+" character.
      const raw = spec.endsWith('++') ? spec.slice(0, -2).split('+').concat('+') : spec.split('+');
      const toks = raw.map(t => token(layout, t.trim()));
      if (toks.every(Boolean) && toks.slice(0, -1).every(t => IS_MOD.has(t.code))) parts = toks;
    } else {
      const t = token(layout, spec);
      if (t) parts = [t];
    }
    if (!parts) return { text: Array.from(spec) };

    const main = parts[parts.length - 1];
    const mods = parts.slice(0, -1).map(p => p.code);
    if (main.shift && !mods.some(m => m.startsWith('Shift'))) mods.push(shiftFor(layout, main.code, policy));
    const codes = mods.concat([main.code]);
    const combo = mods.map(m => keyLabel(layout, m)).concat(keyLabel(layout, main.code)).join(' + ');
    let title = combo;
    if (main.char) {
      const shown = { ' ': 'space', '\n': 'newline', '\t': 'tab' }[main.char] || main.char;
      title = '“' + shown + '”  =  ' + combo;
    }
    return { codes, main: main.code, mods, title, char: main.char || null };
  }

  global.KeyMap = { resolve, CHAR, IS_MOD, keyLabel };
})(typeof window !== 'undefined' ? window : globalThis);
