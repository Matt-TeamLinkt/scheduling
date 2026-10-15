// End-to-end: the scheduler's main path, in a real browser, against a running API that
// serves the built app.  Usage:  node e2e/flow.mjs [baseUrl] [screenshotDir]
//
// Needs Playwright (preinstalled in the dev sandbox; elsewhere: npx playwright install chromium).
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); } catch { pw = require(path.join(process.env.PLAYWRIGHT_GLOBAL ?? "", "playwright")); }

const base = process.argv[2] ?? "http://localhost:8000";
const shots = process.argv[3] ?? "e2e/screenshots";
mkdirSync(shots, { recursive: true });
const here = path.dirname(new URL(import.meta.url).pathname);

const step = (msg) => console.log(`• ${msg}`);
const fail = (msg) => { console.error(`✗ ${msg}`); process.exit(1); };

const browser = await pw.chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const toast = () => page.locator(".toast").innerText({ timeout: 5000 }).catch(() => "");

try {
  await page.goto(base);
  await page.getByRole("heading", { name: "Your seasons" }).waitFor();
  step("home page loads");

  // 1. Sample league -> schedule tab
  await page.locator(".list-row", { hasText: "40 teams" }).getByRole("button", { name: "Try it" }).click();
  await page.getByRole("button", { name: "Generate schedule" }).waitFor();
  step("created the 40-team sample");

  // 2. Generate (quick)
  await page.getByRole("button", { name: "Generate schedule" }).click();
  await page.getByText("Quick (about 20 seconds)").click();
  await page.getByRole("dialog").getByRole("button", { name: "Generate" }).click();
  await page.getByText("Building your schedule").waitFor();
  step("generation started, progress shown");
  await page.getByText("Building your schedule").waitFor({ state: "detached", timeout: 120000 });
  const scheduled = await page.locator(".board-bar .muted").innerText();
  if (!/^(2[23]\d|240) games scheduled/.test(scheduled)) fail(`too few games: ${scheduled}`);
  step(`generated: ${scheduled}`);
  await page.screenshot({ path: `${shots}/1-board.png` });

  // 3. Drag a game to an open slot (live check, then move)
  const game = page.locator(".game[draggable=true]").first();
  const label = await game.locator(".who").first().innerText();
  const open = page.locator(".slot.empty").first();
  if (await open.count()) {
    const close = page.getByRole("button", { name: "Dismiss" });
    if (await close.isVisible().catch(() => false)) await close.click();
    // Real mouse movement: HTML5 drag needs a few intermediate moves to start.
    const gb = await game.boundingBox();
    const ob = await open.boundingBox();
    await page.mouse.move(gb.x + gb.width / 2, gb.y + 10);
    await page.mouse.down();
    await page.mouse.move(gb.x + gb.width / 2 + 5, gb.y + 15, { steps: 3 });
    await page.mouse.move(ob.x + ob.width / 2, ob.y + ob.height / 2, { steps: 10 });
    await page.screenshot({ path: `${shots}/2-dragging.png` });
    await page.mouse.up();
    const dlg = page.getByRole("dialog", { name: "This move breaks a rule" });
    const moved = page.locator(".toast", { hasText: /^Moved/ });
    await Promise.race([dlg.waitFor(), moved.waitFor()]);
    if (await dlg.isVisible()) {
      step(`move blocked with an explanation: ${(await dlg.locator(".note").first().innerText()).slice(0, 100)}…`);
      await page.screenshot({ path: `${shots}/2-conflict.png` });
      await dlg.getByRole("button", { name: "Cancel" }).click();
    } else {
      step(`dragged ${label}: ${await moved.innerText()}`);
      await page.keyboard.press("Control+z");
      await page.getByText(/^Undid: Moved/).waitFor();
      step("undo with Ctrl+Z works");
    }
  } else step("no open slot on the first day to drag into (skipped)");

  // 5. Lock a game
  await page.getByRole("button", { name: "Lock game" }).first().click();
  await page.getByRole("button", { name: "Unlock game" }).first().waitFor();
  step("locked a game");

  // 6. By team
  await page.getByRole("button", { name: "By team" }).click();
  await page.locator("table.data tbody tr").first().waitFor();
  step(`team view lists ${await page.locator("table.data tbody tr").count()} games for the first team`);

  // 7. Fairness
  await page.getByRole("button", { name: "Fairness" }).click();
  await page.getByRole("heading", { name: "Every team" }).waitFor();
  await page.screenshot({ path: `${shots}/3-fairness.png`, fullPage: true });
  step(`fairness: ${await page.locator(".note").first().innerText()}`);

  // 8. Publish
  await page.getByRole("button", { name: "Publish", exact: true }).click();
  await page.getByRole("button", { name: "Publish the schedule" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Publish" }).click();
  await page.getByText("Families have the latest schedule").waitFor();
  step("published; status shows families have the latest");
  await page.screenshot({ path: `${shots}/4-publish.png` });

  // 9. New season + messy import
  await page.locator(".brand").click();
  await page.getByPlaceholder("e.g. Spring 2027 house league").fill("E2E fall league");
  await page.getByRole("button", { name: "Create season" }).click();
  await page.getByRole("button", { name: "Import teams" }).click();
  await page.locator("input[type=file]").setInputFiles(path.join(here, "../../engine/tests/data/teams_messy.csv"));
  await page.getByText(/We'll add 7 teams/).waitFor();
  await page.screenshot({ path: `${shots}/5-import-preview.png` });
  await page.getByRole("dialog").getByRole("button", { name: "Import" }).click();
  await page.getByRole("dialog").waitFor({ state: "detached" });
  await page.locator(".card", { hasText: "7 teams in 3 divisions" }).waitFor();
  if (!(await page.locator("td", { hasText: /^U11/ }).count())) fail("expected a U11 division row in Rules");
  step("imported a messy teams file with a preview");
  await page.screenshot({ path: `${shots}/6-setup.png`, fullPage: true });

  if (errors.length) fail(`page errors: ${errors.join("; ")}`);
  console.log("✓ end-to-end flow passed");
} catch (e) {
  await page.screenshot({ path: `${shots}/failure.png` }).catch(() => {});
  fail(String(e));
} finally {
  await browser.close();
}
