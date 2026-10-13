import json, base64, urllib.request, os, urllib.parse, glob, time, sys

# 绕过 Windows 系统代理（本地代理软件关闭时 urllib 全挂，直连 GitHub 可用）
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'

files = [
    ('d:/zcy/ai_ty/packages/index.html', 'index.html'),
    ('d:/zcy/ai_ty/packages/BS诊断工具.html', 'BS诊断工具.html'),
    ('d:/zcy/ai_ty/packages/BS诊断工具.zip', 'BS诊断工具.zip'),
    ('d:/zcy/ai_ty/packages/maya_aov_fix.zip', 'maya_aov_fix.zip'),
    ('d:/zcy/ai_ty/packages/maya_blendshape_abc_diag.zip', 'maya_blendshape_abc_diag.zip'),
    ('d:/zcy/ai_ty/packages/maya_light_tools.zip', 'maya_light_tools.zip'),
    ('d:/zcy/ai_ty/packages/maya_render_queue.zip', 'maya_render_queue.zip'),
    ('d:/zcy/ai_ty/packages/maya_rig_cleaner.zip', 'maya_rig_cleaner.zip'),
    ('d:/zcy/ai_ty/packages/maya_startup_fix.zip', 'maya_startup_fix.zip'),
    ('d:/zcy/ai_ty/packages/assets_index.json', 'assets_index.json'),
    ('d:/zcy/ai_ty/packages/.github/workflows/gen-thumbs.yml', '.github/workflows/gen-thumbs.yml'),
    ('d:/zcy/ai_ty/packages/.github/gen_thumbs.py', '.github/gen_thumbs.py'),
]

# 素材库文件（缩略图和 zip）
for f in glob.glob('d:/zcy/ai_ty/packages/assets/**/*', recursive=True):
    if os.path.isfile(f):
        rel = os.path.relpath(f, 'd:/zcy/ai_ty/packages').replace('\\', '/')
        files.append((f, rel))

def upload(path, remote_name):
    with open(path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('ascii')
    encoded_name = urllib.parse.quote(remote_name, safe='')
    try:
        req = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/contents/{encoded_name}',
            headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            meta = json.loads(r.read())
            sha = meta.get('sha', '')
    except:
        sha = ''
    # 大小相同视为未变化，跳过（避免每次重复上传素材大文件）
    if sha:
        try:
            if int(meta.get('size', -1)) == os.path.getsize(path):
                print(f'SKIP (unchanged): {remote_name}', flush=True)
                return
        except Exception:
            pass
    data = {'message': f'Update {remote_name}', 'content': content}
    if sha:
        data['sha'] = sha
    # 大文件批量上传会触发 GitHub 临时限流(401/409)，加重试+退避；urlopen 加超时防连接挂死
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                f'https://api.github.com/repos/{REPO}/contents/{encoded_name}',
                data=json.dumps(data).encode('utf-8'), method='PUT',
                headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=900) as r:
                json.loads(r.read())
            print(f'OK: {remote_name}', flush=True)
            return
        except Exception as e:
            err = str(e)
            # 409/超时后文件可能实际已上传成功（服务端处理完但响应丢失），核对大小
            if attempt >= 1 and ('409' in err or 'timed out' in err or 'EOF' in err):
                try:
                    req = urllib.request.Request(
                        f'https://api.github.com/repos/{REPO}/contents/{encoded_name}',
                        headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
                    )
                    with urllib.request.urlopen(req, timeout=30) as r:
                        meta = json.loads(r.read())
                    if int(meta.get('size', -1)) == os.path.getsize(path):
                        print(f'OK (already there): {remote_name}', flush=True)
                        return
                except Exception:
                    pass
            if attempt < 3 and ('401' in err or '409' in err or '422' in err or 'EOF' in err or 'timed out' in err or 'No such file' in err):
                # 重新取 sha（文件可能已存在/刚被并发修改），下次尝试用最新 sha
                try:
                    req = urllib.request.Request(
                        f'https://api.github.com/repos/{REPO}/contents/{encoded_name}',
                        headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
                    )
                    with urllib.request.urlopen(req, timeout=30) as r:
                        sha = json.loads(r.read()).get('sha', '')
                    if sha:
                        data['sha'] = sha
                except Exception:
                    pass
                wait = 30 * (attempt + 1) ** 2
                print(f'RETRY({attempt+1}) in {wait}s: {remote_name}: {err}', flush=True)
                time.sleep(wait)
            else:
                print(f'FAIL: {remote_name}: {err}', flush=True)
                return

SMALL_ONLY = '--small-only' in sys.argv
BIG_LIMIT = 20 * 1024 * 1024  # small-only 模式：跳过 >20MB 的文件（大素材以后补传）

for path, name in files:
    if not os.path.exists(path):
        print(f'MISSING: {path}', flush=True)
        continue
    if SMALL_ONLY and os.path.getsize(path) > BIG_LIMIT:
        print(f'SKIP (big): {name}', flush=True)
        continue
    upload(path, name)
    time.sleep(4)  # 大文件间留间隔，降低限流触发概率
