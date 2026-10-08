# 记忆索引

## 📋 规则
- [记忆规则](_rules/记忆规则.md) — 记录前确认修改状态、分类标准、打包规范

## 👤 用户偏好
- [中文交流偏好](user_language_preference.md)
- [专业软件与术语注释](user_professional_software.md)
- [借用电脑—便携工具箱](borrowed_pc_portable.md) — 一键解绑 + 新电脑一键部署

## 🦠 安全事件
- [Maya 场景蠕虫感染](maya_scene_worm.md) — 2026-08 诊断清理，工具/流程/C2 信息，fuckVirus 白名单

---

## 🎨 Nuke
### 通用
```
成功/    （空）
暂时没有/  _追踪表.md  →  Cryptomatte matteList 格式转换（需写自动化脚本）
失败/    _追踪表.md  →  Vivid Light 亮光混合模式（没做成）
```

---

## 🔧 Maya
### 通用
```
成功/
  ├── rig_cleaner_tools.md          → .ma 文件清理工具（4个独立Python脚本）
  ├── light_copy_and_rename.md      → 复制灯光组递增命名 + 查找修复重名
  ├── blendshape_abc_diagnostic.md  → blendShape ABC流程诊断（BS不上对照）
  ├── maya_startup_fix.md           → 启动报错一键修复（解锁defaultTextureList1 + colorSpace + filePathEditor）
  └── maya_render_queue.md          → 渲染队列管理器（独立桌面App，commandPort控制Maya批量渲染）
暂时没有/
  （空）
失败/
  （空）
```

### Arnold
```
成功/
  └── aov_duplicate_alias_fix.md    → AOV重复别名修复（3个脚本 + 热修补）
暂时没有/
  （空）
失败/
  └── _追踪表.md                     → Edge Light 边缘光 OSL（没做成）
```

---

## 🎮 UE
```
成功/     （空）
暂时没有/  （空）
失败/     （空）
```

---

## 📦 打包文件

| zip 包 | 内容 | 路径 |
|--------|------|------|
| maya_aov_fix.zip | AOV 重复别名修复 ×3 | [packages/](d:/zcy/ai_ty/packages/maya_aov_fix.zip) |
| maya_rig_cleaner.zip | Rig 文件清理工具 ×4 | [packages/](d:/zcy/ai_ty/packages/maya_rig_cleaner.zip) |
| maya_light_tools.zip | 灯光命名工具 ×2 | [packages/](d:/zcy/ai_ty/packages/maya_light_tools.zip) |
| maya_blendshape_abc_diag.zip | blendShape ABC诊断 ×1 | [packages/](d:/zcy/ai_ty/packages/maya_blendshape_abc_diag.zip) |
| maya_startup_fix.zip | 启动报错一键修复 ×1 | [packages/](d:/zcy/ai_ty/packages/maya_startup_fix.zip) |
| maya_render_queue.zip | Maya 渲染队列管理器 | [packages/](d:/zcy/ai_ty/packages/maya_render_queue.zip) |
