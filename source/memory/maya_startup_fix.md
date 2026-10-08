---
name: maya_startup_fix
description: Maya启动一键修复工具 — 解锁defaultTextureList1、清理filePathEditor重复注册、修复colorSpace、扫描缺失路径
metadata: 
  node_type: memory
  type: project
  originSessionId: 1430fe5d-77b7-4709-b36c-2e3916ebc72e
  modified: 2026-07-22T14:49:50.673Z
---

[PC端] `maya_startup_fix.py` — Maya 启动/打开场景后常见报错一键修复工具。

修复4类问题：
1. **defaultTextureList1.textures 锁定** → 4层递进解锁（lockNode → setAttr → MEL → 删除重建）
2. **filePathEditor 重复注册** → 删除 prefs mel 文件 + 清 optionVar
3. **file 节点 colorSpace 无效** → fallback 映射 + 兜底关闭色彩管理
4. **缺失路径扫描** → 汇总 file/aiImage/aiStandIn/aiVolume 的无效路径

**Why:** 用户打开外部 Maya 场景时遇到 `defaultTextureList1` 锁定无法创建 file 节点，OCIO 配置不完整导致大量 colorSpace 警告，filePathEditor 重复注册 Arnold 属性。

**How to apply:** Maya Script Editor Python 标签执行 `exec(open(r'D:\zcy\ai_ty\maya_startup_fix.py', encoding='utf-8').read())`。第一遍通常先解锁节点再用 setAttr，第二次运行即可成功。如需在 userSetup.py 自动运行，import 后调用 `maya_startup_fix.run()`。
