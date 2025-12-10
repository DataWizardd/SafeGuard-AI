import os
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

# --- [설정] 폰트 및 컬러 팔레트 ---
try:
    pdfmetrics.registerFont(TTFont('Malgun', 'C:/Windows/Fonts/Malgun.ttf'))
    pdfmetrics.registerFont(TTFont('MalgunBd', 'C:/Windows/Fonts/Malgunbd.ttf'))
    font_norm = 'Malgun'
    font_bold = 'MalgunBd'
except:
    font_norm = 'Helvetica'
    font_bold = 'Helvetica-Bold'

# 컬러 정의
COL_NAVY = (0.05, 0.15, 0.3)
COL_RED = (0.8, 0.1, 0.1)
COL_ORANGE = (0.9, 0.5, 0.1)
COL_GREEN = (0.1, 0.6, 0.3)
COL_GRAY_BG = (0.95, 0.95, 0.96)
COL_DARK_TXT = (0.2, 0.2, 0.2)

def draw_header_banner(c, width, risk_score):
    if risk_score >= 160:
        bg_col = COL_RED
        title_text = "작업 허가 반려 통보서 (High Risk)"
        sub_text = "CRITICAL RISK ALERT"
    elif risk_score >= 70:
        bg_col = COL_ORANGE
        title_text = "조건부 작업 허가서 (Medium Risk)"
        sub_text = "CONDITIONAL APPROVAL REQUIRED"
    else:
        bg_col = COL_GREEN
        title_text = "일반 작업 허가서 (Low Risk)"
        sub_text = "STANDARD WORK PERMIT"

    c.setFillColorRGB(*bg_col)
    c.rect(0, A4[1] - 80, width, 80, stroke=0, fill=1)

    c.setFillColorRGB(1, 1, 1)
    c.setFont(font_bold, 22)
    c.drawCentredString(width / 2, A4[1] - 45, title_text)
    c.setFont(font_norm, 10)
    c.drawCentredString(width / 2, A4[1] - 65, f"SafeGuard-AI | {sub_text}")

def draw_section_title(c, y, text):
    c.setFillColorRGB(*COL_NAVY)
    c.setFont(font_bold, 12)
    c.drawString(50, y, text)
    c.setStrokeColorRGB(*COL_NAVY)
    c.setLineWidth(1)
    c.line(50, y - 5, 545, y - 5)

def draw_footer(c, width):
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(0.5)
    c.line(50, 40, 545, 40)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont(font_norm, 8)
    c.drawCentredString(width / 2, 25, "본 문서는 SafeGuard-AI 지능형 안전 시스템에 의해 생성되었으며, 관리자 서명 후 효력이 발생합니다.")

def generate_permit_pdf(risk_score, risk_level, reason_summary, user_input):
    
    if not os.path.exists("./outputs"):
        os.makedirs("./outputs")
    
    filename = f"./outputs/Permit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # 1. 상단 배너
    draw_header_banner(c, width, risk_score)
    current_y = height - 110

    # 2. 기본 정보 (회색 박스)
    c.setFillColorRGB(*COL_GRAY_BG)
    c.rect(40, current_y - 90, width - 80, 100, stroke=0, fill=1)
    
    c.setFillColorRGB(*COL_NAVY)
    c.setFont(font_bold, 11)
    c.drawString(60, current_y - 20, "■ 발행 정보")
    
    c.setFillColorRGB(*COL_DARK_TXT)
    c.setFont(font_norm, 10)
    c.drawString(60, current_y - 40, f"발행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    
    input_prefix = "신청 작업: "
    full_input = input_prefix + user_input
    wrapped_input = textwrap.wrap(full_input, width=65) 
    
    text_y = current_y - 55
    for line in wrapped_input:
        c.drawString(60, text_y, line)
        text_y -= 14
        if text_y < current_y - 90: break 
        
    current_y -= 120

    # 3. 위험성 평가 결과
    draw_section_title(c, current_y, "1. 정량적 위험성 평가 결과 (Fine-Kinney)")
    current_y -= 30

    if risk_score >= 160:
        box_col = COL_RED
        bg_tint = (1, 0.9, 0.9)
    elif risk_score >= 70:
        box_col = COL_ORANGE
        bg_tint = (1, 0.95, 0.8)
    else:
        box_col = COL_GREEN
        bg_tint = (0.9, 1, 0.9)
        
    box_height = 60
    c.setFillColorRGB(*bg_tint)
    c.setStrokeColorRGB(*box_col)
    c.setLineWidth(1.5)
    c.roundRect(50, current_y - box_height, 500, box_height, 5, stroke=1, fill=1)
    
    c.setFillColorRGB(0,0,0)
    c.setFont(font_bold, 14)
    result_text = f"종합 위험 점수: {risk_score}점  |  판정 등급: {risk_level}"
    c.drawCentredString(width / 2, current_y - 35, result_text)
    
    current_y -= (box_height + 30)

    # 4. 상세 분석 및 조치 사항
    draw_section_title(c, current_y, "2. AI 상세 분석 및 필수 안전 조치")
    current_y -= 25
    
    c.setFillColorRGB(*COL_DARK_TXT)
    c.setFont(font_norm, 10)
    
    clean_summary = reason_summary.replace('**', '').replace('##', '').replace('__', '')
    paragraphs = clean_summary.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip(): continue
        
        # [수정 2] 본문 내용 줄바꿈 너비 축소 (75 -> 50)
        # 한글 50자는 A4 용지 너비에 딱 맞습니다.
        wrapped_lines = textwrap.wrap(paragraph, width=60)
        
        for line in wrapped_lines:
            if current_y < 220:
                c.setFont(font_norm, 8)
                c.drawRightString(545, 50, "(다음 페이지에 계속...)")
                draw_footer(c, width)
                c.showPage()
                current_y = height - 60
                c.setFont(font_norm, 10)
                c.setFillColorRGB(*COL_DARK_TXT)

            c.drawString(50, current_y, line)
            current_y -= 14
        current_y -= 5

    # 5. 필수 보호구 체크리스트
    checklist_y = 180 
    if current_y < checklist_y + 20: 
        draw_footer(c, width)
        c.showPage()
    
    draw_section_title(c, checklist_y, "3. 필수 안전 보호구 및 현장 확인 (작업자 기재)")
    checklist_y -= 25
    
    c.setFont(font_norm, 9)
    checklist_items = [
        "안전모 (턱끈 체결)", "보안경 / 보안면", "안전화",
        "방독/방진 마스크", "안전장갑 (작업용)", "기타 (           )"
    ]
    
    start_x = 50
    col_width = 160
    
    for i, item in enumerate(checklist_items):
        x_pos = start_x + (i * col_width)
        c.setStrokeColorRGB(0.3, 0.3, 0.3)
        c.setLineWidth(1)
        c.rect(x_pos, checklist_y - 10, 12, 12, stroke=1, fill=0)
        c.setFillColorRGB(*COL_DARK_TXT)
        c.drawString(x_pos + 18, checklist_y - 8, item)
        
        if i == 2:
             checklist_y -= 25
             start_x = 50 - (3 * col_width)
    
    c.setFont(font_bold, 10)
    c.drawString(350, 90, "현장 안전 감독자:")
    c.setStrokeColorRGB(0,0,0)
    c.line(450, 90, 545, 90)

    draw_footer(c, width)
    c.save()
    return filename