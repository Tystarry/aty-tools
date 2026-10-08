# -*- coding: utf-8 -*-
"""为所有 HDRI 素材生成缩略图（Reinhard 色调映射，512x256）"""
import os, subprocess

OIIO = r'C:\Program Files\Autodesk\Arnold\maya2024\bin\oiiotool.exe'
HDRI_ROOT = r'D:\zcy\ai_ty\素材库\HDRI'
IMG_EXTS = ('.exr', '.hdr', '.tif', '.tiff')

done = 0
failed = []

for name in sorted(os.listdir(HDRI_ROOT)):
    d = os.path.join(HDRI_ROOT, name)
    if not os.path.isdir(d):
        continue
    src = None
    for f in os.listdir(d):
        if f.lower().endswith(IMG_EXTS) and not f.startswith('缩略图'):
            src = os.path.join(d, f)
            break
    if not src:
        continue
    out = os.path.join(d, '缩略图.png')
    try:
        # A/(1+A) Reinhard + sRGB 曲线 + gamma
        r = subprocess.run(
            [OIIO, src, '--resize', '512x256', '--ch', 'R,G,B',
             src, '--resize', '512x256', '--ch', 'R,G,B',
             '--create', '512x256', '3', '--addc', '1.0',
             '--add', '--div', '--tocolorspace', 'sRGB', '-o', out],
            capture_output=True, timeout=180
        )
        if r.returncode != 0:
            failed.append((name, r.stderr.decode('utf-8', 'ignore')[-150:]))
            continue
        done += 1
        print(f'OK {name}')
    except Exception as e:
        failed.append((name, str(e)))

print(f'\n{done} thumbnails generated')
for name, err in failed:
    print(f'FAIL {name}: {err}')
