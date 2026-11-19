// node capture.js <model> <outdir> <nframes> [testFramesCsv]
const { chromium } = require('playwright');
const fs = require('fs');
const [model, outdir, nStr, test] = process.argv.slice(2);
const N = +nStr;
const TOP = { cane: 580, ground: 370 }[model];
const A0 = { cane: -0.9, ground: -1.1 }[model];
const SWEEP = { cane: 1.25 * Math.PI, ground: 2.1 }[model];
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1300 } });
  p.on('console', m => console.log('page:', m.text()));
  p.on('pageerror', e => console.log('err:', e.message));
  await p.goto('http://127.0.0.1:8765/scene.html');
  await p.waitForFunction('window.ready === true', null, { timeout: 30000 });
  await p.evaluate(m => window.setup(m), model);
  fs.mkdirSync(outdir, { recursive: true });
  const frames = test ? test.split(',').map(Number) : [...Array(N).keys()];
  const c = await p.$('canvas');
  for (const i of frames) {
    const t = i / 30;
    const ease = x => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
    const angle = A0 + SWEEP * (i / N) + 0.6 * (1 - ease(t / 1.2)) * -1;
    const scan = t < 0.2 ? 0 : (t < 1.1 ? TOP * ease((t - 0.2) / 0.9) : 99999);
    const wire = t < 1.1 ? 1 : Math.max(0.12, 1 - (t - 1.1) / 0.5);
    await p.evaluate(([a, w, s]) => window.frame(a, 1, w, s), [angle, wire, scan]);
    await c.screenshot({ path: `${outdir}/f_${String(i).padStart(4, '0')}.png`, omitBackground: true });
  }
  await b.close();
})();
