#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_learning_docx.py — 每日化妆品知识系统学习 → 海报风 Word 总结生成器

用法:
    python3 make_learning_docx.py <content.json> <out.docx>

content.json 结构（详见 README / 任务 prompt）:
  title / subtitle / meta / sections[{type:callout|h|p|bullets|table}] / footer
  references:[{title,url}]  -> 文末带超链接清单
  images:[{role:'cover'|'diagram', path, caption}]  -> 配图嵌入（封面图/附图）

设计：A4、微软雅黑、深蓝封面色块、双视角配色高亮框、斑马纹表格、宽松行距、可嵌入配图。
"""
import sys, json
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HYPERLINK_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
CJK = "微软雅黑"
DARK = RGBColor(0x1F, 0x3A, 0x5F)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
ORANGE = RGBColor(0xC8, 0x6A, 0x1E)
GREY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def set_cjk(run, font=CJK):
    run.font.name = font
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts'); rPr.append(rFonts)
    for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
        rFonts.set(qn(attr), font)


def shade_cell(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), hexcolor)
    tcPr.append(shd)


def set_cell_text(cell, text, bold=False, color=None, size=10.5, fill=None):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2); p.paragraph_format.space_before = Pt(2)
    run = p.add_run(text); run.bold = bold; run.font.size = Pt(size); set_cjk(run)
    if color: run.font.color.rgb = color
    if fill: shade_cell(cell, fill)


def add_leftbar(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '24'); left.set(qn('w:space'), '0'); left.set(qn('w:color'), hexcolor)
    borders.append(left); tcPr.append(borders)


def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, HYPERLINK_REL, is_external=True)
    hyperlink = OxmlElement('w:hyperlink'); hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr'); rStyle = OxmlElement('w:rStyle'); rStyle.set(qn('w:val'), 'Hyperlink'); rPr.append(rStyle)
    rFonts = OxmlElement('w:rFonts')
    for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'): rFonts.set(qn(attr), CJK)
    rPr.append(rFonts)
    t = OxmlElement('w:t'); t.text = text
    new_run.append(rPr); new_run.append(t); hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def cover_block(doc, data):
    """海报封面：全宽深蓝色块 + 白字标题/副标题/日期；紧跟封面配图。"""
    tbl = doc.add_table(rows=1, cols=1); tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0); shade_cell(cell, '1F3A5F')
    cell.text = ''
    p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(data.get('title', '每日化妆品知识系统学习'))
    r.bold = True; r.font.size = Pt(20); r.font.color.rgb = WHITE; set_cjk(r)
    if data.get('subtitle'):
        s = cell.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rs = s.add_run(data['subtitle']); rs.font.size = Pt(12.5); rs.font.color.rgb = RGBColor(0xBD, 0xD7, 0xEE); set_cjk(rs)
    if data.get('meta'):
        m = cell.add_paragraph(); m.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rm = m.add_run(data['meta']); rm.font.size = Pt(9.5); rm.font.color.rgb = RGBColor(0xD9, 0xD9, 0xD9); set_cjk(rm)
    for img in data.get('images', []):
        if img.get('role') == 'cover' and img.get('path'):
            try:
                para = doc.add_paragraph(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.add_run().add_picture(img['path'], width=Inches(5.6))
            except Exception as e:
                print('封面图嵌入失败:', e)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def callout_poster(doc, label, text):
    """双视角高亮框：工程师=蓝底蓝条；产品经理=橙底橙条；其他=浅灰。"""
    fill = 'EAF2F8'; bar = '2E75B6'; col = BLUE
    if '产品经理' in label:
        fill = 'FDF0E4'; bar = 'C86A1E'; col = ORANGE
    tbl = doc.add_table(rows=1, cols=1); tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0); shade_cell(cell, fill); add_leftbar(cell, bar)
    cell.text = ''
    p = cell.paragraphs[0]
    r = p.add_run(label + '：'); r.bold = True; r.font.size = Pt(11.5); r.font.color.rgb = col; set_cjk(r)
    r2 = p.add_run(text); r2.font.size = Pt(10.5); set_cjk(r2)
    doc.add_paragraph()


def build(doc, data):
    style = doc.styles['Normal']; style.font.name = CJK; style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), CJK)
    cover_block(doc, data)
    for sec in data.get('sections', []):
        typ = sec.get('type')
        if typ == 'callout':
            callout_poster(doc, sec.get('label', ''), sec.get('text', ''))
        elif typ == 'h':
            h = doc.add_paragraph(); h.paragraph_format.space_before = Pt(11); h.paragraph_format.space_after = Pt(4)
            rh = h.add_run(sec['text']); rh.bold = True; rh.font.size = Pt(14); rh.font.color.rgb = DARK; set_cjk(rh)
        elif typ == 'p':
            p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(7); p.paragraph_format.line_spacing = 1.4
            rp = p.add_run(sec['text']); rp.font.size = Pt(11); set_cjk(rp)
        elif typ == 'bullets':
            for it in sec.get('items', []):
                p = doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after = Pt(3); p.paragraph_format.line_spacing = 1.3
                rp = p.add_run(it); rp.font.size = Pt(10.5); set_cjk(rp)
        elif typ == 'table':
            cap = sec.get('caption')
            if cap:
                cp = doc.add_paragraph(); cr = cp.add_run(cap); cr.bold = True; cr.font.size = Pt(10.5); cr.font.color.rgb = BLUE; set_cjk(cr)
            headers = sec.get('headers', []); rows = sec.get('rows', [])
            tbl = doc.add_table(rows=1, cols=len(headers)); tbl.style = 'Table Grid'; tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, htext in enumerate(headers):
                set_cell_text(tbl.cell(0, i), htext, bold=True, color=WHITE, size=10.5, fill='2E75B6')
            for ridx, rrow in enumerate(rows):
                cells = tbl.add_row().cells
                z = 'EEF3F8' if ridx % 2 == 0 else None
                for i, val in enumerate(rrow):
                    set_cell_text(cells[i], val, size=10, fill=z)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
    # 附图（非封面图）
    diags = [i for i in data.get('images', []) if i.get('role') != 'cover' and i.get('path')]
    if diags:
        hp = doc.add_paragraph(); hp.paragraph_format.space_before = Pt(10)
        rhp = hp.add_run('附图'); rhp.bold = True; rhp.font.size = Pt(12.5); rhp.font.color.rgb = DARK; set_cjk(rhp)
        for img in diags:
            try:
                para = doc.add_paragraph(); para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.add_run().add_picture(img['path'], width=Inches(5.0))
                if img.get('caption'):
                    cp = doc.add_paragraph(); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cr = cp.add_run(img['caption']); cr.font.size = Pt(9); cr.font.color.rgb = GREY; set_cjk(cr)
            except Exception as e:
                print('配图嵌入失败:', e)
    if data.get('footer'):
        f = doc.add_paragraph(); f.paragraph_format.space_before = Pt(10)
        pPr = f._p.get_or_add_pPr(); pbdr = OxmlElement('w:pBdr'); top = OxmlElement('w:top')
        top.set(qn('w:val'), 'single'); top.set(qn('w:sz'), '6'); top.set(qn('w:space'), '1'); top.set(qn('w:color'), 'BFBFBF')
        pbdr.append(top); pPr.append(pbdr)
        rf = f.add_run('信源：' + data['footer']); rf.font.size = Pt(8.5); rf.font.color.rgb = GREY; set_cjk(rf)
    refs = data.get('references') or []
    if refs:
        h = doc.add_paragraph(); h.paragraph_format.space_before = Pt(12); h.paragraph_format.space_after = Pt(4)
        rh = h.add_run('参考资料与出处链接'); rh.bold = True; rh.font.size = Pt(12.5); rh.font.color.rgb = DARK; set_cjk(rh)
        for i, ref in enumerate(refs, 1):
            p = doc.add_paragraph(style='List Number'); p.paragraph_format.space_after = Pt(2)
            title = ref.get('title', ''); url = ref.get('url', '')
            if url:
                p.add_run(f'{i}. ').font.size = Pt(10)
                add_hyperlink(p, title, url)
                rurl = p.add_run('  ' + url); rurl.font.size = Pt(9); rurl.font.color.rgb = GREY; set_cjk(rurl)
            else:
                rt = p.add_run(f'{i}. {title}'); rt.font.size = Pt(10); set_cjk(rt)


def main():
    if len(sys.argv) < 3:
        print("usage: python3 make_learning_docx.py <content.json> <out.docx>"); sys.exit(1)
    with open(sys.argv[1], encoding='utf-8') as f:
        data = json.load(f)
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8); section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85); section.right_margin = Inches(0.85)
    build(doc, data)
    doc.save(sys.argv[2])
    print("saved:", sys.argv[2])


if __name__ == '__main__':
    main()
