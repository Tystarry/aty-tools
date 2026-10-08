---
name: borrowed-pc-portable
description: 当前电脑为借用 — 工具箱全便携式，换电脑时一键解绑+新电脑一键部署
metadata: 
  node_type: memory
  type: project
  originSessionId: 1430fe5d-77b7-4709-b36c-2e3916ebc72e
  modified: 2026-07-23T08:59:20.088Z
---

当前电脑是借用的，所有工具集中在 `d:\zcy\ai_ty\` 目录下，可完整迁移。

**换电脑流程：**
1. 把 `d:\zcy\ai_ty\` 整个目录拷贝到 U 盘
2. 运行 `uninstall.bat` 清除本机痕迹（开机自启、userSetup 等）
3. 在新电脑上把目录放到任意位置（推荐 `d:\zcy\ai_ty\`）
4. 运行 `install.bat` 一键部署（开机自启 + Maya userSetup + 启动面板）

**关键文件：**
- [install.bat](d:/zcy/ai_ty/install.bat) — 新电脑部署脚本
- [uninstall.bat](d:/zcy/ai_ty/uninstall.bat) — 本机清除脚本
- [AI_TY_便携工具箱.zip](d:/zcy/ai_ty/AI_TY_便携工具箱.zip) — 完整打包（12 MB，不含场景文件）

**本机安装痕迹（uninstall 会清除）：**
- `%APPDATA%\...\Startup\start_server.vbs` — 开机自启
- `%USERPROFILE%\Documents\maya\2022\scripts\userSetup.py` — Maya 启动（如被修改过）
- `d:\zcy\ai_ty\` 目录本身

**Why:** 用户不是这台电脑的主人，需要能随时带走所有工具，在新电脑上一键恢复。
