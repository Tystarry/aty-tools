---
name: maya-startup-fix
description: Maya 启动报错一键修复 — 解锁defaultTextureList1 + colorSpace修复 + filePathEditor清理
metadata: 
  node_type: memory
  software: maya
  subtag: 通用
  category: 成功
  packages: maya_startup_fix.zip
  originSessionId: 466b2cd9-7b5c-4322-a1b2-8763fe4d65d0
  modified: 2026-08-12T14:04:56.085Z
---

Maya 启动报错一键修复 — 4项自动化检测与修复，消除每次启动的控制台报错和警告

🔓 解锁 defaultTextureList1 — 修复 "Connection not made: Destination is locked" 连接错误

🧹 清理 filePathEditor 注册表 — 消除重复文件路径 "have been saved already" 警告

🎨 修复 file 节点 colorSpace — 解决 "Color space 'sRGB' is not defined" 报错

🔍 扫描缺失路径 — 检测 XGen / 贴图丢失路径（仅报告不自动修复，避免误删）

⚡ 灵活调用 — 支持一键全自动修复 或 import 后单独调用特定功能函数

```python
# 一键修复
exec(open(r'D:\zcy\ai_ty\maya_startup_fix.py', encoding='utf-8').read())

# 单独调用特定功能
import maya_startup_fix
maya_startup_fix.unlock_default_texture_list()
maya_startup_fix.fix_file_colorspaces()
```
