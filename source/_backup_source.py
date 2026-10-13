# -*- coding: utf-8 -*-
"""把本地源码脚本 + 记忆文件备份到 GitHub 仓库的 source/ 目录（电脑退役前的保险）"""
import json, base64, os, time, urllib.parse, urllib.request

TOKEN = 'YOUR_GH_TOKEN_HERE'
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
H = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
REPO = 'Tystarry/aty-tools'


def api(method, path, body=None):
    enc = urllib.parse.quote(path, safe='')
    req = urllib.request.Request(
        'https://api.github.com/repos/%s/contents/%s' % (REPO, enc),
        data=json.dumps(body).encode('utf-8') if body else None, method=method,
        headers=dict(H, **({'Content-Type': 'application/json'} if body else {}))
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def upload(local, remote):
    if not os.path.exists(local):
        print('MISSING', local)
        return
    with open(local, 'rb') as f:
        content = base64.b64encode(f.read()).decode('ascii')
    for attempt in range(3):
        sha = ''
        try:
            sha = api('GET', remote).get('sha', '')
        except Exception:
            pass
        body = {'message': 'Backup source', 'content': content}
        if sha:
            body['sha'] = sha
        try:
            api('PUT', remote, body)
            print('OK', remote)
            return
        except urllib.error.HTTPError as e:
            if attempt >= 2 or e.code not in (409, 422):
                print('FAIL', remote, e.code)
                return
            time.sleep(8 * (attempt + 1))


# 1. packages 里的所有 py/js 源码
for f in sorted(os.listdir('D:/zcy/ai_ty/packages')):
    if f.endswith(('.py', '.js', '.json')) and not f.startswith('index'):
        upload('D:/zcy/ai_ty/packages/' + f, 'source/' + f)
# api 目录
for f in sorted(os.listdir('D:/zcy/ai_ty/packages/api')):
    upload('D:/zcy/ai_ty/packages/api/' + f, 'source/api/' + f)
# .github 工作流
upload('D:/zcy/ai_ty/packages/.github/workflows/gen-thumbs.yml', 'source/workflow/gen-thumbs.yml')
upload('D:/zcy/ai_ty/packages/.github/gen_thumbs.py', 'source/workflow/gen_thumbs.py')

# 2. 记忆文件
mem_root = r'C:\Users\D\.claude\projects\d--zcy-ai-ty\memory'
for root, dirs, files in os.walk(mem_root):
    for f in files:
        if f.endswith('.md'):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, mem_root).replace(os.sep, '/')
            upload(p, 'source/memory/' + rel)

print('backup done')
