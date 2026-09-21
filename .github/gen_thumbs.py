# -*- coding: utf-8 -*-
"""GitHub Actions 内运行：为 assets/ 下没有缩略图的 exr/hdr/tif 生成缩略图并更新索引。
Reinhard 色调映射链：A/(1+A) 后转 sRGB；失败则退回直接 sRGB（高光裁剪）。"""
import json, os, subprocess

ROOT = os.getcwd()
EXTS = ('.exr', '.hdr', '.tif', '.tiff')


def make_thumb(src, out):
    # 主链：Reinhard 色调映射
    r = subprocess.run(
        ['oiiotool', src, '--resize', '512x256', '--ch', 'R,G,B',
         src, '--resize', '512x256', '--ch', 'R,G,B',
         '--create', '512x256', '3', '--addc', '1.0',
         '--add', '--div', '--tocolorspace', 'sRGB', '-o', out],
        capture_output=True, timeout=600
    )
    if r.returncode == 0 and os.path.exists(out):
        return True
    # 回退链：直接 sRGB（可能高光裁剪，但可见）
    r = subprocess.run(
        ['oiiotool', src, '--resize', '512x256', '--ch', 'R,G,B',
         '--tocolorspace', 'sRGB', '-o', out],
        capture_output=True, timeout=600
    )
    return r.returncode == 0 and os.path.exists(out)


generated = []
for dirpath, dirs, files in os.walk(os.path.join(ROOT, 'assets')):
    for f in sorted(files):
        ext = os.path.splitext(f)[1].lower()
        if ext not in EXTS:
            continue
        src = os.path.join(dirpath, f)
        thumb = os.path.join(dirpath, '缩略图.png')
        if os.path.exists(thumb):
            continue
        if make_thumb(src, thumb):
            generated.append(src.replace(os.sep, '/'))
            print('OK', src)
        else:
            print('FAIL', src)

if generated:
    # 更新索引：给对应条目补 thumbnail 路径
    ip = os.path.join(ROOT, 'assets_index.json')
    if os.path.exists(ip):
        with open(ip, encoding='utf-8') as fh:
            idx = json.load(fh)
        for a in idx.get('assets', []):
            if a.get('thumbnail'):
                continue
            for d in (a.get('downloads') or []):
                thumb_rel = '/'.join(d.split('/')[:-1]) + '/缩略图.png'
                if os.path.exists(os.path.join(ROOT, thumb_rel.replace('/', os.sep))):
                    a['thumbnail'] = thumb_rel
                    break
        with open(ip, 'w', encoding='utf-8') as fh:
            json.dump(idx, fh, ensure_ascii=False, indent=2)
        print('index updated')

print('generated', len(generated))
