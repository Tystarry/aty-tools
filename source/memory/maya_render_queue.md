---
name: maya_render_queue
description: Maya 批量渲染队列管理桌面应用
metadata: 
  node_type: memory
  type: project
  originSessionId: 2ddfa87a-851d-4f5b-8b6c-f37e8028e44a
  modified: 2026-08-12T13:02:25.355Z
---

# Maya Render Queue

独立桌面应用，通过 Maya commandPort (port 7778) 控制已打开的 Maya，批量配置并依次渲染多个场景文件。

## 支持
- Arnold / Redshift 双渲染器
- 帧范围、分辨率、采样参数、输出路径、渲染层开关
- 多文件队列（自动逐一渲染，等前一个完成再开下一个）
- 渲染完成后 postRenderMel 创建标记文件 → App 检测 → 开空场景 → 下一个

## 位置
`d:\zcy\ai_ty\maya_render_queue\`

## 启动
双击 `M_R` 桌面快捷方式，或 `run.bat`

## 使用前
在 Maya 脚本编辑器执行:
## 打包
`d:\zcy\ai_ty\packages\maya_render_queue.zip`
