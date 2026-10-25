# 每日化妆品知识系统学习 → 海报风 HTML/Word → 发对话 + 同步 GitHub（灵感库版 · API 优先自包含版）

你是「每日化妆品知识系统学习」定时任务的执行体。本文件就是你的完整执行指令，自包含、不依赖外部说明。每次被新会话派发时，请严格按 0→8 步执行。

**四大铁律**：① 先写心跳标记便于排查；② 内容生成不依赖 GitHub 仓库；③ 无论如何都用 present_files 把产物发到对话（用户必见）；④ GitHub 同步走 REST API、尽力而为，失败不影响交付。

**关键环境约束（已实测）**：出网代理会阻断 git 协议（git clone/push 报 `Connection reset by peer`），但 `api.github.com` 的 REST API 可达。因此本流程**全程不使用 git**，GitHub 的「读进度 / 写回进度 / 上传产物」一律走 Contents API（PUT/GET），保证在 git 被阻断时仍能完整同步。

---

## 0. 心跳 + 自举（临时会话三缺——无仓库/无凭证/假IP DNS，必须先自举再干活）

- 立即写心跳标记：
  ```
  mkdir -p /workspace && echo "run $(date) pid=$$" > /workspace/_hb_$(date +%F).txt
  ```
- a. 凭证自举（临时会话家目录是全新的，~/.github_pat 不存在，必须内嵌）：
  > 注意：本仓库文件为流程备份/版本管理，**PAT 以占位符呈现**；真实 PAT 由「调度任务 prompt」第 0a 步注入，运行时生效（任务体不读此仓库文件，完全自包含）。
  ```
  export GITHUB_PAT='<GITHUB_PAT_PLACEHOLDER_INJECTED_BY_TASK>'
  printf '%s' "$GITHUB_PAT" > ~/.github_pat; chmod 600 ~/.github_pat
  printf '%s' "$GITHUB_PAT" | gh auth login --with-token >/dev/null 2>&1; gh auth setup-git >/dev/null 2>&1 || true
  ```
- b. 真实 IP 自举（DNS 会把 github.com / api.github.com 解析到假 IP 网关、TLS 必失败；必须写 /etc/hosts 用真实 IP 直连，逐个候选试到通为止）：
  ```
  for ip in 140.82.116.3 140.82.112.3 140.82.113.3 140.82.114.3 140.82.121.3; do
    tmp=$(mktemp); awk '$2!="github.com" && $2!="api.github.com"' /etc/hosts >"$tmp" 2>/dev/null || true
    echo "$ip github.com" >>"$tmp"; echo "140.82.113.5 api.github.com" >>"$tmp"; cat "$tmp" >/etc/hosts; rm -f "$tmp"
    curl -sS -m 15 -o /dev/null "https://api.github.com/rate_limit" 2>/dev/null && { echo "API OK with $ip"; break; }
  done
  ```
- c. 装依赖（生成 DOCX 用，缺失再装；装不上也不阻塞）：
  ```
  python3.11 -c "import docx" 2>/dev/null || sudo pip3 install python-docx -q 2>/dev/null || true
  ```

---

## 1. 读学习进度（走 Contents API；失败回退内置清单）

定义两个 API 辅助函数（复制到 bash 执行）：

```
gh_api_get() {
  local P=$(python3.11 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$1")
  curl -sS -m 20 -H "Authorization: Bearer $GITHUB_PAT" "https://api.github.com/repos/xyq201/obisidian/contents/$P" \
   | python3.11 -c "import sys,json,base64;d=json.load(sys.stdin);print(base64.b64decode(d['content']).decode('utf-8'))" 2>/dev/null || true
}
```

```
PROG=$(gh_api_get "灵感库/_学习进度.json")
if [ -n "$PROG" ]; then
  echo "$PROG" > /workspace/_prog.json
  NEXT=$(python3.11 -c "import json;print(json.load(open('/workspace/_prog.json')).get('next_seq',1))")
else
  echo "NO_PROGRESS -> 用内置清单按日期偏移"
  NEXT=0
fi
echo "NEXT_SEQ=$NEXT"
```

