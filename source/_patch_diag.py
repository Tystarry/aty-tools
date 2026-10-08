import re

with open('d:/zcy/ai_ty/packages/generate_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the genDiag function's table section
# Search for the table header pattern
old = '''h+='<table id="diag-table"'''

# Find the genDiag function body
gen_start = content.find("function genDiag(){")
gen_end = content.find("function exportPDF(){")
if gen_start < 0 or gen_end < 0:
    print("Can't find genDiag")
    exit(1)

gen_body = content[gen_start:gen_end]

# Replace the summary line
old_summary = "<span style=\"color:#e05555\">🧊 <b>'+(s.not_frozen||0)+'</b> 未冻结</span>'\n+'<span style=\"color:#e05555\">🏗 <b>'+(s.hierarchy_mismatch||0)+'</b> 层级不符</span>'"
new_summary = "<span style=\"color:#e05555\">🧊 <b>'+(s.not_frozen||0)+'</b> 未冻结</span>'\n+'<span style=\"color:#e05555\">🏗 <b>'+(s.hierarchy_mismatch||0)+'</b> 层级</span>'\n+'<span style=\"color:#e05555\">🔀 <b>'+(s.order_mismatch||0)+'</b> 顺序</span>'"
if old_summary in content:
    content = content.replace(old_summary, new_summary)
    print("Summary updated")
else:
    print("Summary not found, trying alt...")

# Replace the table and iteration section
old_table = '''if(data.pairs&&data.pairs.length){
            h+='<table id="diag-table" class="diag-table" style="font-size:12px"><thead><tr style="background:var(--border)"><th style="padding:6px 10px;text-align:left">Mesh</th><th style="padding:6px 10px;text-align:right">mod顶点</th><th style="padding:6px 10px;text-align:right">ABC顶点</th><th style="padding:6px 10px;text-align:left">状态</th><th style="padding:6px 10px;text-align:right">差</th><th style="padding:6px 10px;text-align:left">冻结</th><th style="padding:6px 10px;text-align:left">层级</th></tr></thead><tbody>';'''

if old_table in content:
    new_table = '''if(data.pairs&&data.pairs.length){
            var branches={},ci=0;
            data.pairs.forEach(function(p){var b=p.branch.split('_')[0]||'0';if(!branches[b])branches[b]=ci++;});
            var MC=['#b8a99a','#9cadb0','#c0a8b0','#a0b0a0','#c0a098','#8ab0a8','#b0a0c0','#b0b098'];
            h+='<table id="diag-table" class="diag-table" style="font-size:12px"><thead><tr style="background:var(--border)"><th style="padding:6px 10px;text-align:left">Mesh</th><th style="padding:6px 10px;text-align:right">mod顶点</th><th style="padding:6px 10px;text-align:right">ABC顶点</th><th style="padding:6px 10px;text-align:left">状态</th><th style="padding:6px 10px;text-align:right">差</th><th style="padding:6px 10px;text-align:left">冻结</th><th style="padding:6px 10px;text-align:left">层级</th><th style="padding:6px 10px;text-align:left">顺序</th></tr></thead><tbody>';'''
    content = content.replace(old_table, new_table)
    print("Table header updated")
else:
    print("Table header not found")
    # Try to find what's actually there
    idx = content.find('diag-table')
    if idx >= 0:
        print("Found diag-table at", idx)
        print(repr(content[idx:idx+300]))

# Update per-row rendering
old_row = '''var hm=p.hierarchy_match!==false;
                var hierTxt=hm?'✅ 一致':'❌ mod:'+he(p.mod_hierarchy||'')+' / abc:'+he(p.abc_hierarchy||'');
                var hierStyle=!hm?'color:#e05555;font-weight:600':'';
                h+='<tr style="'+rowStyle+'"><td style="'+nameStyle+';padding:5px 10px">'+he(p.name)+'</td><td style="padding:5px 10px;text-align:right">'+p.mod_vtx+'</td><td style="padding:5px 10px;text-align:right">'+p.abc_vtx+'</td><td style="'+stColor+';padding:5px 10px">'+st+'</td><td style="padding:5px 10px;text-align:right;'+(diff>0?'color:#e05555;font-weight:600':'')+'">'+(diff>0?diff:'-')+'</td><td style="'+(frozen?'':'color:#e05555;font-weight:600')+'">'+frozenTxt+'</td><td style="'+(hm?'':'color:#e05555;font-weight:600')+';font-size:11px">'+hierTxt+'</td></tr>';'''

new_row = '''var hm=p.hierarchy_match!==false;
                var hierTxt=hm?'✅':'❌ mod:'+he(p.mod_chain||'')+' / abc:'+he(p.abc_chain||'');
                var om=p.order_match!==false;
                var orderTxt=om?'✅':'❌';
                var branchRoot=p.branch.split('_')[0]||'0';
                var bci=branches[branchRoot]||0;
                var indent='&nbsp;&nbsp;'.repeat((p.depth||0)-1);
                var col=MC[bci%MC.length];
                h+='<tr style="'+rowStyle+'"><td style="'+nameStyle+';padding:5px 10px;border-left:3px solid '+col+'">'+indent+he(p.name)+'</td><td style="padding:5px 10px;text-align:right">'+p.mod_vtx+'</td><td style="padding:5px 10px;text-align:right">'+p.abc_vtx+'</td><td style="'+stColor+';padding:5px 10px">'+st+'</td><td style="padding:5px 10px;text-align:right;'+(diff>0?'color:#e05555;font-weight:600':'')+'">'+(diff>0?diff:'-')+'</td><td style="'+(frozen?'':'color:#e05555;font-weight:600')+'">'+frozenTxt+'</td><td style="'+(hm?'':'color:#e05555;font-weight:600')+';font-size:11px">'+hierTxt+'</td><td style="'+(om?'':'color:#e05555;font-weight:600')+'">'+orderTxt+'</td></tr>';'''

if old_row in content:
    content = content.replace(old_row, new_row)
    print("Row rendering updated")
else:
    print("Row not found")
    idx = content.find('hierarchy_match!==false')
    if idx >= 0:
        print("Found at", idx)
        print(repr(content[idx:idx+400]))

with open('d:/zcy/ai_ty/packages/generate_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
