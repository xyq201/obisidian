#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_learning_docx.py — 每日化妆品知识系统学习 → Word 总结 生成器

用法:
    python3 make_learning_docx.py <content.json> <out.docx>

content.json 结构（所有字段均可省，按需给）:
{
  "title":   "每日化妆品知识系统学习",
  "subtitle":"神经美容与皮肤-脑轴（Neurocosmetics & the Skin–Brain Axis）",
  "meta":    "日期 2026-09-13 ｜ 视角：研发工程师 × 产品经理 ｜ 信源：前沿研究+公众号+经典教材",
  "sections": [
     {"type":"callout", "label":"一句话结论（双视角）", "text":"..."},
     {"type":"h", "text":"一、机理：皮肤-脑轴是什么"},
     {"type":"p", "text":"段落正文……"},
     {"type":"bullets", "items":["要点1","要点2"]},
     {"type":"table", "caption":"表：靶点→原料→规格",
        "headers":["靶点/通路","可选原料","建议添加量","配伍/pH/稳定要点"],
        "rows":[["TRPV1 感觉神经","XX","x%","..."]]},
     {"type":"callout", "label":"产品经理视角", "text":"..."}
  ],
  "footer": "信源：MDPI Cosmetics 2026; Science 2026-03; 个人护理洞察/Givaudan 2026; 《皮肤科学与化妆品功效评价》《Cosmeceuticals》"
}

设计：A4、中文（微软雅黑）渲染、分级标题、双视角高亮框、规范表格。
"""
import sys, json
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CJK = "微软雅黑"
DARK = RGBColor(0x1F, 0x3A, 0x5F)      # 深蓝标题
ACCENT = RGBColor(0x2E, 0x75, 0xB6)    # 蓝绿强调
GREY = RGBColor(0x59, 0x59, 0x59)


def set_cjk(run, font=CJK):
    run.font.name = font
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
        rFonts.set(qn(attr), font)


def shade_cell(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hexcolor)
    tcPr.append(shd)


def set_cell_text(cell, text, bold=False, color=None, size=10.5):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    run = p.add_run(text)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    run.font.size = Pt(size)
    set_cjk(run)


def add_callout(doc, label, text, fill="EAF2F8"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    shade_cell(cell, fill)
    # 左侧色条
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '24')
    left.set(qn('w:space'), '0'); left.set(qn('w:color'), '2E75B6')
    borders.append(left)
    tcPr.append(borders)
    cell.text = ''
    p = cell.paragraphs[0]
    r = p.add_run(label + "：")
    r.bold = True; r.font.size = Pt(11); r.font.color.rgb = ACCENT; set_cjk(r)
    r2 = p.add_run(text)
    r2.font.size = Pt(10.5); set_cjk(r2)
    doc.add_paragraph()


def build(doc, data):
    # 默认样式：中文
    style = doc.styles['Normal']
    style.font.name = CJK
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), CJK)

    # 标题
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run(data.get('title', '每日化妆品知识系统学习'))
    r.bold = True; r.font.size = Pt(18); r.font.color.rgb = DARK; set_cjk(r)

    if data.get('subtitle'):
        s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rs = s.add_run(data['subtitle']); rs.font.size = Pt(13); rs.font.color.rgb = ACCENT; set_cjk(rs)

    if data.get('meta'):
        m = doc.add_paragraph(); m.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rm = m.add_run(data['meta']); rm.font.size = Pt(9.5); rm.font.color.rgb = GREY; set_cjk(rm)

    # 分隔线
    hr = doc.add_paragraph()
    pPr = hr._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single'); bottom.set(qn('w:sz'), '8')
    bottom.set(qn('w:space'), '1'); bottom.set(qn('w:color'), '2E75B6')
    pbdr.append(bottom); pPr.append(pbdr)
    hr.paragraph_format.space_after = Pt(6)

    for sec in data.get('sections', []):
        typ = sec.get('type')
        if typ == 'callout':
            add_callout(doc, sec.get('label', ''), sec.get('text', ''))
        elif typ == 'h':
            h = doc.add_paragraph(); h.paragraph_format.space_before = Pt(10); h.paragraph_format.space_after = Pt(4)
            rh = h.add_run(sec['text']); rh.bold = True; rh.font.size = Pt(13.5); rh.font.color.rgb = DARK; set_cjk(rh)
        elif typ == 'p':
            p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(6); p.paragraph_format.line_spacing = 1.25
            rp = p.add_run(sec['text']); rp.font.size = Pt(11); set_cjk(rp)
        elif typ == 'bullets':
            for it in sec.get('items', []):
                p = doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after = Pt(2)
                rp = p.add_run(it); rp.font.size = Pt(10.5); set_cjk(rp)
        elif typ == 'table':
            cap = sec.get('caption')
            if cap:
                cp = doc.add_paragraph(); cr = cp.add_run(cap)
                cr.bold = True; cr.font.size = Pt(10.5); cr.font.color.rgb = ACCENT; set_cjk(cr)
            headers = sec.get('headers', [])
            rows = sec.get('rows', [])
            tbl = doc.add_table(rows=1, cols=len(headers))
            tbl.style = 'Table Grid'; tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            # 表头
            for i, htext in enumerate(headers):
                set_cell_text(tbl.cell(0, i), htext, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), size=10.5)
                shade_cell(tbl.cell(0, i), '2E75B6')
            for rrow in rows:
                cells = tbl.add_row().cells
                for i, val in enumerate(rrow):
                    set_cell_text(cells[i], val, size=10)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

    if data.get('footer'):
        f = doc.add_paragraph(); f.paragraph_format.space_before = Pt(10)
        pPr = f._p.get_or_add_pPr()
        pbdr = OxmlElement('w:pBdr')
        top = OxmlElement('w:top')
        top.set(qn('w:val'), 'single'); top.set(qn('w:sz'), '6'); top.set(qn('w:space'), '1'); top.set(qn('w:color'), 'BFBFBF')
        pbdr.append(top); pPr.append(pbdr)
        rf = f.add_run('信源：' + data['footer']); rf.font.size = Pt(8.5); rf.font.color.rgb = GREY; set_cjk(rf)


def main():
    if len(sys.argv) < 3:
        print("usage: python3 make_learning_docx.py <content.json> <out.docx>"); sys.exit(1)
    with open(sys.argv[1], encoding='utf-8') as f:
        data = json.load(f)
    doc = Document()
    # A4 页边距
    for section in doc.sections:
        section.top_margin = Inches(0.9); section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9); section.right_margin = Inches(0.9)
    build(doc, data)
    doc.save(sys.argv[2])
    print("saved:", sys.argv[2])


if __name__ == '__main__':
    main()
