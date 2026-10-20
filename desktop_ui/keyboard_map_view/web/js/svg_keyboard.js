/*
 * Draws the K860 as one SVG, in key units (viewBox 1 = one key pitch), so it
 * scales to any window size with no re-layout.
 *
 * Why SVG for the 2D views: the board is ~105 shapes that never move. SVG
 * keeps them as live elements, so highlighting a key is just adding a CSS
 * class to it; the browser repaints only that key. Nothing is redrawn per
 * frame, which is why it stays smooth.
 */
(function (global) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';

  function el(name, attrs, parent) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function poly(points) { return points.map(p => p.x.toFixed(3) + ',' + p.y.toFixed(3)).join(' '); }

  function create(container, layout) {
    const palms = [K860.palmRest(layout, 'L'), K860.palmRest(layout, 'R')];
    const maxY = Math.max(layout.height, ...palms.flat().map(p => p.y + 0.5));
    const svg = el('svg', { viewBox: '0 0 ' + layout.width.toFixed(2) + ' ' + maxY.toFixed(2),
      class: 'kb', preserveAspectRatio: 'xMidYMid meet' }, container);

    const defs = el('defs', {}, svg);
    const body = el('g', { class: 'body' }, svg);
    const under = el('g', { class: 'under' }, svg);   // glows that sit under keycaps
    const keysG = el('g', { class: 'keys' }, svg);
    const over = el('g', { class: 'over' }, svg);     // arrows and labels on top

    // Case: hull of the keys. A thick round-joined stroke in the
    // same colour rounds the hull's corners for free.
    // The K860 is one piece, so one hull around every key, plus one palm cushion.
    el('polygon', { points: poly(K860.bodyOutline(layout.keys, 0.35)), class: 'case' }, body);
    el('polygon', { points: poly(K860.palmOutline(layout)), class: 'palm' }, body);

    const keyEls = {};
    for (const k of layout.keys) {
      const g = el('g', { class: 'key', 'data-code': k.code, 'data-id': k.id,
        transform: 'translate(' + k.x.toFixed(3) + ' ' + k.y.toFixed(3) + ') rotate(' + k.angle + ')' }, keysG);
      el('rect', { class: 'cap', x: -k.w / 2 + 0.06, y: -k.h / 2 + 0.06, width: k.w - 0.12, height: k.h - 0.12,
        rx: 0.13 }, g);
      if (k.shiftLabel) {
        el('text', { class: 'lbl', x: 0, y: -0.12, 'font-size': 0.27 }, g).textContent = k.shiftLabel;
        el('text', { class: 'lbl', x: 0, y: 0.25, 'font-size': 0.27 }, g).textContent = k.label;
      } else {
        el('text', { class: 'lbl', x: 0, y: 0.1, 'font-size': k.label.length > 2 ? 0.22 : 0.3 }, g)
          .textContent = k.label;
      }
      keyEls[k.id] = g;
    }

    function capsFor(code) { return (layout.byCode[code] || []).map(k => keyEls[k.id]); }
    function mark(codes, cls, on) {
      for (const c of codes) for (const g of capsFor(c)) g.classList.toggle(cls, on);
    }
    function clear(cls) { for (const g of svg.querySelectorAll('.key.' + cls)) g.classList.remove(cls); }

    return { svg, defs, body, under, keysG, over, keyEls, capsFor, mark, clear, el };
  }

  global.KbSvg = { create, el, poly };
})(window);
