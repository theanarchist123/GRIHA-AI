from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from database.models.legal_report import LegalReport

class PDFGenerator:
    @staticmethod
    def generate_legal_report_pdf(report: LegalReport, property_title: str) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=24, spaceAfter=20, textColor=colors.HexColor("#2D5016")))
        styles.add(ParagraphStyle(name='Heading2Custom', parent=styles['Heading2'], fontName='Helvetica-Bold', spaceBefore=15, spaceAfter=10, textColor=colors.HexColor("#1C1C1C")))
        styles.add(ParagraphStyle(name='BodyCustom', parent=styles['BodyText'], spaceAfter=10, fontSize=11, leading=14))
        
        # Risk verdict color
        verdict = report.overall_risk.lower()
        verdict_color = colors.green if verdict == "clean" else colors.orange if verdict == "caution" else colors.red
        styles.add(ParagraphStyle(name='Verdict', parent=styles['BodyText'], spaceAfter=20, fontSize=14, fontName='Helvetica-Bold', textColor=verdict_color))
        
        Story = []
        
        Story.append(Paragraph(f"Legal Verification Report", styles['CustomTitle']))
        Story.append(Paragraph(f"Property: {property_title}", styles['Heading2Custom']))
        
        Story.append(Paragraph(f"Overall Verdict: {report.overall_risk.upper()}", styles['Verdict']))
        
        if report.plain_english_summary:
            Story.append(Paragraph("Summary", styles['Heading2Custom']))
            Story.append(Paragraph(report.plain_english_summary, styles['BodyCustom']))

        Story.append(Paragraph("RERA Status", styles['Heading2Custom']))
        Story.append(Paragraph(f"<b>Status:</b> {report.rera.get('status', 'Unknown')}", styles['BodyCustom']))
        if report.rera.get('number'):
            Story.append(Paragraph(f"<b>Reg No:</b> {report.rera.get('number')}", styles['BodyCustom']))
        if report.rera.get('complaints'):
            Story.append(Paragraph(f"<b>Complaints:</b> {report.rera.get('complaints')}", styles['BodyCustom']))
        
        Story.append(Paragraph("Encumbrance (Title Clear)", styles['Heading2Custom']))
        Story.append(Paragraph(f"<b>Status:</b> {report.encumbrance.get('status', 'Unknown')}", styles['BodyCustom']))
        if report.encumbrance.get('details'):
            Story.append(Paragraph(f"<b>Details:</b> {report.encumbrance.get('details')}", styles['BodyCustom']))
        
        Story.append(Paragraph("Property Tax", styles['Heading2Custom']))
        Story.append(Paragraph(f"<b>Status:</b> {report.property_tax.get('status', 'Unknown')}", styles['BodyCustom']))
        if report.property_tax.get('details'):
            Story.append(Paragraph(f"<b>Details:</b> {report.property_tax.get('details')}", styles['BodyCustom']))
        
        Story.append(Paragraph("Builder Track Record", styles['Heading2Custom']))
        Story.append(Paragraph(f"<b>Status:</b> {report.builder_track_record.get('status', 'Unknown')}", styles['BodyCustom']))
        if report.builder_track_record.get('details'):
            Story.append(Paragraph(f"<b>Details:</b> {report.builder_track_record.get('details')}", styles['BodyCustom']))
        
        doc.build(Story)
        buffer.seek(0)
        return buffer
