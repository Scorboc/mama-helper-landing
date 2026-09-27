from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

root=Path(__file__).resolve().parents[1]
source=root/'docs/CHATGPT_CONTINUATION_RU.md'
out=root/'output/pdf/chatgpt-continuation-mama-helper.pdf'
pdfmetrics.registerFont(TTFont('ArialRU','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialRUBold','C:/Windows/Fonts/arialbd.ttf'))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleRU',parent=styles['Title'],fontName='ArialRUBold',fontSize=22,leading=28,alignment=TA_CENTER,textColor=colors.HexColor('#3b2b63'),spaceAfter=12))
styles.add(ParagraphStyle(name='H1RU',parent=styles['Heading1'],fontName='ArialRUBold',fontSize=15,leading=19,textColor=colors.HexColor('#3b2b63'),spaceBefore=13,spaceAfter=7))
styles.add(ParagraphStyle(name='H2RU',parent=styles['Heading2'],fontName='ArialRUBold',fontSize=12,leading=16,textColor=colors.HexColor('#5b437f'),spaceBefore=9,spaceAfter=4))
styles.add(ParagraphStyle(name='BodyRU',parent=styles['BodyText'],fontName='ArialRU',fontSize=9.2,leading=13,spaceAfter=5,textColor=colors.HexColor('#202124')))
styles.add(ParagraphStyle(name='SmallRU',parent=styles['BodyText'],fontName='ArialRU',fontSize=8,leading=10,textColor=colors.HexColor('#666666')))
styles.add(ParagraphStyle(name='CodeRU',parent=styles['BodyText'],fontName='ArialRU',fontSize=8.2,leading=11,leftIndent=10,rightIndent=10,backColor=colors.HexColor('#f2f0f7'),borderPadding=6,spaceBefore=3,spaceAfter=7))

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def inline(s):
    s=esc(s); s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s); return re.sub(r'`(.+?)`',r'<font name="ArialRUBold">\1</font>',s)

lines=source.read_text(encoding='utf-8').splitlines(); story=[]; bullets=[]; code=[]; in_code=False
def flush():
    global bullets
    if bullets:
        story.append(ListFlowable([ListItem(Paragraph(inline(x),styles['BodyRU']),leftIndent=10) for x in bullets],bulletType='bullet',leftIndent=16,bulletFontName='ArialRU',bulletFontSize=6,spaceAfter=5)); bullets=[]
for line in lines:
    if line.startswith('```'):
        if not in_code: flush(); in_code=True; code=[]
        else: story.append(Paragraph(esc('\n'.join(code)).replace('\n','<br/>'),styles['CodeRU'])); in_code=False
        continue
    if in_code: code.append(line); continue
    if not line.strip(): flush(); continue
    if line.startswith('# '):
        flush(); story.append(Paragraph(inline(line[2:]),styles['TitleRU'])); story.append(Paragraph('Передача проекта в другой ChatGPT · версия 27.09.2026',styles['SmallRU'])); story.append(Spacer(1,8)); continue
    if line.startswith('## '): flush(); story.append(Paragraph(inline(line[3:]),styles['H1RU'])); continue
    if line.startswith('### '): flush(); story.append(Paragraph(inline(line[4:]),styles['H2RU'])); continue
    if line.startswith('- '): bullets.append(line[2:]); continue
    flush(); story.append(Paragraph(inline(line),styles['BodyRU']))
flush()
doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=16*mm,title='Передача работы в ChatGPT — Мамин помощник',author='Мамин помощник')
def footer(canvas,doc):
    canvas.saveState(); canvas.setFont('ArialRU',8); canvas.setFillColor(colors.HexColor('#777777')); canvas.drawString(18*mm,9*mm,'Мамин помощник · внутренняя инструкция'); canvas.drawRightString(192*mm,9*mm,f'{doc.page}'); canvas.restoreState()
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(out)

