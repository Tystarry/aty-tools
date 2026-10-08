# -*- coding: utf-8 -*-
"""对比本地 packages/assets 与 GitHub 仓库文件，列出缺传和孤儿文件"""
import json, os

with open('D:/zcy/ai_ty/packages/_repo_tree.json', encoding='utf-8') as f:
    tree = json.load(f)
repo = set(t['path'] for t in tree.get('tree', []))

local = []
for root, dirs, files in os.walk('D:/zcy/ai_ty/packages/assets'):
    for f in files:
        p = os.path.join(root, f).replace('D:/zcy/ai_ty/packages/', '').replace(os.sep, '/')
        local.append(p)

missing = sorted(p for p in local if p not in repo)
extra = sorted(p for p in repo if p.startswith('assets/') and p not in local)
print(f'local={len(local)}  repo_assets={len([p for p in repo if p.startswith("assets/")])}  missing={len(missing)}  extra={len(extra)}')
print('--- missing (need upload) ---')
for p in missing:
    print('  ', p)
print('--- extra (orphans on repo) ---')
for p in extra:
    print('  ', p)
