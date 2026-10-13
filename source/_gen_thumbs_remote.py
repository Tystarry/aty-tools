# -*- coding: utf-8 -*-
"""为网页上传的素材（索引中 thumbnail 为空的 exr/hdr/tif）远程生成缩略图：
下载源文件 -> oiiotool Reinhard 链 -> 上传 缩略图.png -> 更新索引"""
import json, base64, os, subprocess, tempfile, time, urllib.parse, urllib.request

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'
OIIO = r'C:\Program Files\Autodesk\Arnold\maya2024\bin\oiiotool.exe'
HDRS = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
EXTS = ('.exr', '.hdr', '.tif', '.tiff')
TMP = tempfile.gettempdir()


def gh_get(path):
    enc = urllib.parse.quote(path, safe='')
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{enc}', headers=HDRS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def gh_put(path, content_bytes, sha=''):
    enc = urllib.parse.quote(path, safe='')
    data = {'message': 'Auto thumbnail', 'content': base64.b64encode(content_bytes).decode('ascii')}
    if sha:
        data['sha'] = sha
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/{enc}',
                                 data=json.dumps(data).encode('utf-8'), method='PUT',
                                 headers=dict(HDRS, **{'Content-Type': 'application/json'}))
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


with urllib.request.urlopen(
    f'https://raw.githubusercontent.com/{REPO}/main/assets_index.json?t={int(time.time())}', timeout=15
) as r:
    idx = json.loads(r.read())

done = 0
failed = []
for a in idx['assets']:
    if a.get('thumbnail'):
        continue
    dls = a.get('downloads') or []
    if not dls:
        continue
    ext = os.path.splitext(dls[0])[1].lower()
    if ext not in EXTS:
        continue
    name = a.get('name', '?')
    src_path = dls[0]
    thumb_rel = '/'.join(src_path.split('/')[:-1]) + '/缩略图.png'
    src_local = os.path.join(TMP, '_thumbsrc' + ext)
    out_local = os.path.join(TMP, '_thumbout.png')
    try:
        # 下载源文件
        url = f'https://raw.githubusercontent.com/{REPO}/main/' + urllib.parse.quote(src_path, safe='/')
        with urllib.request.urlopen(url, timeout=600) as r, open(src_local, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        # oiiotool Reinhard 链
        r2 = subprocess.run(
            [OIIO, src_local, '--resize', '512x256', '--ch', 'R,G,B',
             src_local, '--resize', '512x256', '--ch', 'R,G,B',
             '--create', '512x256', '3', '--addc', '1.0',
             '--add', '--div', '--tocolorspace', 'sRGB', '-o', out_local],
            capture_output=True, timeout=300
        )
        if r2.returncode != 0:
            raise RuntimeError(r2.stderr.decode('utf-8', 'ignore')[-150:])
        with open(out_local, 'rb') as f:
            png = f.read()
        sha = ''
        try:
            sha = gh_get(thumb_rel).get('sha', '')
        except Exception:
            pass
        gh_put(thumb_rel, png, sha)
        a['thumbnail'] = thumb_rel
        done += 1
        print(f'OK {name}')
    except Exception as e:
        failed.append((name, str(e)[:120]))
    finally:
        for p in (src_local, out_local):
            if os.path.exists(p):
                os.remove(p)

if done:
    idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    sha = ''
    try:
        sha = gh_get('assets_index.json').get('sha', '')
    except Exception:
        pass
    content = json.dumps(idx, ensure_ascii=False).encode('utf-8')
    gh_put('assets_index.json', content, sha)
    print(f'\n{done} thumbnails generated, index updated')
else:
    print('\nno thumbnails needed')
for name, err in failed:
    print(f'FAIL {name}: {err}')