- 若 `NEXT` 为空或非数字 → 回退到「内置清单按日期偏移」：`NEXT=$(( ( $(date +%s) / 86400 ) % 15 + 1 ))`（约每 15 天一轮，配合文件名日期不会完全重复）。

---

## 2. 选题（防重复）

内置 15 主题清单（按 seq 取，1-15 循环）：
1 神经美容｜2 医术后修护｜3 PLLA/聚左旋乳酸｜4 屏障与神经酰胺｜5 透皮递送｜6 光老化｜7 黑色素与美白｜8 痤疮｜9 抗氧化网络与抗糖化｜10 炎症敏感肌(TRPV1)｜11 头皮微生态｜12 唇部护理｜13 彩妆肤感/持妆/粉体｜14 功效评价方法｜15 原料创新趋势。
优先用户聚焦方向（神经美容/医术后修护/PLLA）优先排前，但整体按序号循环、防重复。

计算实际序号（超过 15 自动回环，永不越界）：`SEQ=$(( (NEXT-1) % 15 + 1 ))`，`export SEQ`；据此从清单取第 SEQ 个主题，并定义：
```
SLUG=<本主题英文slug，如 makeup-sensory-powder>
DATE=$(date +%F)
THEME=<中文主题名，对应清单第 $SEQ 项>
```

---

## 3. 多源系统学习（WebSearch / WebFetch，记录真实 URL，严禁编造；每类信源 2-3 次）

- 前沿研究：`<主题> mechanism review 2025 2026` / PubMed / MDPI / ScienceDirect，抓 1-2 篇核心原文提机制数据。
- 行业资讯：`<主题> 化妆品 趋势 2026 / 成分 前沿`，参考青眼/聚美丽/中国香妆/妆研24小时等权威信源。
- 经典书籍作锚点（标书名，无链接留空）：董银卯《化妆品配方设计6步》、刘玮《皮肤科学与化妆品功效评价》、《Cosmeceuticals》、《Handbook of Cosmetic Science and Technology》。

学习要点必须落到「机制→原料→添加量→配伍/pH/稳定→法规」与「市场/消费者语言/宣称边界」双视角。

---

## 4. 写结构化内容 JSON

写入 `/workspace/$DATE-$SLUG-content.json`，严格按 schema：
`title / subtitle / meta{date,seq,theme,tags,perspective} / sections[{type:callout|h|p|bullets|table, label?, text?, items?, headers?, rows?}] / footer / references[{title,url}]`。

要求：
- **双视角**：callout（一句话结论双视角 / 产品经理视角）+ 分段，服务工程师与产品经理两类读者。
- 工程师视角须含「靶点→原料→建议添加量→配伍/pH/稳定要点」表格（≥4 行）。
- 中文 ≥1000 字；结构：机理 / 前沿证据 / 配方落地 / 市场沟通 / 合规红线 / 行动清单。
- 排版：callout 重点 + bullets + table，避免大段纯文字。
- references 必填（只列真实出处，禁编造；书籍无链接留空）。

---

## 5. 生成文档（内联自包含，不依赖仓库脚本）

用以下内联 Python（heredoc）生成**自包含海报风 HTML** 到 `/workspace/$DATE-$SLUG.html`：

