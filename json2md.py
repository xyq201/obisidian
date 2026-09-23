#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把灵感库 *-content.json 每日学习产物转成 markdown（供 IMA 知识库同步与纯文本检索）。

用法： python3 json2md.py            # 转换全部缺 md 的 json
      python3 json2md.py --force    # 全部重新生成
"""
import json
import glob
import os
import sys

SRC_GLOB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "灵感库", "*-content.json")


def section_to_md(s):
    t = s.get("type")
    if t == "callout":
        label = s.get("label", "")
        text = s.get("text", "")
        return f"> **{label}** {text}" if label else f"> {text}"
    if t == "h":
        return f"\n## {s.get('text','')}\n"
    if t == "p":
        return s.get("text", "")
    if t == "bullets":
        return "\n".join(f"- {it}" for it in s.get("items", []))
    if t == "table":
        headers = s.get("headers", [])
        rows = s.get("rows", [])
        lines = []
        if headers:
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            lines.append("|" + "---|" * len(headers))
        for r in rows:
            cells = [str(c).replace("\n", " ").replace("|", "\\|") for c in r]
            lines.append("| " + " | ".join(cells) + " |")
        cap = s.get("caption") or s.get("label")
        if cap:
            lines.append(f"\n*{cap}*")
        return "\n".join(lines)
    if t == "footer":
        return f"\n---\n\n*{s.get('text','')}*"
    return ""


def json_to_md(d):
    parts = []
    title = d.get("title", "未命名")
    parts.append(f"# {title}\n")
    if d.get("subtitle"):
        parts.append(f"> {d['subtitle']}\n")
    meta = d.get("meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    meta_bits = []
    if meta.get("date"):
        meta_bits.append(f"日期：{meta['date']}")
    if meta.get("seq") is not None:
        meta_bits.append(f"主题序号：#{meta['seq']}")
    if meta.get("perspective"):
        meta_bits.append(meta["perspective"])
    if meta_bits:
        parts.append(" | ".join(meta_bits) + "\n")
    if meta.get("tags"):
        parts.append("**标签**：" + "、".join(meta["tags"]) + "\n")
    for s in d.get("sections", []):
        md = section_to_md(s)
        if md:
            parts.append(md)
    refs = d.get("references") or []
    if refs:
        parts.append("\n## 参考资料\n")
        for r in refs:
            parts.append(f"- [{r.get('title','')}]({r.get('url','')})")
    footer = d.get("footer")
    if footer:
        parts.append(f"\n---\n\n*{footer}*")
    return "\n\n".join(parts) + "\n"


def main():
    force = "--force" in sys.argv
    made = 0
    for fp in sorted(glob.glob(SRC_GLOB)):
        d = json.load(open(fp, encoding="utf-8"))
        meta = d.get("meta") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if not isinstance(meta, dict):
            meta = {}
        stem = os.path.basename(fp).replace("-content.json", "")
        theme = meta.get("theme") or d.get("title") or stem
        base = f"{stem.split('-', 3)[0]}-{stem.split('-', 3)[1]}-{stem.split('-', 3)[2]}-{theme}" if stem[:2] == "20" else f"{stem}-{theme}"
        for ch in "/\\:*?\"<>|":
            base = base.replace(ch, "·")
        out = os.path.join(os.path.dirname(fp), f"{base}.md")
        if os.path.exists(out) and not force:
            continue
        md = json_to_md(d)
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        made += 1
        print(f"✓ {os.path.basename(fp)} -> {os.path.basename(out)} ({len(md)} 字)")
    print(f"\n共生成 {made} 个 md")


if __name__ == "__main__":
    main()
