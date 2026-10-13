# -*- coding: utf-8 -*-
"""删除 GitHub 仓库中的指定文件（如果存在）"""
import json, base64, urllib.request, urllib.parse, sys

TOKEN = 'YOUR_GH_TOKEN_HERE'
REPO = 'Tystarry/aty-tools'

# 旧 zip（改为单文件直传）和旧参考图路径（参考图升级为一级板块后迁移）
PATHS = [
    'assets/HDRI/Glazed_Patio.zip',
    'assets/HDRI/HighwayOverpass.zip',
    'assets/HDRI/carb_01_L.zip',
    'assets/HDRI/kloppenheim_02_puresky_4k.zip',
    'assets/HDRI/the_sky_is_on_fire_4k.zip',
    'assets/HDRI/belfast_sunset_4k.zip',
    'assets/HDRI/Panorama.zip',
    'assets/HDRI/qwantani_dusk_1_puresky_4k.zip',
    'assets/HDRI/studio_small_09_4k.zip',
    'assets/材质球/示例_金属材质.zip',
    'assets/参考图/OIP_C.zip',
    'assets/参考图/OIP_C.png',
    'assets/参考图/main_参考图.zip',
]

for p in PATHS:
    enc = urllib.parse.quote(p, safe='')
    try:
        req = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/contents/{enc}',
            headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        )
        with urllib.request.urlopen(req) as r:
            meta = json.loads(r.read())
        sha = meta.get('sha', '')
        if not sha:
            print(f'NOT FOUND: {p}')
            continue
        req = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/contents/{enc}',
            data=json.dumps({'message': f'Remove {p}', 'sha': sha}).encode('utf-8'),
            method='DELETE',
            headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as r:
            json.loads(r.read())
        print(f'DELETED: {p}')
    except Exception as e:
        print(f'FAIL: {p}: {e}')
