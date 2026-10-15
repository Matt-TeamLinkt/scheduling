// Assemble the shareable preview page from a VITE_DEMO=1 build:
//   VITE_DEMO=1 npx vite build --outDir dist-demo && node scripts/build-preview.mjs <data.json> <outDir>
// Output: <outDir>/scheduling-preview.html (CSS and JS inlined, fonts from Google Fonts)
// and <outDir>/demo-data.json (precomputed by the real engine).
import { copyFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const [dataFile, outDir] = process.argv.slice(2);
const assets = "dist-demo/assets";
const files = readdirSync(assets);
const js = readFileSync(path.join(assets, files.find((f) => f.endsWith(".js"))), "utf8");
let css = readFileSync(path.join(assets, files.find((f) => f.endsWith(".css"))), "utf8");
// The brand fonts come from Google Fonts here; drop the bundled font files.
css = css.replace(/@font-face\{[^}]*\}/g, "").replace(/@import url\([^)]*\);?/g, "");

const page = `<title>Scheduling Preview</title>
<meta name="description" content="Try the youth sports scheduler with sample leagues.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..700,0..1,-50..200&display=block">
<style>${css}</style>
<div id="root"></div>
<script type="module">${js.replace(/<\/script/g, "<\\/script")}</script>
`;
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "scheduling-preview.html"), page);
copyFileSync(dataFile, path.join(outDir, "demo-data.json"));
console.log(`page ${(page.length / 1024).toFixed(0)} KB`);
