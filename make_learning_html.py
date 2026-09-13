#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_learning_html.py — 每日化妆品知识系统学习 → 海报风 HTML 生成器

用法:
    python3 make_learning_html.py <content.json> <out.html>

输出自包含单文件 HTML（内联 CSS，无外部依赖），适合手机预览 / 转 PDF / 转图。
结构同 make_learning_docx.py：title/subtitle/meta/sections/footer/references/images。
"""
import sys, json, os, html


def esc(s):
    return html.escape(str(s), quote=True)


def render_section(sec):
    typ = sec.get('type')
    if typ == 'callout':
        label = esc(sec.get('label', ''))
        text = esc(sec.get('text', ''))
        cls = 'callout'
        if '产品经理' in label:
            cls = 'callout pm'
        elif '工程师' in label:
            cls = 'callout eng'
        return f'<div class="{cls}"><span class="clabel">{label}：</span>{text}</div>'
    if typ == 'h':
        return f'<h2>{esc(sec["text"])}</h2>'
    if typ == 'p':
        return f'<p>{esc(sec["text"])}</p>'
    if typ == 'bullets':
        items = ''.join(f'<li>{esc(it)}</li>' for it in sec.get('items', []))
        return f'<ul class="bullets">{items}</ul>'
    if typ == 'table':
        cap = sec.get('caption')
        cap_html = f'<div class="tcap">{esc(cap)}</div>' if cap else ''
        thead = ''.join(f'<th>{esc(h)}</th>' for h in sec.get('headers', []))
        rows = sec.get('rows', [])
        tbody = ''
        for r in rows:
            tbody += '<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>'
        return (f'{cap_html}<div class="tablewrap"><table>'
                f'<thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>')
    return ''


def build_html(data):
    title = esc(data.get('title', '每日化妆品知识系统学习'))
    subtitle = esc(data.get('subtitle', ''))
    meta = esc(data.get('meta', ''))
    cover_img = ''
    for img in data.get('images', []):
        if img.get('role') == 'cover' and img.get('path'):
            src = esc(os.path.basename(img['path']))
            cover_img = f'<img class="cover-img" src="{src}" alt="cover">'
            break
    sections_html = ''.join(render_section(s) for s in data.get('sections', []))
    diags = [i for i in data.get('images', []) if i.get('role') != 'cover' and i.get('path')]
    diag_html = ''
    if diags:
        items = ''
        for img in diags:
            src = esc(os.path.basename(img['path']))
            cap = esc(img.get('caption', ''))
            items += f'<figure><img src="{src}" alt="diagram"><figcaption>{cap}</figcaption></figure>'
        diag_html = f'<h2>附图</h2><div class="figrow">{items}</div>'
    footer = esc(data.get('footer', ''))
    footer_html = f'<div class="footer">信源：{footer}</div>' if footer else ''
    refs = data.get('references') or []
    refs_html = ''
    if refs:
        lis = ''
        for i, ref in enumerate(refs, 1):
            t = esc(ref.get('title', '')); u = ref.get('url', '')
            if u:
                lis += f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{t}</a> <span class="url">{esc(u)}</span></li>'
            else:
                lis += f'<li>{t}</li>'
        refs_html = f'<h2>参考资料与出处链接</h2><ol class="refs">{lis}</ol>'
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#eef2f5; font-family:"微软雅黑","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; color:#22303f; line-height:1.85; }}
.wrap {{ max-width:840px; margin:24px auto; background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 10px 40px rgba(31,58,95,.12); }}
.cover {{ padding:46px 38px 30px; background:linear-gradient(135deg,#1f3a5f 0%,#2e75b6 60%,#3aa6a0 100%); color:#fff; }}
.cover h1 {{ margin:0 0 10px; font-size:30px; letter-spacing:1px; }}
.cover .sub {{ font-size:17px; color:#cfe6fb; margin:0 0 8px; }}
.cover .meta {{ font-size:13px; color:#d6dce4; margin:0; }}
.cover-img {{ display:block; width:100%; max-height:340px; object-fit:cover; border-radius:14px; margin-top:22px; box-shadow:0 8px 24px rgba(0,0,0,.25); }}
.content {{ padding:30px 38px 40px; }}
h2 {{ font-size:20px; color:#1f3a5f; border-left:6px solid #2e75b6; padding-left:12px; margin:30px 0 12px; }}
p {{ margin:0 0 14px; font-size:15.5px; }}
.bullets {{ margin:0 0 14px; padding-left:22px; }}
.bullets li {{ margin:0 0 8px; font-size:15px; }}
.callout {{ border-radius:12px; padding:16px 18px; margin:0 0 16px; font-size:15px; background:#eaf2f8; border-left:6px solid #2e75b6; }}
.callout.pm {{ background:#fdf0e4; border-left-color:#c86a1e; }}
.callout.eng {{ background:#eaf2f8; border-left-color:#2e75b6; }}
.callout .clabel {{ font-weight:700; }}
.tablewrap {{ overflow-x:auto; margin:0 0 16px; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; border-radius:10px; overflow:hidden; }}
th,td {{ border:1px solid #dbe4ec; padding:10px 12px; text-align:left; vertical-align:top; }}
thead th {{ background:#2e75b6; color:#fff; font-weight:600; }}
tbody tr:nth-child(even) {{ background:#eef3f8; }}
.tcap {{ font-weight:700; color:#2e75b6; font-size:14px; margin:0 0 6px; }}
.figrow {{ display:flex; flex-wrap:wrap; gap:16px; }}
figure {{ margin:0; flex:1 1 280px; }}
figure img {{ width:100%; border-radius:12px; box-shadow:0 6px 18px rgba(0,0,0,.12); }}
figcaption {{ font-size:12.5px; color:#5a6b7b; text-align:center; margin-top:6px; }}
.footer {{ margin-top:26px; padding-top:14px; border-top:1px solid #e1e7ee; font-size:12px; color:#7a8694; }}
.refs {{ padding-left:22px; }}
.refs li {{ margin:0 0 9px; font-size:13.5px; }}
.refs a {{ color:#2e75b6; text-decoration:none; font-weight:600; }}
.refs a:hover {{ text-decoration:underline; }}
.refs .url {{ color:#9aa6b3; font-size:11.5px; word-break:break-all; }}
</style></head>
<body><div class="wrap">
<div class="cover"><h1>{title}</h1>{('<p class="sub">{0}</p>'.format(subtitle)) if subtitle else ''}{('<p class="meta">{0}</p>'.format(meta)) if meta else ''}{cover_img}</div>
<div class="content">
{sections_html}
{diag_html}
{footer_html}
{refs_html}
</div></div></body></html>'''


def main():
    if len(sys.argv) < 3:
        print("usage: python3 make_learning_html.py <content.json> <out.html>"); sys.exit(1)
    with open(sys.argv[1], encoding='utf-8') as f:
        data = json.load(f)
    out = build_html(data)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(out)
    print("saved:", sys.argv[2])


if __name__ == '__main__':
    main()
