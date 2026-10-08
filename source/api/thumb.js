// Vercel serverless — 素材缩略图代理
// ≤1MB 走 contents API（返回 base64 content，无 CDN 缓存问题）；更大走 raw 回退
const MIME = {
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.gif': 'image/gif',
};
export default async function handler(req, res) {
  const p = String(req.query.p || '');
  if (!p || p.indexOf('/') < 0 || p.indexOf('..') >= 0) {
    res.status(400).end();
    return;
  }
  try {
    const apiUrl = 'https://api.github.com/repos/Tystarry/aty-tools/contents/' +
      p.split('/').map(encodeURIComponent).join('/');
    const r = await fetch(apiUrl, {
      headers: { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
      cache: 'no-store',
    });
    let buf = null;
    if (r.ok) {
      const meta = await r.json();
      if (meta && meta.content && meta.encoding === 'base64' && meta.size <= 1024 * 1024) {
        buf = Buffer.from(meta.content, 'base64');
      }
    }
    if (!buf) {
      const r2 = await fetch(
        'https://raw.githubusercontent.com/Tystarry/aty-tools/main/' +
          p.split('/').map(encodeURIComponent).join('/'),
        { cache: 'no-store' }
      );
      if (!r2.ok) {
        res.status(404).end();
        return;
      }
      buf = Buffer.from(await r2.arrayBuffer());
    }
    const ext = (p.split('.').pop() || '').toLowerCase();
    res.setHeader('Content-Type', MIME['.' + ext] || 'application/octet-stream');
    res.setHeader('Cache-Control', 'public, max-age=86400');
    res.status(200).send(buf);
  } catch (e) {
    res.status(502).end();
  }
}
