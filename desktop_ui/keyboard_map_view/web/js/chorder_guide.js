/*
 * Keyboard Map View, CharaChorder boards (Master Forge, CC1, CC2): the K860
 * finger guide, redrawn for switches that move in directions.
 *
 * What changes from the K860 version, and why:
 *  - The thing to highlight is one DIRECTION wedge of a switch, not a key.
 *  - The main arrow is a PUSH arrow on the switch (which way to move the
 *    finger), because fingers mostly stay on their own switch. A travel
 *    arrow only appears for switches a finger has to move to (aux, mouse,
 *    arrow and the outer thumb switches).
 *  - Layers: when the target lives on the 123 or fx layer, the whole board
 *    relabels to that layer, the same way the device's own layer works.
 *  - D (press down) is the centre of the switch; on CC1/CC2 a pinky pressed
 *    down is the fx layer.
 * Which device is drawn comes from ?board=forge|cc1|cc2 (chorder_layout.js).
 */
(function () {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const board = new URLSearchParams(location.search).get('board');
  const layout = Chorder.build(board, { joined: new URLSearchParams(location.search).get('joined') === '1' });
  const stage = document.getElementById('stage');
  const stepsEl = document.getElementById('steps');
  const fingerColor = f => 'var(--f-' + f[1] + ')';
  const DIR_ANGLE = { N: -90, E: 0, S: 90, W: 180 };   // D (press down) is the centre
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
    class: 'kb chorder ' + layout.device + ' layer-A1', preserveAspectRatio: 'xMidYMid meet' }, stage);
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

  // Bodies. Forge: two metal blocks joined only by a USB-C cable that sags
  // between their back corners. CC1/CC2: a dome per half and a centre bar;
  // each dome's cable runs to the pod in the middle of the bar.
  const poly = pts => pts.map(p => p.x.toFixed(3) + ',' + p.y.toFixed(3)).join(' ');
  const domeGrad = el('radialGradient', { id: 'dome-shade', cx: 0.4, cy: 0.35, r: 0.7 }, defs);
  el('stop', { offset: 0, class: 'dome-hi' }, domeGrad);
  el('stop', { offset: 1, class: 'dome-lo' }, domeGrad);
  const bar = layout.bar, pod = bar ? { x: (bar.x1 + bar.x2) / 2, y: bar.y } : null;
  if (bar) el('rect', { class: 'bar', x: bar.x1, y: bar.y - bar.h / 2, width: bar.x2 - bar.x1, height: bar.h,
    rx: 0.08 }, body);
  for (const d of layout.domes) el('ellipse', { class: 'dome', cx: d.x, cy: d.y, rx: d.rx, ry: d.ry,
    fill: 'url(#dome-shade)' }, body);
  if (pod) {
    for (const e of layout.cableEnds) {
      const dir = Math.sign(pod.x - e.x);
      el('path', { class: 'cable thin', d: 'M' + e.x + ',' + e.y + ' C' + (e.x + dir * 1.2) + ',' + (e.y + 0.5) + ' ' +
        (pod.x - dir * 1.6) + ',' + pod.y + ' ' + (pod.x - dir * 0.6) + ',' + pod.y }, body);
      el('rect', { class: 'plug', x: e.x - 0.18, y: e.y - 0.08, width: 0.36, height: 0.16, rx: 0.04 }, body);
    }
    el('ellipse', { class: 'pod', cx: pod.x, cy: pod.y, rx: 0.75, ry: 0.55 }, body);
    drawLogo('cc', pod.x, pod.y, 0, 0.38, 'logo pod-logo');
  } else if (layout.cableEnds.length === 2) {
    const [a, b] = layout.cableEnds, sag = 1.1;
    el('path', { class: 'cable', d: 'M' + a.x + ',' + a.y + ' C' + (a.x + 0.6) + ',' + (a.y - sag) + ' ' +
      (b.x - 0.6) + ',' + (b.y - sag) + ' ' + b.x + ',' + b.y }, body);
    for (const e of layout.cableEnds) el('rect', { class: 'plug', x: e.x - 0.1, y: e.y - 0.16, width: 0.2,
      height: 0.32, rx: 0.05 }, body);
  }
  // Shapes come lowest first, so each covers what lies under it when you look
  // down. A shape with several rings has holes; a fill is baked-in shading.
  for (const [cls, rings, fill] of layout.shapes) {
    const a = { class: 'body-' + cls, d: rings.map(r => 'M' + poly(r).replace(/ /g, ' L') + 'Z').join(' ') };
    if (fill) a.style = 'fill:' + fill + ';stroke:' + fill;
    el('path', a, body);
  }
  for (const l of layout.logos) {
    if (l.size) drawMark(l.kind, l.x, l.y, l.angle, l.size);
    else drawLogo(l.kind, l.x, l.y, l.angle, l.kind === 'cc' ? 1.4 : 1.6, 'logo');
  }

  // The real marks, as the 3D view draws them, size = width in plan units.
  // CharaChorder: a disc with a hairline ring cut through it and a slot that
  // runs out through the right side. Forge: CharaChorder's own artwork, used
  // as a mask so it takes the etched colour.
  function drawMark(kind, x, y, angle, size) {
    const g = el('g', { class: 'logo mark', transform: 'translate(' + x + ' ' + y + ') rotate(' + angle + ')' }, body);
    if (kind === 'cc') {
      const R = size / 2, hh = R * 0.294, x0 = R * 0.026;
      const circle = r => 'M' + r + ',0 A' + r + ',' + r + ' 0 1 0 ' + -r + ',0 A' + r + ',' + r + ' 0 1 0 ' + r + ',0Z';
      const m = el('mask', { id: 'cc-mark', maskUnits: 'userSpaceOnUse', x: -R, y: -R, width: 2 * R, height: 2 * R }, defs);
      el('path', { d: circle(R), fill: '#fff' }, m);
      el('path', { d: circle(R * 0.710) + circle(R * 0.651), fill: '#000', 'fill-rule': 'evenodd' }, m);
      el('path', { d: 'M' + (x0) + ',' + -hh + ' A' + hh + ',' + hh + ' 0 0 0 ' + x0 + ',' + hh + ' L' + R + ',' + hh +
        ' L' + R + ',' + -hh + 'Z', fill: '#000' }, m);
      el('rect', { x: -R, y: -R, width: 2 * R, height: 2 * R, mask: 'url(#cc-mark)' }, g);
    } else if (layout.dev.forgeMask) {
      const h = size * 347 / 512;
      const m = el('mask', { id: 'forge-mark', maskUnits: 'userSpaceOnUse', x: -size / 2, y: -h / 2, width: size,
        height: h }, defs);
      el('image', { href: layout.dev.forgeMask, x: -size / 2, y: -h / 2, width: size, height: h,
        preserveAspectRatio: 'none' }, m);
      el('rect', { x: -size / 2, y: -h / 2, width: size, height: h, mask: 'url(#forge-mark)' }, g);
    }
  }

  // Simplified marks, drawn in a unit box and scaled: the CharaChorder "C"
  // (a thick C with a thinner C inside it) and the Forge's anvil-like mark.
  function drawLogo(kind, x, y, angle, size, cls) {
    const g = el('g', { class: cls, transform: 'translate(' + x + ' ' + y + ') rotate(' + angle + ') scale(' +
      size + ')' }, body);
    const arc = (r, w, open) => {   // a C: ring of radius r, open by +-open degrees on the right
      const [x1, y1] = pt(r, -open), [x2, y2] = pt(r, open);
      el('path', { d: 'M' + x1 + ',' + y1 + ' A' + r + ',' + r + ' 0 1 0 ' + x2 + ',' + y2, 'stroke-width': w }, g);
    };
    if (kind === 'cc') { arc(0.43, 0.12, 30); arc(0.22, 0.17, 42); }
    else {
      // Anvil (horn to the left, waist dropping to a point) over a slash.
      el('polygon', { points: '-0.5,-0.27 0.52,-0.32 0.5,-0.17 0.1,-0.12 -0.13,0.1 -0.17,-0.15 -0.32,-0.22' }, g);
      el('polygon', { points: '-0.13,0.19 0.44,0.02 0.27,0.12 -0.12,0.36' }, g);
    }
  }

  const wedgeEls = {};   // "L.index:S" -> path
  for (const s of layout.switches) {
    const g = el('g', { class: 'switch', transform: 'translate(' + s.x + ' ' + s.y + ') rotate(' + s.angle + ')' },
      keysG);
    s.g = g;
    const shape = el('g', { transform: 'scale(' + s.w + ' 1)' }, g);
    for (const d of ['N', 'E', 'S', 'W']) {
      const a = DIR_ANGLE[d];
      const [x1, y1] = pt(RO, a - 45), [x2, y2] = pt(RO, a + 45), [x3, y3] = pt(RI, a + 45), [x4, y4] = pt(RI, a - 45);
      wedgeEls[s.id + ':' + d] = el('path', { class: 'wedge', d: 'M' + x1 + ',' + y1 + ' A' + RO + ',' + RO +
        ' 0 0 1 ' + x2 + ',' + y2 + ' L' + x3 + ',' + y3 + ' A' + RI + ',' + RI + ' 0 0 0 ' + x4 + ',' + y4 + ' Z' },
      shape);
    }
    // The centre is the press-down (D) slot.
    wedgeEls[s.id + ':D'] = el('circle', { class: 'wedge hole', r: RI - 0.02 }, shape);
    el('ellipse', { class: 'fring', rx: RO + 0.03, ry: RO + 0.03, stroke: fingerColor(s.finger) }, shape);
    layout.DIRS.forEach((d, i) => {
      const [lx, ly] = d === 'D' ? [0, 0] : pt((RO + RI) / 2, DIR_ANGLE[d]);
      for (const layer of ['A1', 'A2', 'A3']) {
        // Empty slots on the 123/fx layers fall through to the base layer
        // (that is how Ctrl, Alt and the layer keys stay reachable), shown dimmer.
        let txt = layout.label(s.slots[layer][i]), cls = 'lbl lbl-' + layer;
        if (!txt && layer !== 'A1') { txt = layout.label(s.slots.A1[i]); cls += ' fallthrough'; }
        if (!txt) continue;
        const t = el('text', { class: cls, x: lx * s.w, y: ly + 0.055,
          'font-size': txt.length > 2 ? 0.1 : 0.15 }, g);
        t.textContent = txt;
        if (s.turn) t.setAttribute('transform', 'rotate(' + -s.turn + ' ' + lx * s.w + ' ' + ly + ')');
      }
      // Small hint of the 123 layer, like Device Manager shows.
      const hint = layout.label(s.slots.A2[i]);
      if (hint && d !== 'D' && hint !== layout.label(s.slots.A1[i])) {
        const [hx, hy] = pt(RO - 0.06, DIR_ANGLE[d] + 30);
        const t = el('text', { class: 'hint', x: hx * s.w, y: hy + 0.03, 'font-size': 0.075 }, g);
        t.textContent = hint;
        if (s.turn) t.setAttribute('transform', 'rotate(' + -s.turn + ' ' + hx * s.w + ' ' + hy + ')');
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
    svg.setAttribute('class', 'kb chorder ' + layout.device + ' layer-A1');
    stepsEl.innerHTML = '';
  }

  function dirWord(s, d) {
    if (d === 'D') return 'down (press in)';
    // On a steep face (the Forge's thumb facet) N and S are up and down the slope.
    if (s.turn && (d === 'N' || d === 'S')) return d === 'N' ? 'up the slope' : 'down the slope';
    // Otherwise name the way the push really points from above.
    const a = ((DIR_ANGLE[d] + s.angle) % 360 + 360) % 360;
    if (a > 225 && a < 315) return 'away';
    if (a > 45 && a < 135) return 'toward you';
    const inward = (s.half === 'L') === (a < 90 || a > 270);
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
    if (st.dir === 'D') {
      // Press down: a ring that shrinks into the centre.
      el('circle', { class: 'press', cx: s.x, cy: s.y, r: RI, stroke: color }, over);
    } else {
      const [ax, ay] = pt(RO + 0.04, DIR_ANGLE[st.dir]), [bx, by] = pt(RO + 0.36, DIR_ANGLE[st.dir]);
      const [sx, sy] = local(s, ax * s.w, ay), [ex, ey] = local(s, bx * s.w, by);
      el('line', { class: 'push', x1: sx, y1: sy, x2: ex, y2: ey, stroke: color,
        'marker-end': 'url(#head-' + s.finger[1] + ')' }, over);
    }
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
    resolve: (spec, o) => Chorder.resolve(layout, spec, o),
    setTarget(res) {
      clear();
      if (!res || !res.steps.length) return;
      const strike = res.steps[res.steps.length - 1];
      svg.setAttribute('class', 'kb chorder ' + layout.device + ' layer-' + strike.layer);
      keysG.classList.add('focus');
      stepsEl.innerHTML = res.steps.map((st, i) => drawStep(st, i + 1, res.steps.length)).join('<br>');
    },
    setLive(code, down, key) {
      if (down) live[code] = Chorder.liveSlots(layout, code, key);
      for (const [id, d] of live[code] || []) {
        const w = wedgeEls[id + ':' + d];
        w.classList.toggle('live', down);
        if (down && !w.classList.contains('hole')) w.parentNode.insertBefore(w, w.parentNode.querySelector('.hole'));   // draw last (under the hole) so its outline sits on top
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
