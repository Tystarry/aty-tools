#!/usr/bin/env python3
"""
仪表盘生成器 v3
- 脚本自包含（读取 .py 内容嵌入，复制即可用）
- 卡片简洁展开 → 诊断面板弹窗
- 方法下载按钮可用
"""
import os, re, json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MEMORY_DIR = Path.home() / ".claude" / "projects" / "d--zcy-ai-ty" / "memory"
OUTPUT_HTML = Path(__file__).parent / "插件面板.html"

MORANDI = ['#b8a99a','#9cadb0','#c0a8b0','#a0b0a0','#c0a098','#8ab0a8','#b0a0c0','#b0b098']
REMOTE_DELETED = set()  # 网页删除的素材墓碑 {(subtag, name)}，本地重新生成时不复活
REMOTE_GUEST = {}  # 访客上传配置（enable/密码），重新生成时保留

# 绕过 Windows 系统代理（本地代理软件关闭时 urllib 全挂，直连 GitHub 可用）
import urllib.request as _ur
_ur.install_opener(_ur.build_opener(_ur.ProxyHandler({})))


def _fetch_remote_index():
    """通过 GitHub API 读取远程索引（raw 有 CDN 缓存，会读到旧版本）"""
    import base64, urllib.request
    try:
        req = urllib.request.Request(
            'https://api.github.com/repos/Tystarry/aty-tools/contents/assets_index.json',
            headers={
                'Authorization': 'Bearer YOUR_GH_TOKEN_HERE',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            }
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            meta = json.loads(r.read())
        return json.loads(base64.b64decode(meta['content']).decode('utf-8'))
    except Exception:
        return {}


def parse_simple_yaml(text):
    result = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        m = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if m: result[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return result


def parse_frontmatter(text):
    if not text.startswith('---'): return {}, text
    parts = text.split('---', 2)
    if len(parts) < 3: return {}, text
    try: meta = parse_simple_yaml(parts[1])
    except: meta = {}
    return meta or {}, parts[2].strip()


def read_script(path_str):
    """读取脚本文件内容（限制 30KB，太长的不嵌入）"""
    p = Path(path_str)
    if not p.exists():
        return ''
    try:
        content = p.read_text(encoding='utf-8', errors='replace')
        if len(content) > 30000:
            return content[:30000] + '\n# ... (truncated)'
        return content
    except:
        return ''


def extract_usage(content):
    # 只提取 python/bash 代码块，跳过纯文本块
    return [b.strip() for b in re.findall(r'```(?:python|bash)\n(.*?)```', content, re.DOTALL)]


def extract_files(content):
    result = []
    for name, path in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content):
        if path.startswith('d:') or path.startswith('/'):
            result.append({'name': name, 'path': path})
    return result


def extract_error_patterns(content):
    patterns = []
    for m in re.finditer(r'["\'`]([^"\'\`]*?(?:error|Error|not|Error|cannot|failed|Failed|报错|错误)[^"\'\`]*?)["\'`]', content):
        patterns.append(m.group(1).strip())
    for m in re.finditer(r'报错[：:]\s*(.+?)(?:[。；;.\n]|$)', content):
        patterns.append(m.group(1).strip())
    return list(set(patterns))


def auto_generate_methods(item):
    usage = item.get('usage', [])
    if not usage: return []
    all_text = '\n'.join(usage)
    parts = re.split(r'\n(?=# )', all_text)
    methods = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part: continue
        lines = part.split('\n')
        name = None; pros = []; cons = []; code_lines = []
        for line in lines:
            s = line.strip()
            if s.startswith('#') and not name:
                name = s.lstrip('#').strip().rstrip('：:')
            elif s.startswith('# 优点') or s.startswith('# ✅'):
                pros.append(re.sub(r'^#\s*(优点|✅)\s*[：:]?\s*', '', s))
            elif s.startswith('# 缺点') or s.startswith('# ⚠'):
                cons.append(re.sub(r'^#\s*(缺点|⚠)\s*[：:]?\s*', '', s))
            elif s.startswith('# 适用'):
                pros.append(re.sub(r'^#\s*适用\s*[：:]?\s*', '', s))
            elif s.startswith('# 注意'):
                cons.append(re.sub(r'^#\s*注意\s*[：:]?\s*', '', s))
            elif s:
                code_lines.append(line)
        if not name: name = code_lines[0][:60] if code_lines else f'方法 {i+1}'
        code = '\n'.join(code_lines).strip()
        if not pros:
            if 'exec(open(' in code: pros.append('一条命令，复制即用')
            elif 'mayapy' in code: pros.append('无需打开 Maya UI')
            elif 'userSetup' in code: pros.append('一劳永逸')
            elif 'import ' in code: pros.append('可按需分步调用')
            else: pros.append('直接可用')
        if not cons:
            if 'userSetup' in code: cons.append('需重启 Maya')
            elif 'mayapy' in code: cons.append('需要命令行')
            elif 'exec(' in code: cons.append('需在 Script Editor 中运行')
            else: cons.append('—')
        methods.append({
            'name': name, 'pros': pros, 'cons': cons,
            'color': MORANDI[i % len(MORANDI)],
            'code': code,
        })
    return methods


def collect_items():
    items = []
    for software_dir in sorted(MEMORY_DIR.iterdir()):
        if not software_dir.is_dir() or software_dir.name.startswith('_'): continue
        sw = software_dir.name.capitalize()
        for subtag_dir in sorted(software_dir.iterdir()):
            if not subtag_dir.is_dir(): continue
            st = subtag_dir.name
            for cat_dir in sorted(subtag_dir.iterdir()):
                if not cat_dir.is_dir(): continue
                cat = cat_dir.name
                if cat == '失败': continue
                for md_file in sorted(cat_dir.iterdir()):
                    if md_file.suffix != '.md': continue
                    try: text = md_file.read_text(encoding='utf-8')
                    except: continue
                    meta, body = parse_frontmatter(text)
                    name = meta.get('name', md_file.stem)
                    desc = meta.get('description', '')
                    pkg = meta.get('packages', '')
                    if md_file.name.startswith('_'):
                        for ti in extract_table_items(body):
                            ti['software'] = sw; ti['subtag'] = st
                            ti['category'] = cat; ti['is_tracking'] = True
                            ti['methods'] = []
                            items.append(ti)
                    else:
                        fls = extract_files(body)
                        item = {
                            'software': sw, 'subtag': st, 'category': cat,
                            'name': name, 'description': desc,
                            'usage': extract_usage(body),
                            'files': fls,
                            'package': pkg,
                            'is_tracking': False,
                            'errorPatterns': extract_error_patterns(body),
                            'embeddedScripts': [],
                            'body': body[:2000],
                        }
                        # 读取引用文件的实际内容
                        for f in fls:
                            ext = os.path.splitext(f['name'])[1].lower()
                            if ext in ('.py', '.mel'):
                                content = read_script(f['path'])
                                if content:
                                    item['embeddedScripts'].append({
                                        'name': f['name'],
                                        'content': content,
                                    })
                        item['methods'] = auto_generate_methods(item)
                        items.append(item)
    return items


def extract_table_items(body):
    items, headers, in_table = [], [], False
    for line in body.split('\n'):
        line = line.strip()
        if line.startswith('|') and '---' not in line.replace('-', ''):
            if not in_table:
                headers = [h.strip() for h in line.split('|')[1:-1]]
                in_table = True; continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= len(headers):
                row = {}
                for i, h in enumerate(headers):
                    row[h] = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cells[i] if i < len(cells) else '')
                if all(re.match(r'^[-—]+$', v) for v in row.values() if v): continue
                name = row.get('名称','')
                if not name or re.match(r'^[-—]+$', name): continue
                if name:
                    items.append({'name': row['名称'], 'description': row.get('功能简述', ''), 'tracking_detail': row})
        elif in_table and not line.startswith('|'): in_table = False
    return items


