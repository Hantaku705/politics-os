// Vercel build step: assemble the site in dist/ with data pulled straight from the private GCS bucket.
// Nothing is stored on the developer's machine; the Mac only uploads code.
// Auth: env GCS_SA_KEY_B64 = base64 of a service-account JSON key (read-only on the bucket).
// No npm dependencies (Node built-in fetch + crypto).
import { createSign } from 'node:crypto';
import { mkdir, writeFile, copyFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';

const BUCKET = 'politics-os-data-2026';
const PREFIX = 'v1/';
const OUT = 'dist';
const CODE = ['index.html', 'app.js', 'styles.css', 'robots.txt', 'llms.txt', 'catalog.json'];
const DATA = ['members.json', 'meta.json', 'records.json', 'pledges.json', 'japan-map.json', 'speeches.json', 'x_reactions.json', 'pledges_personal.json', 'party_finance.json', 'pledges_progress.json'];
const DIRS = { 'photos/': 500, 'fonts/': 4 }; // prefix -> minimum expected object count (guards against partial builds)

const b64url = (b) => Buffer.from(b).toString('base64').replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');

async function token() {
  const raw = process.env.GCS_SA_KEY_B64;
  if (!raw) throw new Error('GCS_SA_KEY_B64 is not set');
  const key = JSON.parse(Buffer.from(raw, 'base64').toString('utf8'));
  const now = Math.floor(Date.now() / 1000);
  const head = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claim = b64url(JSON.stringify({
    iss: key.client_email, scope: 'https://www.googleapis.com/auth/devstorage.read_only',
    aud: 'https://oauth2.googleapis.com/token', iat: now, exp: now + 3600,
  }));
  const sig = createSign('RSA-SHA256').update(`${head}.${claim}`).sign(key.private_key);
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: `${head}.${claim}.${b64url(sig)}` }),
  });
  if (!res.ok) throw new Error(`token ${res.status} ${await res.text()}`);
  return (await res.json()).access_token;
}

async function list(tok, prefix) {
  const names = [];
  let pageToken = '';
  do {
    const u = new URL(`https://storage.googleapis.com/storage/v1/b/${BUCKET}/o`);
    u.searchParams.set('prefix', prefix);
    u.searchParams.set('fields', 'items(name,size),nextPageToken');
    if (pageToken) u.searchParams.set('pageToken', pageToken);
    const r = await fetch(u, { headers: { authorization: `Bearer ${tok}` } });
    if (!r.ok) throw new Error(`list ${prefix} ${r.status}`);
    const j = await r.json();
    for (const it of j.items || []) if (!it.name.endsWith('/')) names.push(it);
    pageToken = j.nextPageToken || '';
  } while (pageToken);
  return names;
}

async function download(tok, name, dest, expectSize) {
  const u = `https://storage.googleapis.com/storage/v1/b/${BUCKET}/o/${encodeURIComponent(name)}?alt=media`;
  for (let attempt = 1; ; attempt++) {
    try {
      const r = await fetch(u, { headers: { authorization: `Bearer ${tok}` } });
      if (!r.ok) throw new Error(`${r.status}`);
      const buf = Buffer.from(await r.arrayBuffer());
      if (expectSize != null && buf.length !== Number(expectSize)) throw new Error(`size ${buf.length} != ${expectSize}`);
      await mkdir(dirname(dest), { recursive: true });
      await writeFile(dest, buf);
      return buf.length;
    } catch (e) {
      if (attempt >= 4) throw new Error(`download ${name}: ${e.message}`);
      await new Promise((ok) => setTimeout(ok, 1000 * attempt));
    }
  }
}

async function pool(items, n, fn) {
  let i = 0;
  await Promise.all(Array.from({ length: n }, async () => { while (i < items.length) await fn(items[i++]); }));
}

const tok = await token();
await mkdir(OUT, { recursive: true });
for (const f of CODE) await copyFile(f, join(OUT, f));
const jobs = [];
for (const f of DATA) jobs.push({ name: PREFIX + f, dest: join(OUT, 'data', f) });
for (const [dir, min] of Object.entries(DIRS)) {
  const objs = await list(tok, PREFIX + dir);
  if (objs.length < min) throw new Error(`${dir}: only ${objs.length} objects (expected >= ${min})`);
  for (const o of objs) jobs.push({ name: o.name, dest: join(OUT, o.name.slice(PREFIX.length)), size: o.size });
}
let bytes = 0;
await pool(jobs, 16, async (j) => { const n = await download(tok, j.name, j.dest, j.size); bytes += n; });
console.log(`dist ready: ${jobs.length} files from gs://${BUCKET}/${PREFIX} (${(bytes / 1e6).toFixed(1)} MB) + ${CODE.length} code files`);
