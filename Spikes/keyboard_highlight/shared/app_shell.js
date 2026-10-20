/*
 * The part every spike shares: reading parameters, the small control bar,
 * text-sequence stepping, and listening to your real keyboard.
 *
 * Each spike only supplies a renderer with three hooks:
 *   setTarget(resolved|null)   draw the key(s) to press
 *   setLive(code, isDown)      draw a key you are physically holding
 *   flash(ok)                  optional feedback when you type the target
 *
 * Parameters (URL query string):
 *   key=G            a key, character or combo: g  G  {  RCtrl+c  Enter
 *   text=\frac{a}{b} step through a string, one character at a time
 *   interval=900     ms per step for text; 0 (default) = wait until you type it
 *   shift=left       left | right | opposite  (which Shift capitals use)
 *   ui=0             hide the control bar (for embedding)
 *
 * Embedding: the page exposes window.KB.show("G"), KB.showText("abc", 0),
 * KB.clear(), so a host app (e.g. a Qt QWebEngineView via runJavaScript)
 * can drive it without reloading.
 */
(function (global) {
  'use strict';

  const params = new URLSearchParams(location.search);
  function param(name, fallback) { const v = params.get(name); return v == null ? fallback : v; }

  function visible(ch) {
    return { ' ': '␣', '\n': '↵', '\t': '⇥' }[ch] || ch;
  }

  function start(layout, renderer) {
    // A board can bring its own resolver (e.g. the Forge maps characters to
    // switch directions, not keys); the default is the QWERTY key map.
    const resolve = renderer.resolve || ((spec, o) => KeyMap.resolve(layout, spec, o));
    let shiftPolicy = param('shift', 'left');
    let seq = null, seqIdx = 0, seqTimer = null, interval = 0;
    let current = null;

    // ---- control bar -------------------------------------------------------
    const bar = document.createElement('header');
    bar.className = 'bar';
    bar.innerHTML =
      '<div class="title" id="kb-title">Type a key above, or just press keys</div>' +
      '<form id="kb-form"><input id="kb-input" placeholder="g, G, {, RCtrl+c, or text" autocomplete="off" spellcheck="false">' +
      '<select id="kb-shift" title="Which Shift capital letters and symbols use">' +
      '<option value="left">Shift: always left</option><option value="right">Shift: always right</option>' +
      '<option value="opposite">Shift: opposite hand</option></select>' +
      '<button type="submit">Show</button></form>';
    document.body.prepend(bar);
    if (param('ui', '1') === '0') bar.classList.add('hidden');
    const titleEl = bar.querySelector('#kb-title');
    const input = bar.querySelector('#kb-input');
    const shiftSel = bar.querySelector('#kb-shift');
    shiftSel.value = shiftPolicy;

    const strip = document.createElement('div');
    strip.className = 'seq hidden';
    document.body.append(strip);

    bar.querySelector('#kb-form').addEventListener('submit', e => {
      e.preventDefault();
      show(input.value);
      input.blur(); // hand the keyboard back to the live view
    });
    shiftSel.addEventListener('change', () => {
      shiftPolicy = shiftSel.value;
      if (seq) showStep(); else if (current && current.spec) show(current.spec);
      shiftSel.blur();
    });

    // ---- showing -----------------------------------------------------------
    function setTarget(res, spec) {
      current = res ? Object.assign({ spec }, res) : null;
      titleEl.textContent = res ? res.title : 'Type a key above, or just press keys';
      renderer.setTarget(res);
    }

    function show(spec) {
      stopSeq();
      const res = resolve(spec, { shift: shiftPolicy });
      if (res && res.text) return showText(spec, interval);
      setTarget(res, spec);
    }

    function stopSeq() {
      if (seqTimer) clearInterval(seqTimer);
      seqTimer = null; seq = null;
      strip.classList.add('hidden');
    }

    function showText(text, ms) {
      stopSeq();
      seq = Array.from(text); seqIdx = 0; interval = +ms || 0;
      strip.classList.remove('hidden');
      showStep();
      if (interval > 0) seqTimer = setInterval(() => advance(), interval);
    }

    function showStep() {
      strip.innerHTML = seq.map((ch, i) =>
        '<span class="' + (i < seqIdx ? 'done' : i === seqIdx ? 'now' : '') + '">' +
        escapeHtml(visible(ch)) + '</span>').join('');
      const ch = seq[seqIdx];
      setTarget(resolve(ch, { shift: shiftPolicy }), ch);
    }

    function advance() {
      if (!seq) return;
      seqIdx = (seqIdx + 1) % seq.length;
      showStep();
    }

    function escapeHtml(s) {
      return s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    // ---- your real keyboard ------------------------------------------------
    // e.code is the physical key (ShiftLeft vs ShiftRight), e.key the character.
    const held = new Set();
    const BLOCK = new Set(['Tab', 'Space', 'Backspace', 'Quote', 'Slash', 'AltLeft', 'AltRight',
      'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageUp', 'PageDown', 'Home', 'End']);
    function typing(e) { return e.target === input || e.target === shiftSel; }

    window.addEventListener('keydown', e => {
      if (typing(e)) return;
      if (BLOCK.has(e.code)) e.preventDefault();
      if (!held.has(e.code)) { held.add(e.code); renderer.setLive(e.code, true, e.key); }
      if (e.repeat || !current || !current.char) return;
      const want = { '\n': 'Enter', '\t': 'Tab' }[current.char] || current.char;
      if (KeyMap.IS_MOD.has(e.code)) return; // holding Shift is not an answer yet
      const ok = e.key === want;
      if (renderer.flash) renderer.flash(ok);
      if (ok && seq && interval === 0) setTimeout(advance, 120);
    });
    window.addEventListener('keyup', e => {
      if (held.delete(e.code)) renderer.setLive(e.code, false);
    });
    window.addEventListener('blur', () => {
      for (const c of held) renderer.setLive(c, false);
      held.clear();
    });

    // ---- initial state -----------------------------------------------------
    interval = +param('interval', 0) || 0;
    const text = params.get('text');
    const key = params.get('key');
    if (text) showText(text, interval);
    else if (key) { input.value = key; show(key); }
    else setTarget(null);

    global.KB = {
      show, showText, clear: () => { stopSeq(); setTarget(null); },
      setShiftPolicy: p => { shiftPolicy = p; shiftSel.value = p; },
    };
  }

  global.AppShell = { start, param };
})(window);
