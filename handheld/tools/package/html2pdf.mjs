// STRUTHIO · print an HTML file to an A4 PDF with headless Chromium (Playwright).
//   node html2pdf.mjs IN.html OUT.pdf
let pw;
try { pw = await import('playwright'); } catch { pw = await import('/opt/node22/lib/node_modules/playwright/index.mjs'); }
const { chromium } = pw;
import path from 'path';
const [src, dst] = process.argv.slice(2);
const b = await chromium.launch();
const p = await b.newPage();
await p.goto('file://' + path.resolve(src), { waitUntil: 'load' });
await p.pdf({ path: dst, format: 'A4', printBackground: true, preferCSSPageSize: true,
              displayHeaderFooter: true, headerTemplate: '<span></span>',
              footerTemplate: '<div style="font-size:7pt;color:#6b7783;width:100%;text-align:center;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
await b.close();
console.log('wrote', dst);