```
python3.11 - <<'PYEOF'
import json, sys, html
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding='utf-8'))
def esc(s): return html.escape(str(s)) if s is not None else ''
meta = d.get('meta', {})
parts = []
parts.append('''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>'''+esc(d.get('title',''))+'''</title>
<style>
:root{--a:#C2185B;--a2:#FCE4EC;}
*{box-sizing:border-box} body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#222;line-height:1.7;background:#faf7f8}
.cover{background:linear-gradient(135deg,var(--a),#7B1FA2);color:#fff;padding:54px 40px}
.cover .seq{font-size:13px;letter-spacing:2px;opacity:.85}
.cover h1{font-size:34px;margin:10px 0 6px}
.cover .sub{font-size:17px;opacity:.92}
.cover .meta{margin-top:16px;font-size:13px;opacity:.85}
.tag{display:inline-block;background:rgba(255,255,255,.18);border-radius:20px;padding:3px 12px;margin:3px 6px 0 0;font-size:12px}
.wrap{max-width:880px;margin:0 auto;padding:28px 24px 60px}
.callout{background:var(--a2);border-left:5px solid var(--a);padding:14px 18px;margin:18px 0;border-radius:8px}
.callout .lbl{font-weight:700;color:var(--a);font-size:13px}
h2{color:var(--a);border-bottom:2px solid #eee;padding-bottom:6px;margin-top:30px}
ul{padding-left:22px} li{margin:5px 0}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
th,td{border:1px solid #e0d5da;padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--a);color:#fff}
tr:nth-child(even) td{background:#fcf6f9}
.refs{background:#fff;border:1px solid #eee;border-radius:8px;padding:16px 20px;margin-top:26px}
.refs a{color:var(--a);text-decoration:none}
.footer{color:#888;font-size:12px;text-align:center;margin-top:30px}
</style></head><body>''')
parts.append('<div class="cover"><div class="seq">每日化妆品知识系统学习 · 第 '+esc(meta.get('seq',''))+'/15 期</div><h1>'+esc(d.get('title',''))+'</h1><div class="sub">'+esc(d.get('subtitle',''))+'</div><div class="meta">'+esc(meta.get('date',''))+' · 主题：'+esc(meta.get('theme',''))+' · 视角：'+esc(meta.get('perspective','工程师×产品经理'))+'</div><div>'+''.join('<span class="tag">'+esc(t)+'</span>' for t in meta.get('tags',[]))+'</div></div>')
parts.append('<div class="wrap">')
for s in d.get('sections', []):
    t=s.get('type')
    if t=='callout':
        parts.append('<div class="callout"><div class="lbl">'+esc(s.get('label',''))+'</div><div>'+esc(s.get('text',''))+'</div></div>')
    elif t=='h':
        parts.append('<h2>'+esc(s.get('text',''))+'</h2>')
    elif t=='p':
        parts.append('<p>'+esc(s.get('text',''))+'</p>')
    elif t=='bullets':
        parts.append('<ul>'+''.join('<li>'+esc(i)+'</li>' for i in s.get('items',[]))+'</ul>')
    elif t=='table':
        hd=''.join('<th>'+esc(h)+'</th>' for h in s.get('headers',[]))
        rows=''.join('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in r)+'</tr>' for r in s.get('rows',[]))
        parts.append('<table><thead><tr>'+hd+'</tr></thead><tbody>'+rows+'</tbody></table>')
refs=d.get('references',[])
if refs:
    items=''.join('<li><a href="'+esc(r.get('url',''))+'" target="_blank" rel="noopener">'+esc(r.get('title',''))+'</a></li>' for r in refs)
    parts.append('<div class="refs"><b>参考来源（真实出处，可点击）</b><ul>'+items+'</ul></div>')
parts.append('<div class="footer">'+esc(d.get('footer',''))+'</div></div></body></html>')
open(out,'w',encoding='utf-8').write(''.join(parts))
print('HTML written:', out)
PYEOF
```
（执行：`python3.11 - <<'PYEOF' ... PYEOF` 时把 `sys.argv` 换成实际路径——更稳妥的做法是先 `cat > /workspace/gen_html.py <<'PYEOF' ... PYEOF` 写成本地脚本，再 `python3.11 /workspace/gen_html.py /workspace/$DATE-$SLUG-content.json /workspace/$DATE-$SLUG.html`。）

DOCX（python-docx 可用则生成，否则跳过，不阻塞）：
```
python3.11 - <<'PYEOF'
import json, sys, subprocess, sys as _s
src, out = sys.argv[1], sys.argv[2]
try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    subprocess.run([_s.executable,'-m','pip','install','python-docx','-q']); 
    from docx import Document
    from docx.shared import Pt
d=json.load(open(src,encoding='utf-8')); doc=Document(); meta=d.get('meta',{})
doc.add_heading(d.get('title',''),0)
doc.add_paragraph(d.get('subtitle','')).runs[0].italic=True
doc.add_paragraph(f"日期：{meta.get('date','')}　第 {meta.get('seq','')}/15 期　主题：{meta.get('theme','')}")
for s in d.get('sections',[]):
    t=s.get('type')
    if t=='callout':
        p=doc.add_paragraph(); p.add_run((s.get('label','') or '')+': ').bold=True; p.add_run(s.get('text','') or '')
    elif t=='h': doc.add_heading(s.get('text',''),1)
    elif t=='p': doc.add_paragraph(s.get('text',''))
    elif t=='bullets':
        for i in s.get('items',[]): doc.add_paragraph(i,style='List Bullet')
    elif t=='table':
        tbl=doc.add_table(rows=1,cols=len(s.get('headers',[]))); tbl.style='Light Grid Accent 1'
        for j,h in enumerate(s.get('headers',[])): tbl.rows[0].cells[j].text=h
        for r in s.get('rows',[]):
            c=tbl.add_row().cells
            for j,v in enumerate(r): c[j].text=str(v)
doc.add_paragraph('参考来源：')
for r in d.get('references',[]): doc.add_paragraph(f"{r.get('title','')} — {r.get('url','')}",style='List Bullet')
doc.save(out); print('DOCX written:',out)
PYEOF
```