def collect_assets():
    """
    扫描素材库目录，为每个素材文件夹生成 zip 并收集信息。
    素材库结构：
      素材库/{分类}/{素材名}/文件... + 缩略图.* + 说明.txt
    返回: [{"software":"素材","subtag":分类,"category":"素材","name":素材名,
            "description":说明,"thumbnail":相对路径,"download":zip名,"is_asset":True}, ...]
    """
    import shutil, zipfile

    assets_root = PROJECT_ROOT / '素材库'
    assets_out = PROJECT_ROOT / 'packages' / 'assets'
    items = []

    if not assets_root.exists():
        print("  Assets dir not found, skip")
        return items

    # 清空旧 zip
    if assets_out.exists():
        shutil.rmtree(assets_out)
    assets_out.mkdir(parents=True, exist_ok=True)

    for cat_dir in sorted(assets_root.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat = cat_dir.name
        if cat == '参考图':
            continue  # 参考图是独立一级板块，不归素材库管
        cat_out = assets_out / cat
        cat_out.mkdir(exist_ok=True)

        for asset_dir in sorted(cat_dir.iterdir()):
            if not asset_dir.is_dir():
                continue
            name = asset_dir.name

            # 查找缩略图和说明
            thumb = None
            desc = ''
            for f in asset_dir.iterdir():
                fl = f.name.lower()
                if f.name.startswith('缩略图') and f.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                    thumb = f
                elif f.name.startswith('说明') and f.suffix.lower() == '.txt':
                    try:
                        desc = f.read_text(encoding='utf-8').strip()
                    except Exception:
                        desc = ''

            # 素材文件：单文件直接引用原文件，多文件打包 zip
            thumb_name = thumb.name if thumb else ''
            file_names = [f.name for f in asset_dir.iterdir() if f.is_file() and f.name != thumb_name and not f.name.startswith('缩略图') and not (f.name.startswith('说明') and f.suffix.lower() == '.txt')]
            zip_path = None
            if len(file_names) == 1:
                single_dir = cat_out / name
                single_dir.mkdir(exist_ok=True)
                single_out = single_dir / file_names[0]
                src = next(f for f in asset_dir.iterdir() if f.name == file_names[0])
                shutil.copy2(src, single_out)
                dl = f'assets/{cat}/{name}/{file_names[0]}'
                total_size = single_out.stat().st_size
            else:
                zip_name = name + '.zip'
                zip_path = cat_out / zip_name
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for fn in file_names:
                        zf.write(asset_dir / fn, fn)
                dl = f'assets/{cat}/{zip_name}'
                total_size = zip_path.stat().st_size

            # 复制缩略图（放在素材文件夹内，与 GitHub Actions 自动生成路径一致）
            thumb_rel = ''
            if thumb:
                thumb_dir = cat_out / name
                thumb_dir.mkdir(exist_ok=True)
                thumb_out = thumb_dir / ('缩略图' + thumb.suffix.lower())
                shutil.copy2(thumb, thumb_out)
                thumb_rel = f'assets/{cat}/{name}/{thumb_out.name}'

            items.append({
                'software': '素材',
                'subtag': cat,
                'category': '素材',
                'name': name,
                'description': desc,
                'thumbnail': thumb_rel,
                'download': dl,
                'downloads': [dl],
                'files': file_names,
                'size': total_size,
                'date': __import__('datetime').date.today().isoformat(),
                'is_asset': True,
            })

    # 合并线上已有的网页上传素材（避免重新生成时丢失网页上传的条目）
    remote_items = []
    global REMOTE_DELETED, REMOTE_GUEST
    rd = _fetch_remote_index()
    remote_items = rd.get('assets', [])
    REMOTE_DELETED = REMOTE_DELETED | {(t.get('subcat'), t.get('name')) for t in rd.get('deleted', [])}
    REMOTE_GUEST = rd.get('guest') or {}
    # 墓碑（网页删除清单）在独立文件，索引本身保持干净
    try:
        import urllib.request, time
        with urllib.request.urlopen(
            'https://raw.githubusercontent.com/Tystarry/aty-tools/main/deleted_assets.json?t=' + str(int(time.time())), timeout=8
        ) as r:
            REMOTE_DELETED = REMOTE_DELETED | {(t.get('subcat'), t.get('name')) for t in json.loads(r.read()).get('deleted', [])}
    except Exception:
        pass
    local_keys = {(i['subtag'], i['name']) for i in items}
    for ri in remote_items:
        if ri.get('kind') == 'ref' or ri.get('category') == '参考图':
            continue  # 参考图条目由 collect_refs 合并
        if (ri.get('category'), ri.get('name')) not in local_keys:
            items.append({
                'software': '素材',
                'subtag': ri.get('category', '素材'),
                'category': '素材',
                'name': ri.get('name', ''),
                'description': ri.get('description', ''),
                'thumbnail': ri.get('thumbnail', ''),
                'download': (ri.get('downloads') or [''])[0],
                'downloads': ri.get('downloads', []),
                'files': ri.get('files', []),
                'size': ri.get('size', 0),
                'date': ri.get('date', ''),
                'is_asset': True,
            })

    # 网页删除的素材不再从本地复活（墓碑机制）
    items = [i for i in items if (i['subtag'], i['name']) not in REMOTE_DELETED]

    return items


REF_SUBCATS = ['摄影', '油画', 'CG动画', '电影', '插画']


def collect_refs():
    """
    扫描参考图库目录（与素材库平级的一级板块）：
      参考图/{子类:摄影/油画/CG动画/电影/插画}/{分组文件夹}/
        图片文件... + 标签.txt + 说明.txt
    每张图片一个条目（kind=ref），缩略图=图片本身
    标签.txt 格式：每行「组名: 值1, 值2」（组名: 时间/主题/季节/情绪/色调/参考来源）
    """
    import shutil
    refs_root = PROJECT_ROOT / '参考图'
    refs_out = PROJECT_ROOT / 'packages' / 'assets' / 'refs'
    items = []

    if not refs_root.exists():
        print("  Refs dir not found, skip")
        return items

    for subcat in REF_SUBCATS:
        sc_dir = refs_root / subcat
        if not sc_dir.is_dir():
            continue
        for grp_dir in sorted(sc_dir.iterdir()):
            if not grp_dir.is_dir():
                continue
            # 读标签和说明
            tags = {}
            desc = ''
            for tf in grp_dir.iterdir():
                if tf.name.startswith('标签') and tf.suffix.lower() == '.txt':
                    try:
                        for line in tf.read_text(encoding='utf-8').splitlines():
                            if ':' in line or '：' in line:
                                k, v = re.split(r'[:：]', line, 1)
                                k = k.strip()
                                v = v.strip()
                                if k and v:
                                    tags[k] = [x.strip() for x in v.replace('，', ',').split(',') if x.strip()]
                    except Exception:
                        pass
                elif tf.name.startswith('说明') and tf.suffix.lower() == '.txt':
                    try:
                        desc = tf.read_text(encoding='utf-8').strip()
                    except Exception:
                        desc = ''
            for img in sorted(grp_dir.iterdir()):
                if not img.is_file() or img.name.startswith(('标签', '说明')):
                    continue
                if img.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff'):
                    continue
                out_dir = refs_out / subcat
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / img.name
                shutil.copy2(img, out_path)
                rel = f'assets/refs/{subcat}/{img.name}'
                items.append({
                    'software': '参考图',
                    'subtag': subcat,
                    'category': '参考图',
                    'kind': 'ref',
                    'name': img.stem,
                    'description': desc,
                    'thumbnail': rel,
                    'download': rel,
                    'downloads': [rel],
                    'files': [img.name],
                    'size': img.stat().st_size,
                    'date': __import__('datetime').date.today().isoformat(),
                    'tags': {k: v for k, v in tags.items() if k != '参考来源'},
                    'source': ', '.join(tags.get('参考来源', [])),
                    'is_asset': True,
                })

    # 合并线上已有的网页上传参考图
    remote_refs = _fetch_remote_index().get('assets', [])
    local_keys = {(i['subtag'], i['name']) for i in items}
    for ri in remote_refs:
        if ri.get('kind') != 'ref':
            continue
        if (ri.get('subcat'), ri.get('name')) not in local_keys:
            items.append({
                'software': '参考图',
                'subtag': ri.get('subcat', ''),
                'category': '参考图',
                'kind': 'ref',
                'name': ri.get('name', ''),
                'description': ri.get('description', ''),
                'thumbnail': ri.get('thumbnail', ''),
                'download': (ri.get('downloads') or [''])[0],
                'downloads': ri.get('downloads', []),
                'files': ri.get('files', []),
                'size': ri.get('size', 0),
                'date': ri.get('date', ''),
                'tags': ri.get('tags', {}),
                'source': ri.get('source', ''),
                'rot_ts': ri.get('rot_ts', 0),
                'status': ri.get('status', ''),
                'is_asset': True,
            })

    # 网页删除的参考图不再从本地复活（墓碑机制）
    items = [i for i in items if (i['subtag'], i['name']) not in REMOTE_DELETED]

    return items


def main():
    print("Scaning memory/ ...")
    items = collect_items()
    ok = sum(1 for i in items if i.get('category')=='成功')
    wip = sum(1 for i in items if i.get('category')=='暂时没有')
    print(f"  {len(items)} items ({ok} success, {wip} wip)")

    print("Scaning 素材库/ ...")
    assets = collect_assets()
    if assets:
        # Vercel 模式：卡片照常展示，但禁用下载
        if VERCEL_MODE:
            for a in assets:
                a['download'] = ''
                a['download_disabled'] = True
        items = items + assets
        print(f"  {len(assets)} assets added")

    print("Scaning 参考图/ ...")
    refs = collect_refs()
    if refs:
        if VERCEL_MODE:
            for a in refs:
                a['download'] = ''
                a['download_disabled'] = True
        items = items + refs
        print(f"  {len(refs)} refs added")

    # 线上模式：只保留下载文件已在 GitHub 仓库的素材/参考图条目（避免死链）
    if LITE_MODE or VERCEL_MODE:
        try:
            import urllib.request, time
            req = urllib.request.Request(
                'https://api.github.com/repos/Tystarry/aty-tools/git/trees/main?recursive=1&t=' + str(int(time.time())),
                headers={'Authorization': 'Bearer YOUR_GH_TOKEN_HERE',
                         'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                repo_files = {t['path'] for t in json.loads(r.read()).get('tree', [])}

            def _online(i):
                if not i.get('is_asset'):
                    return True
                return all(p in repo_files for p in (i.get('downloads') or []))

            n_assets = len(assets)
            n_refs = len(refs)
            assets = [i for i in assets if _online(i)]
            refs = [i for i in refs if _online(i)]
            items = [i for i in items if not i.get('is_asset')] + assets + refs
            print(f"  Online filter: assets {len(assets)}/{n_assets}, refs {len(refs)}/{n_refs}")
        except Exception as e:
            print(f"  Online filter skipped: {e}")

    # 写出素材+参考图索引 JSON（网页上传/动态加载用）
    idx_entries = []
    for i in assets + refs:
        if i.get('kind') == 'ref':
            idx_entries.append({
                'kind': 'ref',
                'category': '参考图',
                'subcat': i['subtag'],
                'name': i['name'],
                'description': i['description'],
                'thumbnail': i['thumbnail'],
                'downloads': i['downloads'],
                'files': i.get('files', []),
                'size': i.get('size', 0),
                'date': i.get('date', ''),
                'tags': i.get('tags', {}),
                'source': i.get('source', ''),
                'status': i.get('status', ''),
            })
        else:
            idx_entries.append({
                'category': i['subtag'],
                'name': i['name'],
                'description': i['description'],
                'thumbnail': i['thumbnail'],
                'downloads': i['downloads'],
                'files': i.get('files', []),
                'size': i.get('size', 0),
                'date': i.get('date', ''),
            })
    idx = {
        'updated': __import__('datetime').datetime.now().isoformat(),
        'assets': idx_entries,
        'guest': REMOTE_GUEST,  # 访客上传配置（保留线上设置）
    }
    (PROJECT_ROOT / 'packages' / 'assets_index.json').write_text(
        json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    data_json = json.dumps(items, ensure_ascii=False)

    # 构建时获取开发日志（直接嵌入 HTML，不依赖运行时 API）
    try:
        import urllib.request
        req = urllib.request.Request(
            'https://api.github.com/gists/dafd7768b51528d4a5a893eaf30b8dd8',
            headers={
                'Authorization': 'Bearer YOUR_GH_TOKEN_HERE',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            gist_data = json.loads(r.read())
            embed_log = json.loads(gist_data['files']['changelog.json']['content'])
            print(f"  Changelog: {len(embed_log)} entries embedded")
    except Exception as e:
        embed_log = []
        print(f"  Changelog fetch failed: {e}")

    # 构建脚本内容存储
    script_store = {}
    for item in items:
        for s in item.get('embeddedScripts', []):
            key = item['name'] + '|' + s['name']
            script_store[key] = s['content']
        for mi, m in enumerate(item.get('methods', [])):
            if m.get('code'):
                key = item['name'] + '|__method__|' + str(mi)
                script_store[key] = m['code']
    store_json = json.dumps(script_store, ensure_ascii=False)

    embed_log_json = json.dumps(embed_log, ensure_ascii=False)
    # __EMBED_LOG__ 定义在主脚本内、任何函数调用之前
    part2 = HTML_PART2.replace(
        '<script>\nvar DATA=',
        '<script>\nwindow.__EMBED_LOG__=' + embed_log_json + ';\nvar DATA=',
        1,
    )
    # 模式标记：vercel=备份站(动态素材走 /api/assets) / gh=GitHub Pages / local=本地
    MODE = 'vercel' if VERCEL_MODE else ('gh' if LITE_MODE else 'local')
    part2 = part2.replace(
        'var DATA=',
        'window.__MODE__=' + json.dumps(MODE) + ';window.__DL_DISABLED__=' + json.dumps(VERCEL_MODE) +
        ';window.__GUEST__=' + json.dumps(REMOTE_GUEST, ensure_ascii=False) + ';\nvar DATA=',
        1,
    )
    html = HTML_PART1.replace('{VER}', __import__('time').strftime('%m%d.%H%M')) + data_json + part2 + '\n<script>window.__S__=' + store_json + ';</script>\n</body>\n</html>'

    # Lite 模式：去掉留言板，缩小日志栏宽度
    if LITE_MODE:
        import re
        # 移除 msg-panel 侧栏
        html = re.sub(r'<aside class="msg-panel".*?</aside>', '', html, flags=re.DOTALL)
        # 移除留言板 CSS
        html = re.sub(r'/\* 留言板右侧面板 \*/\n.*?@media\(max-width:1100px\)\{\.msg-panel\{display:none\}\}', '', html, flags=re.DOTALL)
        # 移除留言板 JS 函数
        html = re.sub(r'// ── 留言板 ──\n.*?// 开发日志', '// 开发日志', html, flags=re.DOTALL)
        html = re.sub(r'renderMsgs\(\);\n', '', html)
        print("  Lite mode: message board removed")

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Done: {OUTPUT_HTML}")


HTML_PART1 = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI_TY 插件面板</title>
<style>
:root{--bg:#1a1d23;--card:#21252b;--card-hover:#282c34;--border:#333842;--text:#c8ccd4;--dim:#7f848e;--accent:#61afef;--ok:#98c379;--warn:#e5c07b;--code-bg:#1a1d23;--inp:#282c34;--r:10px;--m-card:#252830}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Segoe UI","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.topbar{position:sticky;top:0;z-index:100;background:var(--bg);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.topbar h1{font-size:18px;font-weight:600;white-space:nowrap}
.search-wrap{flex:1;min-width:180px;max-width:380px;position:relative}
.search-wrap input{width:100%;padding:7px 10px 7px 32px;background:var(--inp);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;outline:none}
.search-wrap input:focus{border-color:var(--accent)}
.search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:13px}
.fbtn{padding:5px 12px;border:1px solid var(--border);border-radius:16px;background:transparent;color:var(--dim);cursor:pointer;font-size:12px;transition:all .2s}
.fbtn:hover{border-color:var(--accent);color:var(--text)}
.fbtn.on{background:var(--accent);color:#1a1d23;border-color:var(--accent)}
.main{display:flex}
.side{width:190px;border-right:1px solid var(--border);padding:12px 0;flex-shrink:0;position:sticky;top:52px;height:calc(100vh - 52px);overflow-y:auto}
.side .sec{padding:6px 16px;font-size:11px;color:var(--dim);letter-spacing:1px}
.side a{display:block;padding:6px 16px;color:var(--dim);text-decoration:none;font-size:12px;border-left:2px solid transparent;cursor:pointer}
.side a:hover{color:var(--text);background:var(--card)}
.side a.on{color:var(--accent);border-left-color:var(--accent);background:var(--card)}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:6px}
.dot.ok{background:var(--ok)}.dot.wip{background:var(--warn)}
.content{flex:1;padding:20px;min-width:0}
.bar{margin-bottom:16px}.bar h2{font-size:18px;margin-bottom:2px}.bar .sub{color:var(--dim);font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:14px;cursor:pointer;transition:all .15s;position:relative}
.card:hover{border-color:var(--accent);background:var(--card-hover)}
.card .tag{position:absolute;top:10px;right:10px;font-size:10px;padding:2px 6px;border-radius:10px;font-weight:600}
.tag-ok{color:var(--ok);background:#98c37918;border:1px solid #98c37933}
.tag-wip{color:var(--warn);background:#e5c07b18;border:1px solid #e5c07b33}
.card .sw{font-size:10px;padding:1px 5px;border-radius:3px;background:var(--border);color:var(--dim)}
.card h3{font-size:17px;margin:5px 0;color:var(--accent);font-weight:600;letter-spacing:.3px}
.card .desc{color:var(--dim);font-size:12px;line-height:1.4;margin-bottom:6px}
.card .foot{display:flex;gap:10px;font-size:11px;color:var(--dim);align-items:center}
.card .detail{display:none;margin-top:10px;padding-top:10px;border-top:1px solid var(--border)}
.card.open .detail{display:block}
.pkg-l{display:inline-flex;align-items:center;gap:4px;padding:5px 10px;background:var(--accent);color:#1a1d23;border-radius:6px;text-decoration:none;font-size:11px;font-weight:600;margin-left:auto;transition:opacity .2s;white-space:nowrap}
.pkg-l:hover{opacity:.8}

/* 方法模块 */
.methods-list{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px}
.method-item{background:var(--m-card);border-radius:6px;overflow:hidden;cursor:pointer;transition:all .15s;border:1.5px solid #b8a99a;border-top-width:4px}
.method-item:hover{filter:brightness(1.08)}
.method-item .m-head{display:flex;align-items:flex-start;justify-content:space-between;padding:9px 11px}
.method-item .m-info{flex:1;min-width:0}
.method-item .m-name{font-size:12px;font-weight:500;margin-bottom:4px;line-height:1.35;letter-spacing:.2px}
.method-item .m-tags{display:flex;flex-wrap:wrap;gap:4px}
.method-item .m-tag{padding:1px 7px;border-radius:9px;font-size:10px;white-space:nowrap}
.m-tag.pro{background:#98c37914;color:#8ab87a;border:1px solid #98c37928}
.m-tag.con{background:#e5c07b14;color:#c8a860;border:1px solid #e5c07b28}
.method-item .m-dl{display:inline-flex;align-items:center;gap:2px;padding:2px 6px;background:var(--card);color:var(--dim);border:1px solid var(--border);border-radius:4px;text-decoration:none;font-size:10px;white-space:nowrap;flex-shrink:0;margin-left:6px;transition:all .15s;cursor:pointer}
.method-item .m-dl:hover{background:var(--accent);color:#1a1d23;border-color:var(--accent)}
.method-item .m-body{display:none;padding:0 10px 10px;border-top:1px solid rgba(255,255,255,.04)}
.method-item.open{grid-column:1 / -1}
.method-item.open .m-body{display:block}
.m-arrow{display:inline-block;transition:transform .2s;font-size:10px;margin-left:4px}
.method-item.open .m-arrow{transform:rotate(90deg)}

/* 代码 */
.code-box{background:var(--code-bg);border:1px solid var(--border);border-radius:6px;margin:8px 0;position:relative}
.code-box pre{padding:10px 50px 10px 10px;margin:0;font-family:"Cascadia Code","Fira Code",Consolas,monospace;font-size:12px;line-height:1.4;overflow-x:auto;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow-y:auto}
.cbtn{position:absolute;top:4px;right:4px;background:var(--border);border:none;color:var(--dim);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;transition:all .15s}
.cbtn:hover{background:var(--accent);color:#1a1d23}
.cbtn.done{background:var(--ok);color:#1a1d23}

/* 卡片内按钮 */
.card-actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.card-btn{display:inline-flex;align-items:center;gap:4px;padding:5px 10px;background:var(--border);color:var(--text);border:none;border-radius:6px;cursor:pointer;font-size:11px;transition:all .15s}
.card-btn:hover{background:var(--accent);color:#1a1d23}
.diag-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;background:#61afef18;color:var(--accent);border:1px solid #61afef33;border-radius:8px;cursor:pointer;font-size:12px;font-weight:500;transition:all .2s}
.diag-btn:hover{background:#61afef28;border-color:var(--accent)}
.diag-btn:active{transform:scale(.98)}

/* 弹窗 */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:200;justify-content:center;align-items:center}
.modal-overlay.show{display:flex}
.modal-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;max-width:900px;width:95%;max-height:85vh;overflow-y:auto;position:relative}
.modal-close{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--dim);font-size:20px;cursor:pointer}
.modal-close:hover{color:var(--text)}
.modal-box h2{font-size:18px;margin-bottom:16px}
.modal-cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:768px){.modal-cols{grid-template-columns:1fr}}
.modal-col h3{font-size:13px;margin-bottom:8px;color:var(--dim)}
.modal-col textarea{width:100%;height:300px;background:var(--code-bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;font-family:monospace;padding:10px;resize:vertical}
.modal-col .hint{font-size:11px;color:var(--dim);margin:4px 0 8px}
.modal-col button{padding:6px 14px;border:1px solid var(--border);border-radius:6px;background:var(--border);color:var(--text);cursor:pointer;font-size:12px;margin-top:6px;transition:all .15s}
.modal-col button.gen{background:var(--accent);color:#1a1d23;border-color:var(--accent)}
.modal-col button:hover{opacity:.85}

/* 脚本区 */
.script-section{border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:8px}
.script-section .s-name{font-size:12px;font-weight:600;margin-bottom:4px}
.script-section .s-hint{font-size:10px;color:var(--dim);margin-bottom:6px}
.script-section .s-actions{display:flex;gap:6px}

/* 结果表 */
.diag-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
.diag-table th{background:var(--border);padding:6px 10px;text-align:left;font-weight:600}
.diag-table td{padding:5px 10px;border-bottom:1px solid var(--border)}
.diag-table .ok{color:var(--ok)}.diag-table .bad{color:#e05555}.diag-table .warn{color:var(--warn)}

.flist{list-style:none}.flist li{padding:2px 0;font-size:12px;color:var(--dim)}
.track{margin-top:10px;font-size:12px;color:var(--dim)}.track p{margin:2px 0}
/* 留言板右侧面板 */
.msg-panel{width:260px;border-left:1px solid var(--border);display:flex;flex-direction:column;height:calc(100vh - 52px - 26px);position:sticky;top:52px;background:var(--card);flex-shrink:0}
.msg-header{padding:10px 14px;border-bottom:1px solid var(--border);flex-shrink:0}
.msg-header{display:flex;align-items:center;justify-content:space-between}
.msg-header h3{font-size:13px;font-weight:600}
.msg-header span{font-size:10px;color:var(--dim);font-weight:400}
.admin-btn{background:none;border:1px solid var(--border);color:var(--dim);cursor:pointer;font-size:14px;padding:2px 6px;border-radius:4px;transition:all .15s}
.admin-btn:hover{color:var(--text);border-color:var(--accent)}
.msg-list{flex:1;overflow-y:auto;padding:8px 14px}
.msg-item{padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.msg-item .who{font-size:11px;font-weight:600;color:var(--accent);margin-right:8px}
.msg-item .when{font-size:9px;color:var(--dim)}
.msg-item .what{font-size:11px;color:var(--text);margin-top:2px;line-height:1.4}
.msg-input{padding:8px 14px;border-top:1px solid var(--border);flex-shrink:0;display:flex;flex-direction:column;gap:5px}
.msg-input input,.msg-input textarea{width:100%;padding:5px 8px;background:var(--inp);border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:11px;outline:none;resize:none;font-family:inherit}
.msg-input textarea:focus,.msg-input input:focus{border-color:var(--accent)}
.msg-input button{padding:5px 0;background:var(--accent);color:#1a1d23;border:none;border-radius:5px;cursor:pointer;font-size:11px;font-weight:600;transition:opacity .15s}
.msg-input button:hover{opacity:.85}
@media(max-width:1100px){.msg-panel{display:none}}
.empty{text-align:center;padding:60px 20px;color:var(--dim)}.empty .big{font-size:40px;margin-bottom:12px}
.msg-item{padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px}
.msg-item .who{font-weight:600;color:var(--accent);margin-right:8px}
.msg-item .when{font-size:10px;color:var(--dim);margin-left:8px}
.msg-item .what{color:var(--text);margin-top:2px}
@media(max-width:768px){.side{display:none}.grid{grid-template-columns:1fr}.methods-list{grid-template-columns:1fr}}

/* 参考图 */
.ref-tile{position:relative;border-radius:6px;overflow:hidden;cursor:zoom-in;border:1px solid var(--border);background:var(--code-bg)}
.ref-tile img{display:block;width:100%;height:200px;object-fit:cover}
.ref-hover{position:absolute;left:0;right:0;top:0;bottom:0;background:linear-gradient(rgba(0,0,0,.1),rgba(0,0,0,.85));opacity:0;transition:opacity .15s;display:flex;flex-direction:column;justify-content:flex-end;padding:8px;color:#fff;font-size:10px;pointer-events:none}
.ref-tile:hover .ref-hover{opacity:1}
.rt-del{position:absolute;top:4px;right:4px;background:rgba(0,0,0,.55);border:none;color:#fff;border-radius:4px;padding:2px 6px;font-size:11px;cursor:pointer;opacity:0;transition:opacity .15s;z-index:2}
.ref-tile:hover .rt-del{opacity:1}
.rt-pending{position:absolute;bottom:4px;left:4px;background:rgba(229,192,123,.92);color:#1a1d23;font-size:9px;padding:1px 6px;border-radius:8px;z-index:2}
.rt-tag{display:inline-block;background:rgba(97,175,239,.9);border-radius:8px;padding:1px 6px;margin:1px;font-size:9px;color:#1a1d23;line-height:1.5}
.rt-src{margin-top:3px;font-size:9px;color:#dde;word-break:break-all}
.tag-chip{padding:3px 9px;border:1px solid var(--border);border-radius:12px;background:transparent;color:var(--dim);cursor:pointer;font-size:11px;transition:all .15s;margin:2px}
.tag-chip.on{background:var(--accent);color:#1a1d23;border-color:var(--accent)}
.rs-group .rs-title{font-size:11px;color:var(--dim);margin:8px 0 4px}
.refup-sel{background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px}
.refup-tone{padding:3px 9px;border:1px solid var(--border);border-radius:12px;background:transparent;color:var(--dim);cursor:pointer;font-size:11px;transition:all .15s}
.refup-tone.on{background:var(--warn);color:#1a1d23;border-color:var(--warn)}
</style>
</head>
<body>
<div class="topbar">
<h1>🧩 插件面板 <span style="font-size:11px;color:var(--dim);font-weight:400" title="页面版本，缓存未更新时版本号不变">v{VER}</span></h1>
<div class="search-wrap"><span class="search-icon">🔍</span><input type="text" id="search" placeholder="搜索插件、功能、报错信息..." oninput="render()"></div>
<button class="fbtn on" data-sw="all" onclick="setFilt('all',this)">全部</button>
<button class="fbtn" data-sw="Maya" onclick="setFilt('Maya',this)">Maya</button>
<button class="fbtn" data-sw="Nuke" onclick="setFilt('Nuke',this)">Nuke</button>
<button class="fbtn" data-sw="UE" onclick="setFilt('UE',this)">UE</button>
<button class="fbtn" data-sw="素材" onclick="setFilt('素材',this)">🎨 素材库</button>
<button class="fbtn" data-sw="参考图" onclick="setFilt('参考图',this)">🖼 参考图</button>
<button class="fbtn" style="border-color:#8ab0a8;color:#8ab0a8" onclick="openUpload()" title="上传素材（管理员）">⬆️ 上传素材</button>
</div>
<div class="main">
<nav class="side" id="side"></nav>
<main class="content" id="main"></main>
<aside class="msg-panel" id="msg-panel">
  <div class="msg-header"><h3>💬 留言板 <span id="msg-mode-hint"></span></h3><span><button class="admin-btn" id="admin-btn" onclick="toggleAdmin()" title="管理">🔑</button><button class="admin-btn" onclick="setupAPI()" title="配置共享" style="margin-left:4px">⚙</button></span></div>
  <div class="msg-list" id="msg-list"><p style="color:var(--dim);font-size:12px">加载中...</p></div>
  <div class="msg-input">
    <input id="msg-name" placeholder="名字">
    <textarea id="msg-text" placeholder="写留言..." rows="2" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMsg();}"></textarea>
    <button onclick="sendMsg()">发送</button>
  </div>
</aside>
</div>

<!-- 开发日志底部栏 -->
<div id="log-bar" style="position:fixed;bottom:0;left:0;right:0;z-index:140;background:var(--card);border-top:1px solid var(--border);padding:5px 16px;display:flex;align-items:center;justify-content:space-between;font-size:11px;color:var(--dim)">
  <span>📝 <span id="log-latest">加载中...</span></span>
  <span style="display:flex;gap:8px;align-items:center">
    <span id="log-admin-actions" style="display:none">
      <button onclick="toggleLog()" style="background:var(--border);border:none;color:var(--dim);cursor:pointer;font-size:10px;padding:2px 6px;border-radius:3px">📋 完整日志</button>
      <button onclick="copyFullLog()" style="background:var(--border);border:none;color:var(--dim);cursor:pointer;font-size:10px;padding:2px 6px;border-radius:3px">📤 复制全部</button>
    </span>
  </span>
</div>
<!-- 完整日志弹窗 -->
<div id="log-full" style="display:none;position:fixed;bottom:28px;left:0;right:0;z-index:139;background:var(--card);border-top:1px solid var(--border);max-height:50vh;overflow-y:auto;padding:16px 24px">
  <div id="log-full-list"></div>
</div>

<!-- 弹窗 -->
<div class="modal-overlay" id="modal">
<div class="modal-box">
<button class="modal-close" onclick="closeModal()">✕</button>
<div id="modal-content"></div>
</div>
</div>

<!-- 素材库浏览器（独立界面） -->
<div class="modal-overlay" id="asset-modal" onclick="if(event.target===this)closeAssetBrowser()">
<div class="modal-box" style="max-width:1100px;height:88vh;display:flex;flex-direction:column">
<button class="modal-close" onclick="closeAssetBrowser()">✕</button>
<h2 style="margin-bottom:8px">🎨 素材库</h2>
<div id="ab-tabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px"></div>
<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
  <input id="ab-search" placeholder="搜索素材..." oninput="renderAssetBrowser()" style="flex:1;max-width:260px;padding:6px 10px;background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none">
  <button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="openUpload()">⬆️ 上传素材</button>
</div>
<div id="ab-grid" style="flex:1;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px;align-content:start"></div>
</div>
</div>

<!-- 参考图浏览器 -->
<div class="modal-overlay" id="ref-modal" onclick="if(event.target===this)closeRefBrowser()">
<div class="modal-box" style="max-width:1200px;height:88vh;display:flex;flex-direction:column">
<button class="modal-close" onclick="closeRefBrowser()">✕</button>
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">
  <h2 style="margin:0" id="ref-modal-title">🖼 参考图</h2>
  <button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="openRefUpload(_refCat)">⬆️ 上传</button>
</div>
<div id="ref-grid" style="flex:1;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px;align-content:start"></div>
</div>
</div>

<!-- 参考图查找（标签筛选） -->
<div class="modal-overlay" id="refsearch-modal" onclick="if(event.target===this)closeRefSearch()">
<div class="modal-box" style="max-width:1200px;height:88vh;display:flex;flex-direction:column">
<button class="modal-close" onclick="closeRefSearch()">✕</button>
<h2 style="margin-bottom:8px">🔍 查找参考图</h2>
<div style="display:flex;gap:14px;flex:1;min-height:0">
  <div id="rs-tags" style="width:190px;overflow-y:auto;flex-shrink:0;border-right:1px solid var(--border);padding-right:10px"></div>
  <div id="rs-grid" style="flex:1;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px;align-content:start"></div>
</div>
</div>
</div>

<!-- 参考图查看器（双击弹出） -->
<div class="modal-overlay" id="refview-modal" onclick="if(event.target===this)closeRefViewer()">
<div class="modal-box" style="max-width:900px">
<button class="modal-close" onclick="closeRefViewer()">✕</button>
<div style="display:flex;align-items:center;justify-content:center;max-height:70vh;overflow:auto;background:var(--code-bg);border-radius:8px">
  <img id="refview-img" src="" alt="" style="max-width:100%;max-height:70vh;object-fit:contain">
</div>
<div id="refview-info" style="margin-top:12px;text-align:left;font-size:12px"></div>
<div id="refview-actions" style="margin-top:10px;text-align:left;display:none;align-items:center;gap:10px">
  <button class="card-btn" style="background:#e5c07b;color:#1a1d23" onclick="saveRotate()">💾 保存旋转</button>
  <span id="refview-rot-label" style="font-size:11px;color:var(--dim)"></span>
</div>
</div>
</div>

<!-- 参考图上传弹窗 -->
<div class="modal-overlay" id="refup-modal" onclick="if(event.target===this)closeRefUpload()">
<div class="modal-box" style="max-width:560px">
<button class="modal-close" onclick="closeRefUpload()">✕</button>
<h2>⬆️ 上传参考图 — <span id="refup-title"></span></h2>
<div style="display:grid;grid-template-columns:100px 1fr;gap:8px 12px;font-size:13px;align-items:center">
  <span>图片</span><div>
    <div id="refup-drop" style="border:2px dashed var(--border);border-radius:8px;padding:20px 12px;text-align:center;color:var(--dim);font-size:12px;cursor:pointer;transition:border-color .15s" onclick="document.getElementById('refup-files').click()">📁 拖拽图片到这里，或点击选择（可多张）</div>
    <input id="refup-files" type="file" accept="image/*" multiple style="display:none" onchange="refupShowFiles()">
    <div style="font-size:11px;color:var(--dim);margin-top:4px">色调可多选，其余可单选或不选；每张图片独立成卡；上传完成后可在图片查看器里修改标签</div>
  </div>
  <span>时间</span><select id="refup-time" class="refup-sel"></select>
  <span>主题</span><select id="refup-theme" class="refup-sel"></select>
  <span>季节</span><select id="refup-season" class="refup-sel"></select>
  <span>情绪</span><select id="refup-emotion" class="refup-sel"></select>
  <span>色调</span><div id="refup-tone" style="display:flex;gap:5px;flex-wrap:wrap"></div>
  <span>参考来源</span><input id="refup-source" placeholder="自定义说明，如 ArtStation - xxx" style="background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px">
</div>
<div style="margin-top:12px;display:flex;gap:10px;align-items:center">
  <button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="doRefUpload()">🚀 上传</button>
  <span id="refup-status" style="font-size:12px;color:var(--dim)"></span>
</div>
<div id="refup-log" style="margin-top:10px;max-height:160px;overflow-y:auto;font-size:11px;color:var(--dim);font-family:monospace"></div>
</div>
</div>

<!-- 参考图标签编辑（上传后修改） -->
<div class="modal-overlay" id="refedit-modal" onclick="if(event.target===this)closeRefEdit()">
<div class="modal-box" style="max-width:560px">
<button class="modal-close" onclick="closeRefEdit()">✕</button>
<h2>🏷 编辑标签 — <span id="refedit-title"></span></h2>
<div style="display:grid;grid-template-columns:100px 1fr;gap:8px 12px;font-size:13px;align-items:center">
  <span>时间</span><select id="refedit-time" class="refup-sel"></select>
  <span>主题</span><select id="refedit-theme" class="refup-sel"></select>
  <span>季节</span><select id="refedit-season" class="refup-sel"></select>
  <span>情绪</span><select id="refedit-emotion" class="refup-sel"></select>
  <span>色调</span><div id="refedit-tone" style="display:flex;gap:5px;flex-wrap:wrap"></div>
  <span>参考来源</span><input id="refedit-source" style="background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px">
  <span>说明</span><textarea id="refedit-desc" rows="2" style="background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px;resize:vertical;font-family:inherit"></textarea>
</div>
<div style="margin-top:12px;display:flex;gap:10px;align-items:center">
  <button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="saveRefEdit()">💾 保存</button>
  <span id="refedit-status" style="font-size:12px;color:var(--dim)"></span>
</div>
</div>
</div>

<!-- 访客上传设置（管理员） -->
<div class="modal-overlay" id="guest-modal" onclick="if(event.target===this)closeGuestSettings()">
<div class="modal-box" style="max-width:520px">
<button class="modal-close" onclick="closeGuestSettings()">✕</button>
<h2>⚙ 访客上传设置</h2>
<div style="font-size:12px;color:var(--dim);margin-bottom:10px">生成访客密码（可一人一个），朋友凭密码在网站上传图片，上传后直接公开显示</div>
<label style="font-size:13px;margin-bottom:10px;display:block"><input type="checkbox" id="guest-enabled"> 启用访客上传</label>
<div id="guest-list" style="margin-bottom:10px"></div>
<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
  <input id="guest-newpw" placeholder="新访客密码" style="flex:1;background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px">
  <button class="card-btn" onclick="addGuestPw()">➕ 添加</button>
  <button class="card-btn" onclick="genGuestPw()">🎲 随机生成</button>
</div>
<div style="display:flex;gap:10px;align-items:center">
  <button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="saveGuestSettings()">💾 保存</button>
  <span id="guest-status" style="font-size:12px;color:var(--dim)"></span>
</div>
</div>
</div>

<!-- 素材上传弹窗 -->
<div class="modal-overlay" id="upload-modal" onclick="if(event.target===this)closeUpload()">
<div class="modal-box" style="max-width:560px">
<button class="modal-close" onclick="closeUpload()">✕</button>
<h2>⬆️ 上传素材</h2>
<div style="display:grid;grid-template-columns:100px 1fr;gap:8px 12px;font-size:13px;align-items:center">
  <span>分类</span><select id="up-cat" onchange="upThumbRowToggle()" style="background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px"></select>
  <span>素材名</span><input id="up-name" placeholder="必填，如 金属材质01" style="background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px">
  <span>说明</span><textarea id="up-desc" rows="2" placeholder="卡片上的自定义说明" style="background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:6px;font-size:13px;resize:vertical;font-family:inherit"></textarea>
  <span id="up-thumb-label">缩略图</span><div id="up-thumb-row">
    <div id="upthumb-drop" style="border:2px dashed var(--border);border-radius:8px;padding:10px;text-align:center;color:var(--dim);font-size:12px;cursor:pointer;transition:border-color .15s" onclick="document.getElementById('up-thumb').click()">🖼 拖拽图片到这里 / 点击选择 / Ctrl+V 粘贴</div>
    <input id="up-thumb" type="file" accept="image/*" style="display:none" onchange="upThumbShow()">
  </div>
  <span>素材文件</span><div>
    <div id="upfiles-drop" style="border:2px dashed var(--border);border-radius:8px;padding:10px;text-align:center;color:var(--dim);font-size:12px;cursor:pointer;transition:border-color .15s" onclick="document.getElementById('up-files').click()">📦 拖拽文件到这里，或点击选择（可多选）</div>
    <input id="up-files" type="file" multiple style="display:none" onchange="upFilesShow()">
  </div>
  <span></span><div id="up-hint" style="font-size:11px;color:var(--dim)">可多选文件；单个文件 ≤ 90MB（GitHub 上限 100MB）。超大文件（HDRI 等）建议本地素材库方式</div>
</div>
<div style="margin-top:12px;display:flex;gap:10px;align-items:center">
  <button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="doUpload()">🚀 上传</button>
  <span id="up-status" style="font-size:12px;color:var(--dim)"></span>
</div>
<div id="up-log" style="margin-top:10px;max-height:160px;overflow-y:auto;font-size:11px;color:var(--dim);font-family:monospace"></div>
</div>
</div>

<script type="application/json" id="data-store">
"""

HTML_PART2 = r"""
</script>

<script>
var DATA=JSON.parse(document.getElementById('data-store').textContent.trim());
var fSw='all',fSub=null,modalItem=null;

function setFilt(sw,btn){
    fSw=sw;fSub=null;
    document.querySelectorAll('.fbtn').forEach(function(b){b.classList.remove('on')});
    if(btn)btn.classList.add('on');
    render();
}
function setSub(sw,sub,el){
    fSw=sw;fSub=sub;
    document.querySelectorAll('.fbtn').forEach(function(b){b.classList.remove('on')});
    document.querySelectorAll('.side a').forEach(function(b){b.classList.remove('on')});
    if(el)el.classList.add('on');
    if(sw==='素材'){openAssetBrowser(sub);return;}
    if(sw==='参考图'){openRefBrowser(sub);return;}
    render();
}
function getData(){
    var q=(document.getElementById('search').value||'').toLowerCase();
    return DATA.filter(function(d){
        if(fSw!=='all'&&d.software!==fSw)return false;
        if(fSub&&d.subtag!==fSub)return false;
        if(q){
            var s=(d.name||'')+' '+(d.description||'')+' '+JSON.stringify(d.files||[])+' '+(d.errorPatterns||[]).join(' ');
            if(s.toLowerCase().indexOf(q)===-1)return false;
        }
        return true;
    });
}
function he(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

// 脚本内容从 window.__S 查找，避免 onclick 溢出
function copyById(id,btn){
    var txt=window.__S__[id]||'';
    if(navigator.clipboard){navigator.clipboard.writeText(txt).then(function(){
        var orig=btn.textContent;
        btn.textContent='已复制!';btn.classList.add('done');
        setTimeout(function(){btn.textContent=orig;btn.classList.remove('done');},1500);
    });}
}
function copyPre(btn){
    var pre=btn.parentElement.querySelector('pre');
    var txt=pre?pre.textContent:'';
    if(navigator.clipboard){navigator.clipboard.writeText(txt).then(function(){
        btn.textContent='已复制!';btn.classList.add('done');
        setTimeout(function(){btn.textContent='复制';btn.classList.remove('done');},1500);
    });}
}

function render(){
    var items=getData();
    var grp={};
    var assetN=0,refN=0;
    items.forEach(function(d){
        if(d.is_asset){
            if(d.kind==='ref')refN++;else assetN++;
            if(fSw==='all')return; // 全部视图下素材/参考图走模块入口，不进侧栏分类
        }
        var k=d.software+' / '+d.subtag;
        if(!grp[k])grp[k]={sw:d.software,sub:d.subtag,n:0,ok:false,wip:false};
        grp[k].n++;
        if(d.category==='成功')grp[k].ok=true;
        if(d.category==='暂时没有')grp[k].wip=true;
    });
    var sh='<div class="sec">软件 / 子标签</div>';
    Object.keys(grp).sort().forEach(function(k){
        var g=grp[k],on=(fSw===g.sw&&fSub===g.sub)?' on':'';
        sh+='<a class="side-item'+on+'" data-sw="'+he(g.sw)+'" data-sub="'+he(g.sub)+'" onclick="setSub(this.dataset.sw,this.dataset.sub,this)">';
        sh+='<span class="dot '+(g.ok?'ok':'wip')+'"></span>'+he(k)+' ('+g.n+')</a>';
    });
    if(fSw==='all'){
        sh+='<a class="side-item" style="cursor:pointer" onclick="setFilt(\'素材\',null)"><span class="dot ok"></span>🎨 素材库 ('+assetN+')</a>';
        sh+='<a class="side-item" style="cursor:pointer" onclick="setFilt(\'参考图\',null)"><span class="dot ok"></span>🖼 参考图 ('+refN+')</a>';
    }
    document.getElementById('side').innerHTML=sh;
    if(fSw==='素材'){document.getElementById('main').innerHTML=assetHero();return;}
    if(fSw==='参考图'){document.getElementById('main').innerHTML=refHero();return;}
    if(!items.length){
        document.getElementById('main').innerHTML='<div class="empty"><div class="big">📭</div><h3>没有匹配项</h3><p>试试调整搜索或筛选</p></div>';
        return;
    }
    var dg={};
    items.forEach(function(d){
        if(fSw==='all'&&d.is_asset)return; // 全部视图：素材不散开，由模块区展示
        var k=d.software+' / '+d.subtag;if(!dg[k])dg[k]=[];dg[k].push(d);
    });
    var h='';
    Object.keys(dg).sort().forEach(function(k){
        var its=dg[k];
        h+='<div class="bar"><h2>'+he(k)+'</h2><div class="sub">'+its.length+' 个</div></div><div class="grid">';
        its.forEach(function(d){h+=card(d);});
        h+='</div>';
    });
    if(fSw==='all'){
        h+=assetHero();
        h+=refHero();
    }
    document.getElementById('main').innerHTML=h;
}

function card(d){
    // 素材卡片：缩略图 + 名称 + 说明 + 下载
    if(d.is_asset){
        var ah='<div class="card asset-card" style="cursor:default">';
        if(d.thumbnail)ah+='<div style="height:140px;overflow:hidden;border-radius:6px;margin-bottom:8px;background:var(--code-bg);display:flex;align-items:center;justify-content:center"><img src="'+he(d.thumbnail)+'" alt="" style="max-width:100%;max-height:140px;object-fit:contain" onerror="this.parentElement.innerHTML=\'<span style=&quot;color:var(--dim);font-size:12px&quot;>无缩略图</span>\'"></div>';
        ah+='<span class="tag tag-ok" style="position:static;float:right">素材</span>';
        ah+='<span class="sw">素材</span> <span style="color:var(--dim);font-size:11px">'+he(d.subtag)+'</span>';
        ah+='<h3>'+he(d.name)+'</h3>';
        ah+='<div class="desc">'+he(d.description||'')+'</div>';
        var dls=d.downloads&&d.downloads.length?d.downloads:(d.download?[d.download]:[]);
        if(d.download_disabled||window.__DL_DISABLED__){
            ah+='<div class="foot"><span class="pkg-l" style="margin-left:0;background:var(--border);color:var(--dim);cursor:not-allowed" title="素材下载请访问 GitHub 站">📥 下载不可用</span></div>';
        }else if(dls.length===1){
            ah+='<div class="foot"><a class="pkg-l" style="margin-left:0" href="'+he(dls[0])+'" download>📥 下载</a></div>';
        }else if(dls.length>1){
            var lid='dl_'+Math.random().toString(36).slice(2);
            ah+='<div class="foot"><button class="pkg-l" style="margin-left:0;border:none;cursor:pointer" onclick="event.stopPropagation();var p=document.getElementById(\''+lid+'\');p.style.display=p.style.display===\'none\'?\'\':\'none\'">📥 下载 ('+dls.length+')</button></div>';
            ah+='<div id="'+lid+'" style="display:none;margin-top:6px">';
            dls.forEach(function(u){var fn=decodeURIComponent(u.split('/').pop());ah+='<div style="font-size:11px;padding:2px 0"><a href="'+he(u)+'" download style="color:var(--accent);text-decoration:none">⬇ '+he(fn)+'</a></div>';});
            ah+='</div>';
        }
        if(window._isAdmin){
            ah+='<div class="foot" style="margin-top:8px"><button style="background:none;border:1px solid var(--border);border-radius:4px;color:var(--dim);cursor:pointer;font-size:11px;padding:3px 8px" onclick="event.stopPropagation();delAsset(\''+he(d.name)+'\',\''+he(d.subtag)+'\',event)">🗑 删除素材</button></div>';
        }
        ah+='</div>';
        return ah;
    }
    var ok=d.category==='成功',cl=ok?'tag-ok':'tag-wip',tx=ok?'成功':'开发中';
    var fl=d.files||[],methods=d.methods||[],scripts=d.embeddedScripts||[];

    // 方法模块
    var mh='';
    if(methods.length>0){
        mh='<div class="methods-list">';
        methods.forEach(function(m,i){
            var pros='',cons='';
            if(m.pros&&m.pros.length)pros=m.pros.map(function(p){return'<span class="m-tag pro">👍 '+he(p)+'</span>';}).join('');
            if(m.cons&&m.cons.length)cons=m.cons.map(function(c){return'<span class="m-tag con">⚠ '+he(c)+'</span>';}).join('');
            var code=m.code||'';
            mh+='<div class="method-item" style="border-color:'+he(m.color||'#b8a99a')+'" onclick="event.stopPropagation();this.classList.toggle(\'open\')">'+
                '<div class="m-head">'+
                    '<div class="m-info">'+
                        '<div class="m-name">'+he(m.name)+' <span class="m-arrow">▶</span></div>'+
                        '<div class="m-tags">'+pros+cons+'</div>'+
                    '</div>'+
                    (code?'<button class="m-dl" onclick="event.stopPropagation();copyById(\''+he(d.name)+'|__method__|'+i+'\',this);return false" title="复制此方法脚本">📋</button>':'')+
                '</div>'+
                (code?'<div class="m-body"><div class="code-box"><button class="cbtn" onclick="event.stopPropagation();copyPre(this)">复制</button><pre>'+he(code)+'</pre></div></div>':'')+
            '</div>';
        });
        mh+='</div>';
    }

    var desc=d.description||'';
    if(!desc&&d.is_tracking&&d.tracking_detail)desc=d.tracking_detail['功能简述']||'';

    // 追踪信息
    var th='';
    if(d.is_tracking&&d.tracking_detail){
        var td=d.tracking_detail;
        th='<div class="track">';
        if(td['当前进度'])th+='<p>📌 '+he(td['当前进度'])+'</p>';
        if(td['待完善'])th+='<p>🔧 '+he(td['待完善'])+'</p>';
        th+='</div>';
    }

    var ph='';
    if(d.package)ph='<a class="pkg-l" href="./'+he(d.package)+'" onclick="event.stopPropagation()">📦 下载</a>';

    // 操作按钮 — 仅 blendShape 模块显示
    var isBS=(d.name.indexOf('blendshape')!==-1||d.name.indexOf('abc')!==-1||d.name.indexOf('bs-')!==-1||d.name.indexOf('BS')!==-1);
    var actions='';
    if(isBS){
        actions='<div class="card-actions"><button class="diag-btn" onclick="event.stopPropagation();openModal(\''+he(d.name)+'\')">📋 复制脚本 + 诊断面板</button></div>';
    }

        var body=d.body||'';
        var bh='';
    if(body){
        var clean=body.replace(/```[\s\S]*?```/g,'');
        var lines=clean.replace(/\r/g,'').split('\n').filter(Boolean);
        lines.forEach(function(l){bh+='<div style=font-size:12px;color:var(--dim);margin:3px0>'+he(l)+'</div>';});
        if(bh)bh='<div class=card-body style=margin-bottom:10px>'+bh+'</div>';
    }
    return'<div class="card" onclick="this.classList.toggle(\'open\')">'+
        '<span class="tag '+cl+'">'+tx+'</span>'+
        '<span class="sw">'+he(d.software.toUpperCase())+'</span> '+
        '<span style="color:var(--dim);font-size:11px">'+he(d.subtag)+'</span>'+
        '<h3>'+he(d.name)+'</h3>'+
        '<div class="desc">'+he(desc)+'</div>'+
        '<div class="foot">'+(d.package?'<span>📦 已打包</span>':'')+ph+'</div>'+
        '<div class="detail">'+bh+mh+th+actions+'</div>'+
        '</div>';
}

// ── 弹窗 ──
function openModal(name){
    var items=DATA.filter(function(d){return d.name===name;});
    if(!items.length)return;
    var d=items[0];
    modalItem=d;
    var isBS=(d.name.indexOf('blendshape')!==-1||d.name.indexOf('abc')!==-1||d.name.indexOf('bs-')!==-1||d.name.indexOf('BS')!==-1);

    var left='';
    if(isBS){
        // blendShape 专用：输入框 + 脚本模板
        left='<h3>📋 Maya 诊断脚本</h3>'+
            '<div class="script-section">'+
                '<p class="hint">填写组名后点复制，粘贴到 Maya Script Editor (Python) 运行</p>'+
                '<label style="font-size:12px;display:block;margin:8px 0 2px">Mod 组名</label>'+
                '<input id="bs-mod" style="width:100%;padding:6px 8px;background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px" placeholder="例如 Ahri_mod3">'+
                '<label style="font-size:12px;display:block;margin:8px 0 2px">ABC 组名</label>'+
                '<input id="bs-abc" style="width:100%;padding:6px 8px;background:var(--inp);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px" placeholder="例如 CHR_Ahri">'+
                '<button style="margin-top:12px" onclick="copyBSScript()">📋 复制脚本到剪贴板</button>'+
            '</div>';
    }else{
        // 通用：嵌入脚本 + 方法
        var scripts=d.embeddedScripts||[];
        if(scripts.length>0){
            left='<h3>📋 Maya 脚本（自包含，复制到任何电脑都能用）</h3>';
            scripts.forEach(function(s){
                left+='<div class="script-section">'+
                    '<div class="s-name">'+he(s.name)+'</div>'+
                    '<div class="s-hint">全选复制 → 粘贴到 Maya Script Editor (Python) 运行</div>'+
                    '<button onclick="copyById(\''+he(d.name)+'|'+he(s.name)+'\',this)">📋 复制完整脚本 ('+Math.round(s.content.length/1000)+'KB)</button>'+
                '</div>';
            });
        }
        var methods=d.methods||[];
        if(methods.length>0&&methods[0].code){
            left+='<h3 style="margin-top:16px">📋 各方式脚本</h3>';
            methods.forEach(function(m,mi){
                if(!m.code)return;
                left+='<div class="script-section">'+
                    '<div class="s-name">'+he(m.name)+'</div>'+
                    '<div class="s-hint">'+he((m.pros||[]).join(' / '))+'</div>'+
                    '<button onclick="copyById(\''+he(d.name)+'|__method__|'+mi+'\',this)">📋 复制</button>'+
                '</div>';
            });
        }
    }

    var right='<h3>📊 诊断数据粘贴区</h3>'+
        '<p class="hint">将 Maya 诊断脚本运行后输出的 JSON 粘贴到下方，点击「生成清单」得到对照表。</p>'+
        '<textarea id="diag-json" placeholder=\'粘贴 JSON，例如：&#10;{"mod_group":"Ahri_mod3","abc_group":"CHR_Ahri","summary":{"ok":72,...},"pairs":[...]}\'></textarea>'+
        '<button class="gen" onclick="genDiag()">📊 生成清单</button>'+
        '<button onclick="document.getElementById(\'diag-json\').value=\'\';document.getElementById(\'diag-result\').innerHTML=\'\'">清空</button>'+
        '<div id="diag-result"></div>';

    document.getElementById('modal-content').innerHTML='<h2>'+he(d.name)+'</h2>'+
        '<div class="modal-cols"><div class="modal-col">'+left+'</div><div class="modal-col">'+right+'</div></div>';
    document.getElementById('modal').classList.add('show');
}
function closeModal(){
    document.getElementById('modal').classList.remove('show');
    modalItem=null;
}
function genDiag(){
    var resultDiv=document.getElementById('diag-result');
    try{
        var data=JSON.parse(document.getElementById('diag-json').value.trim());
        var s=data.summary;
        var h='<div style="margin-top:4px;font-size:11px;color:var(--dim)">'+
            '<b>mod:</b> '+he(data.mod_group||'?')+'  |  <b>ABC:</b> '+he(data.abc_group||'?')+'  |  '+he(data.time||'')+'</div>';
        h+='<div style="margin:6px 0;font-size:12px;display:flex;gap:14px;flex-wrap:wrap">'+
            '<span>✅ <b>'+s.ok+'</b> 可连</span>'+
            '<span style="color:#e05555">❌ <b>'+s.mismatch+'</b> 顶点不符</span>'+
            '<span style="color:#e05555">🧊 <b>'+(s.not_frozen||0)+'</b> 未冻结</span>'+
            '<span style="color:#e05555">🏗 <b>'+(s.hierarchy_mismatch||0)+'</b> 层级不符</span>'+
            '<span style="color:#e05555">🔀 <b>'+(s.order_mismatch||0)+'</b> 顺序不符</span>'+
            '<span style="color:#e05555">🔷 <b>'+(s.shape_mismatch||0)+'</b> shape名不符</span>'+
            '<span style="color:var(--warn)">⚠ <b>'+s.mod_only+'</b> mod独有</span>'+
            '<span style="color:var(--warn)">⚠ <b>'+s.abc_only+'</b> ABC独有</span></div>';
        if(data.ordered_pairs&&data.ordered_pairs.length){
            var MC=['#b8a99a','#9cadb0','#c0a8b0','#a0b0a0','#c0a098','#8ab0a8','#b0a0c0','#b0b098'];
            h+='<table id="diag-table" class="diag-table" style="font-size:12px"><thead><tr style="background:var(--border)"><th style="padding:6px 10px;text-align:left">mod 层级顺序</th><th style="padding:6px 10px;text-align:left">abc 层级顺序</th><th style="padding:6px 10px;text-align:right">mod顶点</th><th style="padding:6px 10px;text-align:right">ABC顶点</th><th style="padding:6px 10px;text-align:left">状态</th><th style="padding:6px 10px;text-align:left">冻结</th></tr></thead><tbody>';
            data.ordered_pairs.forEach(function(op){
                var same=op.same!==false;
                var rowStyle=!same?'background:#e0555518':'';
                var d1=op.mod?(data.mesh_data&&data.mesh_data[op.mod]):null;
                var d2=op.abc?(data.mesh_data&&data.mesh_data[op.abc]):null;
                var mv=d1?d1.mod_vtx:'';var av=d2?d2.abc_vtx:'';
                var st=d1?(d1.status==='ok'?'✅':(d1.status==='mismatch'?'❌ 顶点不符':'⚠')):'';
                var unf=d1&&d1.unfrozen_nodes?d1.unfrozen_nodes:[];
                var frozen=unf.length===0;
                var ft=frozen?'✅':'❌ '+unf.join(' ');
                var dep=(op.depth||0);
                var col=MC[(dep-1)%MC.length];
                var indent='&nbsp;&nbsp;'.repeat(dep-1);
                if(op.is_group){
                    var gmod=op.mod?'📁 '+he(op.mod):'<span style="color:var(--dim)">—</span>';
                    var gabc=op.abc?'📁 '+he(op.abc):'<span style="color:var(--dim)">—</span>';
                    var gtag=op.mod_only_row?'<span style="color:#e05555;font-size:10px">(mod独有)</span>':(op.abc_only_row?'<span style="color:#e05555;font-size:10px">(abc独有)</span>':(op.name_mismatch?'<span style="color:#e05555;font-size:10px">(命名不同)</span>':''));
                    h+='<tr style="'+rowStyle+'"><td style="padding:4px 10px;border-left:4px solid '+col+';color:'+col+';font-weight:600">'+indent+gmod+gtag+'</td><td style="padding:4px 10px;border-left:4px solid '+col+';color:'+col+';font-weight:600">'+indent+gabc+'</td><td colspan="4"></td></tr>';
                } else {
                    var modCell=op.mod?he(op.mod):(op.abc_only_row?'<span style="color:var(--dim)">—</span>':'');
                    var abcCell=op.abc?he(op.abc):(op.mod_only_row?'<span style="color:var(--dim)">—</span>':'');
                    var tag=op.mod_only_row?'<span style="color:#e05555;font-size:10px">(mod独有)</span>':(op.abc_only_row?'<span style="color:#e05555;font-size:10px">(abc独有)</span>':(op.name_mismatch?'<span style="color:#e05555;font-size:10px">(命名不同)</span>':''));
                    var shm=d1?d1.shape_match:true;
                    var shTag=!shm?'<span style="color:#e05555;font-size:10px">(shape名: '+he(d1.mod_shape||'')+' vs '+he(d1.abc_shape||'')+')</span>':'';
                    h+='<tr style="'+rowStyle+'"><td style="padding:5px 10px;border-left:3px solid '+col+'">'+indent+modCell+'</td><td style="padding:5px 10px">'+abcCell+'</td><td style="padding:5px 10px;text-align:right">'+mv+'</td><td style="padding:5px 10px;text-align:right">'+av+'</td><td style="padding:5px 10px">'+st+' '+tag+shTag+'</td><td style="padding:5px 10px;'+(frozen?'':'color:#e05555;font-weight:600')+'">'+ft+'</td></tr>';
                }
            });
            h+='</tbody></table>';
        } else if(data.pairs&&data.pairs.length){
            var MC=['#b8a99a','#9cadb0','#c0a8b0','#a0b0a0','#c0a098','#8ab0a8','#b0a0c0','#b0b098'];
            h+='<table id="diag-table" class="diag-table" style="font-size:12px"><thead><tr style="background:var(--border)"><th style="padding:6px 10px;text-align:left">Mesh</th><th style="padding:6px 10px;text-align:right">mod顶点</th><th style="padding:6px 10px;text-align:right">ABC顶点</th><th style="padding:6px 10px;text-align:left">状态</th><th style="padding:6px 10px;text-align:right">差</th><th style="padding:6px 10px;text-align:left">冻结</th><th style="padding:6px 10px;text-align:left">层级</th><th style="padding:6px 10px;text-align:left">顺序</th></tr></thead><tbody>';
            data.pairs.forEach(function(p){
                var diff=Math.abs(p.mod_vtx-p.abc_vtx);
                var rowStyle=p.status==='mismatch'?'background:#e0555518':'';
                var nameStyle=p.status==='mismatch'?'color:#e05555;font-weight:600':'';
                var st=p.status==='ok'?'✅ 可连':(p.status==='mismatch'?'❌ 顶点不符':'⚠');
                var stColor=p.status==='mismatch'?'color:#e05555':'';
                var xf=p.mod_transform;
                var frozen=xf&&xf.frozen;
                var frozenTxt=frozen?'✅':'❌ 未冻结';
                var frozenStyle=!frozen?'color:#e05555;font-weight:600':'';
                if(!frozen&&xf){
                    var parts=[];
                    if(xf.t&&(xf.t[0]||xf.t[1]||xf.t[2]))parts.push('T('+xf.t.join(',')+')');
                    if(xf.r&&(xf.r[0]||xf.r[1]||xf.r[2]))parts.push('R('+xf.r.join(',')+')');
                    if(xf.s&&(xf.s[0]!==1||xf.s[1]!==1||xf.s[2]!==1))parts.push('S('+xf.s.join(',')+')');
                    frozenTxt='❌ '+parts.join(' ');
                }
                if(p.is_group){
                    // 组行：只显示组名+是否存在，按深度着色
                    var gcol=MC[(p.depth-1)%MC.length];
                    var gindent='&nbsp;&nbsp;'.repeat(p.depth-1);
                    var gin=p.group_in_abc?'':'<span style="color:#e05555;margin-left:6px">(ABC缺失)</span>';
                    h+='<tr><td style="padding:4px 10px;border-left:4px solid '+gcol+';color:'+gcol+';font-weight:600;background:rgba(255,255,255,.03)">'+gindent+'📁 '+he(p.name)+gin+'</td><td colspan="7"></td></tr>';
                } else {
                    var hm=p.hierarchy_match!==false;
                    var hierTxt=hm?'✅':'❌ mod:'+he(p.mod_chain||'')+' / abc:'+he(p.abc_chain||'');
                    var om=p.order_match!==false,orderTxt=om?'✅':'❌';
                    var col=MC[(p.depth-1)%MC.length];
                    var indent='&nbsp;&nbsp;'.repeat((p.depth||0)-1);
                    h+='<tr style="'+rowStyle+'"><td style="'+nameStyle+';padding:5px 10px;border-left:3px solid '+col+'">'+indent+he(p.name)+'</td><td style="padding:5px 10px;text-align:right">'+p.mod_vtx+'</td><td style="padding:5px 10px;text-align:right">'+p.abc_vtx+'</td><td style="'+stColor+';padding:5px 10px">'+st+'</td><td style="padding:5px 10px;text-align:right;'+(diff>0?'color:#e05555;font-weight:600':'')+'">'+(diff>0?diff:'-')+'</td><td style="'+(xf&&xf.frozen?'':'color:#e05555;font-weight:600')+'">'+frozenTxt+'</td><td style="'+(hm?'':'color:#e05555;font-weight:600')+';font-size:11px">'+hierTxt+'</td><td style="'+(om?'':'color:#e05555;font-weight:600')+'">'+orderTxt+'</td></tr>';
                }
            });
            h+='</tbody></table>';
        }
        if(data.group_mod_only&&data.group_mod_only.length)h+='<p style="margin-top:8px;color:#e05555;font-size:12px">🏗 <b>mod独有子组</b>: '+he(data.group_mod_only.join(', '))+'</p>';
        if(data.group_abc_only&&data.group_abc_only.length)h+='<p style="margin-top:4px;color:#e05555;font-size:12px">🏗 <b>ABC独有子组</b>: '+he(data.group_abc_only.join(', '))+'</p>';
        if(data.mod_only&&data.mod_only.length)h+='<p style="margin-top:8px;color:var(--warn);font-size:12px">⚠ <b>mod独有mesh</b>: '+he(data.mod_only.join(', '))+'</p>';
        if(data.abc_only&&data.abc_only.length)h+='<p style="margin-top:4px;color:var(--warn);font-size:12px">⚠ <b>ABC独有mesh</b>: '+he(data.abc_only.join(', '))+'</p>';
        h+='<button style="margin-top:10px;padding:6px 14px;background:var(--accent);color:#1a1d23;border:none;border-radius:6px;cursor:pointer;font-size:12px;margin-right:8px" onclick="exportPDF()">📄 导出 PDF</button>';
        resultDiv.innerHTML=h;
    }catch(e){
        resultDiv.innerHTML='<p style="color:#e05555;font-size:12px">❌ JSON 解析失败: '+he(e.message)+'</p>';
    }
}
function exportPDF(){
    var container=document.getElementById('diag-result');
    var html='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>BS诊断清单</title>';
    html+='<style>';
    html+=':root{--bg:#fff;--card:#fff;--border:#ccc;--text:#1a1a1a;--dim:#666;--accent:#2563eb;--ok:#2a8a2a;--warn:#c80}';
    html+='body{font-family:"Microsoft YaHei",sans-serif;padding:30px;color:#1a1a1a;max-width:1100px;margin:0 auto}';
    html+='h2{font-size:18px;margin-bottom:4px}';
    html+='.info{color:#666;font-size:12px;margin-bottom:12px}';
    html+='.summary{display:flex;gap:16px;margin:8px 0;font-size:13px;flex-wrap:wrap}';
    html+='table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}';
    html+='th{background:#f0f0f0;padding:6px 10px;text-align:left;border-bottom:2px solid #ccc}';
    html+='td{padding:5px 10px;border-bottom:1px solid #eee}';
    html+='.ok{color:#2a8a2a}.bad{color:#c00}.warn{color:#c80}';
    html+='.dl-btn{display:inline-block;padding:10px 20px;background:#2563eb;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer;margin-bottom:16px}';
    html+='@media print{.dl-btn{display:none}body{padding:0}@page{size:A4 landscape;margin:10mm}}';
    html+='</style></head><body>';
    html+='<button class="dl-btn" onclick="window.print()">📥 保存为 PDF</button>';
    html+='<p style="color:#888;font-size:11px;margin-bottom:16px">点击上方按钮 → 打印对话框 → 目标选「另存为 PDF」→ 保存</p>';
    html+=container.innerHTML;
    html+='</body></html>';

    var blob=new Blob([html],{type:'text/html;charset=UTF-8'});
    var url=URL.createObjectURL(blob);
    var w=window.open(url,'_blank');
    if(!w){alert('弹窗被拦截，请允许弹出窗口后重试');}
}

var BS_TEMPLATE='import maya.cmds as cmds,json,math\n'+
'mod="__MOD__";abc="__ABC__"\n'+
'def sn(n):return n.split("|")[-1].split(":")[-1]\n'+
'def get_xf(n):\n'+
' t=cmds.getAttr(n+".t")[0];r=cmds.getAttr(n+".r")[0];s=cmds.getAttr(n+".s")[0]\n'+
' return{"t":[round(v,4)for v in t],"r":[round(v,4)for v in r],"s":[round(v,4)for v in s],"frozen":all(abs(v)<1e-6 for v in t)and all(abs(v)<1e-6 for v in r)and all(abs(v-1)<1e-6 for v in s)}\n'+
'def build_tree(root):\n'+
' # 递归构建层级树, 返回{name,path,is_mesh,is_group,vtx,xf,children:[],children_order:[names]}\n'+
' node={"name":sn(root),"path":root,"is_mesh":False,"is_group":True,"vtx":0,"xf":get_xf(root),"children":[],"child_order":[]}\n'+
' ch=cmds.listRelatives(root,children=True,type="transform",fullPath=True)or[]\n'+
' for c in ch:\n'+
'  sh=cmds.listRelatives(c,shapes=True,type="mesh",fullPath=True)or[]\n'+
'  if sh:\n'+
'   v=cmds.polyEvaluate(c,v=True)\n'+
'   fc=cmds.polyEvaluate(c,f=True)\n'+
'   mnode={"name":sn(c),"path":c,"is_mesh":True,"is_group":False,"vtx":v,"fcs":fc,"xf":get_xf(c),"children":[],"child_order":[],"shapes":[sn(s) for s in sh]}\n'+
'   node["children"].append(mnode)\n'+
'   node["child_order"].append(sn(c))\n'+
'  else:\n'+
'   sub=build_tree(c)\n'+
'   node["children"].append(sub)\n'+
'   node["child_order"].append(sn(c))\n'+
' return node\n'+
'def walk_tree(node,parent_name,depth,branch_id,result):\n'+
' # 深度优先遍历, 按大纲顺序输出扁平列表（组和mesh都输出）\n'+
' if not node["is_mesh"] and depth>0:\n'+
'  result.append({"name":node["name"],"parent":parent_name,"depth":depth,"branch":branch_id,"path":node["path"],"vtx":0,"xf":node["xf"],"is_mesh":False,"is_group":True})\n'+
' if node["is_mesh"]:\n'+
'  result.append({"name":node["name"],"parent":parent_name,"depth":depth,"branch":branch_id,"path":node["path"],"vtx":node["vtx"],"xf":node["xf"],"is_mesh":True,"shapes":node.get("shapes",[]),"fcs":node.get("fcs",0)})\n'+
' else:\n'+
'  for i,ch in enumerate(node["children"]):\n'+
'   walk_tree(ch,node["name"],depth+1,branch_id+"_"+str(i),result)\n'+
'def match_trees(mod_tree,abc_tree,issues):\n'+
' # 对比两棵树:组名+顺序+层级\n'+
' if mod_tree["name"]!=abc_tree["name"]:issues.append("组名不一致: mod."+mod_tree["name"]+" vs abc."+abc_tree["name"])\n'+
' if mod_tree["child_order"]!=abc_tree["child_order"]:issues.append("子级顺序不一致 @"+mod_tree["name"]+": mod"+str(mod_tree["child_order"])+" vs abc"+str(abc_tree["child_order"]))\n'+
' for i in range(min(len(mod_tree["children"]),len(abc_tree["children"]))):\n'+
'  mc=mod_tree["children"][i];ac=abc_tree["children"][i]\n'+
'  if mc["is_mesh"] and ac["is_mesh"]:continue  # mesh check later\n'+
'  if mc["is_mesh"]!=ac["is_mesh"]:\n'+
'   issues.append("类型不一致 @"+mc["name"]+": mod."+("mesh"if mc["is_mesh"]else"group")+" vs abc."+("mesh"if ac["is_mesh"]else"group"))\n'+
'   continue\n'+
'  if not mc["is_mesh"]:match_trees(mc,ac,issues)\n'+
'print("[ABC BS Diagnostic v3]")\n'+
'mod_root=cmds.ls("__MOD__",long=True)[0];abc_root=cmds.ls("__ABC__",long=True)[0]\n'+
'mod_tree=build_tree(mod_root);abc_tree=build_tree(abc_root)\n'+
'issues=[];match_trees(mod_tree,abc_tree,issues)\n'+
'if issues:\n'+
' for iss in issues:print("🏗 "+iss)\n'+
'else:print("🏗 层级结构一致")\n'+
'# 收集所有mesh\n'+
'mr={};mod_list=[];walk_tree(mod_tree,"",0,"M",mod_list)\n'+
'ar={};abc_list=[];walk_tree(abc_tree,"",0,"A",abc_list)\n'+
'for m in mod_list:\n'+
' if m["is_mesh"]:mr[m["name"]]=m\n'+
'for m in abc_list:\n'+
' if m["is_mesh"]:ar[m["name"]]=m\n'+
'# 按大纲顺序生成 mod/abc 两个列表\n'+
'mo=[];ao=[];ok=0;mm=0;nf=0;nh=0;no=0;ns=0;md={}\n'+
'# 冻结链检查辅助：收集所有节点(组+mesh)的冻结状态\n'+
'mfree={m["path"]:m["xf"]["frozen"] for m in mod_list}\n'+
'afree={m["path"]:m["xf"]["frozen"] for m in abc_list}\n'+
'for m in mod_list+abc_list:\n'+
' n=m["name"]\n'+
' if not m["is_mesh"]:continue\n'+
' if n in mr and n in ar and n not in md:\n'+
'  s="ok"if mr[n]["vtx"]==ar[n]["vtx"]else"mismatch"\n'+
'  if s=="ok":ok+=1\n'+
'  else:mm+=1\n'+
'  mfull=[sn(p)for p in mr[n]["path"].split("|")];afull=[sn(p)for p in ar[n]["path"].split("|")]\n'+
'  mrname=sn(mod_root);arname=sn(abc_root)\n'+
'  mod_parts=mfull[mfull.index(mrname):] if mrname in mfull else mfull\n'+
'  abc_parts=afull[afull.index(arname):] if arname in afull else afull\n'+
'  hm=mod_parts==abc_parts\n'+
'  if not hm:nh+=1\n'+
'  # shape 节点名对比（blendShape 按 shape 名匹配，名字不一致会连不上）\n'+
'  sm=mr[n]["shapes"][0] if mr[n]["shapes"] else ""\n'+
'  sa=ar[n]["shapes"][0] if ar[n]["shapes"] else ""\n'+
'  shm=sm==sa\n'+
'  if not shm:ns+=1\n'+
'  # 面数对比\n'+
'  fm=mr[n]["fcs"]==ar[n]["fcs"]\n'+
'  # 冻结链检查：mod 和 abc 两边的整条链（组+mesh）都查\n'+
'  unfrozen_nodes=[]\n'+
'  for ci in range(len(mfull)):\n'+
'   cum="|".join(mfull[:ci+1])\n'+
'   if cum in mfree and not mfree[cum]:unfrozen_nodes.append("mod:"+sn(cum))\n'+
'  for ci in range(len(afull)):\n'+
'   cum="|".join(afull[:ci+1])\n'+
'   if cum in afree and not afree[cum]:unfrozen_nodes.append("abc:"+sn(cum))\n'+
'  if unfrozen_nodes:nf+=1\n'+
'  md[n]={"mod_vtx":mr[n]["vtx"],"abc_vtx":ar[n]["vtx"],"mod_fcs":mr[n]["fcs"],"abc_fcs":ar[n]["fcs"],"status":s,"mod_transform":mr[n]["xf"],"abc_transform":ar[n]["xf"],"hierarchy_match":hm,"mod_chain":"|".join(mod_parts),"abc_chain":"|".join(abc_parts),"shape_match":shm,"mod_shape":sm,"abc_shape":sa,"face_match":fm,"unfrozen_nodes":unfrozen_nodes}\n'+
' elif n in mr and n not in ar and n not in mo:mo.append(n)\n'+
' elif n in ar and n not in mr and n not in ao:ao.append(n)\n'+
'# 顺序对照：对齐算法 — 单边独有空出，顺序错位标红（含组行和深度信息）\n'+
'ordered_pairs=[]\n'+
'mlist_info={m["name"]:m for m in mod_list};alist_info={m["name"]:m for m in abc_list}\n'+
'mnames=[m["name"] for m in mod_list];anames=[m["name"] for m in abc_list]\n'+
'i=j=0\n'+
'while i<len(mnames) or j<len(anames):\n'+
' if i<len(mnames) and j<len(anames) and mnames[i]==anames[j]:\n'+
'  mi=mlist_info[mnames[i]]\n'+
'  ordered_pairs.append({"mod":mnames[i],"abc":anames[j],"same":True,"is_group":not mi["is_mesh"],"depth":mi["depth"]})\n'+
'  i+=1;j+=1\n'+
' elif i<len(mnames) and j<len(anames) and mnames[i] not in anames and anames[j] not in mnames:\n'+
'  mi=mlist_info[mnames[i]]\n'+
'  ordered_pairs.append({"mod":mnames[i],"abc":anames[j],"same":False,"name_mismatch":True,"is_group":not mi["is_mesh"],"depth":mi["depth"]})\n'+
'  i+=1;j+=1;no+=1\n'+
' elif i<len(mnames) and mnames[i] not in anames:\n'+
'  mi=mlist_info[mnames[i]]\n'+
'  ordered_pairs.append({"mod":mnames[i],"abc":"","same":False,"mod_only_row":True,"is_group":not mi["is_mesh"],"depth":mi["depth"]})\n'+
'  i+=1;no+=1\n'+
' elif j<len(anames) and anames[j] not in mnames:\n'+
'  ai=alist_info[anames[j]]\n'+
'  ordered_pairs.append({"mod":"","abc":anames[j],"same":False,"abc_only_row":True,"is_group":not ai["is_mesh"],"depth":ai["depth"]})\n'+
'  j+=1;no+=1\n'+
' else:\n'+
'  mi=mlist_info[mnames[i]] if i<len(mnames) else {"is_mesh":True,"depth":0}\n'+
'  ordered_pairs.append({"mod":mnames[i] if i<len(mnames) else "","abc":anames[j] if j<len(anames) else "","same":False,"is_group":not mi["is_mesh"],"depth":mi["depth"]})\n'+
'  i+=1;j+=1;no+=1\n'+
'import datetime as dt\n'+
'r={"mod_group":mod,"abc_group":abc,"time":dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"summary":{"total_pairs":ok+mm,"ok":ok,"mismatch":mm,"mod_only":len(mo),"abc_only":len(ao),"not_frozen":nf,"hierarchy_mismatch":nh,"order_mismatch":no,"shape_mismatch":ns},"ordered_pairs":ordered_pairs,"mesh_data":md,"mod_only":mo,"abc_only":ao,"structure_issues":issues}\n'+
'print("\\n=== COPY JSON BELOW ===\\n"+json.dumps(r,ensure_ascii=False,indent=2))';

function updateBSScript(){}  // 占位，脚本由 copyBSScript 即时生成
function copyBSScript(){
    var mod=document.getElementById('bs-mod').value.trim();
    var abc=document.getElementById('bs-abc').value.trim();
    if(!mod||!abc){alert('请先填写 Mod 组名和 ABC 组名');return;}
    var txt=BS_TEMPLATE.replace(/__MOD__/g,mod).replace(/__ABC__/g,abc);
    if(navigator.clipboard){navigator.clipboard.writeText(txt).then(function(){
        var btn=document.querySelector('#bs-mod').parentElement.querySelector('button');
        if(btn){btn.textContent='已复制!';setTimeout(function(){btn.textContent='📋 复制脚本到剪贴板';},1500);}
    });}
}

// ── 留言板 ──
function loadLocal(cb){try{cb(JSON.parse(localStorage.getItem('aty_msgs')||'[]'));}catch(e){cb([]);}}
function saveLocal(ms,cb){localStorage.setItem('aty_msgs',JSON.stringify(ms));if(cb)cb();}
function loadMsgs(cb){
    if(window._useAPI){
        fetch('/api/msgs').then(function(r){if(!r.ok)throw Error();return r.json();}).then(function(ms){cb(ms);}).catch(function(){loadLocal(cb);});
    }else{loadLocal(cb);}
}
function saveMsgs(ms,cb){
    if(window._useAPI){
        fetch('/api/msgs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ms[ms.length-1])}).then(function(r){if(!r.ok)throw Error();}).then(function(){if(cb)cb();}).catch(function(){saveLocal(ms,cb);});
    }else{saveLocal(ms,cb);}
}
// API 仅在 Python server 使用时启用（localhost 检测）
// API 可用时启用共享模式（file:// 时关闭）
window._useAPI=location.protocol!=='file:';
window._gistId=localStorage.getItem('aty_gistId')||'';
window._ghToken=localStorage.getItem('aty_ghToken')||'';
function renderMsgs(){
    loadMsgs(function(ms){
        var h='';
        ms.slice(-50).reverse().forEach(function(m,i){
            var del=window._isAdmin?' <button onclick="event.stopPropagation();deleteMsg('+i+')" style="background:none;border:none;color:#e05555;cursor:pointer;font-size:10px;padding:0 2px" title="删除此留言">✕</button>':'';
            h+='<div class="msg-item"><span class="who">'+he(m.name||'匿名')+'</span><span class="when">'+he(m.time)+'</span>'+del+'<div class="what">'+he(m.text)+'</div></div>';
        });
        document.getElementById('msg-list').innerHTML=h||'<p style="color:var(--dim);font-size:12px">暂无留言，来说两句吧</p>';
    });
}
function sendMsg(){
    var name=document.getElementById('msg-name').value.trim()||'匿名';
    var text=document.getElementById('msg-text').value.trim();
    if(!text)return;
    loadMsgs(function(ms){
        ms.push({name:name,text:text,time:new Date().toLocaleString('zh-CN')});
        saveMsgs(ms,function(){
            document.getElementById('msg-text').value='';
            renderMsgs();
        });
    });
}
function toggleMsg(){
    var p=document.getElementById('msg-panel');
    var btn=document.getElementById('msg-btn');
    if(p.style.display==='none'||!p.style.display){
        p.style.display='block';btn.classList.add('on');renderMsgs();
    }else{
        p.style.display='none';btn.classList.remove('on');
    }
}
if(window._gistId&&window._ghToken){document.getElementById('msg-mode-hint').textContent='（共享模式）';}else if(window._useAPI){document.getElementById('msg-mode-hint').textContent='（本机存储，可⚙配置共享）';}else{document.getElementById('msg-mode-hint').textContent='（本机存储）';}
function setupAPI(){
    var gid=prompt('请输入 Gist ID（留空取消共享）:',window._gistId||'');
    if(gid===null)return;
    var tok='';
    if(gid)tok=prompt('请输入 GitHub Token:','');
    localStorage.setItem('aty_gistId',gid);
    localStorage.setItem('aty_ghToken',tok);
    window._gistId=gid;window._ghToken=tok;
    if(gid&&tok){document.getElementById('msg-mode-hint').textContent='（共享模式）';}else{document.getElementById('msg-mode-hint').textContent='（本机存储）';}
    renderMsgs();
}
// 管理员密码验证（默认密码 ty190219，存 localStorage）
window._adminPwd='ty190219';
window._isAdmin=localStorage.getItem('aty_admin')==='1';
if(window._isAdmin){document.getElementById('admin-btn').textContent='🔓';document.getElementById('log-admin-actions').style.display='inline';}
function toggleAdmin(){
    if(window._isAdmin){window._isAdmin=false;localStorage.removeItem('aty_admin');document.getElementById('admin-btn').textContent='🔑';document.getElementById('log-admin-actions').style.display='none';renderMsgs();return;}
    var p=prompt('请输入管理员密码：');
    if(p===window._adminPwd){window._isAdmin=true;localStorage.setItem('aty_admin','1');document.getElementById('admin-btn').textContent='🔓';document.getElementById('log-admin-actions').style.display='inline';renderMsgs();}
    else if(p!==null){alert('密码错误');}
}
function deleteMsg(idx){
    if(!window._isAdmin)return;
    if(!confirm('确定删除这条留言？'))return;
    loadMsgs(function(ms){
        // 显示顺序是倒序（最新在前），idx 是显示下标
        var realIdx=ms.length-1-idx;
        ms.splice(realIdx,1);
        if(window._useAPI){
            fetch('/api/msgs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({replace:true,msgs:ms})})
            .then(function(r){if(!r.ok)throw Error();})
            .then(function(){renderMsgs();})
            .catch(function(){saveLocal(ms,function(){renderMsgs();});});
        }else{
            saveLocal(ms,function(){renderMsgs();});
        }
    });
}
// 开发日志
var _logCache=[];
function loadLog(cb){
    // 优先用生成时嵌入的日志
    if(window.__EMBED_LOG__&&window.__EMBED_LOG__.length>0){
        _logCache=window.__EMBED_LOG__;
        if(cb)cb(_logCache);
        return;
    }
    if(window._useAPI){
        fetch('https://api.github.com/gists/'+window._gistId,{
            headers:{Authorization:'Bearer '+window._ghToken,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
        }).then(function(r){return r.json();}).then(function(d){
            try{_logCache=JSON.parse(d.files['changelog.json']&&d.files['changelog.json'].content||'[]');}catch(e){_logCache=[];}
            if(cb)cb(_logCache);
        }).catch(function(){_logCache=loadLocalLog();if(cb)cb(_logCache);});
    }else{_logCache=loadLocalLog();if(cb)cb(_logCache);}
}
function loadLocalLog(){try{return JSON.parse(localStorage.getItem('aty_log')||'[]');}catch(e){return[];}}
function showLogLatest(){
    loadLog(function(log){
        if(log.length>0){
            var l=log[log.length-1];
            document.getElementById('log-latest').textContent='最近更新: '+l.time+' | '+he(l.ver||'')+' — '+he(l.text||'');
        }else{
            document.getElementById('log-latest').textContent='暂无更新记录';
        }
    });
}
function toggleLog(){
    var p=document.getElementById('log-full');
    if(p.style.display==='none'||!p.style.display){
        p.style.display='block';
        var h='';_logCache.slice().reverse().forEach(function(l){h+='<div style="padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04)"><span style="font-size:11px;color:var(--dim)">'+he(l.time)+'</span> <b style="font-size:12px;color:var(--accent)">'+he(l.ver||'')+'</b> <span style="font-size:12px">'+he(l.text||'')+'</span></div>';});
        document.getElementById('log-full-list').innerHTML=h||'<p style="color:var(--dim);font-size:12px">暂无日志</p>';
    }else{
        p.style.display='none';
    }
}
function copyFullLog(){
    var txt=_logCache.map(function(l){return '['+l.time+'] '+l.ver+' — '+l.text;}).join('\n');
    if(navigator.clipboard){navigator.clipboard.writeText(txt).then(function(){alert('已复制完整日志');});}
}
function addLog(ver,text){
    var log=loadLocalLog();log.push({ver:ver,text:text,time:new Date().toLocaleString('zh-CN')});
    if(log.length>50)log=log.slice(-50);
    localStorage.setItem('aty_log',JSON.stringify(log));
    if(window._useAPI){
        fetch('https://api.github.com/gists/'+window._gistId,{
            method:'PATCH',
            headers:{Authorization:'Bearer '+window._ghToken,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'},
            body:JSON.stringify({files:{'changelog.json':{content:JSON.stringify(log,null,2)}}})
        });
    }
}
// ── 素材库：主页入口模块 + 独立浏览界面 + 上传/删除/动态加载 ──
var ASSET_CATS=['材质球','纹理','合成素材','HDRI','模型'];
var AUTO_THUMB_CATS=['纹理','合成素材','HDRI']; // 这些分类缩略图自动生成，不上传
// 主页显示 5 个分类模块（与参考图一致），点模块进独立界面
var ASSET_ICONS={'材质球':'🔮','纹理':'🪢','合成素材':'🧩','HDRI':'🌅','模型':'🗿'};
function assetHero(){
    var counts={},total=0;
    DATA.forEach(function(d){if(d.is_asset&&d.kind!=='ref'){counts[d.subtag]=(counts[d.subtag]||0)+1;total++;}});
    var tiles='<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px">';
    ASSET_CATS.forEach(function(c){
        tiles+='<div class="card" style="cursor:pointer" onclick="openAssetBrowser(\''+c+'\')">'+
          '<div style="font-size:32px">'+ASSET_ICONS[c]+'</div>'+
          '<h3 style="font-size:16px;margin:8px 0 2px">'+c+'</h3>'+
          '<div style="color:var(--dim);font-size:11px">'+(counts[c]||0)+' 个素材</div>'+
          '<div style="margin-top:10px;display:flex;gap:8px">'+
            '<button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="event.stopPropagation();openUpload(\''+c+'\')">⬆️ 上传</button>'+
            '<button class="card-btn" onclick="event.stopPropagation();openAssetBrowser(\''+c+'\')">查看 →</button>'+
          '</div></div>';
    });
    tiles+='</div>';
    return '<div class="bar"><h2 style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">🎨 素材库'+
      '<span style="font-size:12px;color:var(--dim);font-weight:400">'+total+' 个素材 · 按分类查看</span></h2></div>'+tiles;
}
var _abCat='全部';
function openAssetBrowser(cat){
    _abCat=cat||'全部';
    document.getElementById('ab-search').value='';
    document.getElementById('asset-modal').classList.add('show');
    renderAssetBrowser();
}
function closeAssetBrowser(){document.getElementById('asset-modal').classList.remove('show');}
function renderAssetBrowser(){
    var q=(document.getElementById('ab-search').value||'').toLowerCase();
    var all=DATA.filter(function(d){return d.is_asset;});
    var list=all.filter(function(d){return _abCat==='全部'||d.subtag===_abCat;});
    if(q)list=list.filter(function(d){return (d.name||'').toLowerCase().indexOf(q)!==-1;});
    var tabs=['全部'].concat(ASSET_CATS);
    document.getElementById('ab-tabs').innerHTML=tabs.map(function(c){
        var n=c==='全部'?all.length:all.filter(function(d){return d.subtag===c;}).length;
        return '<button class="fbtn'+(c===_abCat?' on':'')+'" onclick="_abCat=\''+c+'\';renderAssetBrowser();">'+he(c)+' ('+n+')</button>';
    }).join('');
    if(!list.length){
        document.getElementById('ab-grid').innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--dim);padding:40px">📭 没有素材</div>';
        return;
    }
    document.getElementById('ab-grid').innerHTML=list.map(assetTile).join('');
}
function assetTile(d){
    var t='<div class="card" style="cursor:default;padding:10px">';
    if(d.thumbnail){
        t+='<div style="height:110px;overflow:hidden;border-radius:6px;margin-bottom:6px;background:var(--code-bg)"><img src="'+he(encUrl(d.thumbnail))+'" alt="" style="width:100%;height:110px;object-fit:cover" onerror="this.parentElement.innerHTML=\'<span style=&quot;color:var(--dim);font-size:12px&quot;>无缩略图</span>\'"></div>';
    }else{
        t+='<div style="height:110px;border-radius:6px;margin-bottom:6px;background:var(--code-bg);display:flex;align-items:center;justify-content:center"><span style="color:var(--dim);font-size:12px">无缩略图</span></div>';
    }
    t+='<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:2px;word-break:break-all">'+he(d.name)+'</div>';
    t+='<div style="color:var(--dim);font-size:10px;margin-bottom:6px">'+he(d.subtag)+'</div>';
    var dls=d.downloads&&d.downloads.length?d.downloads:(d.download?[d.download]:[]);
    if(d.download_disabled||window.__DL_DISABLED__){
        t+='<span class="pkg-l" style="margin-left:0;background:var(--border);color:var(--dim);cursor:not-allowed;padding:4px 8px" title="素材下载请访问 GitHub 站">📥 不可下载</span>';
    }else if(dls.length===1){
        t+='<a class="pkg-l" style="margin-left:0;padding:4px 8px" href="'+he(encUrl(dls[0]))+'" download>📥 下载</a>';
    }else if(dls.length>1){
        var lid='dl_'+Math.random().toString(36).slice(2);
        t+='<button class="pkg-l" style="margin-left:0;border:none;cursor:pointer;padding:4px 8px" onclick="event.stopPropagation();var p=document.getElementById(\''+lid+'\');p.style.display=p.style.display===\'none\'?\'\':\'none\'">📥 下载 ('+dls.length+')</button>';
        t+='<div id="'+lid+'" style="display:none;margin-top:6px">';
        dls.forEach(function(u){var fn=decodeURIComponent(u.split('/').pop());t+='<div style="font-size:11px;padding:2px 0"><a href="'+he(encUrl(u))+'" download style="color:var(--accent);text-decoration:none">⬇ '+he(fn)+'</a></div>';});
        t+='</div>';
    }
    if(window._isAdmin){
        t+='<div style="margin-top:6px"><button style="background:none;border:1px solid var(--border);border-radius:4px;color:var(--dim);cursor:pointer;font-size:10px;padding:2px 6px" onclick="event.stopPropagation();delAsset(\''+he(d.name)+'\',\''+he(d.subtag)+'\',event)">🗑 删除</button></div>';
    }
    t+='</div>';
    return t;
}
var _assetState={uploading:false};
// ── 参考图：一级板块，5 个类型模块 + 标签筛选查找 + 双击查看 ──
var REF_CATS=['摄影','油画','CG动画','电影','插画'];
var REF_TAGS={
    时间:['清晨','午后','黄昏','夜晚'],
    主题:['服装设计','场景设计','角色设计','概念设计','氛围插画','游戏','平面设计','构成设计'],
    季节:['春','夏','秋','冬'],
    情绪:['喜','怒','哀','乐','忧'],
    色调:['红','橙','黄','绿','青','蓝','紫','黑','白','冷','暖','粉','灰','金','自然']
};
var REF_ICONS={'摄影':'📷','油画':'🖌','CG动画':'🎬','电影':'🎞','插画':'🎨'};
var _refCat='摄影';
var _refSel={};
var _guestCfg=window.__GUEST__||{};
var _uploadMode='admin';
var _refPendingOnly=false;
function refVisible(d){
    if(_refPendingOnly)return d.status==='pending';
    return true; // 访客上传直接公开，无需审核
}
function refHero(){
    var counts={},total=0,pendN=0;
    DATA.forEach(function(d){
        if(d.is_asset&&d.kind==='ref'){
            if(d.status==='pending'){pendN++;if(!window._isAdmin)return;}
            counts[d.subtag]=(counts[d.subtag]||0)+1;total++;
        }
    });
    var tiles='<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px">';
    REF_CATS.forEach(function(c){
        tiles+='<div class="card" style="cursor:pointer" onclick="openRefBrowser(\''+c+'\')">'+
          '<div style="font-size:32px">'+REF_ICONS[c]+'</div>'+
          '<h3 style="font-size:16px;margin:8px 0 2px">'+c+'</h3>'+
          '<div style="color:var(--dim);font-size:11px">'+(counts[c]||0)+' 张参考图</div>'+
          '<div style="margin-top:10px;display:flex;gap:8px">'+
            '<button class="card-btn" style="background:var(--accent);color:#1a1d23" onclick="event.stopPropagation();openRefUpload(\''+c+'\')">⬆️ 上传</button>'+
            '<button class="card-btn" onclick="event.stopPropagation();openRefBrowser(\''+c+'\')">查看 →</button>'+
          '</div></div>';
    });
    tiles+='</div>';
    var adminBtns='';
    if(window._isAdmin){
        adminBtns='<button class="diag-btn" style="border-radius:999px" onclick="openGuestSettings()">⚙ 访客设置</button>';
    }
    return '<div class="bar"><h2 style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">🖼 参考图'+
      '<span style="font-size:12px;color:var(--dim);font-weight:400">'+total+' 张 · 按类型 / 标签查找</span>'+
      '<button class="diag-btn" style="margin-left:10px;border-radius:999px;background:rgba(229,192,123,.15);border-color:#e5c07b;color:#e5c07b" onclick="openRefSearch()">🔍 查找</button>'+adminBtns+'</h2></div>'+tiles;
}
function openRefBrowser(cat){
    _refCat=cat;
    _refPendingOnly=false;
    document.getElementById('ref-modal-title').textContent='🖼 参考图 — '+cat;
    document.getElementById('ref-modal').classList.add('show');
    renderRefGrid(document.getElementById('ref-grid'),DATA.filter(function(d){return d.is_asset&&d.kind==='ref'&&d.subtag===cat&&refVisible(d);}));
}
async function approveRef(name,subcat){
    if(!window._isAdmin)return;
    if(!ghToken())return;
    if(!confirm('通过审核？图片将公开显示。'))return;
    try{
        var idx=await fetchIndex();
        var e=(idx.assets||[]).filter(function(a){return a.kind==='ref'&&a.subcat===subcat&&a.name===name;})[0];
        if(e)delete e.status;
        var ts=new Date().toISOString();
        idx.updated=ts;
        for(var rp=0;rp<3;rp++){
            var sha='';
            try{var ex=await ghAPI('GET','assets_index.json');sha=ex.sha||'';}catch(err2){}
            try{await ghAPI('PUT','assets_index.json',{message:'Approve ref',content:b64u(JSON.stringify(idx)),sha:sha});break;}catch(e5){if(rp>=2)throw e5;await sleep(4000*(rp+1));}
        }
        markIdxTs(ts);
        var d=DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.name===name&&x.subtag===subcat;})[0];
        if(d)delete d.status;
        render();
        if(document.getElementById('ref-modal').classList.contains('show')){
            var el=document.getElementById('ref-grid');
            if(_refPendingOnly)renderRefGrid(el,DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.status==='pending';}));
            else renderRefGrid(el,DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.subtag===_refCat&&refVisible(x);}));
        }
        if(document.getElementById('refsearch-modal').classList.contains('show'))renderRefSearchGrid();
        alert('已通过审核 ✅');
    }catch(e){alert('审核失败: '+(e&&e.message||e));}
}
var _guestPws=[];
function openGuestSettings(){
    if(!window._isAdmin){alert('需要管理员权限');return;}
    if(!ghToken())return;
    document.getElementById('guest-enabled').checked=!!_guestCfg.enabled;
    _guestPws=(_guestCfg.passwords||[]).slice();
    renderGuestList();
    document.getElementById('guest-status').textContent='';
    document.getElementById('guest-modal').classList.add('show');
}
function renderGuestList(){
    var el=document.getElementById('guest-list');
    if(!_guestPws.length){el.innerHTML='<div style="font-size:12px;color:var(--dim)">暂无访客密码，添加或随机生成一个</div>';return;}
    el.innerHTML=_guestPws.map(function(pw,i){
        return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;font-size:13px">'+
        '<code style="background:var(--code-bg);padding:3px 8px;border-radius:4px">'+he(pw)+'</code>'+
        '<button class="card-btn" style="padding:2px 8px;font-size:11px" onclick="_guestPws.splice('+i+',1);renderGuestList();">🗑</button></div>';
    }).join('');
}
function addGuestPw(){
    var v=(document.getElementById('guest-newpw').value||'').trim();
    if(!v){alert('请输入密码');return;}
    if(_guestPws.indexOf(v)>=0){alert('密码已存在');return;}
    _guestPws.push(v);
    document.getElementById('guest-newpw').value='';
    renderGuestList();
}
function genGuestPw(){
    var chars='abcdefghjkmnpqrstuvwxyz23456789';
    var s='';
    for(var i=0;i<6;i++)s+=chars[Math.floor(Math.random()*chars.length)];
    document.getElementById('guest-newpw').value=s;
}
function closeGuestSettings(){document.getElementById('guest-modal').classList.remove('show');}
async function saveGuestSettings(){
    if(!ghToken())return;
    var enabled=document.getElementById('guest-enabled').checked;
    try{
        var idx=await fetchIndex();
        idx.guest={enabled:enabled,passwords:_guestPws};
        var ts=new Date().toISOString();
        idx.updated=ts;
        for(var rp=0;rp<3;rp++){
            var sha='';
            try{var ex=await ghAPI('GET','assets_index.json');sha=ex.sha||'';}catch(err2){}
            try{await ghAPI('PUT','assets_index.json',{message:'Update guest settings',content:b64u(JSON.stringify(idx)),sha:sha});break;}catch(e5){if(rp>=2)throw e5;await sleep(4000*(rp+1));}
        }
        _guestCfg=idx.guest;
        markIdxTs(ts);
        document.getElementById('guest-status').textContent='已保存 ✅';
        alert(enabled?('✅ 访客上传已开启！\n当前 '+_guestPws.length+' 个访客密码，把密码分别发给朋友即可，上传直接公开。'):'访客上传已关闭');
        closeGuestSettings();
    }catch(e){document.getElementById('guest-status').textContent='保存失败: '+(e&&e.message||e);}
}
function openRefPendingList(){
    _refPendingOnly=true;
    document.getElementById('ref-modal-title').textContent='⏳ 待审核图片';
    document.getElementById('ref-modal').classList.add('show');
    renderRefGrid(document.getElementById('ref-grid'),DATA.filter(function(d){return d.is_asset&&d.kind==='ref'&&d.status==='pending';}));
}
function closeRefBrowser(){document.getElementById('ref-modal').classList.remove('show');}
function renderRefGrid(el,list){
    if(!list.length){el.innerHTML='<div style="grid-column:1/-1;text-align:center;color:var(--dim);padding:40px">📭 暂无图片</div>';return;}
    el.innerHTML=list.map(refTile).join('');
}
function refTagsHtml(d){
    var t=d.tags||{},parts=[];
    Object.keys(t).forEach(function(g){(t[g]||[]).forEach(function(v){parts.push('<span class="rt-tag">'+he(v)+'</span>');});});
    return parts.join('');
}
function refTile(d){
    var hover='';
    var th=refTagsHtml(d);
    if(th||d.source)hover='<div class="ref-hover"><div>'+th+'</div>'+(d.source?'<div class="rt-src">📎 '+he(d.source)+'</div>':'')+'</div>';
    // 上传后本地模糊预览占位：真实图就绪后淡入替换
    var ph='';
    try{ph=localStorage.getItem('aty_ph_'+d.thumbnail)||'';}catch(e){}
    var bg=ph?' style="background-image:url(\''+ph+'\');background-size:cover;background-position:center"':'';
    var imgs=ph?' style="opacity:0;transition:opacity .35s" onload="this.style.opacity=1;var b=this.parentElement.querySelector(\'.rt-pending\');if(b)b.style.display=\'none\';"':'';
    var badge=ph?'<span class="rt-pending">⏳ 发布中</span>':'';
    var hasph=ph?' data-hasph="1"':'';
    var delBtn=window._isAdmin&&d.status!=='pending'?'<button class="rt-del" title="删除" onclick="event.stopPropagation();delAsset(\''+he(d.name)+'\',\''+he(d.subtag)+'\',event)">🗑</button>':'';
    var pend='';
    if(d.status==='pending'&&window._isAdmin){
        pend='<span class="rt-pending" style="background:rgba(224,85,85,.92);bottom:auto;top:4px;left:4px">⏳ 待审核</span>'+
             '<div style="position:absolute;top:4px;right:4px;display:flex;gap:4px;z-index:3">'+
             '<button style="background:rgba(152,195,121,.92);border:none;color:#1a1d23;border-radius:4px;padding:2px 6px;font-size:11px;cursor:pointer" onclick="event.stopPropagation();approveRef(\''+he(d.name)+'\',\''+he(d.subtag)+'\')">✅ 通过</button>'+
             '<button style="background:rgba(224,85,85,.92);border:none;color:#fff;border-radius:4px;padding:2px 6px;font-size:11px;cursor:pointer" onclick="event.stopPropagation();delAsset(\''+he(d.name)+'\',\''+he(d.subtag)+'\',event)">❌ 拒绝</button>'+
             '</div>';
    }else if(d.status==='pending'){
        pend='<span class="rt-pending" style="background:rgba(224,85,85,.92);bottom:auto;top:4px;left:4px">⏳ 待审核</span>';
    }
    return '<div class="ref-tile"'+bg+' ondblclick="openRefViewer(\''+he(d.name)+'\',\''+he(d.subtag)+'\')">'+delBtn+pend+badge+
      '<img src="'+he(encUrl(d.thumbnail||''))+(d.rot_ts?'?v='+d.rot_ts:'')+'" alt="" loading="lazy"'+hasph+imgs+' onerror="if(this.dataset.hasph){var t=this;setTimeout(function(){t.src=(t.src.split(\'?\')[0])+\'?v=\'+Date.now();},20000);}else{var n=parseInt(this.dataset.rt||0);if(n<3){this.dataset.rt=n+1;this.src=(this.src.split(\'?\')[0])+\'?v=\'+Date.now();}else{this.parentElement.innerHTML=\'<div style=&quot;height:200px;display:flex;align-items:center;justify-content:center;color:var(--dim);font-size:11px;padding:8px;text-align:center&quot;>图片加载失败<br>'+he(d.name)+'</div>\';}}">'+hover+'</div>';
}
// 生成模糊小图 dataURL（上传后的本地占位预览）
function makeThumbPreview(file){
    return new Promise(function(res){
        try{
            var img=new Image();
            var url=URL.createObjectURL(file);
            img.onload=function(){
                try{
                    var w=img.naturalWidth,h=img.naturalHeight;
                    var sc=Math.min(96/w,96/h);
                    var c=document.createElement('canvas');
                    c.width=Math.max(1,Math.round(w*sc));
                    c.height=Math.max(1,Math.round(h*sc));
                    var ctx=c.getContext('2d');
                    ctx.drawImage(img,0,0,c.width,c.height);
                    URL.revokeObjectURL(url);
                    res(c.toDataURL('image/jpeg',0.55));
                }catch(e){URL.revokeObjectURL(url);res('');}
            };
            img.onerror=function(){URL.revokeObjectURL(url);res('');};
            img.src=url;
        }catch(e){res('');}
    });
}
function openRefViewer(name,subcat){
    var d=DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.name===name&&x.subtag===subcat;})[0];
    if(!d)return;
    _refView=d;
    resetRefRot();
    document.getElementById('refview-img').src=encUrl(d.thumbnail||'');
    var h='<div style="font-size:14px;font-weight:600;margin-bottom:6px">'+he(d.name)+' <span style="color:var(--dim);font-size:11px">'+he(d.subtag)+'</span></div>';
    var t=d.tags||{},th=[];
    Object.keys(t).forEach(function(g){(t[g]||[]).forEach(function(v){th.push('<span class="rt-tag" style="display:inline-block;margin:2px">'+he(v)+'</span>');});});
    if(th.length)h+='<div style="margin-bottom:6px">'+th.join('')+'</div>';
    if(d.source)h+='<div style="color:var(--dim);margin-bottom:4px">📎 参考来源：'+he(d.source)+'</div>';
    if(d.description)h+='<div style="color:var(--dim)">📝 说明：'+he(d.description)+'</div>';
    if(d.download&&!window.__DL_DISABLED__)h+='<div style="margin-top:8px"><a class="pkg-l" style="margin-left:0" href="'+he(encUrl(d.download))+'" download>📥 下载原图</a></div>';
    if(window._isAdmin)h+='<div style="margin-top:8px"><button class="card-btn" onclick="openRefEdit(\''+he(d.name)+'\',\''+he(d.subtag)+'\')">🏷 编辑标签</button> <button class="card-btn" onclick="previewRotate()">🔄 旋转 90°</button> <button class="card-btn" style="border-color:#e05555;color:#e05555" onclick="closeRefViewer();delAsset(\''+he(d.name)+'\',\''+he(d.subtag)+'\',event)">🗑 删除</button></div>';
    document.getElementById('refview-info').innerHTML=h;
    document.getElementById('refview-modal').classList.add('show');
}
function closeRefViewer(){resetRefRot();document.getElementById('refview-modal').classList.remove('show');}
var _refView=null;
var _refRot=0;
// 旋转改为两步：先实时预览（CSS 变换），点「保存旋转」才写回仓库
function resetRefRot(){
    _refRot=0;
    var el=document.getElementById('refview-img');
    if(el)el.style.transform='';
    var act=document.getElementById('refview-actions');
    if(act)act.style.display='none';
}
function previewRotate(){
    if(!window._isAdmin){alert('需要管理员权限');return;}
    _refRot=(_refRot+90)%360;
    var el=document.getElementById('refview-img');
    if(_refRot===0)el.style.transform='';
    else el.style.transform='rotate('+_refRot+'deg) scale(0.85)';
    var act=document.getElementById('refview-actions');
    act.style.display=_refRot===0?'none':'flex';
    document.getElementById('refview-rot-label').textContent='当前预览旋转 '+_refRot+'°（未保存，可继续点旋转调整）';
}
async function saveRotate(){
    var d=_refView;
    if(!d||_refRot===0)return;
    if(!ghToken())return;
    var path=d.thumbnail;
    var img=new Image();
    img.crossOrigin='anonymous'; // 防画布污染（Vercel 缩略图走代理，需要 CORS）
    img.onload=async function(){
        try{
            var w=img.naturalWidth,h=img.naturalHeight;
            var rad=_refRot*Math.PI/180;
            var cos=Math.abs(Math.cos(rad)),sin=Math.abs(Math.sin(rad));
            var nw=Math.round(w*cos+h*sin),nh=Math.round(w*sin+h*cos);
            var c=document.createElement('canvas');
            c.width=nw;c.height=nh;
            var ctx=c.getContext('2d');
            ctx.translate(nw/2,nh/2);
            ctx.rotate(rad);
            ctx.drawImage(img,-w/2,-h/2);
            var isPng=(path||'').toLowerCase().indexOf('.png')>=0;
            var blob=await new Promise(function(res){c.toBlob(function(b){res(b);},isPng?'image/png':'image/jpeg',0.92);});
            if(!blob){alert('保存失败：画布读取失败（图片可能跨域受限），请刷新页面重试');return;}
            var content=await new Promise(function(res,rej){var fr=new FileReader();fr.onload=function(){res(String(fr.result).split(',')[1]);};fr.onerror=rej;fr.readAsDataURL(blob);});
            // Git Data API 提交路线：树快照一致，无 sha 竞态
            await ghWriteFileViaGit(path, content, 'Rotate image');
            // 旋转版本号写入索引，图墙用 ?v= 打破缓存，刷新不再变回旧图
            var rotTs=Date.now();
            var idx=await fetchIndex();
            var e=(idx.assets||[]).filter(function(a){return a.kind==='ref'&&a.subcat===d.subtag&&a.name===d.name;})[0];
            if(e)e.rot_ts=rotTs;
            idx.updated=new Date().toISOString();
            for(var rp=0;rp<3;rp++){
                var sha2='';
                try{var ex2=await ghAPI('GET','assets_index.json');sha2=ex2.sha||'';}catch(err2){}
                try{
                    await ghAPI('PUT','assets_index.json',{message:'Rotate version',content:b64u(JSON.stringify(idx)),sha:sha2});
                    break;
                }catch(e5){if(rp>=2)throw e5;await sleep(4000*(rp+1));}
            }
            d.rot_ts=rotTs;
            markIdxTs(idx.updated);
            resetRefRot();
            document.getElementById('refview-img').src=encUrl(path)+'?t='+Date.now();
            alert('✅ 旋转已保存（图墙约 1-2 分钟后更新）');
        }catch(e){alert('保存失败: '+(e&&e.message||e));}
    };
    img.onerror=function(){alert('图片加载失败，请刷新页面后重试');};
    img.src=encUrl(path)+'?t='+Date.now();
}
function openRefSearch(){
    document.getElementById('refsearch-modal').classList.add('show');
    renderRefSearchTags();
    renderRefSearchGrid();
}
function closeRefSearch(){document.getElementById('refsearch-modal').classList.remove('show');}
function renderRefSearchTags(){
    var h='';
    Object.keys(REF_TAGS).forEach(function(g){
        h+='<div class="rs-group"><div class="rs-title">'+he(g)+'</div>';
        REF_TAGS[g].forEach(function(v){
            var on=(_refSel[g]||[]).indexOf(v)>=0;
            h+='<button class="tag-chip'+(on?' on':'')+'" onclick="toggleRefTag(\''+he(g)+'\',\''+he(v)+'\',this)">'+he(v)+'</button>';
        });
        h+='</div>';
    });
    document.getElementById('rs-tags').innerHTML=h;
}
function toggleRefTag(g,v,btn){
    if(!_refSel[g])_refSel[g]=[];
    var i=_refSel[g].indexOf(v);
    if(i>=0)_refSel[g].splice(i,1);else _refSel[g].push(v);
    btn.classList.toggle('on');
    renderRefSearchGrid();
}
function refMatch(d){
    for(var g in _refSel){
        var sel=_refSel[g];
        if(sel&&sel.length){
            var tags=(d.tags&&d.tags[g])||[];
            var hit=sel.some(function(v){return tags.indexOf(v)>=0;});
            if(!hit)return false;
        }
    }
    return true;
}
function renderRefSearchGrid(){
    var list=DATA.filter(function(d){return d.is_asset&&d.kind==='ref'&&refMatch(d)&&refVisible(d);});
    renderRefGrid(document.getElementById('rs-grid'),list);
}
function openRefUpload(cat){
    if(window._isAdmin){
        _uploadMode='admin';
    }else{
        var p=prompt('请输入管理员密码，或访客上传密码：');
        if(p===window._adminPwd){
            window._isAdmin=true;localStorage.setItem('aty_admin','1');_uploadMode='admin';
        }else if(_guestCfg.enabled&&(_guestCfg.passwords||[]).indexOf(p)>=0){
            _uploadMode='guest';
        }else{
            if(p!==null)alert('密码错误');
            return;
        }
    }
    if(_uploadMode==='admin'&&!ghToken())return;
    _refCat=cat;
    document.getElementById('refup-title').textContent=cat+(_uploadMode==='guest'?'（访客模式）':'');
    [['refup-time','时间'],['refup-theme','主题'],['refup-season','季节'],['refup-emotion','情绪']].forEach(function(pair){
        document.getElementById(pair[0]).innerHTML='<option value="">（不选）</option>'+REF_TAGS[pair[1]].map(function(v){return '<option>'+v+'</option>';}).join('');
    });
    document.getElementById('refup-tone').innerHTML=REF_TAGS['色调'].map(function(v){return '<button class="refup-tone" onclick="this.classList.toggle(\'on\')">'+v+'</button>';}).join('');
    document.getElementById('refup-status').textContent='';
    document.getElementById('refup-log').innerHTML='';
    // 拖拽上传
    var fi=document.getElementById('refup-files');
    fi.value='';
    refupShowFiles();
    var drop=document.getElementById('refup-drop');
    drop.ondragover=function(e){e.preventDefault();drop.style.borderColor='var(--accent)';};
    drop.ondragleave=function(e){e.preventDefault();drop.style.borderColor='var(--border)';};
    drop.ondrop=function(e){
        e.preventDefault();
        drop.style.borderColor='var(--border)';
        var fs=[].slice.call(e.dataTransfer.files||[]).filter(function(f){return f.type.indexOf('image/')===0;});
        if(fs.length){
            try{
                var dt=new DataTransfer();
                fs.forEach(function(f){dt.items.add(f);});
                fi.files=dt.files;
                refupShowFiles();
            }catch(err){alert('拖拽失败，请用点击选择');}
        }
    };
    document.getElementById('refup-modal').classList.add('show');
}
function refupShowFiles(){
    var fs=[].slice.call(document.getElementById('refup-files').files||[]);
    var d=document.getElementById('refup-drop');
    d.innerHTML=fs.length?('✅ 已选 '+fs.length+' 张：'+fs.map(function(f){return he(f.name);}).join('、')):'📁 拖拽图片到这里，或点击选择（可多张）';
}
function closeRefUpload(){document.getElementById('refup-modal').classList.remove('show');}
// 上传后修改标签
var _refEdit=null;
function openRefEdit(name,subcat){
    if(!window._isAdmin){var p=prompt('请输入管理员密码：');if(p!==window._adminPwd){if(p!==null)alert('密码错误');return;}window._isAdmin=true;localStorage.setItem('aty_admin','1');}
    var d=DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.name===name&&x.subtag===subcat;})[0];
    if(!d)return;
    _refEdit=d;
    document.getElementById('refedit-title').textContent=d.name;
    [['refedit-time','时间'],['refedit-theme','主题'],['refedit-season','季节'],['refedit-emotion','情绪']].forEach(function(pair){
        var cur=(d.tags&&d.tags[pair[1]]&&d.tags[pair[1]][0])||'';
        document.getElementById(pair[0]).innerHTML='<option value="">（不选）</option>'+REF_TAGS[pair[1]].map(function(v){return '<option'+(v===cur?' selected':'')+'>'+v+'</option>';}).join('');
    });
    var tones=(d.tags&&d.tags['色调'])||[];
    document.getElementById('refedit-tone').innerHTML=REF_TAGS['色调'].map(function(v){return '<button class="refup-tone'+(tones.indexOf(v)>=0?' on':'')+'" onclick="this.classList.toggle(\'on\')">'+v+'</button>';}).join('');
    document.getElementById('refedit-source').value=d.source||'';
    document.getElementById('refedit-desc').value=d.description||'';
    document.getElementById('refedit-status').textContent='';
    document.getElementById('refedit-modal').classList.add('show');
}
function closeRefEdit(){document.getElementById('refedit-modal').classList.remove('show');}
async function saveRefEdit(){
    var d=_refEdit;
    if(!d||!ghToken())return;
    var tags={};
    [['refedit-time','时间'],['refedit-theme','主题'],['refedit-season','季节'],['refedit-emotion','情绪']].forEach(function(pair){
        var v=document.getElementById(pair[0]).value;
        if(v)tags[pair[1]]=[v];
    });
    var tones=[].slice.call(document.querySelectorAll('#refedit-tone .on')).map(function(b){return b.textContent;});
    if(tones.length)tags['色调']=tones;
    var source=(document.getElementById('refedit-source').value||'').trim();
    var desc=(document.getElementById('refedit-desc').value||'').trim();
    try{
        var idx=await fetchIndex();
        var e=(idx.assets||[]).filter(function(a){return a.kind==='ref'&&a.subcat===d.subtag&&a.name===d.name;})[0];
        if(e){e.tags=tags;e.source=source;e.description=desc;}
        var ts=new Date().toISOString();
        idx.updated=ts;
        var sha='';
        try{var ex=await ghAPI('GET','assets_index.json');sha=ex.sha||'';}catch(err){}
        await ghAPI('PUT','assets_index.json',{message:'Edit ref tags',content:b64u(JSON.stringify(idx)),sha:sha});
        markIdxTs(ts);
        d.tags=tags;d.source=source;d.description=desc;
        document.getElementById('refedit-status').textContent='已保存 ✅';
        openRefViewer(d.name,d.subtag);
        if(document.getElementById('ref-modal').classList.contains('show'))renderRefGrid(document.getElementById('ref-grid'),DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.subtag===_refCat;}));
        if(document.getElementById('refsearch-modal').classList.contains('show'))renderRefSearchGrid();
        setTimeout(closeRefEdit,600);
    }catch(err){
        document.getElementById('refedit-status').textContent='保存失败: '+(err&&err.message||err);
    }
}
async function doRefUpload(){
    if(_assetState.uploading)return;
    if(!window._isAdmin){var p=prompt('请输入管理员密码：');if(p!==window._adminPwd){if(p!==null)alert('密码错误');return;}window._isAdmin=true;localStorage.setItem('aty_admin','1');}
    if(!ghToken())return;
    var files=[].slice.call(document.getElementById('refup-files').files||[]);
    if(!files.length){alert('请选择图片');return;}
    var tags={};
    [['refup-time','时间'],['refup-theme','主题'],['refup-season','季节'],['refup-emotion','情绪']].forEach(function(pair){
        var v=document.getElementById(pair[0]).value;
        if(v)tags[pair[1]]=[v];
    });
    var tones=[].slice.call(document.querySelectorAll('#refup-tone .on')).map(function(b){return b.textContent;});
    if(tones.length)tags['色调']=tones;
    var source=(document.getElementById('refup-source').value||'').trim();
    // ── 访客模式：走 Vercel 服务端代写（密钥在云端），上传标记 pending 待审核 ──
    if(_uploadMode==='guest'){
        _assetState.uploading=true;
        document.getElementById('refup-status').textContent='上传中（访客模式）...';
        var glog=document.getElementById('refup-log');
        var gupLog=function(t,c){glog.innerHTML+='<div style="color:'+(c||'')+'">'+he(t)+'</div>';glog.scrollTop=glog.scrollHeight;};
        var upEntries=[];
        try{
            var seenH={};
            try{
                var idxPub=await fetch('./assets_index.json?t='+Date.now(),{cache:'no-store'}).then(function(r){return r.json();});
                (idxPub.assets||[]).forEach(function(a){if(a.kind==='ref'&&a.hash)seenH[a.hash]=1;});
            }catch(e){}
            for(var gi=0;gi<files.length;gi++){
                var gf=files[gi];
                var ghash=await fileHash(gf);
                if(ghash&&seenH[ghash]){gupLog('⏭ 跳过重复图片：'+gf.name);continue;}
                if(ghash)seenH[ghash]=1;
                var gfname=newImgName(gf.name,gi);
                gupLog('⬆ '+gf.name+' → '+gfname+'（访客模式，等待审核）');
                var gcontent=await readB64(gf);
                var gresp=await fetch('https://packages-puce.vercel.app/api/gupload',{
                    method:'POST',headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({password:_guestCfg.password,cat:_refCat,name:gfname,content:gcontent,tags:tags,source:source})
                });
                var grj=await gresp.json();
                if(!gresp.ok)throw Error(grj.error||('HTTP '+gresp.status));
                var gph='';
                try{gph=await makeThumbPreview(gf);}catch(e){}
                if(gph){try{localStorage.setItem('aty_ph_'+grj.path,gph);}catch(e){}}
                upEntries.push({kind:'ref',category:'参考图',subcat:_refCat,name:grj.name,description:'',thumbnail:grj.path,downloads:[grj.path],files:[gfname],size:gf.size,date:new Date().toISOString().slice(0,10),tags:tags,source:source,hash:ghash,ph_data:gph});
                gupLog('✅ '+gf.name+' 已上传');
            }
            if(!upEntries.length){document.getElementById('refup-status').textContent='没有新图片需要上传';_assetState.uploading=false;return;}
            markIdxTs(new Date().toISOString());
            savePendingRefs(pendingRefs().concat(upEntries));
            upEntries.forEach(function(e2){
                e2.is_asset=true;e2.software='参考图';e2.subtag=e2.subcat;e2.category='参考图';
                DATA=DATA.filter(function(d){return !(d.is_asset&&d.kind==='ref'&&d.name===e2.name&&d.subtag===e2.subcat);}).concat([e2]);
            });
            render();
            if(document.getElementById('ref-modal').classList.contains('show'))renderRefGrid(document.getElementById('ref-grid'),DATA.filter(function(d){return d.is_asset&&d.kind==='ref'&&d.subtag===_refCat&&refVisible(d);}));
            if(document.getElementById('refsearch-modal').classList.contains('show'))renderRefSearchGrid();
            document.getElementById('refup-status').textContent='上传完成！';
            document.getElementById('refup-files').value='';
            document.getElementById('refup-source').value='';
            alert('✅ 上传成功！共 '+upEntries.length+' 张图片已添加。\n（网站约 1-2 分钟后显示）');
        }catch(e){
            gupLog('❌ 失败: '+(e&&e.message||e),'#e05555');
            document.getElementById('refup-status').textContent='上传失败，见下方日志';
        }
        _assetState.uploading=false;
        return;
    }
    _assetState.uploading=true;
    document.getElementById('refup-status').textContent='上传中...';
    var logEl=document.getElementById('refup-log');
    var upLog2=function(t,c){logEl.innerHTML+='<div style="color:'+(c||'')+'">'+he(t)+'</div>';logEl.scrollTop=logEl.scrollHeight;};
    var newEntries=[],stems=[],skipped=0;
    try{
        var idx=null;
        try{idx=await fetchIndex();}catch(e){idx={assets:[]};}
        if(!idx||!idx.assets)idx={assets:[]};
        // 重复检测：用内容指纹（SHA-256），已有相同图片的跳过
        var seenHashes={};
        (idx.assets||[]).forEach(function(a){if(a.kind==='ref'&&a.hash)seenHashes[a.hash]=1;});
        for(var i=0;i<files.length;i++){
            var f=files[i];
            var h=await fileHash(f);
            if(h&&seenHashes[h]){
                upLog2('⏭ 跳过重复图片：'+f.name+'（内容与已有图片相同）');
                skipped++;
                continue;
            }
            if(h)seenHashes[h]=1;
            var fname=newImgName(f.name, i); // 统一安全命名：字母+数字，杜绝特殊字符问题
            upLog2('⬆ '+f.name+' → '+fname+' ('+(f.size/1024/1024).toFixed(1)+'MB)');
            var path='assets/refs/'+_refCat+'/'+fname;
            var sha='';
            try{var ex=await ghAPI('GET',path);sha=ex.sha||'';}catch(e){}
            var body={message:'Upload ref '+fname,content:await readB64(f)};if(sha)body.sha=sha;
            await ghAPI('PUT',path,body);
            var stem=fname.replace(/\.[^.]+$/,'');
            stems.push(stem);
            var entry={kind:'ref',category:'参考图',subcat:_refCat,name:stem,description:'',thumbnail:path,downloads:[path],files:[fname],size:f.size,date:new Date().toISOString().slice(0,10),tags:tags,source:source,hash:h};
            // 本地模糊预览占位（存入 localStorage，图墙立即可见）
            var ph='';
            try{ph=await makeThumbPreview(f);}catch(e){}
            entry.ph_data=ph;
            if(ph){
                try{localStorage.setItem('aty_ph_'+path,ph);}catch(e){}
                upLog2('🖼 占位图已生成并保存本地');
            }else{
                upLog2('⚠ 占位图生成失败（此格式浏览器无法预览）');
            }
            idx.assets=idx.assets.filter(function(a){return !(a.kind==='ref'&&a.subcat===_refCat&&a.name===stem);});
            var idxEntry=JSON.parse(JSON.stringify(entry));
            delete idxEntry.ph_data; // 占位图只存本地，不进线上索引
            idx.assets.unshift(idxEntry);
            newEntries.push(entry);
            upLog2('✅ '+f.name+' 已上传');
        }
        var ts=new Date().toISOString();
        idx.updated=ts;
        document.getElementById('refup-status').textContent='正在写入索引...';
        // 索引写入带重试（并发写入 409 常见）
        for(var rp=0;rp<3;rp++){
            var sha2='';
            try{var ex2=await ghAPI('GET','assets_index.json');sha2=ex2.sha||'';}catch(e){}
            try{
                await ghAPI('PUT','assets_index.json',{message:'Update assets index',content:b64u(JSON.stringify(idx)),sha:sha2});
                break;
            }catch(e4){
                if(rp>=2)throw e4;
                await sleep(4000*(rp+1));
            }
        }
        markIdxTs(ts);
        var dlist=await fetchDeleted();
        dlist=dlist.filter(function(t){return !(t.subcat===_refCat&&stems.indexOf(t.name)>=0);});
        await putDeleted(dlist);
        // 新条目存本地待发布列表（刷新后先显示本地占位版本）
        savePendingRefs(pendingRefs().concat(newEntries));
        upLog2('💾 已保存本地待发布记录（'+pendingRefs().length+' 条），刷新后占位图仍会显示');
        document.getElementById('refup-status').textContent='上传完成！';
        document.getElementById('refup-files').value='';
        document.getElementById('refup-source').value='';
        var msg='✅ 上传并添加索引完成！\n共 '+newEntries.length+' 张图片已保存到「'+_refCat+'」板块。';
        if(skipped)msg+='\n⏭ 跳过 '+skipped+' 张重复图片。';
        msg+='\n（网站约 1-2 分钟后显示新图片）';
        alert(msg);
        newEntries.forEach(function(e2){
            e2.is_asset=true;e2.software='参考图';e2.subtag=e2.subcat;e2.category='参考图';
            DATA=DATA.filter(function(d){return !(d.is_asset&&d.kind==='ref'&&d.name===e2.name&&d.subtag===e2.subcat);}).concat([e2]);
        });
        render();
        if(document.getElementById('ref-modal').classList.contains('show'))renderRefGrid(document.getElementById('ref-grid'),DATA.filter(function(d){return d.is_asset&&d.kind==='ref'&&d.subtag===_refCat;}));
        if(document.getElementById('refsearch-modal').classList.contains('show'))renderRefSearchGrid();
        refreshAssets();
    }catch(e){
        upLog2('❌ 失败: '+(e&&e.message||e),'#e05555');
        document.getElementById('refup-status').textContent='上传失败，见下方日志';
    }
    _assetState.uploading=false;
}
if(!window._adminPwd)window._adminPwd='ty190219';
window._isAdmin=window._isAdmin||localStorage.getItem('aty_admin')==='1';
function ghToken(){
    var t=localStorage.getItem('aty_ghToken');
    if(!t){t=prompt('首次上传需要 GitHub Token（仅保存在本机浏览器）：');if(t)localStorage.setItem('aty_ghToken',t);}
    return t||'';
}
function encPath(p){return p.split('/').map(encodeURIComponent).join('/');}
function encUrl(p){return p.split('/').map(encodeURIComponent).join('/');}
function safeName(n){
    n=n.replace(/[#?%()]/g,'_');  // GitHub Pages 不服务含这些字符的文件名
    n=n.replace(/^_+/,'');        // 下划线开头会被 Jekyll 当 partial 排除
    if(!n)n='img';
    return n;
}
function newImgName(orig, i){
    // 参考图统一用「字母+数字」安全命名：img_时间戳_序号.ext
    var ext=(orig.split('.').pop()||'png').toLowerCase();
    return 'img_'+Date.now().toString(36)+(i?'_'+i:'')+'.'+ext;
}
async function fileHash(file){
    try{
        var buf=await file.arrayBuffer();
        var h=await crypto.subtle.digest('SHA-256', buf);
        var arr=Array.from(new Uint8Array(h));
        return arr.map(function(b){return b.toString(16).padStart(2,'0');}).join('');
    }catch(e){return '';}
}
function ghRaw(method,url,body){
    return fetch(url,{
        method:method,
        headers:{Authorization:'Bearer '+ghToken(),Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'},
        body:body?JSON.stringify(body):undefined,
        cache:'no-store'
    }).then(function(r){return r.json().then(function(j){if(!r.ok)throw Error(j.message||('HTTP '+r.status));return j;});});
}
// 用 Git Data API 写文件（基于树快照，无需单文件 sha，避免 contents API 的 sha 竞态/缓存问题）
async function ghWriteFileViaGit(path, contentB64, message){
    var repo='https://api.github.com/repos/Tystarry/aty-tools';
    var tree=await ghRaw('GET',repo+'/git/trees/main?recursive=1&t='+Date.now());
    var blob=await ghRaw('POST',repo+'/git/blobs',{content:contentB64,encoding:'base64'});
    var nt=await ghRaw('POST',repo+'/git/trees',{base_tree:tree.sha,tree:[{path:path,mode:'100644',type:'blob',sha:blob.sha}]});
    var head=await ghRaw('GET',repo+'/git/refs/heads/main');
    var commit=await ghRaw('POST',repo+'/git/commits',{message:message,tree:nt.sha,parents:[head.object.sha]});
    await ghRaw('PATCH',repo+'/git/refs/heads/main',{sha:commit.sha,force:false});
    return commit.sha;
}
function ghAPI(method,path,body){
    return fetch('https://api.github.com/repos/Tystarry/aty-tools/contents/'+encPath(path),{
        method:method,
        headers:{Authorization:'Bearer '+ghToken(),Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'},
        body:body?JSON.stringify(body):undefined
    }).then(function(r){return r.json().then(function(j){if(!r.ok)throw Error(j.message||('HTTP '+r.status));return j;});});
}
function fetchIndex(){
    // 走 API 读索引（raw 有 CDN 缓存，删除/上传竞态会读到旧版本）
    // 注意：atob 得到的是字节串，必须用 TextDecoder 按 UTF-8 解码，否则中文路径会双重编码损坏
    return ghAPI('GET','assets_index.json').then(function(meta){
        var bin=atob(meta.content);
        var bytes=new Uint8Array(bin.length);
        for(var i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);
        return JSON.parse(new TextDecoder('utf-8').decode(bytes));
    });
}
function markIdxTs(ts){localStorage.setItem('aty_idx_ts',ts);}
// 刚上传还未发布的条目存本地，刷新后先显示（含模糊占位图），线上索引追上后自动替换
function pendingRefs(){try{return JSON.parse(localStorage.getItem('aty_pending_refs')||'[]');}catch(e){return [];}}
function savePendingRefs(list){try{localStorage.setItem('aty_pending_refs',JSON.stringify(list));}catch(e){}}
function mergePendingRefs(){
    var pl=pendingRefs();
    if(!pl.length)return;
    pl.forEach(function(e){
        e.is_asset=true;e.software='参考图';e.subtag=e.subcat;e.category='参考图';
        e.downloads=e.downloads||[e.thumbnail];
        if(e.ph_data){try{localStorage.setItem('aty_ph_'+e.thumbnail,e.ph_data);}catch(err){}}
        if(!DATA.some(function(d){return d.is_asset&&d.kind==='ref'&&d.name===e.name&&d.subtag===e.subcat;})){
            DATA.push(e);
        }
    });
}
// 墓碑（网页删除清单）存独立文件，素材索引本身保持干净
async function fetchDeleted(){
    try{
        var r=await fetch('https://raw.githubusercontent.com/Tystarry/aty-tools/main/deleted_assets.json?t='+Date.now(),{cache:'no-store'});
        if(!r.ok)throw Error();
        return (await r.json()).deleted||[];
    }catch(e){return [];}
}
async function putDeleted(list){
    var sha='';
    try{var ex=await ghAPI('GET','deleted_assets.json');sha=ex.sha||'';}catch(e){}
    await ghAPI('PUT','deleted_assets.json',{message:'Update deleted list',content:b64u(JSON.stringify({deleted:list})),sha:sha});
}
function refreshAssets(cb){
    var done=cb||function(){};
    var url=window.__MODE__==='vercel'?'/api/assets':'./assets_index.json';
    fetch(url+'?t='+Date.now(),{cache:'no-store'}).then(function(r){if(!r.ok)throw Error();return r.json();}).then(function(j){
        // CDN 旧缓存保护：本机刚改过索引（删除/上传）时，忽略更旧的缓存版本，防止已删素材复活
        var ts=localStorage.getItem('aty_idx_ts')||'';
        if(ts&&j.updated&&j.updated<ts){done();return;}
        localStorage.removeItem('aty_idx_ts');
        // 线上索引已包含的待发布条目：从本地列表移除（自动替换为线上版本）
        // 索引里还没有的（发布竞态/被部署覆盖）继续保留本地版本显示
        var liveMap={};
        (j.assets||[]).forEach(function(a){if(a.kind==='ref')liveMap[a.subcat+'|'+a.name]=1;});
        var stillPending=pendingRefs().filter(function(e){return !liveMap[e.subcat+'|'+e.name];});
        savePendingRefs(stillPending);
        if(j&&j.assets&&j.assets.length){
            var merged=DATA.filter(function(d){return !d.is_asset;});
            j.assets.forEach(function(a){
                delete a.ph_data; // 线上索引不应携带本地占位图数据
                if(a.kind==='ref'){
                    a.is_asset=true;a.software='参考图';a.subtag=a.subcat||'';a.category='参考图';
                }else{
                    a.is_asset=true;a.software='素材';a.subtag=a.category;a.category='素材';
                }
                a.downloads=a.downloads||(a.download?[a.download]:[]);
                merged.push(a);
            });
            // 待发布条目追加回显示（占位图 + 发布中角标）
            stillPending.forEach(function(e){
                e.is_asset=true;e.software='参考图';e.subtag=e.subcat;e.category='参考图';
                e.downloads=e.downloads||[e.thumbnail];
                if(e.ph_data){try{localStorage.setItem('aty_ph_'+e.thumbnail,e.ph_data);}catch(err){}}
                if(!merged.some(function(d){return d.is_asset&&d.kind==='ref'&&d.name===e.name&&d.subtag===e.subcat;})){
                    merged.push(e);
                }
            });
            DATA=merged;
            render();
            if(document.getElementById('asset-modal').classList.contains('show'))renderAssetBrowser();
            if(document.getElementById('ref-modal').classList.contains('show')){
                var rel=document.getElementById('ref-grid');
                if(_refPendingOnly)renderRefGrid(rel,DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.status==='pending';}));
                else renderRefGrid(rel,DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.subtag===_refCat&&refVisible(x);}));
            }
            if(document.getElementById('refsearch-modal').classList.contains('show'))renderRefSearchGrid();
        }
        done();
    }).catch(function(){done();});
}
function openUpload(cat){
    if(!window._isAdmin){
        var p=prompt('请输入管理员密码：');
        if(p!==window._adminPwd){if(p!==null)alert('密码错误');return;}
        window._isAdmin=true;localStorage.setItem('aty_admin','1');
        var ab=document.getElementById('admin-btn');if(ab)ab.textContent='🔓';
    }
    if(!ghToken())return;
    var preset=cat||fSub||'';
    var sel=document.getElementById('up-cat');
    sel.innerHTML='';
    ASSET_CATS.forEach(function(c){var o=document.createElement('option');o.value=c;o.textContent=c;if(c===preset)o.selected=true;sel.appendChild(o);});
    upThumbRowToggle();
    document.getElementById('up-status').textContent='';
    document.getElementById('up-log').innerHTML='';
    // 拖拽上传：缩略图 + 素材文件
    var ti=document.getElementById('up-thumb'),fi2=document.getElementById('up-files');
    ti.value='';fi2.value='';
    upThumbShow();upFilesShow();
    [['upthumb-drop',ti,false],['upfiles-drop',fi2,true]].forEach(function(cfg){
        var zone=document.getElementById(cfg[0]),input=cfg[1],multi=cfg[2];
        zone.ondragover=function(e){e.preventDefault();zone.style.borderColor='var(--accent)';};
        zone.ondragleave=function(e){e.preventDefault();zone.style.borderColor='var(--border)';};
        zone.ondrop=function(e){
            e.preventDefault();
            zone.style.borderColor='var(--border)';
            var fs=[].slice.call(e.dataTransfer.files||[]);
            if(!multi)fs=fs.filter(function(f){return f.type.indexOf('image/')===0;}); // 只有缩略图区限定图片
            if(!fs.length)return;
            try{
                var dt=new DataTransfer();
                fs.forEach(function(f){dt.items.add(f);});
                input.files=dt.files;
                if(multi)upFilesShow();else upThumbShow();
            }catch(err){alert('拖拽失败，请用点击选择');}
        };
    });
    document.getElementById('upload-modal').classList.add('show');
}
function upThumbShow(){
    var f=document.getElementById('up-thumb').files[0];
    document.getElementById('upthumb-drop').innerHTML=f?('✅ 缩略图：'+he(f.name)):'🖼 拖拽图片到这里 / 点击选择 / Ctrl+V 粘贴';
}
function canAutoThumb(f){
    var n=(f.name||'').toLowerCase();
    if(f.type&&f.type.indexOf('image/')===0)return true;
    return /\.(exr|hdr|tif|tiff)$/.test(n);
}
function upThumbRowToggle(){
    var cat=document.getElementById('up-cat').value;
    var autoT=AUTO_THUMB_CATS.indexOf(cat)>=0;
    var needManual=false;
    if(autoT){
        var fs=[].slice.call(document.getElementById('up-files').files||[]);
        needManual=fs.some(function(f){return !canAutoThumb(f);});
    }
    var show=!autoT||needManual;
    document.getElementById('up-thumb-label').style.display=show?'':'none';
    document.getElementById('up-thumb-row').style.display=show?'':'none';
    var hint=document.getElementById('up-hint');
    if(hint){
        if(autoT&&needManual)hint.innerHTML='检测到 zip 压缩包等无法自动生成缩略图的文件，请上传缩略图（图片文件即时生成；EXR/HDR 由云端自动生成）。单个文件 ≤ 90MB';
        else if(autoT)hint.innerHTML='✅ 缩略图全自动生成：图片文件即时生成；EXR/HDR 上传后约 1-2 分钟由云端自动生成。可多选文件；单个文件 ≤ 90MB（GitHub 上限 100MB）';
        else hint.innerHTML='可多选文件；单个文件 ≤ 90MB（GitHub 上限 100MB）。超大文件（HDRI 等）建议本地素材库方式';
    }
}
function makeThumbFile(file,w,h){
    return new Promise(function(res,rej){
        var img=new Image();
        var url=URL.createObjectURL(file);
        img.onload=function(){
            try{
                var c=document.createElement('canvas');
                c.width=w;c.height=h;
                var ctx=c.getContext('2d');
                var scale=Math.max(w/img.width,h/img.height); // cover 裁切
                var sw=w/scale,sh=h/scale,sx=(img.width-sw)/2,sy=(img.height-sh)/2;
                ctx.drawImage(img,sx,sy,sw,sh,0,0,w,h);
                URL.revokeObjectURL(url);
                c.toBlob(function(b){if(b)res(b);else rej(Error('thumb fail'));},'image/png');
            }catch(e){URL.revokeObjectURL(url);rej(e);}
        };
        img.onerror=function(){URL.revokeObjectURL(url);rej(Error('not image'));};
        img.src=url;
    });
}
function upFilesShow(){
    var fs=[].slice.call(document.getElementById('up-files').files||[]);
    document.getElementById('upfiles-drop').innerHTML=fs.length?('✅ 已选 '+fs.length+' 个：'+fs.map(function(f){return he(f.name);}).join('、')):'📦 拖拽文件到这里，或点击选择（可多选）';
    // 素材名自动识别：取第一个文件的文件名（去扩展名），仅当名字为空时填充
    var nm=document.getElementById('up-name');
    if(fs.length&&(!nm.value||!nm.value.trim())){
        nm.value=fs[0].name.replace(/\.[^.]+$/,'');
    }
    upThumbRowToggle();
}
// Ctrl+V 粘贴图片作为缩略图（上传弹窗打开且显示缩略图栏时）
document.addEventListener('paste',function(e){
    var um=document.getElementById('upload-modal');
    if(!um.classList.contains('show'))return;
    if(document.getElementById('up-thumb-row').style.display==='none')return;
    var items=(e.clipboardData&&e.clipboardData.items)||[];
    for(var i=0;i<items.length;i++){
        if(items[i].type.indexOf('image/')===0){
            var f=items[i].getAsFile();
            if(f){
                try{
                    var dt=new DataTransfer();dt.items.add(f);
                    document.getElementById('up-thumb').files=dt.files;
                    upThumbShow();
                    e.preventDefault();
                }catch(err){}
            }
            break;
        }
    }
});
function closeUpload(){document.getElementById('upload-modal').classList.remove('show');}
function upLog(t,c){var el=document.getElementById('up-log');el.innerHTML+='<div style="color:'+(c||'')+'">'+he(t)+'</div>';el.scrollTop=el.scrollHeight;}
function readB64(file){return new Promise(function(res,rej){var r=new FileReader();r.onload=function(){res(String(r.result).split(',')[1]);};r.onerror=rej;r.readAsDataURL(file);});}
function b64u(s){return btoa(unescape(encodeURIComponent(s)));}
async function doUpload(){
    if(_assetState.uploading)return;
    var name=(document.getElementById('up-name').value||'').trim();
    var cat=document.getElementById('up-cat').value;
    var desc=(document.getElementById('up-desc').value||'').trim();
    // 素材名自动识别：为空时取第一个文件名（去扩展名）
    if(!name&&files.length){
        name=files[0].name.replace(/\.[^.]+$/,'');
        document.getElementById('up-name').value=name;
    }
    if(!name){alert('请填写素材名');return;}
    if(!window._isAdmin){var p=prompt('请输入管理员密码：');if(p!==window._adminPwd){if(p!==null)alert('密码错误');return;}window._isAdmin=true;localStorage.setItem('aty_admin','1');}
    if(!ghToken())return;
    var files=[].slice.call(document.getElementById('up-files').files||[]);
    var thumb=document.getElementById('up-thumb').files[0];
    if(!files.length&&!thumb){alert('请选择素材文件或缩略图');return;}
    // 自动缩略图分类：纹理/合成素材/HDRI 不上传缩略图（除非有压缩包需手动缩略图）
    if(AUTO_THUMB_CATS.indexOf(cat)>=0&&!thumb){
        for(var tfi=0;tfi<files.length;tfi++){
            if(files[tfi].type.indexOf('image/')===0){
                try{
                    upLog('🖼 自动生成缩略图...');
                    var tw=cat==='HDRI'?512:256,th=cat==='HDRI'?256:256;
                    var blob=await makeThumbFile(files[tfi],tw,th);
                    thumb=new File([blob],'缩略图.png',{type:'image/png'});
                    upLog('✅ 缩略图已自动生成');
                }catch(e){}
                break;
            }
        }
        if(!thumb)upLog('ℹ 该格式无法在浏览器生成缩略图，稍后自动补生成');
    }
    var total=files.concat(thumb?[thumb]:[]);
    var big=total.filter(function(f){return f.size>90*1024*1024;});
    if(big.length){alert('文件 '+big.map(function(f){return f.name;}).join(', ')+' 超过 90MB（GitHub 单文件上限 100MB）。\n超大文件放本地素材库会自动压缩后上传：放到 D:/zcy/ai_ty/素材库/ 对应分类下，然后说「更新素材库」');return;}
    _assetState.uploading=true;
    document.getElementById('up-status').textContent='上传中...';
    var base='assets/'+cat+'/'+name;
    var entry={category:cat,name:name,description:desc,thumbnail:'',downloads:[],files:[],size:0,date:new Date().toISOString().slice(0,10)};
    try{
        for(var i=0;i<total.length;i++){
            var f=total[i];
            var fname=safeName(f.name); // 净化文件名：# ? % 会破坏 URL
            upLog('⬆ '+f.name+' ('+(f.size/1024/1024).toFixed(1)+'MB)');
            var content=await readB64(f);
            var path=base+'/'+fname;
            var sha='';
            try{var ex=await ghAPI('GET',path);sha=ex.sha||'';}catch(e){}
            var body={message:'Upload asset '+name,content:content};if(sha)body.sha=sha;
            await ghAPI('PUT',path,body);
            entry.size+=f.size;entry.files.push(fname);
            if(f===thumb)entry.thumbnail='assets/'+cat+'/'+name+'/'+fname;
            else entry.downloads.push('assets/'+cat+'/'+name+'/'+fname);
            upLog('✅ '+f.name+' 已上传');
        }
        upLog('✏ 更新素材索引...');
        var idx=null;
        try{idx=await fetchIndex();}catch(e){idx={assets:[]};}
        if(!idx||!idx.assets)idx={assets:[]};
        idx.assets=idx.assets.filter(function(a){return !(a.category===cat&&a.name===name);});
        idx.assets.unshift(entry);
        var ts=new Date().toISOString();
        idx.updated=ts;
        upLog('✏ 正在写入索引...');
        for(var rp=0;rp<3;rp++){
            var sha2='';
            try{var ex2=await ghAPI('GET','assets_index.json');sha2=ex2.sha||'';}catch(e){}
            try{
                await ghAPI('PUT','assets_index.json',{message:'Update assets index',content:b64u(JSON.stringify(idx)),sha:sha2});
                break;
            }catch(e4){
                if(rp>=2)throw e4;
                await sleep(4000*(rp+1));
            }
        }
        markIdxTs(ts);
        var dlist=await fetchDeleted();
        dlist=dlist.filter(function(t){return !(t.subcat===cat&&t.name===name);});
        await putDeleted(dlist);
        upLog('✅ 索引已更新');
        alert('✅ 上传并添加索引完成！\n（网站约 1-2 分钟后显示新素材）');
        document.getElementById('up-status').textContent='上传完成！新素材约 1-2 分钟后在网站可见';
        document.getElementById('up-name').value='';document.getElementById('up-desc').value='';
        document.getElementById('up-files').value='';document.getElementById('up-thumb').value='';
        upFilesShow();upThumbShow();
        var e2=JSON.parse(JSON.stringify(entry));
        e2.is_asset=true;e2.software='素材';e2.subtag=e2.category;e2.category='素材';
        DATA=DATA.filter(function(d){return !(d.is_asset&&d.name===name&&d.subtag===cat);}).concat([e2]);
        render();
        if(document.getElementById('asset-modal').classList.contains('show'))renderAssetBrowser();
        refreshAssets();
    }catch(e){
        upLog('❌ 失败: '+(e&&e.message||e),'#e05555');
        document.getElementById('up-status').textContent='上传失败，见下方日志';
    }
    _assetState.uploading=false;
}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}
async function ghDeleteRetry(path,name){
    var lastErr='';
    for(var a=0;a<3;a++){
        try{
            var ex=await ghAPI('GET',path);
            await ghAPI('DELETE',path,{message:'Delete asset '+name,sha:ex.sha});
            return '';
        }catch(e){
            lastErr=(e&&e.message)||e;
            var s=String(lastErr);
            if(a<2&&(s.indexOf('401')>=0||s.indexOf('409')>=0||s.indexOf('EOF')>=0)){
                await sleep(8000*(a+1));
            }else{break;}
        }
    }
    return lastErr;
}
async function delAsset(name,cat,ev){
    if(ev)ev.stopPropagation();
    if(!window._isAdmin){alert('需要管理员权限');return;}
    if(!confirm('确定删除素材「'+name+'」及其全部文件？'))return;
    try{
        var idx=await fetchIndex();
        var entry=(idx.assets||[]).filter(function(a){return (a.category===cat||a.subcat===cat)&&a.name===name;})[0];
        if(!entry){alert('素材不在索引中');return;}
        var paths=[];
        (entry.downloads||[]).concat(entry.thumbnail?[entry.thumbnail]:[]).forEach(function(p){if(paths.indexOf(p)<0)paths.push(p);});
        var errs=[];
        for(var i=0;i<paths.length;i++){
            var e=await ghDeleteRetry(paths[i],name);
            if(e)errs.push(paths[i]+': '+e);
            try{localStorage.removeItem('aty_ph_'+paths[i]);}catch(e2){}
        }
        idx.assets=idx.assets.filter(function(a){return !((a.category===cat||a.subcat===cat)&&a.name===name);});
        var ts=new Date().toISOString();
        idx.updated=ts;
        // 索引更新加重试（409 表示 sha 过期，重新取）
        for(var a2=0;a2<3;a2++){
            var sha='';
            try{var ex2=await ghAPI('GET','assets_index.json');sha=ex2.sha||'';}catch(e2){}
            try{
                await ghAPI('PUT','assets_index.json',{message:'Update assets index',content:b64u(JSON.stringify(idx)),sha:sha});
                break;
            }catch(e3){
                if(a2>=2)throw e3;
                await sleep(5000*(a2+1));
            }
        }
        markIdxTs(ts);
        // 墓碑写入独立文件，防止本地重新生成时复活已删素材
        var dlist=await fetchDeleted();
        dlist=dlist.filter(function(t){return !(t.subcat===cat&&t.name===name);});
        dlist.push({subcat:cat,name:name});
        await putDeleted(dlist);
        savePendingRefs(pendingRefs().filter(function(e){return !(e.subcat===cat&&e.name===name);}));
        DATA=DATA.filter(function(d){return !(d.is_asset&&d.name===name&&d.subtag===cat);});
        render();
        if(document.getElementById('asset-modal').classList.contains('show'))renderAssetBrowser();
        if(document.getElementById('ref-modal').classList.contains('show'))renderRefGrid(document.getElementById('ref-grid'),DATA.filter(function(x){return x.is_asset&&x.kind==='ref'&&x.subtag===_refCat;}));
        if(document.getElementById('refsearch-modal').classList.contains('show'))renderRefSearchGrid();
        refreshAssets();
        if(errs.length)alert('已从列表删除，但 '+errs.length+' 个文件删除失败（稍后自动清理或重试）：\n'+errs.join('\n'));
        else alert('已删除');
    }catch(e){alert('删除失败: '+(e&&e.message||e));}
}
renderMsgs();
showLogLatest();
mergePendingRefs();
refreshAssets();
render();
</script>
"""


if __name__ == '__main__':
    import sys
    # --lite: 去掉留言板，仅保留日志（用于 GitHub Pages）
    LITE_MODE = '--lite' in sys.argv
    # --vercel: Vercel 模式 — 素材卡片展示但禁用下载
    VERCEL_MODE = '--vercel' in sys.argv
    main()
