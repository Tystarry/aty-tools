---
name: rig-cleaner-tools
description: Maya .ma 文件清理工具 — 扫描孤儿节点、删除冗余历史、清理 UI 数据提升视口性能
metadata: 
  node_type: memory
  software: maya
  subtag: 通用
  category: 成功
  packages: maya_rig_cleaner.zip
  originSessionId: 466b2cd9-7b5c-4322-a1b2-8763fe4d65d0
  modified: 2026-08-12T14:04:54.375Z
---

4个独立 Python 脚本，清理 Maya .ma 绑定文件中累积的垃圾数据，显著提升文件加载速度和视口 FPS

🔍 扫描孤儿节点 — 全文件扫描，按类型统计 groupId、animCurveUU、network 等无引用节点

🧹 清理冗余 UI 数据 — 移除 nodeGraphEditorInfo、hyperShadePrimary 等编辑历史记录

✂️ 删除遗留构造历史 — polyBridgeEdge、polyExtrudeFace 等不再需要的操作节点

💾 自动备份原文件 — 每次修改前自动创建 .bak 备份，安全可逆

🐍 不依赖 Maya — 纯 Python 处理 .ma 文本文件，命令行直接运行

```bash
# 1. 分析（只读不写）
python scan_orphans.py

# 2. 逐轮清理（自动备份）
python clean_rig_file.py
python clean_round2.py
python fix_hyperShade_refs.py
```
