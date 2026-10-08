// Vercel serverless — 素材索引代理
// 从 GitHub contents API 读（无 CDN 缓存问题），缩略图改写到 /api/thumb 代理
export default async function handler(req, res) {
  try {
    const r = await fetch(
      'https://api.github.com/repos/Tystarry/aty-tools/contents/assets_index.json',
      { headers: { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' }, cache: 'no-store' }
    );
    if (!r.ok) throw new Error('upstream ' + r.status);
    const meta = await r.json();
    const idx = JSON.parse(Buffer.from(meta.content, 'base64').toString('utf-8'));
    (idx.assets || []).forEach((a) => {
      if (a.thumbnail && a.thumbnail.indexOf('assets/') === 0) {
        a.thumbnail = '/api/thumb?p=' + encodeURIComponent(a.thumbnail);
      }
    });
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store');
    res.status(200).json(idx);
  } catch (e) {
    res.status(200).json({ assets: [], error: String(e) });
  }
}
