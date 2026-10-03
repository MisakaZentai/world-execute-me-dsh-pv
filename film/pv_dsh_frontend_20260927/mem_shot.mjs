// Screenshot the memory sprites of dsh_patch_mem.py: every [data-sprite] element of mem.html is saved as
// mem_sprites/<name>.png at 2x, on a transparent background (the element's own bbox, dsh's rounded corners kept).
//   python dsh_patch_mem.py page && node mem_shot.mjs
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const require = createRequire(process.env.PV_PACKAGE_JSON || new URL("../../package.json", import.meta.url));
const { chromium } = require("playwright");

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(here, "mem_sprites");
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 354, height: 900 }, deviceScaleFactor: 2 });
await page.goto(pathToFileURL(path.join(here, "mem.html")).href);
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
await page.waitForTimeout(150);
const names = await page.$$eval("[data-sprite]", (els) => els.map((e) => e.dataset.sprite));
for (const name of names) {
  const el = page.locator(`[data-sprite="${name}"]`);
  await el.screenshot({ path: path.join(out, `${name}.png`), omitBackground: true });
  const b = await el.boundingBox();
  console.log(name, Math.round(b.width), "x", Math.round(b.height));
}
await browser.close();
