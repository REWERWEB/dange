// Rendert STL-Teile mit three.js in Chromium (Playwright).
// Aufruf: node render_chromium.js <three.min.js> <ausgabe-prefix> <ansichten> datei.stl:#rrggbb ...
// ansichten z.B. "vorne_rechts,seite,front,heck"
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [threePath, outPrefix, viewsArg, ...files] = process.argv.slice(2);
const parts = files.map((f, i) => { const [p, c] = f.split(':'); return { p, c: c || '#dddddd', url: `/m${i}.stl` }; });

const server = http.createServer((req, res) => {
  if (req.url === '/three.js') { res.end(fs.readFileSync(threePath)); return; }
  const part = parts.find(x => x.url === req.url);
  if (part) { res.end(fs.readFileSync(part.p)); return; }
  res.setHeader('content-type', 'text/html');
  res.end(`<html><body style="margin:0;background:#fff"><script src="/three.js"></script></body></html>`);
});

(async () => {
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1 });
  page.on('console', m => console.log('page:', m.text()));
  await page.goto(`http://localhost:${port}/`);
  await page.evaluate(async (parts) => {
    const T = window.THREE;
    const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(1200, 900);
    renderer.setClearColor(0xf4f4f2);
    document.body.appendChild(renderer.domElement);
    const scene = new T.Scene();
    scene.add(new T.HemisphereLight(0xffffff, 0x777770, 1.6));
    const d1 = new T.DirectionalLight(0xffffff, 1.6); d1.position.set(-1, -2, 3); scene.add(d1);
    const d2 = new T.DirectionalLight(0xffffff, 0.6); d2.position.set(2, 1, 1); scene.add(d2);
    const box = new T.Box3();
    for (const p of parts) {
      const buf = await (await fetch(p.url)).arrayBuffer();
      const dv = new DataView(buf); const n = dv.getUint32(80, true);
      const pos = new Float32Array(n * 9);
      for (let i = 0; i < n; i++) for (let k = 0; k < 9; k++) pos[i * 9 + k] = dv.getFloat32(84 + i * 50 + 12 + k * 4, true);
      const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(pos, 3));
      g.computeVertexNormals();
      const mat = new T.MeshStandardMaterial({ color: p.c, roughness: 0.45, metalness: 0.05, flatShading: false });
      const mesh = new T.Mesh(g, mat); scene.add(mesh); box.expandByObject(mesh);
    }
    window.__r = { T, renderer, scene, box };
  }, parts);

  const views = {
    vorne_rechts: [1, -1.15, 0.55, 'p'], vorne_links: [1, 1.1, 0.5, 'p'],
    hinten_links: [-1, 1.15, 0.55, 'p'], hinten_rechts: [-1, -1.1, 0.5, 'p'],
    seite: [0, -1, 0, 'o'], seite_links: [0, 1, 0, 'o'], front: [1, 0, 0, 'o'], heck: [-1, 0, 0, 'o'],
    oben: [0.3, -0.5, 1, 'p'], unten: [0.2, -0.3, -1, 'p'], detail_front: [1, -0.55, 0.25, 'p'],
  };
  for (const name of viewsArg.split(',')) {
    const [x, y, z, kind] = views[name];
    await page.evaluate(([x, y, z, kind]) => {
      const { T, renderer, scene, box } = window.__r;
      const c = box.getCenter(new T.Vector3()); const s = box.getSize(new T.Vector3()).length();
      let cam;
      if (kind === 'o') {
        const h = s * 0.36; cam = new T.OrthographicCamera(-h * 4 / 3, h * 4 / 3, h, -h, 0.1, s * 10);
      } else { cam = new T.PerspectiveCamera(kind === 'p' ? 28 : 30, 4 / 3, 0.1, s * 10); }
      const dir = new T.Vector3(x, y, z).normalize();
      const dist = kind === 'o' ? s * 2 : s * 1.55;
      cam.position.copy(c).addScaledVector(dir, dist);
      cam.up.set(0, 0, 1); cam.lookAt(c);
      renderer.render(scene, cam);
    }, [x, y, z, kind]);
    await page.locator('canvas').screenshot({ path: `${outPrefix}_${name}.png` });
    console.log(`${outPrefix}_${name}.png`);
  }
  await browser.close(); server.close();
})();
