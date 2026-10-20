/*
 * Spike 5: the CharaChorder Master Forge in 3D (three.js / WebGL), with every
 * switch a little joystick.
 *
 * Where the shape comes from
 * --------------------------
 * The geometry is CharaChorder's own CAD (github.com/CharaChorder/CAD-CAM,
 * "Master Forge"), used under the CharaChorder BY-SA-CR licence
 * (github.com/CharaChorder/CAD-CAM/blob/main/LICENSE.md): non-commercial,
 * credit CharaChorder, share alike. Changes made: the flat shell was folded,
 * and the meshes were converted to plain arrays in 5_forge_3d_cad.js.
 * - The aluminium shell is published FLAT, the way it is laser cut: one sheet
 *   with V-grooves where it bends. The pipeline splits the sheet into panels
 *   along those grooves and folds each panel about its groove line, the way
 *   the sheet is bent in the factory. Only six fold angles are free (the
 *   halves are symmetric), and they were solved so the folded panels land on
 *   the faces of the black internal frame (the endoskeleton) that they are
 *   screwed to: the front panel on the window face, the side walls on the
 *   side plates, the thumb and outer facets parallel to the frame walls the
 *   thumb board sits on. Folding the real outline is what keeps every crease,
 *   hole and window where it really is; tracing photos never got that right.
 * - The frame, the slotted rails along the back V, the bookend bar across
 *   the front and the moulded caps are CharaChorder's meshes as published.
 *   The gritty skirts are simple quads under the side facets.
 *
 * Design intuition for the rendering
 * ----------------------------------
 * - Folded sheet metal is a few flat facets, so everything is drawn with FLAT
 *   normals: each facet catches the light on its own and creases stay crisp.
 *   Smoothing the normals would melt the angularity.
 * - Aluminium = metalness 1 + a brushed-streak texture. The streaks use the
 *   FLAT-sheet coordinates, so the brushing runs on across each fold exactly
 *   as it does on a sheet brushed before bending. Metal only reflects its
 *   surroundings, so a tiny made-up studio provides the environment.
 * - Logos are alpha masks (the CharaChorder mark measured from your image,
 *   the Forge mark cut from the silver logo) on a dark plane on the logo face.
 * - LED windows are emissive panes just behind the real cut-outs.
 * - Each switch is a joystick: a "stick" (boot + cap) that pivots about a
 *   point a little BELOW the surface, which is why a real joystick cap slides
 *   sideways as it tilts. Every mount has its own frame (east, normal,
 *   south), so a thumb switch tilts in its own facet's plane.
 * - Motion is a damped spring per switch in small fixed substeps (stable at
 *   any frame rate; zeta about 0.55 gives a small overshoot on release).
 *   Frames are drawn only while something moves, so an idle page costs
 *   nothing.
 *
 * Directions follow the Keyboard Map View: N = away from you, S = toward you,
 * E/W = screen right/left, D = press down. On the slanted thumb face "N" is up
 * the slope (toward the deck); that is an assumption to check on the device.
 */
