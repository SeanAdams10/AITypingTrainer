/*
 * Spike 2: the K860 in 3D (three.js / WebGL), with an animated key press.
 *
 * Design intuition
 * ----------------
 * - Same layout data as the 2D spikes. A 2D key position (x, y) becomes a 3D
 *   position (x, 0, y): the board lies on the floor, "up" is the y axis.
 * - Every keycap is a real extruded rounded box with its label on a thin
 *   plane glued to the top, so the label travels down with the cap.
 * - Animation is driven by time, not by frames. Each key has a press amount
 *   p (0 = up, 1 = bottomed out) that chases a goal with exponential easing:
 *       p += (goal - p) * (1 - exp(-dt / tau))
 *   Because it uses the real elapsed time dt, it looks the same at 60 Hz or
 *   144 Hz, and a dropped frame does not make the key jump. Down uses a short
 *   tau (a snappy strike), up a longer one (the spring returning).
 * - With a camera only 5 degrees off vertical, a key dropping 2-3 mm is hard
 *   to see from geometry alone. What sells it is lighting: the directional
 *   light casts shadows, so a sunken cap falls into its neighbours' shadow
 *   and its side walls disappear. The highlight colour then carries "which".
 * - The press chord is choreographed like real fingers: hold keys (Shift,
 *   Ctrl) go down first, the strike key goes down and up, then the hold keys
 *   release.
 */
