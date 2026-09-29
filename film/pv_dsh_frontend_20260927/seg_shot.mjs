// Screenshot every frame of a frames file (seg_frames.json, a1_frames.json, ...) into dsh_frames/NNNNN.png (354 x 537, the pane interior).
// CSS animations (the reasoning-row sweep) are pinned to song time, so every frame is deterministic.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const require = createRequire(process.env.PV_PACKAGE_JSON || new URL("../../package.json", import.meta.url));
const { chromium } = require("playwright");

const here = path.dirname(fileURLToPath(import.meta.url));
// usage: node seg_shot.mjs [frames.json] [frame numbers...]   (default seg_frames.json, every frame)
const args = process.argv.slice(2);
const file = args[0] && args[0].endsWith(".json") ? args.shift() : "seg_frames.json";
const frames = JSON.parse(fs.readFileSync(path.join(here, file), "utf8"));
const only = args.length ? new Set(args.map(Number)) : null;
fs.mkdirSync(path.join(here, "dsh_frames"), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 354, height: 537 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(here, "seg.html")).href);
await page.evaluate(() => document.fonts.ready);
const SHEETS = ["s-vendor", "s-index", "s-components", "s-palette", "s-bare", "s-code", "s-pv"];
let last = null;
for (const f of frames) {
  if (only && !only.has(f.n)) continue;
  await page.evaluate(({ body, t, sheets, ids }) => {
    for (const id of ids) document.getElementById(id).disabled = !sheets.includes(id);
    const app = document.getElementById("app");
    if (app.dataset.body !== body) {
      app.innerHTML = body;
      app.dataset.body = body;
    }
    for (const a of document.getAnimations()) {
      a.pause();
      const d = a.effect?.getTiming().duration;
      a.currentTime = typeof d === "number" && d > 0 ? (t * 1000) % d : 0;
    }
  }, { ...f, ids: SHEETS });
  if (last === null) await page.waitForTimeout(150);
  await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
  await page.screenshot({ path: path.join(here, "dsh_frames", `${String(f.n).padStart(5, "0")}.png`) });
  if (f.measure) {  // where the last cursor sits in the pane: dsh_her.py takes it from here
    const r = await page.evaluate(() => {
      const b = document.querySelector(".cur").getBoundingClientRect();
      return { x: b.x, y: b.y, w: b.width, h: b.height, n: 0 };
    });
    r.n = f.n;
    fs.writeFileSync(path.join(here, "cursor.json"), JSON.stringify(r));
  }
  last = f.n;
}
await browser.close();
console.log("done", last);
