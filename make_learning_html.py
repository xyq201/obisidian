#!/usr/bin/env python3.11
# 读与 make_learning_docx.py 相同的 JSON schema，输出自包含 HTML（手机/浏览器可直接预览）
import sys, json

def esc(s):
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def render_section(sec, buf):
    t = sec.get("type")
    if t == "callout":
        label = esc(sec.get("label",""))
        text = esc(sec.get("text",""))
        buf.append(f'<div class="callout"><div class="callout-label">{label}</div><div class="callout-text">{text}</div></div>')
    elif t == "h":
        buf.append(f'<h2>{esc(sec.get("text",""))}</h2>')
    elif t == "p":
        buf.append(f'<p>{esc(sec.get("text",""))}</p>')
    elif t == "bullets":
        items = "".join(f"<li>{esc(it)}</li>" for it in sec.get("items",[]))
        buf.append(f"<ul>{items}</ul>")
    elif t == "table":
        cap = sec.get("caption")
        headers = sec.get("headers",[])
        rows = sec.get("rows",[])
        th = "".join(f"<th>{esc(h)}</th>" for h in headers)
        body = ""
        for r in rows:
            body += "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>"
        cap_html = f'<div class="cap">{esc(cap)}</div>' if cap else ""
        buf.append(f'{cap_html}<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>')

def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    buf = []
    buf.append(f'<h1>{esc(data.get("title",""))}</h1>')
    if data.get("subtitle"):
        buf.append(f'<div class="subtitle">{esc(data["subtitle"])}</div>')
    if data.get("meta"):
        buf.append(f'<div class="meta">{esc(data["meta"])}</div>')
    for sec in data.get("sections",[]):
        render_section(sec, buf)
    if data.get("footer"):
        buf.append(f'<div class="footer">信源：{esc(data["footer"])}</div>')
    refs = data.get("references") or []
    if refs:
        items = "".join(f'<li><a href="{esc(r.get("url",""))}" target="_blank" rel="noopener">{esc(r.get("title",""))}</a></li>' for r in refs)
        buf.append(f'<h2 class="refs">参考资料与出处链接</h2><ol>{items}</ol>')
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data.get('title',''))}</title>
<style>
*{{box-sizing:border-box}}
body{{max-width:780px;margin:0 auto;padding:24px 18px;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#222;line-height:1.7}}
h1{{font-size:21px;color:#1a4f7a;margin:0 0 6px}}
.subtitle{{font-size:14px;color:#2e75b6;font-weight:600;margin-bottom:4px}}
.meta{{font-size:11.5px;color:#888;margin-bottom:14px;border-bottom:2px solid #2e75b6;padding-bottom:8px}}
h2{{font-size:16.5px;color:#123;margin:22px 0 8px;border-left:4px solid #2e75b6;padding-left:8px}}
p{{font-size:14.5px;margin:8px 0}}
ul{{font-size:14px;padding-left:20px}} li{{margin:5px 0}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0}}
th,td{{border:1px solid #cdd;padding:6px 8px;vertical-align:top}}
th{{background:#2e75b6;color:#fff;text-align:left}}
tr:nth-child(even) td{{background:#f4f8fc}}
.cap{{font-size:12.5px;color:#2e75b6;font-weight:600;margin:10px 0 2px}}
.callout{{background:#eaf2f8;border:1px solid #bcd; border-left:4px solid #2e75b6;border-radius:6px;padding:10px 12px;margin:12px 0}}
.callout-label{{font-size:12.5px;font-weight:700;color:#1a4f7a;margin-bottom:4px}}
.callout-text{{font-size:13.5px;color:#234}}
.footer{{font-size:11px;color:#999;border-top:1px solid #ddd;margin-top:18px;padding-top:8px}}
.refs{{margin-top:18px}}
ol a{{color:#2e75b6;word-break:break-all;font-size:12.5px}}
</style></head><body>{''.join(buf)}</body></html>"""
    open(dst,"w",encoding="utf-8").write(html)
    print("saved:", dst)

if __name__ == "__main__":
    main()
