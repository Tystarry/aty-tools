---
name: maya-scene-worm
description: 2026-08 用户遭遇 Maya 场景蠕虫（maya_secure_system / C2 远程控制），已诊断清理，工具与流程记录
metadata: 
  node_type: memory
  type: project
  originSessionId: dd445e96-057d-471d-8d9b-19ed66cff9e7
  modified: 2026-08-25T06:54:22.260Z
---

# Maya 场景蠕虫感染事件（2026-08-24 诊断）

**病毒**：伪装 "maya_secure_system" / "SafeMode"，通过场景 scriptNode 传播。打开带毒场景 → 弹假 "Fatal Error" → `quit -f` 强退 Maya（即用户看到的"闪退"）→ 安装载荷到 `Documents\maya\<版本>\scripts\maya_secure_system.py` → 篡改 userSetup.py → 每 5 分钟向 C2 `analytics.stictionholdings.info/api` 心跳（可下发任意代码 RCE），外传机器/用户/场景路径信息。8,273 行控制流平坦化混淆（KEY1=FKEAJHKA KEY2=OKMYSVBYAYNMJRJQ，b85+XOR）。

**已做**（2026-08-24/25）：
- SM_Cut05_S06_lgt_v01.mb 手术修复（b/a 脚本属性清空，字节级验证）
- Maya 2022/2024/2025 环境清理（userSetup.py、maya_secure_system.py、pyc、SafeMode optionVar、日志）
- 全盘扫描：224 个场景中 185 个感染；按用户选择批量修复了 sjmg+jcc（133 个），zcy_01/ai_ty/os_ue_aql/SM_JCC 未修
- 工具留存：ai_ty/clean_mb.js（.mb 双变体清理，补丁式备份 .malware_patch.json + restore_mb.js 可还原）、clean_ma.js、scan_scenes.js；分析产物 payload_decoded.py、payload_clean.py、deobfuscate_payload.py
- 感染源备份：ai_ty/quarantine/

**关键格式知识**（.mb 二进制，两种序列化变体，data 都在记录头 +16）：
- 变体 F：`TAG F` + 02 + 2零 + len8(BE)
- 变体 X：`TAG ` + 类型字节(f8/6f) + 01 + len10右对齐BE
- STR data = 属性名 + 00 + 20 + 值

**未完成**：zcy_01（45）/ os_ue_aql（4）/ ai_ty（3）/ SM_JCC（4）未修；用户拒绝了 hosts 屏蔽 C2 域名的建议。

**重要**：用户自己的反病毒工具叫 fuckVirus（fuckVirus.py，注入 fuckVirus_gene/breed_gene 脚本节点）——任何扫描/清理逻辑必须白名单它，否则会误删用户工具。相关 [[borrowed_pc_portable]]
