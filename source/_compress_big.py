# -*- coding: utf-8 -*-
"""把 F:/hdr 中超 100MB 的 EXR 自动压缩为 DWAA:100 并导入素材库；
96-97MB 的原样导入。后续「更新素材库」流程也会自动压缩素材库里 >100MB 的文件。"""
import os, shutil, subprocess

OIIO = r'C:\Program Files\Autodesk\Arnold\maya2024\bin\oiiotool.exe'
SRC = 'F:/hdr'
DST = r'D:\zcy\ai_ty\素材库\HDRI'
TODAY = '2026-09-22'
LIMIT = 100 * 1024 * 1024

# 超 100MB：压缩导入
COMPRESS = ['cloudy.exr', 'indoor.exr', 'studio.exr', 'sun_v002.exr']
# 96-97MB：原样导入（在 GitHub 100MB 上限内）
RAW = ['events_hall_interior_4k.exr', 'plains_sunset_4k.exr', 'qwantani_dusk_2_4k.exr']


def write_desc(d, name, files, note=''):
    with open(os.path.join(d, '说明.txt'), 'w', encoding='utf-8') as f:
        f.write(f'HDRI素材「{name}」\n')
        f.write('文件：\n' + '\n'.join(f'  - {x}' for x in files) + '\n')
        if note:
            f.write(f'备注：{note}\n')
        f.write(f'来源: F:/hdr\n导入日期: {TODAY}\n')


for fn in COMPRESS:
    name = os.path.splitext(fn)[0]
    src = os.path.join(SRC, fn)
    if not os.path.exists(src):
        print(f'MISSING {fn}')
        continue
    d = os.path.join(DST, name)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, fn)
    try:
        r = subprocess.run(
            [OIIO, src, '--ch', 'R,G,B', '--attrib', 'compression', 'dwaa:100', '-o', out],
            capture_output=True, timeout=600
        )
        if r.returncode != 0:
            print(f'FAIL {fn}: {r.stderr.decode("utf-8", "ignore")[-150:]}')
            continue
        size = os.path.getsize(out)
        write_desc(d, name, [f'{fn}: {size/1024/1024:.1f} MB'], 'DWAA:100 压缩版（原文件 %d MB 超 GitHub 100MB 上限，保留在 F:/hdr）' % (os.path.getsize(src) / 1024 / 1024))
        print(f'OK {fn}: {os.path.getsize(src)/1024/1024:.1f}MB -> {size/1024/1024:.1f}MB')
    except Exception as e:
        print(f'FAIL {fn}: {e}')

for fn in RAW:
    name = os.path.splitext(fn)[0]
    src = os.path.join(SRC, fn)
    if not os.path.exists(src):
        print(f'MISSING {fn}')
        continue
    d = os.path.join(DST, name)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(src, os.path.join(d, fn))
    write_desc(d, name, [f'{fn}: {os.path.getsize(src)/1024/1024:.1f} MB'])
    print(f'OK(raw) {fn}: {os.path.getsize(src)/1024/1024:.1f}MB')
