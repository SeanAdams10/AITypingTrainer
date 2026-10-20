/*
 * Spike 3 (my pick): finger guide.
 *
 * Design intuition
 * ----------------
 * For learning to type, "press G" is only half the instruction. The useful
 * half is "your LEFT INDEX moves from F, one key right". Typing speed comes
 * from fingers making the same short trips every time, so the guide shows:
 *   - a colour strip on every key = which finger owns it (same colour for the
 *     same finger on both hands, so pinky is always purple),
 *   - the owning finger's home key, ringed,
 *   - an animated path from home to the target (the trip to make),
 *   - a pulsing glow on the target, which catches the eye in peripheral
 *     vision while you look at the text,
 *   - numbered steps for chords: 1 hold Shift (with which finger), 2 strike.
 * Everything else dims, so the eye goes to the 1-3 keys that matter.
 *
 * It is pure SVG + CSS animation: the pulse and the flowing dashes are CSS
 * keyframes, which the browser runs on the compositor, so there is no
 * JavaScript per frame at all.
 */
(function () {
  'use strict';
  const layout = K860.build({ splay: +AppShell.param('splay', 6), gap: +AppShell.param('gap', 0.9) });
  const kb = KbSvg.create(document.getElementById('stage'), layout);
  const el = kb.el;
  const stepsEl = document.getElementById('steps');
  const fingerColor = f => 'var(--f-' + f[1] + ')';

  // Glow filter for the halo.
  const filt = el('filter', { id: 'glow', x: '-50%', y: '-50%', width: '200%', height: '200%' }, kb.defs);
  el('feGaussianBlur', { stdDeviation: 0.22 }, filt);
  // Arrowheads, one per finger colour.
  for (const f of ['P', 'R', 'M', 'I', 'T']) {
    const m = el('marker', { id: 'head-' + f, viewBox: '0 0 10 10', refX: 6, refY: 5, markerWidth: 3.2,
      markerHeight: 3.2, orient: 'auto-start-reverse' }, kb.defs);
    el('path', { d: 'M0,0 L10,5 L0,10 z', fill: 'var(--f-' + f + ')' }, m);
  }

  // Finger strip along the bottom of every cap.
  for (const k of layout.keys) {
    if (!k.finger) continue;
    el('rect', { class: 'strip', x: -k.w / 2 + 0.16, y: k.h / 2 - 0.17, width: k.w - 0.32, height: 0.06, rx: 0.03,
      fill: fingerColor(k.finger) }, kb.keyEls[k.id]);
  }

  const transformOf = k => 'translate(' + k.x + ' ' + k.y + ') rotate(' + k.angle + ')';
  let halos = [];

  function clearOverlay() {
    kb.under.innerHTML = ''; kb.over.innerHTML = '';
    kb.clear('target'); kb.clear('target-mod'); kb.clear('home');
    kb.keysG.classList.remove('focus');
    stepsEl.innerHTML = ''; halos = [];
  }

  // Pick the cap a finger should use when a code has two (the two space bars).
  function capFor(code) {
    const caps = layout.byCode[code] || [];
    return caps.find(c => c.id === 'SpaceR') || caps[0];
  }

  function halo(k, color) {
    const r = el('rect', { class: 'halo', x: -k.w / 2 - 0.12, y: -k.h / 2 - 0.12, width: k.w + 0.24,
      height: k.h + 0.24, rx: 0.25, fill: color, transform: transformOf(k) }, kb.under);
    halos.push(r);
  }

  function badge(k, n, color) {
    const g = el('g', { class: 'badge', transform: 'translate(' + (k.x + k.w / 2 - 0.1) + ' ' + (k.y - k.h / 2 + 0.05) + ')' }, kb.over);
    el('circle', { r: 0.24, fill: color }, g);
    el('text', { y: 0.11 }, g).textContent = n;
  }

  // Finger trip from home to target as a gently curved arrow.
  function trip(home, k, color, f) {
    const dx = k.x - home.x, dy = k.y - home.y, len = Math.hypot(dx, dy);
    const shrink = Math.min(0.42, len * 0.25);
    const sx = home.x + dx / len * 0.12, sy = home.y + dy / len * 0.12;
    const ex = k.x - dx / len * shrink, ey = k.y - dy / len * shrink;
    const bend = Math.min(0.6, len * 0.18);
    const mx = (sx + ex) / 2 - dy / len * bend, my = (sy + ey) / 2 + dx / len * bend;
    el('path', { class: 'path', d: 'M' + sx + ',' + sy + ' Q' + mx + ',' + my + ' ' + ex + ',' + ey,
      stroke: color, 'marker-end': 'url(#head-' + f[1] + ')' }, kb.over);
  }

  // Show one key: home ring, path, halo. Returns a sentence for the steps panel.
  function guide(code, verb, n, total) {
    const k = capFor(code);
    if (!k) return '';
    const color = k.finger ? fingerColor(k.finger) : 'var(--target)';
    halo(k, verb === 'hold' ? 'var(--target-mod)' : 'var(--target)');
    if (total > 1) badge(k, n, verb === 'hold' ? 'var(--target-mod)' : 'var(--target)');
    let who = 'Press';
    if (k.finger) {
      const home = layout.byId[k.home];
      const name = layout.fingerNames[k.finger];
      who = name[0].toUpperCase() + name.slice(1);
      if (home && home.id !== k.id) {
        kb.keyEls[home.id].classList.add('home');
        el('rect', { class: 'home-ring', x: -home.w / 2 + 0.02, y: -home.h / 2 + 0.02, width: home.w - 0.04,
          height: home.h - 0.04, rx: 0.16, stroke: color, transform: transformOf(home) }, kb.over);
        trip(home, k, color, k.finger);
      } else {
        who += ' (already home)';
      }
    }
    const lbl = KeyMap.keyLabel(layout, code);
    return (total > 1 ? '<b style="background:' + (verb === 'hold' ? 'var(--target-mod)' : 'var(--target)') + '">' +
      n + '</b>' : '') + '<span style="color:' + color + '">' + who + '</span>' + ' ' + (verb === 'hold' ? 'holds ' : 'strikes ') + lbl;
  }

  AppShell.start(layout, {
    setTarget(res) {
      clearOverlay();
      if (!res) return;
      kb.mark(res.mods, 'target-mod', true);
      kb.mark([res.main], 'target', true);
      kb.keysG.classList.add('focus');
      const total = res.mods.length + 1;
      const lines = res.mods.map((m, i) => guide(m, 'hold', i + 1, total));
      lines.push(guide(res.main, 'strike', total, total));
      stepsEl.innerHTML = lines.join('<br>');
    },
    setLive(code, down) { kb.mark([code], 'live', down); },
    flash(ok) {
      const main = halos[halos.length - 1];
      if (!main) return;
      main.classList.add(ok ? 'ok' : 'bad');
      setTimeout(() => main.classList.remove('ok', 'bad'), 260);
    },
  });
})();
