# -*- coding: utf-8 -*-
"""扫描素材库，把超过 GitHub 可上传大小（实测约 35MB，取 30MB 保险）的 exr/hdr
自动压缩为 DWAA:100 并就地替换（原文件保留在 F:/hdr）。「更新素材库」前置步骤。"""
import os, subprocess, time

OIIO = r'C:\Program Files\Autodesk\Arnold\maya2024\bin\oiiotool.exe'
ROOT = r'D:\zcy\ai_ty\素材库'
LIMIT = 30 * 1024 * 1024
EXTS = ('.exr', '.hdr')

done = 0
failed = []
for dirpath, dirs, files in os.walk(ROOT):
    for f in sorted(files):
        ext = os.path.splitext(f)[1].lower()
        if ext not in EXTS or f.startswith('缩略图'):
            continue
        src = os.path.join(dirpath, f)
        size = os.path.getsize(src)
        if size <= LIMIT:
            continue
        tmp = src + '.dwaa_tmp.exr'  # 必须 .exr 结尾，oiiotool 按扩展名识别输出格式
        try:
            r = subprocess.run(
                [OIIO, src, '--ch', 'R,G,B', '--attrib', 'compression', 'dwaa:100', '-o', tmp],
                capture_output=True, timeout=900
            )
            if r.returncode != 0 or not os.path.exists(tmp):
                failed.append((f, r.stderr.decode('utf-8', 'ignore')[-120:]))
                if os.path.exists(tmp):
                    os.remove(tmp)
                continue
            new_size = os.path.getsize(tmp)
            os.remove(src)
            os.rename(tmp, src)
            # 备注写进说明.txt
            note = 'DWAA:100 压缩版（原 %d MB，GitHub 上传上限约 35MB）' % (size / 1024 / 1024)
            desc_file = os.path.join(dirpath, '说明.txt')
            if os.path.exists(desc_file):
                with open(desc_file, 'a', encoding='utf-8') as df:
                    df.write(f'\n备注：{note}\n')
            done += 1
            print(f'OK {f}: {size/1024/1024:.1f}MB -> {new_size/1024/1024:.1f}MB', flush=True)
        except Exception as e:
            failed.append((f, str(e)[:120]))
            if os.path.exists(tmp):
                os.remove(tmp)

print(f'\n{done} compressed, {len(failed)} failed')
for f, err in failed:
    print(f'FAIL {f}: {err}')
