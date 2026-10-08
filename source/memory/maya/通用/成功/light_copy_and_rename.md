---
name: light-copy-and-rename
description: Maya 灯光工具 — 复制灯光组自动递增命名、查找修复重复命名灯光
metadata: 
  node_type: memory
  software: maya
  subtag: 通用
  category: 成功
  packages: maya_light_tools.zip
  originSessionId: 466b2cd9-7b5c-4322-a1b2-8763fe4d65d0
  modified: 2026-08-12T14:04:52.929Z
---

Maya 灯光管理工具 — 复制灯光组自动递增命名 + 查找并修复场景中重复的灯光名称

📋 复制灯光组 — 选中灯光组一键复制，所有子灯光自动递增命名，保持原层级结构

🔎 查找重复灯光 — 全场景扫描重名灯光，支持仅检查 / 预览修改 / 直接修复三种模式

💡 广泛兼容 — Maya 原生灯光（spotLight, areaLight 等）+ Arnold（aiAreaLight, aiSkyDomeLight 等）+ Redshift

🚫 安全跳过参考节点 — 自动忽略 reference 中的灯光，避免修改参考文件

```python
# 复制灯光组（自动递增命名）
exec(open(r'D:\zcy\ai_ty\copy_light_group.py', encoding='utf-8').read())

# 查找并修复重复灯光（支持仅检查/预览/修复三种模式）
exec(open(r'D:\zcy\ai_ty\fix_duplicate_light_names.py', encoding='utf-8').read())
```
