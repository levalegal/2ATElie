"""Export to Excel and PDF."""
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer


def export_salary_to_excel(records: list, filepath: str, period_start: date, period_end: date):
    """Export salary records to Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ведомость"
    ws.append(["Ведомость по зарплате", f"Период: {period_start} — {period_end}"])
    ws.append([])
    headers = ["ФИО", "Должность", "База", "От заказов", "По часам", "Итого"]
    ws.append(headers)
    for row in ws.iter_rows(min_row=3, max_row=3, min_col=1, max_col=6):
        for cell in row:
            cell.font = Font(bold=True)
    for rec in records:
        ws.append([
            rec.get("name", ""),
            rec.get("position", ""),
            rec.get("base", 0),
            rec.get("order_amount", 0),
            rec.get("hourly_amount", 0),
            rec.get("total", 0),
        ])
    wb.save(filepath)


def export_expenses_to_excel(records: list, filepath: str, period_start: date, period_end: date):
    """Export expenses to Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Затраты"
    ws.append(["Отчёт по затратам", f"Период: {period_start} — {period_end}"])
    ws.append([])
    headers = ["Дата", "Категория", "Сумма", "Описание"]
    ws.append(headers)
    for row in ws.iter_rows(min_row=3, max_row=3, min_col=1, max_col=4):
        for cell in row:
            cell.font = Font(bold=True)
    for rec in records:
        ws.append([
            rec.get("date", ""),
            rec.get("category", ""),
            rec.get("amount", 0),
            rec.get("description", ""),
        ])
    wb.save(filepath)


def export_salary_to_pdf(records: list, filepath: str, period_start: date, period_end: date):
    """Export salary records to PDF."""
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Ведомость по зарплате", styles["Title"]))
    story.append(Paragraph(f"Период: {period_start} — {period_end}", styles["Normal"]))
    story.append(Spacer(1, 20))
    data = [["ФИО", "Должность", "База", "От заказов", "По часам", "Итого"]]
    for rec in records:
        data.append([
            str(rec.get("name", "")),
            str(rec.get("position", "")),
            str(rec.get("base", 0)),
            str(rec.get("order_amount", 0)),
            str(rec.get("hourly_amount", 0)),
            str(rec.get("total", 0)),
        ])
    t = Table(data)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    story.append(t)
    doc.build(story)
