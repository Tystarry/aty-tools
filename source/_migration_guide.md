# 🧳 换电脑迁移指南（2026-10-08）

## 云端已有的（不依赖任何电脑）

| 内容 | 位置 |
|------|------|
| 网站（日常） | https://tystarry.github.io/aty-tools/ |
| 网站（备份） | https://packages-puce.vercel.app |
| 全部素材文件+缩略图+索引 | GitHub 仓库 Tystarry/aty-tools |
| 网页上传/删除/旋转/标签 | 全浏览器端，任意电脑可用 |
| 访客上传 | Vercel 函数 api/gupload，密钥在 Vercel 环境变量 GH_TOKEN |
| HDRI 自动缩略图 | GitHub Actions（gen-thumbs 工作流） |
| 源码备份 | 仓库 source/ 目录（生成器、部署脚本、记忆文件） |

## 旧电脑上需要拷贝的东西

1. `F:\hdr`（3.4GB HDRI 原始文件——网站上是压缩版）
2. `D:\zcy\ai_ty\素材库`（~380MB 本地素材库，含缩略图和说明）
3. `D:\zcy\ai_ty\packages`（本地工作目录，也可从 GitHub source/ 恢复）
4. `C:\Users\D\.claude\projects\d--zcy-ai-ty`（Claude Code 项目+记忆，也可从 source/memory/ 恢复）

## 新电脑需要的环境

- Maya 2024（mayapy 在 `C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe`）——用于本地重新生成仪表盘；没有 Maya 也可以，一切网页操作不依赖它
- Arnold 的 oiiotool（`C:\Program Files\Autodesk\Arnold\maya2024\bin\oiiotool.exe`）——仅本地生成缩略图用
- GitHub Token：`YOUR_GH_TOKEN_HERE`（生成器/部署脚本里要换；Vercel 环境变量里的不用动）
- Vercel CLI：`npm i -g vercel@56.5.0` 或 npx 使用

## 新电脑重新搭好后的操作流程（见 记忆规则.md 的部署章节）

1. 本地生成：mayapy generate_dashboard.py（--lite 给 GitHub / --vercel 给 Vercel / 无参数本地完整版）
2. 部署 GitHub：mayapy _deploy_gh.py
3. 部署 Vercel：npx vercel@56.5.0 build --prod --yes && npx vercel@56.5.0 deploy --prebuilt --prod --yes
4. 更新素材库前置：mayapy _compress_oversize.py（压缩 >30MB 文件）

## 已知坑（必读）

- 本机 `python` 命令是 WindowsApps 死桩，一律用 mayapy
- 所有 Python 脚本开头要绕过 Windows 系统代理：`urllib.request.install_opener(build_opener(ProxyHandler({})))`
- GitHub 上传实际大小上限 ~33MB（不是 100MB），大文件必须 DWAA 压缩
- GitHub Pages 不服务以 `_` 开头或含 `#()` 等特殊字符的文件名
- 读远程索引必须走 GitHub API（raw 有 CDN 缓存会读到旧版）
- vercel.app 域名在国内可能 DNS 污染，部署验证用 `vercel inspect`，浏览器访问走代理