(function () {
  'use strict';
  const P = AppShell.param;
  const TILT_DEG = +P('tilt', 5);
  const TRAVEL = +P('travel', 0.16);   // key units; real K860 travel ~2 mm = 0.11u, a bit exaggerated
  const CYCLE = 1.6;                   // seconds per demo press loop

  const layout = K860.build({ splay: +P('splay', 6), gap: +P('gap', 0.9) });
  const stage = document.getElementById('stage');

  // ---- renderer, scene, camera -------------------------------------------
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x15171c);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 200);

  const palm = K860.palmOutline(layout);
  const cx = layout.width / 2;
  const cz = (Math.max(layout.height, ...palm.map(p => p.y)) ) / 2;
  const toWorld = (x, y) => [x - cx, y - cz];

  scene.add(new THREE.HemisphereLight(0xdde6ff, 0x20222a, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(-7, 16, 9);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 10, bottom: -10, near: 1, far: 50 });
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.02;
  scene.add(sun);

  // ---- geometry helpers ----------------------------------------------------
  function roundedRect(w, h, r) {
    const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
    s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
    s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
    s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
    return s;
  }
  function polyShape(points) {
    const s = new THREE.Shape();
    points.forEach((p, i) => { const [x, z] = toWorld(p.x, p.y); i ? s.lineTo(x, z) : s.moveTo(x, z); });
    return s;
  }
  // Extrude a flat 2D shape (drawn in x/z) into a slab whose top is at `top`.
  function slab(shape, depth, bevel, top) {
    const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: bevel > 0, bevelThickness: bevel,
      bevelSize: bevel, bevelSegments: 3, curveSegments: 6 });
    g.rotateX(Math.PI / 2);         // shape's y -> world z, extrusion goes downward
    g.translate(0, top - bevel, 0);
    return g;
  }

  // ---- case and palm rest --------------------------------------------------
  const caseMesh = new THREE.Mesh(slab(polyShape(K860.bodyOutline(layout.keys, 0.35)), 0.6, 0.12, 0),
    new THREE.MeshStandardMaterial({ color: 0x2b2e35, roughness: 0.8 }));
  caseMesh.receiveShadow = true;
  scene.add(caseMesh);
  const palmMesh = new THREE.Mesh(slab(polyShape(palm), 0.7, 0.3, 0.35),
    new THREE.MeshStandardMaterial({ color: 0x3a3d45, roughness: 1 }));
  palmMesh.receiveShadow = palmMesh.castShadow = true;
  scene.add(palmMesh);

  // ---- keys ----------------------------------------------------------------
  const CAP_H = 0.42, CAP_BASE = 0.08, BEVEL = 0.05;
  const COLORS = { base: 0x3d414a, main: 0xffb020, mod: 0xffd27a, live: 0x2f6aa8, ok: 0x3ddc84, bad: 0xff5a5f };
  const geoCache = {};
  function capGeometry(w, h) {
    const k = w + 'x' + h;
    return geoCache[k] || (geoCache[k] = slab(roundedRect(w - 0.2, h - 0.2, 0.12), CAP_H - 2 * BEVEL, BEVEL,
      CAP_BASE + CAP_H));
  }
  function labelTexture(k) {
    const PX = 128, c = document.createElement('canvas');
    c.width = Math.round((k.w - 0.24) * PX); c.height = Math.round((k.h - 0.24) * PX);
    const g = c.getContext('2d');
    g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    const font = s => (s * PX) + 'px "Segoe UI", system-ui, sans-serif';
    if (k.shiftLabel) {
      g.font = font(0.3); g.fillText(k.shiftLabel, c.width / 2, c.height / 2 - 0.17 * PX);
      g.fillText(k.label, c.width / 2, c.height / 2 + 0.2 * PX);
    } else {
      g.font = font(k.label.length > 2 ? 0.24 : 0.34); g.fillText(k.label, c.width / 2, c.height / 2);
    }
    const t = new THREE.CanvasTexture(c);
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }

  const keys = {};          // id -> key state
  for (const k of layout.keys) {
    const holder = new THREE.Group();
    const [x, z] = toWorld(k.x, k.y);
    holder.position.set(x, 0, z);
    holder.rotation.y = -k.angle * Math.PI / 180;   // 2D clockwise == 3D rotation about -y
    const mat = new THREE.MeshStandardMaterial({ color: COLORS.base, roughness: 0.55 });
    const cap = new THREE.Mesh(capGeometry(k.w, k.h), mat);
    cap.castShadow = cap.receiveShadow = true;
    const lblMat = new THREE.MeshBasicMaterial({ map: labelTexture(k), transparent: true, color: 0xd9dce2 });
    const lbl = new THREE.Mesh(new THREE.PlaneGeometry(k.w - 0.24, k.h - 0.24), lblMat);
    lbl.rotation.x = -Math.PI / 2;
    lbl.position.y = CAP_BASE + CAP_H + 0.002;
    cap.add(lbl);
    holder.add(cap);
    scene.add(holder);
    keys[k.id] = { k, cap, mat, lblMat, p: 0, role: null, live: false, flash: null };
  }
  const capsFor = code => (layout.byCode[code] || []).map(k => keys[k.id]);

  // ---- state from the app shell -------------------------------------------
  const clock = new THREE.Clock();
  let target = null, cycleStart = 0;
  const active = new Set();   // keys that are moving or highlighted, so we skip idle ones

  function paint(s) {
    let c = COLORS.base, e = 0;
    if (s.role === 'mod') { c = COLORS.mod; e = 0.15; }
    if (s.role === 'main') { c = COLORS.main; e = 0.35; }
    if (s.live && !s.role) c = COLORS.live;
    if (s.flash && performance.now() < s.flash.until) { c = s.flash.color; e = 0.4; }
    s.mat.color.setHex(c);
    s.mat.emissive.setHex(c);
    s.mat.emissiveIntensity = e;
    s.lblMat.color.setHex(s.role || (s.flash && performance.now() < s.flash.until) ? 0x1a1a1a : 0xd9dce2);
  }

  AppShell.start(layout, {
    setTarget(res) {
      if (target) for (const s of target.all) { s.role = null; paint(s); active.add(s); }
      target = null;
      if (res) {
        const mods = res.mods.flatMap(capsFor), main = capsFor(res.main);
        mods.forEach(s => { s.role = 'mod'; paint(s); active.add(s); });
        main.forEach(s => { s.role = 'main'; paint(s); active.add(s); });
        target = { mods, main, all: mods.concat(main) };
        cycleStart = clock.elapsedTime;
      }
    },
    setLive(code, down) {
      for (const s of capsFor(code)) { s.live = down; paint(s); active.add(s); }
    },
    flash(ok) {
      if (!target) return;
      for (const s of target.main) { s.flash = { color: ok ? COLORS.ok : COLORS.bad, until: performance.now() + 260 };
        paint(s); active.add(s); }
    },
  });

  // Demo choreography: hold keys down first, strike, release in reverse.
  function demoGoal(s, t) {
    if (!target) return 0;
    const hasMods = target.mods.length > 0;
    if (s.role === 'mod') return t > 0.1 && t < 0.95 ? 1 : 0;
    if (s.role === 'main') return hasMods ? (t > 0.38 && t < 0.72 ? 1 : 0) : (t > 0.2 && t < 0.55 ? 1 : 0);
    return 0;
  }

  // ---- camera fitting and view controls ------------------------------------
  let yaw = 0, tilt = TILT_DEG;
  const note = document.getElementById('view-note');
  function fit() {
    const w = stage.clientWidth, h = stage.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const bw = layout.width + 0.6, bh = cz * 2 + 0.6;
    const t = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const d = Math.max((bh / 2) / t, (bw / 2) / (t * camera.aspect)) * 1.04;
    const a = THREE.MathUtils.degToRad(tilt), b = THREE.MathUtils.degToRad(yaw);
    // Start straight above, lean `tilt` degrees toward the typist, then swing by yaw.
    camera.position.set(d * Math.sin(a) * Math.sin(b), d * Math.cos(a), d * Math.sin(a) * Math.cos(b));
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    note.textContent = ' \u00b7 view: ' + tilt.toFixed(1) + '° off top-down' + (yaw ? ', turned ' + yaw.toFixed(0) + '°' : '');
  }
  new ResizeObserver(fit).observe(stage);

  let drag = null;
  renderer.domElement.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, yaw, tilt };
    renderer.domElement.setPointerCapture(e.pointerId); });
  renderer.domElement.addEventListener('pointermove', e => {
    if (!drag) return;
    yaw = drag.yaw - (e.clientX - drag.x) * 0.25;
    tilt = Math.min(75, Math.max(0, drag.tilt + (e.clientY - drag.y) * 0.2));
    fit();
  });
  renderer.domElement.addEventListener('pointerup', () => { drag = null; });
  renderer.domElement.addEventListener('dblclick', () => { yaw = 0; tilt = TILT_DEG; fit(); });

  // ---- frame loop -----------------------------------------------------------
  function frame() {
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = (clock.elapsedTime - cycleStart) % CYCLE;
    for (const s of active) {
      const goal = s.live ? 1 : demoGoal(s, t);
      const tau = goal > s.p ? 0.022 : 0.045;
      s.p += (goal - s.p) * (1 - Math.exp(-dt / tau));
      s.cap.position.y = -TRAVEL * s.p;
      if (s.flash && performance.now() >= s.flash.until) { s.flash = null; paint(s); }
      if (!s.role && !s.live && !s.flash && s.p < 0.001) { s.p = 0; s.cap.position.y = 0; active.delete(s); }
    }
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  fit();
  requestAnimationFrame(frame);
})();
