---
name: aov-duplicate-alias-fix
description: "Maya Arnold AOV 重复别名修复 — 解决 \"ai_aov_xxx is not a unique name\" 报错"
metadata: 
  node_type: memory
  software: maya
  subtag: arnold
  category: 成功
  packages: maya_aov_fix.zip
  originSessionId: 466b2cd9-7b5c-4322-a1b2-8763fe4d65d0
  modified: 2026-08-12T14:04:51.081Z
---

Maya + Arnold (MtoA) AOV 重复别名修复 — 解决着色引擎上 "ai_aov_xxx is not a unique name" 报错，恢复 AOV Editor 正常使用

📦 3个脚本覆盖不同场景 — 简易版单别名快速修复 / 完整版全场景扫描 / crypto_asset 专项修复

🔧 MtoA 热修补 — 集成到 userSetup.py 永久生效，无需每次手动运行

🧹 removeMultiInstance 兜底 — 处理原版 aliasAttr(remove=True) 无法解决的重复别名

🖥️ 双模式运行 — Maya Script Editor 一键执行 或 mayapy 命令行批量处理

```python
# 一键修复
exec(open(r'D:\zcy\ai_ty\fix_maya_aov_duplicate_alias.py', encoding='utf-8').read())

# 命令行模式
mayapy.exe fix_maya_aov_duplicate_alias.py scene.ma

# 永久生效（userSetup.py）
import fix_maya_aov_duplicate_alias
fix_maya_aov_duplicate_alias.patch_mtoa()

# crypto_asset 专项
exec(open(r'D:\zcy\ai_ty\fix_aov_crypto_asset.py', encoding='utf-8').read())
```