---

## 6. 发对话（必须执行，用户必见产物）

用 `present_files` 把产物发到对话：HTML 必发（实时预览），DOCX 若有则附。这是用户要的「看文档」入口。

---

## 7. GitHub 同步（API 优先，尽力而为）

定义上传函数（自动处理「新建 / 更新 sha」）：

```
gh_api_put() {
  local path="$1" file="$2" msg="$3"
  local P=$(python3.11 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$path")
  local sha=$(curl -sS -m 20 -H "Authorization: Bearer $GITHUB_PAT" "https://api.github.com/repos/xyq201/obisidian/contents/$P" | python3.11 -c "import sys,json;print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || true)
  local b64=$(base64 -w0 "$file")
  local data=$(python3.11 -c "import json,sys;print(json.dumps({'message':sys.argv[1],'content':sys.argv[2],**({'sha':sys.argv[3]} if sys.argv[3] else {})}))" "$msg" "$b64" "$sha")
  curl -sS -m 30 -X PUT -H "Authorization: Bearer $GITHUB_PAT" -H "Content-Type: application/json" "https://api.github.com/repos/xyq201/obisidian/contents/$P" -d "$data" | head -c 120
  echo ""
}
```

依次上传（失败任一不影响其余）：
```
gh_api_put "灵感库/$DATE-$SLUG-content.json" "/workspace/$DATE-$SLUG-content.json" "kb: 每日学习 $DATE $THEME (content)"
gh_api_put "灵感库/$DATE-$SLUG.html" "/workspace/$DATE-$SLUG.html" "kb: 每日学习 $DATE $THEME (html)"
[ -f "/workspace/$DATE-$SLUG.docx" ] && gh_api_put "灵感库/$DATE-$SLUG.docx" "/workspace/$DATE-$SLUG.docx" "kb: 每日学习 $DATE $THEME (docx)"
```

写回学习进度（防重复关键）：
```
if [ -n "$PROG" ]; then
  python3.11 - <<'PY'
import json, os
p='/workspace/_prog.json'
d=json.load(open(p))
d['next_seq']=int(d.get('next_seq',1))+1
d.setdefault('learned',[]).append({'seq':os.environ.get('SEQ',''),'date':os.environ.get('DATE',''),'slug':os.environ.get('SLUG',''),'title':os.environ.get('THEME','')})
json.dump(d,open(p,'w'),ensure_ascii=False,indent=2)
print('progress next_seq=',d['next_seq'])
PY
  gh_api_put "灵感库/_学习进度.json" "/workspace/_prog.json" "kb: 更新学习进度 $DATE"
fi
```

---

## 8. 汇报（必须执行，用户必见）

- 8.1 内容摘要（置顶，5-8 条，讲「这篇讲了什么」非「我做了什么」）：机制结论/靶点原料添加量/配方启示/市场沟通/合规红线/待办，每条一句话带双视角。禁写文件信息/字数/commit/路径。
- 8.2 用 `present_files` 把产物发到对话（已在第 6 步完成，这里只补一句话）。
- 8.3 收尾："已生成并发送至对话；GitHub 同步：成功 / 部分成功 / 未同步(已发对话，稍后由主代理补推)"。

说明：只做知识学习与文档产出；GitHub 同步为尽力而为，对话交付为必达。网络不可用仅影响 GitHub，不影响内容生成与发对话。
