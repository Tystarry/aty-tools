import re

# 从 generate_dashboard.py 提取 BS_TEMPLATE 的 Python 内容
with open('d:/zcy/ai_ty/packages/generate_dashboard.py', 'r', encoding='utf-8') as f:
    gen = f.read()

# 提取模板字符串拼接
start = gen.find("var BS_TEMPLATE='")
end = gen.find("print(\"\\\\n=== COPY JSON BELOW")
if start < 0 or end < 0:
    print('Not found in generator')
    exit(1)

# 提取拼接字符串
seg = gen[start:end]
# 解析出最终字符串
parts = re.findall(r"'((?:[^'\\]|\\.)*)'\s*\+", seg, re.DOTALL)
py_script = ''.join(parts)
py_script = py_script.replace('\\n', '\n')

# 写独立 Python 脚本内容到 BS诊断工具.html 的 var BS
with open('d:/zcy/ai_ty/packages/BS诊断工具.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 找到旧 var BS 块并替换
old_start = html.find("var BS='")
old_end = html.find("function copyBSScript()")
if old_start < 0 or old_end < 0:
    print('Old BS not found in standalone HTML')
    exit(1)

# 构建新的 JS 字符串
lines = []
for line in py_script.split('\n'):
    if not line:
        lines.append("'\\n'")
    else:
        lines.append("'" + line.replace('\\', '\\\\').replace("'", "\\'") + "\\n'")
new_bs = "var BS=" + '+\n'.join(lines) + ';\n\n'

html = html[:old_start] + new_bs + html[old_end:]

with open('d:/zcy/ai_ty/packages/BS诊断工具.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Standalone HTML updated')
