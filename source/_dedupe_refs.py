# -*- coding: utf-8 -*-
"""给参考图补内容指纹(hash)，并删除重复上传的图片（同 hash 保留最早的一个）"""
import json, base64, hashlib, time, urllib.parse, urllib.request

TOKEN = 'YOUR_GH_TOKEN_HERE'
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
H = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
REPO = 'https://api.github.com/repos/Tystarry/aty-tools'


def api(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers=dict(H, **({'Content-Type': 'application/json'} if body else {})))
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


# 读索引
idx_meta = api('GET', REPO + '/contents/assets_index.json')
idx = json.loads(base64.b64decode(idx_meta['content']).decode('utf-8'))
refs = [a for a in idx['assets'] if a.get('kind') == 'ref']
print('refs:', len(refs))

# 树：blob sha -> 路径
tree = api('GET', REPO + '/git/trees/main?recursive=1')
blob_sha_by_path = {t['path']: t['sha'] for t in tree.get('tree', []) if t.get('type') == 'blob'}

# 计算每个文件的 sha256
for a in refs:
    p = a.get('thumbnail')
    if not a.get('hash') and p in blob_sha_by_path:
        blob = api('GET', REPO + '/git/blobs/' + blob_sha_by_path[p])
        raw = base64.b64decode(blob.get('content', ''))
        a['hash'] = hashlib.sha256(raw).hexdigest()
        print('hash', p.split('/')[-1], a['hash'][:10], len(raw))

# 去重：同 hash 保留最早的，删除后面的
seen = {}
dups = []
for a in refs:
    h = a.get('hash')
    if not h:
        continue
    if h in seen:
        dups.append(a)
    else:
        seen[h] = a
print('duplicates:', len(dups))

if dups:
    # 用 git 路线删除重复条目对应的文件
    del_paths = []
    for a in dups:
        for p in [a.get('thumbnail')] + (a.get('downloads') or []):
            if p and p not in del_paths:
                del_paths.append(p)
    tree_entries = []
    for p in del_paths:
        tree_entries.append({'path': p, 'mode': '100644', 'type': 'blob', 'sha': None})
    nt = api('POST', REPO + '/git/trees', {'base_tree': tree['sha'], 'tree': tree_entries})
    head = api('GET', REPO + '/git/refs/heads/main')
    commit = api('POST', REPO + '/git/commits', {'message': 'Remove duplicate refs', 'tree': nt['sha'], 'parents': [head['object']['sha']]})
    api('PATCH', REPO + '/git/refs/heads/main', {'sha': commit['sha'], 'force': False})
    # 从索引移除
    dup_names = {(a.get('subcat'), a.get('name')) for a in dups}
    idx['assets'] = [a for a in idx['assets'] if not (a.get('kind') == 'ref' and (a.get('subcat'), a.get('name')) in dup_names)]
    print('files removed:', len(del_paths))

idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
api('PUT', REPO + '/contents/assets_index.json', {
    'message': 'Backfill hashes and dedupe',
    'content': base64.b64encode(json.dumps(idx, ensure_ascii=False).encode('utf-8')).decode('ascii'),
    'sha': api('GET', REPO + '/contents/assets_index.json').get('sha', ''),
})
print('index updated, refs now:', len([a for a in idx['assets'] if a.get('kind') == 'ref']))
