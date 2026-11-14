// A tiny static server that acts like the Cloudflare asset rules: auto-trailing-slash (/privacy -> privacy.html),
// 404-page (a missing path gets 404.html with status 404), and the headers in _headers for every path.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const ROOT = path.resolve(process.argv[2] || 'site');
const PORT = +(process.argv[3] || 8787);
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.webp': 'image/webp',
  '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.ico': 'image/x-icon', '.avif': 'image/avif', '.jpg': 'image/jpeg' };
function headersFor(url) {
  const out = {};
  let txt = '';
  try { txt = fs.readFileSync(path.join(ROOT, '_headers'), 'utf8'); } catch { return out; }
  let match = false;
  for (const line of txt.split(/\r?\n/)) {
    if (!line.trim() || line.trim().startsWith('#')) continue;
    if (!/^\s/.test(line)) {
      const pat = line.trim().split('*').map((s) => s.replace(/[.+?^${}()|[\]\\]/g, '\\$&')).join('.*');
      match = new RegExp('^' + pat + '$').test(url);
      continue;
    }
    if (match) { const i = line.indexOf(':'); out[line.slice(0, i).trim()] = line.slice(i + 1).trim(); }
  }
  return out;
}
http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  let file = path.join(ROOT, url);
  let status = 200;
  if (url.endsWith('/')) file = path.join(file, 'index.html');
  else if (!fs.existsSync(file) && fs.existsSync(file + '.html')) file += '.html';
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { file = path.join(ROOT, '404.html'); status = 404; }
  if (!fs.existsSync(file)) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('404'); return; }
  res.writeHead(status, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream', ...headersFor(url) });
  fs.createReadStream(file).on('error', () => res.end()).pipe(res);
}).listen(PORT, () => console.log('serving ' + ROOT + ' on http://localhost:' + PORT));
