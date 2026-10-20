/*
 * Spike 4, Forge board: the finger guide from spike 3, drawn for the
 * CharaChorder Master Forge.
 *
 * What changes from the K860 version, and why:
 *  - The thing to highlight is one DIRECTION wedge of a switch, not a key.
 *  - The main arrow is a PUSH arrow on the switch (which way to move the
 *    finger), because on the Forge fingers stay put. A travel arrow only
 *    appears for the aux switches and thumb 2, where the finger does move.
 *  - Layers: when the target lives on the 123 or fx layer, the whole board
 *    relabels to that layer, the same way the device's own layer works.
 *  - Halves are drawn 15 degrees apart (7.5 each way), set in forge_layout.js.
 */
(function () {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const layout = Forge.build();
  const stage = document.getElementById('stage');
  const stepsEl = document.getElementById('steps');
  const fingerColor = f => 'var(--f-' + f[1] + ')';
  const DIR_ANGLE = { N: -90, E: 0, S: 90, W: 180 };
  const RO = 0.47, RI = 0.19;

  function el(name, attrs, parent) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const pt = (r, deg) => [r * Math.cos(deg * Math.PI / 180), r * Math.sin(deg * Math.PI / 180)];

  // ---- board ---------------------------------------------------------------
  const svg = el('svg', { viewBox: '0 0 ' + layout.width.toFixed(2) + ' ' + layout.height.toFixed(2),
    class: 'kb forge layer-A1', preserveAspectRatio: 'xMidYMid meet' }, stage);
  const defs = el('defs', {}, svg);
  const body = el('g', {}, svg), under = el('g', {}, svg), keysG = el('g', { class: 'keys' }, svg),
    over = el('g', {}, svg);

  const filt = el('filter', { id: 'glow', x: '-50%', y: '-50%', width: '200%', height: '200%' }, defs);
  el('feGaussianBlur', { stdDeviation: 0.09 }, filt);
  for (const f of ['P', 'R', 'M', 'I', 'T']) {
    const m = el('marker', { id: 'head-' + f, viewBox: '0 0 10 10', refX: 6, refY: 5, markerWidth: 3,
      markerHeight: 3, orient: 'auto-start-reverse' }, defs);
    el('path', { d: 'M0,0 L10,5 L0,10 z', fill: 'var(--f-' + f + ')' }, m);
  }

  // Aluminium body of each digitizer: hull around its switches.
  for (const half of ['L', 'R']) {
    const pts = [];
    for (const s of layout.switches.filter(q => q.half === half)) {
      for (let a = 0; a < 360; a += 30) {
        const [dx, dy] = pt(0.62, a);
        pts.push({ x: s.x + dx * s.w, y: s.y + dy });
      }
    }
    el('polygon', { class: 'case', points: K860.hull(pts).map(p => p.x.toFixed(3) + ',' + p.y.toFixed(3)).join(' ') },
      body);
  }
  // Bridge between the two index switches.
  const li = layout.byId['L.index'], ri = layout.byId['R.index'];
  el('rect', { class: 'bridge', x: li.x, y: (li.y + ri.y) / 2 + 0.55, width: ri.x - li.x, height: 0.5, rx: 0.12 },
    body);
  body.prepend(body.lastChild);

  const wedgeEls = {};   // "L.index:S" -> path
  for (const s of layout.switches) {
    const g = el('g', { class: 'switch', transform: 'translate(' + s.x + ' ' + s.y + ') rotate(' + s.angle + ')' },
      keysG);
    s.g = g;
    const shape = el('g', { transform: 'scale(' + s.w + ' 1)' }, g);
    for (const d of layout.DIRS) {
      const a = DIR_ANGLE[d];
      const [x1, y1] = pt(RO, a - 45), [x2, y2] = pt(RO, a + 45), [x3, y3] = pt(RI, a + 45), [x4, y4] = pt(RI, a - 45);
      wedgeEls[s.id + ':' + d] = el('path', { class: 'wedge', d: 'M' + x1 + ',' + y1 + ' A' + RO + ',' + RO +
        ' 0 0 1 ' + x2 + ',' + y2 + ' L' + x3 + ',' + y3 + ' A' + RI + ',' + RI + ' 0 0 0 ' + x4 + ',' + y4 + ' Z' },
      shape);
    }
    el('circle', { class: 'hole', r: RI - 0.03 }, shape);
    el('ellipse', { class: 'fring', rx: RO + 0.03, ry: RO + 0.03, stroke: fingerColor(s.finger) }, shape);
    layout.DIRS.forEach((d, i) => {
      const [lx, ly] = pt((RO + RI) / 2, DIR_ANGLE[d]);
      for (const layer of ['A1', 'A2', 'A3']) {
        // Empty slots on the 123/fx layers fall through to the base layer
        // (that is how Ctrl, Alt and the layer keys stay reachable), shown dimmer.
        let txt = layout.label(s.slots[layer][i]), cls = 'lbl lbl-' + layer;
        if (!txt && layer !== 'A1') { txt = layout.label(s.slots.A1[i]); cls += ' fallthrough'; }
        if (!txt) continue;
        el('text', { class: cls, x: lx * s.w, y: ly + 0.055,
          'font-size': txt.length > 2 ? 0.1 : 0.15 }, g).textContent = txt;
      }
      // Small hint of the 123 layer, like Device Manager shows.
      const hint = layout.label(s.slots.A2[i]);
      if (hint && hint !== layout.label(s.slots.A1[i])) {
        const [hx, hy] = pt(RO - 0.06, DIR_ANGLE[d] + 30);
        el('text', { class: 'hint', x: hx * s.w, y: hy + 0.03, 'font-size': 0.075 }, g).textContent = hint;
      }
    });
  }

  // ---- guide drawing -------------------------------------------------------
  let halos = [], live = {};
  function clear() {
    under.innerHTML = ''; over.innerHTML = ''; halos = [];
    for (const k in wedgeEls) wedgeEls[k].classList.remove('target', 'target-mod');
    for (const s of layout.switches) s.g.classList.remove('involved');
    keysG.classList.remove('focus');
    svg.setAttribute('class', 'kb forge layer-A1');
    stepsEl.innerHTML = '';
  }

  function dirWord(s, d) {
    if (d === 'N') return 'away';
    if (d === 'S') return 'toward you';
    const inward = (s.half === 'L') === (d === 'E');
    return inward ? 'inward' : 'outward';
  }

  function local(s, x, y) {   // switch-local point -> board point
    const a = s.angle * Math.PI / 180;
    return [s.x + x * Math.cos(a) - y * Math.sin(a), s.y + x * Math.sin(a) + y * Math.cos(a)];
  }

  function drawStep(st, n, total) {
    const s = st.sw, color = fingerColor(s.finger), hold = st.verb === 'hold';
    const fill = hold ? 'var(--target-mod)' : 'var(--target)';
    wedgeEls[s.id + ':' + st.dir].classList.add(hold ? 'target-mod' : 'target');
    s.g.classList.add('involved');
    halos.push(el('ellipse', { class: 'halo', cx: s.x, cy: s.y, rx: 0.62 * s.w, ry: 0.62, fill }, under));
    // Push arrow: starts at the rim and points the way to push, so it never
    // covers the character printed on the wedge.
    const [ax, ay] = pt(RO + 0.04, DIR_ANGLE[st.dir]), [bx, by] = pt(RO + 0.36, DIR_ANGLE[st.dir]);
    const [sx, sy] = local(s, ax * s.w, ay), [ex, ey] = local(s, bx * s.w, by);
    el('line', { class: 'push', x1: sx, y1: sy, x2: ex, y2: ey, stroke: color,
      'marker-end': 'url(#head-' + s.finger[1] + ')' }, over);
    // Travel arrow when the finger has to leave its resting switch.
    if (s.home) {
      const h = layout.byId[s.home];
      h.g.classList.add('involved');
      el('ellipse', { class: 'home-ring', cx: h.x, cy: h.y, rx: 0.6 * h.w, ry: 0.6, stroke: color }, over);
      const dx = s.x - h.x, dy = s.y - h.y, len = Math.hypot(dx, dy);
      const p0 = [h.x + dx / len * 0.3, h.y + dy / len * 0.3], p1 = [s.x - dx / len * 0.55, s.y - dy / len * 0.55];
      const bend = 0.25, mx = (p0[0] + p1[0]) / 2 - dy / len * bend, my = (p0[1] + p1[1]) / 2 + dx / len * bend;
      el('path', { class: 'path', d: 'M' + p0 + ' Q' + mx + ',' + my + ' ' + p1, stroke: color,
        'marker-end': 'url(#head-' + s.finger[1] + ')' }, over);
    }
    if (total > 1) {
      const [bx2, by2] = local(s, 0.42 * s.w, -0.42);
      const b = el('g', { class: 'badge', transform: 'translate(' + bx2 + ' ' + by2 + ')' }, over);
      el('circle', { r: 0.13, fill }, b);
      el('text', { y: 0.05, 'font-size': 0.15 }, b).textContent = n;
    }
    const name = layout.fingerNames[s.finger];
    const who = name[0].toUpperCase() + name.slice(1) + (s.home ? ' (moves to ' + s.name + ')' : '');
    return (total > 1 ? '<b style="background:' + fill + '">' + n + '</b>' : '') +
      '<span style="color:' + color + '">' + who + '</span> ' + (hold ? 'holds ' : 'pushes ') +
      dirWord(s, st.dir) + ': ' + st.what;
  }

  AppShell.start(layout, {
    resolve: (spec, o) => Forge.resolve(layout, spec, o),
    setTarget(res) {
      clear();
      if (!res || !res.steps.length) return;
      const strike = res.steps[res.steps.length - 1];
      svg.setAttribute('class', 'kb forge layer-' + strike.layer);
      keysG.classList.add('focus');
      stepsEl.innerHTML = res.steps.map((st, i) => drawStep(st, i + 1, res.steps.length)).join('<br>');
    },
    setLive(code, down, key) {
      if (down) live[code] = Forge.liveSlots(layout, code, key);
      for (const [id, d] of live[code] || []) {
        const w = wedgeEls[id + ':' + d];
        w.classList.toggle('live', down);
        if (down) w.parentNode.appendChild(w);   // draw last so its outline sits on top
        // Never dim a switch you are pressing, like the K860 never dims a pressed key.
        layout.byId[id].g.classList.toggle('has-live', !!w.parentNode.querySelector('.wedge.live'));
      }
      if (!down) delete live[code];
    },
    flash(ok) {
      const main = halos[halos.length - 1];
      if (!main) return;
      main.classList.add(ok ? 'ok' : 'bad');
      setTimeout(() => main.classList.remove('ok', 'bad'), 260);
    },
  });
})();