(function () {
  'use strict';
  const P = AppShell.param;
  const JOINED = P('joined', '0') === '1';
  const LEDS = P('led', '1') !== '0';
  const TILT = 16 * Math.PI / 180;   // full push, radians
  const TRAVEL = 0.1;                 // press-down travel, plan units

  const layout = Chorder.build('forge', { joined: JOINED });
  const dev = Chorder.DEVICES.forge;
  const stage = document.getElementById('stage');
  const css = getComputedStyle(document.documentElement);
  const fingerColor = f => new THREE.Color(css.getPropertyValue('--f-' + f).trim() || '#ffb020');
  const LIVE = new THREE.Color(css.getPropertyValue('--live').trim() || '#3fa7ff');

  // ---- renderer, scene, camera -------------------------------------------
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x15171c);
  const camera = new THREE.PerspectiveCamera(32, 1, 0.3, 200);

  // A tiny studio for the metal to reflect: a dim box with a big soft panel
  // overhead and a couple of strip lights. Pre-filtered once with PMREM.
  (function studio() {
    const env = new THREE.Scene();
    const room = new THREE.Mesh(new THREE.BoxGeometry(40, 20, 40),
      new THREE.MeshBasicMaterial({ color: 0x5d6067, side: THREE.BackSide }));
    room.position.y = 8;
    env.add(room);
    const panel = (w, h, x, y, z, ry, rx, c) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.rotation.set(rx, ry, 0); env.add(m);
    };
    panel(10, 6, 0, 17.5, 0, 0, Math.PI / 2, new THREE.Color(2.7, 2.7, 2.8));     // ceiling softbox
    panel(30, 2.2, 0, 7, -19.5, 0, 0, new THREE.Color(2.2, 2.2, 2.4));            // strip behind
    panel(2.2, 12, -19.5, 7, 0, Math.PI / 2, 0, new THREE.Color(1.6, 1.7, 2.0));  // strip left
    panel(30, 12, 0, 6, 19.5, 0, 0, new THREE.Color(2.4, 2.3, 2.2));              // warm wall behind you
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(env, 0.03).texture;
    pmrem.dispose();
  })();

  scene.add(new THREE.HemisphereLight(0xe8eeff, 0x1a1c20, 0.35));
  const sun = new THREE.DirectionalLight(0xffffff, 1.25);
  sun.position.set(-6, 15, 8);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 9, bottom: -9, near: 1, far: 45 });
  sun.shadow.bias = -0.0003;
  sun.shadow.normalBias = 0.02;
  scene.add(sun);

  // Desk.
  const desk = new THREE.Mesh(new THREE.PlaneGeometry(80, 80),
    new THREE.MeshStandardMaterial({ color: 0x1d2026, roughness: 0.92, metalness: 0 }));
  desk.rotation.x = -Math.PI / 2;
  desk.receiveShadow = true;
  scene.add(desk);

  // ---- textures --------------------------------------------------------------
  function canvasTex(w, h, draw, srgb) {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    draw(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c);
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return t;
  }
  // Brushed aluminium: thousands of thin horizontal streaks of random
  // brightness. The same picture drives colour (subtle) and roughness (the
  // streaks scatter the reflection along the brushing direction).
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const brushed = canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = '#c4c4c4'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 9000; i++) {
      const v = 150 + rnd() * 105 | 0;
      g.strokeStyle = 'rgba(' + v + ',' + v + ',' + v + ',' + (0.12 + rnd() * 0.25).toFixed(2) + ')';
      g.lineWidth = 0.5 + rnd();
      const y = rnd() * h, x = rnd() * w, len = 40 + rnd() * 260;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + len, y); g.stroke();
      if (x + len > w) { g.beginPath(); g.moveTo(x - w, y); g.lineTo(x + len - w, y); g.stroke(); }
    }
  });
  brushed.wrapS = brushed.wrapT = THREE.RepeatWrapping;
  const grit = canvasTex(256, 256, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = 40 + rnd() * 120 | 0;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  });
  grit.wrapS = grit.wrapT = THREE.RepeatWrapping;
  grit.repeat.set(3, 3);

  // Logos are alpha masks (white = etched black on the metal).
  const logoTex = {
    // CharaChorder, measured on the reference Sean sent (radius R): a disc
    // with a hairline ring cut through it between 0.651R and 0.710R, and a
    // slot 0.588R tall whose rounded left end is centred 0.026R right of the
    // middle; the slot runs out through the right side, opening both rings.
    cc: canvasTex(512, 512, (g, w) => {
      const c = w / 2, R = w / 2 - 2;
      g.fillStyle = '#000'; g.fillRect(0, 0, w, w);
      g.fillStyle = '#fff';
      g.beginPath(); g.arc(c, c, R, 0, 2 * Math.PI); g.fill();
      g.fillStyle = '#000';
      g.beginPath(); g.arc(c, c, R * 0.710, 0, 2 * Math.PI); g.arc(c, c, R * 0.651, 0, 2 * Math.PI, true); g.fill();
      const hh = R * 0.294, x0 = c + R * 0.026;
      g.beginPath(); g.arc(x0, c, hh, Math.PI / 2, Math.PI * 1.5); g.lineTo(w, c - hh); g.lineTo(w, c + hh);
      g.closePath(); g.fill();
    }),
    // Forge: the mark itself, cut out of the high-resolution silver logo
    // Sean sent (thresholded, so the edges are the real ones, not a tracing).
    forge: canvasTex(512, 347, g => {
      g.fillStyle = '#000'; g.fillRect(0, 0, 512, 347);
    }),
  };
  (() => {
    const img = new Image();
    img.onload = () => {
      logoTex.forge.image.getContext('2d').drawImage(img, 0, 0, 512, 347);
      logoTex.forge.needsUpdate = true;
      wake();
    };
    img.src = window.FORGE_CAD.forgeMask;
  })();

  // ---- materials -------------------------------------------------------------
  const MAT = {
    alu: new THREE.MeshStandardMaterial({ color: 0xd4d7dc, metalness: 1, roughness: 0.48, map: brushed,
      roughnessMap: brushed, envMapIntensity: 1.0, side: THREE.DoubleSide, flatShading: true }),
    black: new THREE.MeshStandardMaterial({ color: 0x0b0c0e, metalness: 0, roughness: 0.3, side: THREE.DoubleSide,
      flatShading: true }),
    // The skirts are a matte, sandpaper-like black: speckle drives colour,
    // roughness and a bump map so the light breaks up into grain.
    grit: new THREE.MeshStandardMaterial({ color: 0x2a2b2e, map: grit, roughnessMap: grit, bumpMap: grit,
      bumpScale: 0.6, metalness: 0, roughness: 1, side: THREE.DoubleSide, flatShading: true }),
    rail: new THREE.MeshStandardMaterial({ color: 0xdfe2e6, metalness: 1, roughness: 0.32,
      side: THREE.DoubleSide, flatShading: true }),
    collar: new THREE.MeshStandardMaterial({ color: 0x050506, metalness: 0, roughness: 0.8 }),
    stem: new THREE.MeshStandardMaterial({ color: 0x2a2c30, metalness: 0.6, roughness: 0.4 }),
    port: new THREE.MeshStandardMaterial({ color: 0x050506, roughness: 0.6 }),
    cable: new THREE.MeshStandardMaterial({ color: 0xb3121c, roughness: 0.55 }),
    plug: new THREE.MeshStandardMaterial({ color: 0xc0141e, metalness: 0.3, roughness: 0.35 }),
  };
  // An LED window: dark smoked glass that glows when the LEDs are on.
  const ledMat = (color, k = 1) => new THREE.MeshStandardMaterial({ color: 0x050607, emissive: color,
    emissiveIntensity: LEDS ? 0.4 * k : 0, roughness: 0.15, polygonOffset: true, polygonOffsetFactor: -2,
    side: THREE.DoubleSide });

  // ---- placing a half ------------------------------------------------------
  // The CAD data (5_forge_3d_cad.js) is the LEFT half in millimetres: x right,
  // y up, z toward you. Each half is turned 7.5 degrees about its own middle
  // and pushed out sideways, the same as the 2D view (chorder_layout.js); the
  // right half is the left one mirrored. One switch pitch is about 18 mm, so
  // 18 mm = 1 scene unit keeps the camera and lights from the plan-unit days.
  const CAD = window.FORGE_CAD;
  const S = 1 / 18;
  const MID_Z = 37;                     // middle of a half, front to back (mm)
  const offset = JOINED ? 3.32 : dev.offset;
  function halfMatrix(half) {
    const sign = half === 'L' ? 1 : -1;
    const m = new THREE.Matrix4().makeTranslation(-sign * offset, 0, 0);
    m.multiply(new THREE.Matrix4().makeRotationY(-sign * dev.halfAngle * Math.PI / 180));
    m.multiply(new THREE.Matrix4().makeScale(sign * S, S, S));
    m.multiply(new THREE.Matrix4().makeTranslation(0, 0, -MID_Z));
    return m;
  }
  const v3 = a => new THREE.Vector3(a[0], a[1], a[2]);

  // A BufferGeometry from the integer arrays in the CAD file.
  function cadGeo(src, k = 100) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(src.v.map(n => n / k), 3));
    if (src.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(src.uv.map(n => n / 10 * 0.035), 2));
    g.setIndex(src.i);
    return g;
  }
  // Grit needs texture coordinates and the CAD frame has none: give every
  // triangle a box projection along its own strongest axis.
  function boxUV(g, scale) {
    const p = g.attributes.position, uv = new Float32Array(p.count * 2), a = new THREE.Vector3(),
      b = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3();
    for (let i = 0; i < p.count; i += 3) {
      a.fromBufferAttribute(p, i); b.fromBufferAttribute(p, i + 1); c.fromBufferAttribute(p, i + 2);
      n.subVectors(c, b).cross(a.clone().sub(b));
      const ax = Math.abs(n.x), ay = Math.abs(n.y), az = Math.abs(n.z);
      for (let j = 0; j < 3; j++) {
        const q = [a, b, c][j];
        const [u, v] = ax >= ay && ax >= az ? [q.y, q.z] : ay >= az ? [q.x, q.z] : [q.x, q.y];
        uv[(i + j) * 2] = u * scale; uv[(i + j) * 2 + 1] = v * scale;
      }
    }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    return g;
  }

  // Shared geometry, built once and reused by both halves.
  const shellGeo = Object.values(CAD.shell).map(p => cadGeo(p));
  const endoGeo = (() => {
    // Gloss triangles (the LED pods) first, grit after, as two draw groups.
    const isGloss = new Uint8Array(CAD.endo.i.length / 3);
    for (const t of CAD.endo.gloss) isGloss[t] = 1;
    const order = [];
    for (const want of [1, 0]) for (let t = 0; t < isGloss.length; t++) if (isGloss[t] === want) order.push(t);
    const idx = [];
    for (const t of order) idx.push(CAD.endo.i[3 * t], CAD.endo.i[3 * t + 1], CAD.endo.i[3 * t + 2]);
    const g = cadGeo({ v: CAD.endo.v, i: idx }).toNonIndexed();
    g.addGroup(0, CAD.endo.gloss.length * 3, 0);
    g.addGroup(CAD.endo.gloss.length * 3, idx.length - CAD.endo.gloss.length * 3, 1);
    return boxUV(g, 0.12);
  })();
  const railGeo = cadGeo(CAD.rail);
  const bookendGeo = cadGeo(CAD.bookend);
  // Cap screw seated in a counterbore: axis along +z (out of the tab), head top flush with the bar.
  const screwGeo = new THREE.CylinderGeometry(2.4, 2.4, 2.6, 24).rotateX(Math.PI / 2).translate(0, 0, 1.3);
  const screwMat = new THREE.MeshStandardMaterial({ color: 0x08080a, metalness: 0.2, roughness: 0.45 });
  const skirtGeo = (() => {
    const pos = [];
    for (const s of CAD.skirts) for (const k of [0, 1, 2, 0, 2, 3]) pos.push(...s[k]);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    return boxUV(g, 0.12);
  })();
  const polyGeo = pts => {
    // A flat polygon from 3D points (fan from the centre).
    const c = pts.reduce((s, p) => s.add(v3(p)), new THREE.Vector3()).multiplyScalar(1 / pts.length);
    const pos = [];
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      pos.push(c.x, c.y, c.z, ...a, ...b);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.computeVertexNormals();
    return g;
  };

  const pickable = [];
  const switches = {};          // 'L.index' -> switch object
  const body = new THREE.Group();
  scene.add(body);

  // A frame on a surface: east, normal, south. "north" is the reference
  // direction projected into the surface (away from you on the deck, up the
  // slope on a steep face); east = north x normal is then screen-right.
  function surfaceFrame(normal) {
    const ref = Math.abs(normal.y) > 0.8 ? new THREE.Vector3(0, 0, -1) : new THREE.Vector3(0, 1, 0);
    const north = ref.sub(normal.clone().multiplyScalar(ref.dot(normal))).normalize();
    const east = north.clone().cross(normal).normalize();
    return { east, normal: normal.clone(), north, south: north.clone().negate() };
  }

  function buildHalf(half) {
    const M = halfMatrix(half);
    const R = new THREE.Matrix3().setFromMatrix4(M);
    const P = a => v3(a).applyMatrix4(M);                       // CAD point -> world
    const N = a => v3(a).applyMatrix3(R).normalize();           // CAD direction -> world
    const g = new THREE.Group();
    g.matrixAutoUpdate = false;
    g.matrix.copy(M);
    body.add(g);
    const add = (geo, mat, shadow = true) => {
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = m.receiveShadow = shadow;
      g.add(m);
      return m;
    };

    for (const geo of shellGeo) add(geo, MAT.alu);
    add(endoGeo, [MAT.black, MAT.grit]);
    add(skirtGeo, MAT.grit);
    for (const m of CAD.rail.m) {
      const r = add(railGeo, MAT.rail);
      r.matrixAutoUpdate = false;
      r.matrix.fromArray(m).transpose();
    }
    // The bookend bar across the front tab, held by two black cap screws.
    const be = add(bookendGeo, MAT.rail);
    be.matrixAutoUpdate = false;
    be.matrix.fromArray(CAD.bookend.m).transpose();
    for (const sc of CAD.bookend.screws) add(screwGeo, screwMat).position.fromArray(sc);
    const ledColor = new THREE.Color(half === 'L' ? 0x19ff7a : 0x9b5cff);
    // LED windows: a glowing pane just behind each hole in the pods and in
    // the front panel, so the light shows through the real cut-outs.
    for (const led of CAD.leds) add(polyGeo(led.pts), ledMat(ledColor), false);
    add(polyGeo(CAD.window.pts), ledMat(ledColor, 0.45), false);
    if (LEDS) {
      const glow = new THREE.PointLight(ledColor, 0.8, 3, 2);
      glow.position.copy(P([half === 'L' ? 50 : 50, 14, 48]));
      body.add(glow);
    }

    // Logo, lying on the logo face with its top toward the deck. Built in
    // world space (not inside the mirrored group) so it never reads backwards.
    const L = CAD.logo, n = N(L.n), up = N(L.up), right = up.clone().cross(n).normalize();
    const tex = logoTex[half === 'L' ? 'cc' : 'forge'];
    const size = L.size * S, aspect = tex.image.height / tex.image.width;
    const logo = new THREE.Mesh(new THREE.PlaneGeometry(size, size * aspect), new THREE.MeshStandardMaterial({
      color: 0x0b0b0d, alphaMap: tex, transparent: true, roughness: 0.55, metalness: 0,
      polygonOffset: true, polygonOffsetFactor: -2 }));
    logo.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, n));
    logo.position.copy(P(L.p)).addScaledVector(n, 0.002);
    logo.receiveShadow = true;
    body.add(logo);

    // ---- switches ----------------------------------------------------------
    for (const sw of dev.switches) {
      const c = CAD.switches[sw.id];
      const id = half + '.' + sw.id;
      switches[id] = makeSwitch(id, P(c.p), N(c.n), sw.id === 'pinky', half + sw.finger);
    }
  }

  function roundedRectGeo(w, h, r) {
    const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
    s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
    s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
    s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
    return new THREE.ShapeGeometry(s, 6);
  }

  // A joystick switch. mount: fixed frame on the surface (x east, y normal,
  // z south). stick: pivots under the surface and carries the boot and cap.
  // The cap is CharaChorder's own moulded primary cap (12.5 mm across), split
  // into its rubber body and the ring in the dish on top.
  const PIVOT_DEPTH = 0.32;
  const BOOT_H = 3.5;                   // mm of black joystick body showing above the deck
  const [capBodyGeo, capRingGeo] = (() => {
    const c = CAD.cap, body = [], ring = [];
    for (let t = 0; t < c.i.length; t += 3) {
      const tri = [c.i[t], c.i[t + 1], c.i[t + 2]];
      (tri.every(k => c.ring[k]) ? ring : body).push(...tri);
    }
    return [body, ring].map(idx => {
      const g = cadGeo({ v: c.v, i: idx }).scale(S, S, S).translate(0, BOOT_H * S, 0);
      g.computeVertexNormals();
      return g;
    });
  })();
  const bootGeo = new THREE.CylinderGeometry(5.0 * S, 5.4 * S, (BOOT_H + 2) * S, 32).translate(0, (BOOT_H - 2) / 2 * S, 0);
  const glowGeo = new THREE.TorusGeometry(0.47, 0.035, 8, 56).rotateX(Math.PI / 2).translate(0, 0.04, 0);
  const arrowGeo = (() => {
    const s = new THREE.Shape();
    s.moveTo(0, 0.95); s.lineTo(0.2, 0.68); s.lineTo(0.07, 0.68); s.lineTo(0.07, 0.56);
    s.lineTo(-0.07, 0.56); s.lineTo(-0.07, 0.68); s.lineTo(-0.2, 0.68); s.closePath();
    return new THREE.ShapeGeometry(s).rotateX(-Math.PI / 2).translate(0, 0.045, 0);
  })();
  const rubber = new THREE.MeshStandardMaterial({ color: 0x141518, roughness: 0.62, metalness: 0, flatShading: false });
  const redRubber = new THREE.MeshStandardMaterial({ color: 0xa3121b, roughness: 0.4, metalness: 0.1 });
  const silver = new THREE.MeshStandardMaterial({ color: 0xd9dce1, metalness: 1, roughness: 0.25 });
  const bootMat = new THREE.MeshStandardMaterial({ color: 0x0c0d0f, roughness: 0.5, metalness: 0 });

  function makeSwitch(id, at, normal, red, finger) {
    const fr = surfaceFrame(normal);
    const mount = new THREE.Group();
    mount.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(fr.east, fr.normal, fr.south));
    mount.position.copy(at);
    scene.add(mount);

    const tint = fingerColor(finger[1]);
    const glowMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0, toneMapped: false });
    const glow = new THREE.Mesh(glowGeo, glowMat);
    mount.add(glow);
    const arrowMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0, toneMapped: false,
      side: THREE.DoubleSide });
    const arrow = new THREE.Mesh(arrowGeo, arrowMat);
    mount.add(arrow);

    const pivot = new THREE.Group();
    pivot.position.y = -PIVOT_DEPTH;
    mount.add(pivot);
    const stick = new THREE.Group();
    stick.position.y = PIVOT_DEPTH;          // stick's origin sits at the surface again
    pivot.add(stick);
    const capMat = (red ? redRubber : rubber).clone();
    const cap = new THREE.Mesh(capBodyGeo, capMat);
    cap.castShadow = true;
    const boot = new THREE.Mesh(bootGeo, bootMat);
    boot.castShadow = true;
    stick.add(boot, cap, new THREE.Mesh(capRingGeo, red ? new THREE.MeshStandardMaterial({ color: 0xff7c84,
      roughness: 0.35 }) : silver));
    cap.userData.switchId = id;
    boot.userData.switchId = id;
    pickable.push(cap, boot);

    return {
      id, mount, pivot, stick, capMat, glowMat, arrow, arrowMat, tint, fr,
      // spring state: tilt east / north as fractions of a full push, press 0..1
      x: 0, y: 0, p: 0, vx: 0, vy: 0, vp: 0,
      gx: 0, gy: 0, gp: 0,          // goal
      glow: 0, glowGoal: 0, glowColor: tint.clone(), liveDir: null, dragged: false,
    };
  }

  buildHalf('L');
  buildHalf('R');
  if (JOINED) {
    // CharaChorder's bridge bar clips the backs of the two halves together.
    const a = new THREE.Vector3(0, 0, 0).applyMatrix4(halfMatrix('L')).setY(0.18);
    const b = new THREE.Vector3(0, 0, 0).applyMatrix4(halfMatrix('R')).setY(0.18);
    const br = new THREE.Mesh(new THREE.BoxGeometry(a.distanceTo(b) * 0.55, 0.32, 0.6), MAT.black);
    br.position.copy(a).lerp(b, 0.5);
    br.castShadow = true;
    scene.add(br);
  }

  // Centre everything on the origin.
  const box = new THREE.Box3().setFromObject(body);
  const centre = box.getCenter(new THREE.Vector3()).setY(0);
  for (const o of [...scene.children]) if (o !== desk && !o.isLight) o.position.sub(centre);
  const span = box.getSize(new THREE.Vector3());

  // ---- camera: orbit around the board --------------------------------------
  const HOME = { az: 0, el: 42 * Math.PI / 180, dist: Math.max(span.x, span.z) * 1.2 };
  const view = Object.assign({}, HOME);
  const look = new THREE.Vector3(0, 0.8, 0.9);
  function placeCamera() {
    camera.position.set(look.x + view.dist * Math.cos(view.el) * Math.sin(view.az), look.y + view.dist * Math.sin(view.el),
      look.z + view.dist * Math.cos(view.el) * Math.cos(view.az));
    camera.lookAt(look);
  }
  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    // Fit the board's width on narrow screens.
    view.fitDist = HOME.dist * Math.max(1, 1.4 / camera.aspect);
    camera.updateProjectionMatrix();
    wake();
  }

  // ---- pointer: orbit, zoom, or push a switch -----------------------------
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  let drag = null;
  const cv = renderer.domElement;
  cv.style.touchAction = 'none';
  function toNdc(e) {
    const r = cv.getBoundingClientRect();
    ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  }
  cv.addEventListener('pointerdown', e => {
    toNdc(e);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickable, false)[0];
    cv.setPointerCapture(e.pointerId);
    if (hit) {
      const sw = switches[hit.object.userData.switchId];
      sw.dragged = true;
      drag = { kind: 'switch', sw, x0: e.clientX, y0: e.clientY };
    } else {
      drag = { kind: 'orbit', x: e.clientX, y: e.clientY };
    }
  });
  cv.addEventListener('pointermove', e => {
    if (!drag) {
      toNdc(e); ray.setFromCamera(ndc, camera);
      cv.style.cursor = ray.intersectObjects(pickable, false).length ? 'grab' : 'default';
      return;
    }
    if (drag.kind === 'orbit') {
      view.az -= (e.clientX - drag.x) * 0.006;
      view.el = Math.min(1.5, Math.max(0.12, view.el + (e.clientY - drag.y) * 0.005));
      drag.x = e.clientX; drag.y = e.clientY;
      wake();
    } else {
      // Screen drag -> push direction in the switch's own plane: project its
      // east and north axes to the screen and see which way the drag points.
      const sw = drag.sw, o = sw.mount.getWorldPosition(new THREE.Vector3());
      const scr = v => { const p = v.clone().project(camera); return new THREE.Vector2(p.x, -p.y); };
      const s0 = scr(o), se = scr(o.clone().add(sw.fr.east)).sub(s0), sn = scr(o.clone().add(sw.fr.north)).sub(s0);
      const d = new THREE.Vector2(e.clientX - drag.x0, e.clientY - drag.y0);
      const ex = se.clone().normalize(), nx = sn.clone().normalize();
      let gx = d.dot(ex), gy = d.dot(nx);
      const len = Math.hypot(gx, gy), full = 40;
      if (len > full) { gx *= full / len; gy *= full / len; }
      sw.gx = gx / full; sw.gy = gy / full;
      wake();
    }
  });
  const endDrag = () => {
    if (drag && drag.kind === 'switch') { drag.sw.dragged = false; restGoal(drag.sw); }
    drag = null; wake();
  };
  cv.addEventListener('pointerup', endDrag);
  cv.addEventListener('pointercancel', endDrag);
  cv.addEventListener('wheel', e => {
    e.preventDefault();
    view.dist = Math.min(40, Math.max(5, view.dist * Math.exp(e.deltaY * 0.001)));
    wake();
  }, { passive: false });
  cv.addEventListener('dblclick', () => { Object.assign(view, HOME, { dist: view.fitDist || HOME.dist }); wake(); });

  // ---- what to show ----------------------------------------------------------
  const DIRV = { N: [0, 1, 0], S: [0, -1, 0], E: [1, 0, 0], W: [-1, 0, 0], D: [0, 0, 1] };
  let chord = null;          // { holds: [[sw, dir]], strike: [sw, dir], t0 }
  const live = new Map();    // code -> [sw, dir]

  function restGoal(sw) {
    // What a switch should do when nobody is dragging it: live key wins,
    // then the demo chord, else centre.
    sw.gx = sw.gy = sw.gp = 0;
    for (const [, [s, d]] of live) if (s === sw) { [sw.gx, sw.gy, sw.gp] = DIRV[d]; }
  }

  function setArrow(sw, dir, color, on) {
    sw.arrowMat.color.copy(color);
    sw.arrowMat.opacity = on && dir !== 'D' ? 0.95 : 0;
    const ang = { N: 0, W: Math.PI / 2, S: Math.PI, E: -Math.PI / 2 }[dir] || 0;
    sw.arrow.rotation.y = ang;
  }

  function setTarget(res) {
    for (const id in switches) {
      const sw = switches[id];
      sw.glowGoal = 0; setArrow(sw, 'N', sw.tint, false);
    }
    chord = null;
    if (res && res.steps && res.steps.length) {
      const holds = [], strike = [];
      for (const st of res.steps) {
        const sw = switches[st.sw.id];
        if (!sw) continue;
        (st.verb === 'hold' ? holds : strike).push([sw, st.dir]);
        sw.glowGoal = st.verb === 'hold' ? 0.55 : 1;
        sw.glowColor.copy(sw.tint);
        setArrow(sw, st.dir, sw.tint, true);
      }
      chord = { holds, strike: strike[0], t0: performance.now() / 1000 };
    }
    for (const id in switches) if (!switches[id].dragged) restGoal(switches[id]);
    wake();
  }

  // The chord as real fingers do it, on a 1.8 s loop: holds go in, the strike
  // goes in and comes back, then the holds let go.
  const CYCLE = 1.8;
  function choreograph(now) {
    if (!chord) return;
    const t = (now - chord.t0) % CYCLE;
    const holdOn = t > 0.1 && t < 1.25;
    const strikeOn = t > 0.4 && t < 0.85;
    const apply = ([sw, dir], on) => {
      if (sw.dragged || [...live.values()].some(([s]) => s === sw)) return;
      [sw.gx, sw.gy, sw.gp] = on ? DIRV[dir] : [0, 0, 0];
    };
    for (const h of chord.holds) apply(h, holdOn);
    if (chord.strike) apply(chord.strike, strikeOn);
  }

  // Wiggle: every switch goes round its four directions and presses, in a
  // wave from the left pinky to the right pinky.
  let wiggle = null;
  const ORDER = ['L.pinky', 'L.ring', 'L.aux1', 'L.middle', 'L.aux2', 'L.index', 'L.thumb1', 'L.thumb2',
    'R.thumb2', 'R.thumb1', 'R.index', 'R.aux2', 'R.middle', 'R.aux1', 'R.ring', 'R.pinky'];
  function runWiggle(now) {
    if (!wiggle) return;
    const t = now - wiggle;
    let busy = false;
    ORDER.forEach((id, i) => {
      const sw = switches[id], lt = t - i * 0.09;
      if (lt < 0 || lt > 2.6) { if (lt > 2.6 && lt < 2.7) restGoal(sw); busy = busy || lt < 0; return; }
      busy = true;
      const seq = ['N', 'E', 'S', 'W', 'D', null], d = seq[Math.min(5, Math.floor(lt / 0.42))];
      [sw.gx, sw.gy, sw.gp] = d ? DIRV[d] : [0, 0, 0];
    });
    if (!busy) { wiggle = null; for (const id in switches) restGoal(switches[id]); }
  }

  // ---- springs and the frame loop ------------------------------------------
  const K = 900, ZETA = 0.55, STEP = 1 / 240;
  function stepSprings(dt) {
    let moving = false;
    for (const id in switches) {
      const s = switches[id];
      // Pushing in is quicker than the spring bringing it back.
      for (let tt = 0; tt < dt; tt += STEP) {
        const h = Math.min(STEP, dt - tt);
        const k = (s.gx || s.gy || s.gp) ? K * 1.6 : K, c = 2 * ZETA * Math.sqrt(k);
        s.vx += (k * (s.gx - s.x) - c * s.vx) * h; s.x += s.vx * h;
        s.vy += (k * (s.gy - s.y) - c * s.vy) * h; s.y += s.vy * h;
        s.vp += (k * (s.gp - s.p) - c * s.vp) * h; s.p += s.vp * h;
      }
      // Keep the push inside a circle, like the gate of a real stick.
      const r = Math.hypot(s.x, s.y);
      if (r > 1.08) { s.x *= 1.08 / r; s.y *= 1.08 / r; }
      s.pivot.rotation.set(-s.y * TILT, 0, -s.x * TILT);
      s.stick.position.y = PIVOT_DEPTH - s.p * TRAVEL;
      const glowWant = s.glowGoal;
      s.glow += (glowWant - s.glow) * (1 - Math.exp(-dt / 0.08));
      const pushed = Math.min(1, Math.hypot(s.x, s.y) + s.p);
      s.glowMat.opacity = Math.min(1, s.glow * 0.9 + (s.liveDir ? 0.9 : 0));
      if (s.liveDir) s.glowMat.color.copy(LIVE); else s.glowMat.color.copy(s.glowColor);
      s.capMat.emissive.copy(s.liveDir ? LIVE : s.tint).multiplyScalar((s.liveDir ? 0.35 : s.glow * 0.28) * (0.5 + pushed));
      if (Math.abs(s.vx) + Math.abs(s.vy) + Math.abs(s.vp) > 1e-3 ||
          Math.abs(s.gx - s.x) + Math.abs(s.gy - s.y) + Math.abs(s.gp - s.p) > 1e-3 ||
          Math.abs(glowWant - s.glow) > 1e-3) moving = true;
    }
    return moving;
  }

  let awake = true, last = performance.now() / 1000, frames = 0, fpsT = last;
  const fpsEl = document.getElementById('fps'), showFps = P('fps', '0') === '1';
  function wake() { if (!awake) { awake = true; last = performance.now() / 1000; requestAnimationFrame(frame); } }
  function frame() {
    const now = performance.now() / 1000;
    const dt = Math.min(0.05, now - last);
    last = now;
    choreograph(now);
    runWiggle(now);
    const moving = stepSprings(dt);
    placeCamera();
    renderer.render(scene, camera);
    frames++;
    if (showFps && now - fpsT > 0.5) { fpsEl.textContent = (1000 * (now - fpsT) / frames).toFixed(1) + ' ms/frame'; frames = 0; fpsT = now; }
    // Keep running while anything animates; otherwise sleep until woken.
    if (moving || chord || wiggle || drag) requestAnimationFrame(frame);
    else awake = false;
  }

  window.addEventListener('resize', resize);
  resize();
  Object.assign(view, { dist: view.fitDist || HOME.dist });
  requestAnimationFrame(frame);

  // ---- app shell: bar, text stepping, your real keyboard ------------------
  AppShell.start(layout, {
    resolve: (spec, o) => Chorder.resolve(layout, spec, o),
    setTarget,
    setLive(code, down, key) {
      if (down) {
        const slots = Chorder.liveSlots(layout, code, key);
        if (!slots.length) return;
        const [id, dir] = slots[0];
        const sw = switches[id];
        if (!sw) return;
        live.set(code, [sw, dir]);
        sw.liveDir = dir;
        if (!sw.dragged) [sw.gx, sw.gy, sw.gp] = DIRV[dir];
      } else {
        const e = live.get(code);
        if (!e) return;
        live.delete(code);
        e[0].liveDir = null;
        if (!e[0].dragged) restGoal(e[0]);
      }
      wake();
    },
    flash(ok) {
      scene.background.set(ok ? 0x16301f : 0x341a1c);
      wake();
      setTimeout(() => { scene.background.set(0x15171c); wake(); }, 140);
    },
  });

  // Extra controls for this spike: wiggle demo and joined halves.
  const form = document.querySelector('.bar form');
  if (form) {
    const box = document.createElement('span');
    box.className = 'spike5';
    const w = document.createElement('button');
    w.type = 'button'; w.textContent = 'Wiggle';
    w.title = 'Push every switch round its four directions and press it';
    w.addEventListener('click', () => { wiggle = performance.now() / 1000; wake(); w.blur(); });
    const lab = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = JOINED;
    cb.addEventListener('change', () => {
      const q = new URLSearchParams(location.search);
      if (cb.checked) q.set('joined', '1'); else q.delete('joined');
      location.search = q;
    });
    lab.append(cb, 'Joined');
    box.append(w, lab);
    form.append(box);
  }
  if (P('wiggle', '0') === '1') { wiggle = performance.now() / 1000 + 0.4; wake(); }

  // For screenshots and the host app.
  window.Forge3D = { switches, view, look, wake, wiggle: () => { wiggle = performance.now() / 1000; wake(); },
    push(id, dir) { const sw = switches[id]; [sw.gx, sw.gy, sw.gp] = dir ? DIRV[dir] : [0, 0, 0]; wake(); } };
})();
