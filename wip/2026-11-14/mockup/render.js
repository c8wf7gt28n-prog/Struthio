// Render a canonical screen: node render.js <screen.html> <out.png> [scale]   (1920x1200 viewport; scale 2 for the record, 1 to look)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [src, out, scale] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1200 }, deviceScaleFactor: Number(scale || 2) });
  await p.goto('file://' + path.resolve(src));
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(500);
  await p.screenshot({ path: out });
  await b.close();
})();
