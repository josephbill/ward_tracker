/**
 * Minimal static file server for the Expo web export (dist/), used only
 * because the Pxxl workspace deploying this project has no distinct
 * "Static Site" mode — every project there is treated as a long-running
 * web service that must bind to $PORT and answer HTTP health checks. A
 * flat dist/ bundle with nothing serving it never binds to anything, so
 * the platform's readiness check fails forever (confirmed the hard way:
 * TCP-checked port stayed "not listening", deploy timed out).
 *
 * Deliberately dependency-free (only Node's built-in http/fs/path) rather
 * than `npx serve` — that downloads a package at container start, which is
 * one more thing that can fail on a cold deploy; this has nothing to fetch.
 *
 * Pxxl start command: `node serve-static.js`
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

const DIST_DIR = path.join(__dirname, "dist");
const PORT = process.env.PORT || 3000;

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".map": "application/json; charset=utf-8",
};

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
  let filePath = path.join(DIST_DIR, urlPath);

  // Never serve outside dist/, regardless of what the request path contains.
  if (!filePath.startsWith(DIST_DIR)) {
    res.writeHead(403, { "Content-Type": "text/plain" });
    res.end("Forbidden");
    return;
  }

  fs.stat(filePath, (statErr, stats) => {
    if (statErr || stats.isDirectory()) {
      // SPA fallback: an unknown path is a client-side route (React
      // Navigation), not a missing file — serve index.html and let the
      // app's own router handle it, same as Expo's dev server already does.
      filePath = path.join(DIST_DIR, "index.html");
    }
    fs.readFile(filePath, (readErr, content) => {
      if (readErr) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end("Not found");
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
      res.end(content);
    });
  });
});

server.listen(PORT, "0.0.0.0", () => {
  // eslint-disable-next-line no-console
  console.log(`Serving mobile-app/dist on 0.0.0.0:${PORT}`);
});
