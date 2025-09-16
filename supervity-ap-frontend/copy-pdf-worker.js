const fs = require("fs");
const path = require("path");

const pdfjsDistPath = path.dirname(require.resolve("pdfjs-dist/package.json"));
const pdfWorkerPath = path.join(pdfjsDistPath, "build", "pdf.worker.min.mjs");
const publicDir = path.join(__dirname, "public");

if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir);
}

const destPath = path.join(publicDir, "pdf.worker.mjs");

fs.copyFileSync(pdfWorkerPath, destPath);

console.log(
  "Successfully copied pdf.worker.min.mjs to /public/pdf.worker.mjs.",
);
