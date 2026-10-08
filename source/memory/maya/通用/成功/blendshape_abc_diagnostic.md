---
name: bs-diagnostic
description: BS诊断 — Maya ABC 流程 blendShape 对照工具，脚本输出 JSON → 仪表盘生成清单导出 PDF
metadata: 
  node_type: memory
  software: maya
  subtag: 通用
  category: 成功
  packages: BS诊断工具.zip
  originSessionId: 466b2cd9-7b5c-4322-a1b2-8763fe4d65d0
  modified: 2026-08-13T06:48:25.347Z
---

Maya ABC 流程 blendShape 诊断工具 — 对比 mod 模型和 ABC 缓存，输出 JSON → 仪表盘生成清单 → 导出 PDF 反馈给其他环节

🔬 自动诊断 — 输入 mod 组名和 ABC 组名，逐一对比所有 mesh 的配对情况

📏 顶点数校验 — 检测配对 mesh 顶点数是否一致，区分可连接（绿标）和不匹配（红标）并显示差值

🏗️ 结构检查 — 验证 transform freeze 状态、层次结构、父子顺序是否正确

📋 JSON 输出 — 诊断结果粘贴到仪表盘生成清单，导出 PDF 直接发给绑定/模型环节
