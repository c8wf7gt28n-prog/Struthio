const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1200 }, deviceScaleFactor: 2 });
  await p.goto('file:///home/user/Struthio/wip/2026-11-14/mockup/perfect_desktop.html');
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(600);
  await p.screenshot({ path: process.argv[2] });
  await b.close();
})();
