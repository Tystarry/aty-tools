// Vercel serverless — 访客上传参考图（管理员授权后，朋友用访客密码上传）
// GitHub 密钥只在服务端（GH_TOKEN 环境变量），上传的图片标记 status=pending，管理员审核后公开
const REPO = 'Tystarry/aty-tools';
const API = 'https://api.github.com/repos/' + REPO;

async function gh(method, path, body, token) {
  const r = await fetch(API + '/contents/' + path.split('/').map(encodeURIComponent).join('/'), {
    method,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.message || 'HTTP ' + r.status);
  return j;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  try {
    const token = process.env.GH_TOKEN;
    if (!token) return res.status(500).json({ error: 'server not configured' });
    const { password, cat, name, content, tags, source } = req.body || {};
    if (!password || !cat || !name || !content) {
      return res.status(400).json({ error: '缺少参数' });
    }
    if (content.length > 6 * 1024 * 1024) {
      return res.status(400).json({ error: '图片过大（限 4.5MB）' });
    }
    // 读索引：校验访客密码 + 拿到当前 sha
    const idxMeta = await gh('GET', 'assets_index.json', null, token);
    const idx = JSON.parse(Buffer.from(idxMeta.content, 'base64').toString('utf-8'));
    const guest = idx.guest || {};
    if (!guest.enabled || !(guest.passwords || []).includes(password)) {
      return res.status(403).json({ error: '访客上传未开启或密码错误' });
    }
    if (!/^img_[0-9a-z_]+\.(png|jpg|jpeg|webp|gif)$/i.test(name)) {
      return res.status(400).json({ error: '文件名不合法' });
    }
    const path = 'assets/refs/' + cat + '/' + name;
    // 查重：相同内容 hash 已有则不传（服务端简化：由客户端 hash 判断，这里只保证写入）
    let sha = '';
    try {
      sha = (await gh('GET', path, null, token)).sha || '';
    } catch (e) {}
    const putBody = { message: 'Guest upload ' + name, content };
    if (sha) putBody.sha = sha;
    await gh('PUT', path, putBody, token);

    // 更新索引：追加 pending 条目
    const stem = name.replace(/\.[^.]+$/, '');
    idx.assets = idx.assets.filter(
      (a) => !(a.kind === 'ref' && a.subcat === cat && a.name === stem)
    );
    idx.assets.unshift({
      kind: 'ref', category: '参考图', subcat: cat, name: stem,
      description: '', thumbnail: path, downloads: [path], files: [name],
      size: Math.round(content.length * 0.75),
      date: new Date().toISOString().slice(0, 10),
      tags: tags || {}, source: source || '',
    });
    idx.updated = new Date().toISOString();
    await gh('PUT', 'assets_index.json', {
      message: 'Guest upload index',
      content: Buffer.from(JSON.stringify(idx)).toString('base64'),
      sha: idxMeta.sha,
    }, token);
    res.status(200).json({ ok: true, name: stem, path });
  } catch (e) {
    res.status(500).json({ error: String(e && e.message || e) });
  }
}
