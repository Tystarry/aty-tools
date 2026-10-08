# -*- coding: utf-8 -*-
import json, os
repo = set(t['path'] for t in json.load(open('D:/zcy/ai_ty/packages/_rt.json', encoding='utf-8')).get('tree', []))
local = []
for root, dirs, files in os.walk('D:/zcy/ai_ty/packages/assets'):
    for f in files:
        p = os.path.join(root, f).replace('D:/zcy/ai_ty/packages/', '').replace(os.sep, '/')
        local.append((p, os.path.getsize(os.path.join(root, f))))
missing = [(p, s) for p, s in local if p not in repo]
print('repo files:', len(repo), 'local:', len(local), 'missing:', len(missing))
for p, s in sorted(missing, key=lambda x: -x[1])[:8]:
    print(f'  {s/1024/1024:7.1f}MB  {p}')
