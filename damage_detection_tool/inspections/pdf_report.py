import os
from io import BytesIO
from datetime import datetime

from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


def _register_poppins_font():
    font_name = "Poppins"
    bold_font_name = "Poppins-Bold"

    registered = set(pdfmetrics.getRegisteredFontNames())
    if font_name in registered and bold_font_name in registered:
        return font_name, bold_font_name

    candidates = [
        os.path.expanduser(
            r"~\AppData\Local\Microsoft\Windows\Fonts\Poppins-Regular.ttf"
        ),
        os.path.expanduser(
            r"~\AppData\Local\Microsoft\Windows\Fonts\Poppins-Medium.ttf"
        ),
        r"C:\Windows\Fonts\Poppins-Regular.ttf",
        r"C:\Windows\Fonts\Poppins-Medium.ttf",
    ]

    regular_path = None
    bold_path = None

    for candidate in candidates:
        if os.path.exists(candidate):
            regular_path = candidate
            break

    if regular_path:
        pdfmetrics.registerFont(TTFont(font_name, regular_path))

        bold_candidate = regular_path.replace("Regular", "Bold")
        if not os.path.exists(bold_candidate):
            bold_candidate = regular_path.replace("Regular", "SemiBold")
        if not os.path.exists(bold_candidate):
            bold_candidate = regular_path.replace("Regular", "Medium")

        if os.path.exists(bold_candidate):
            pdfmetrics.registerFont(TTFont(bold_font_name, bold_candidate))
            return font_name, bold_font_name

        pdfmetrics.registerFont(TTFont(bold_font_name, regular_path))
        return font_name, bold_font_name

    return "Helvetica", "Helvetica-Bold"


def generate_pdf(inspection_results):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    font_name, bold_font_name = _register_poppins_font()
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=bold_font_name,
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0F4C81"),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=10,
    )

    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName=bold_font_name,
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F4C81"),
        spaceAfter=10,
        spaceBefore=8,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1F2937"),
    )

    story = []

    #####################################################
    # Title
    #####################################################

    story.append(Paragraph("CAR DAMAGE INSPECTION REPORT", title_style))
    story.append(
        Paragraph(
            f"Inspection Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    #####################################################
    # Summary
    #####################################################

    total_new = 0

    for result in inspection_results.values():
        total_new += len(result["new_damage"])

    summary_data = [
        ["Metric", "Value"],
        ["New Damages Detected", str(total_new)],
        ["Inspection Status", "Completed"],
    ]

    summary_table = Table(summary_data, colWidths=[3.4 * inch, 1.8 * inch])

    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_font_name),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9FAFB")),
                ("FONTNAME", (0, 1), (-1, -1), font_name),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F9FAFB")],
                ),
            ]
        )
    )

    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    #####################################################
    # Results
    #####################################################

    for part, result in inspection_results.items():

        story.append(Paragraph(part.replace("_", " ").title(), section_style))

        image_row = []

        if result.get("before_annotated_path"):
            before_img = Image(
                result["before_annotated_path"],
                width=2.8 * inch,
                height=2.2 * inch,
            )
            image_row.append(before_img)
        else:
            image_row.append(Paragraph("No Image", body_style))

        if result.get("after_annotated_path"):
            after_img = Image(
                result["after_annotated_path"],
                width=2.8 * inch,
                height=2.2 * inch,
            )
            image_row.append(after_img)
        else:
            image_row.append(Paragraph("No Image", body_style))

        image_table = Table(
            [image_row],
            colWidths=[3 * inch, 3 * inch],
        )

        image_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D1D5DB")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FCFDFF")),
                ]
            )
        )

        story.append(image_table)
        story.append(Spacer(1, 0.15 * inch))

        if result["new_damage"]:
            damage_data = [["Damage", "Confidence"]]

            for damage in result["new_damage"]:
                damage_data.append(
                    [
                        damage["type"],
                        f"{damage['confidence']:.2f}",
                    ]
                )
        else:
            damage_data = [
                ["Status"],
                ["No new damage detected"],
            ]

        damage_table = Table(
            damage_data,
            colWidths=[3.2 * inch, 1.6 * inch],
        )

        damage_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), bold_font_name),
                    ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#D1D5DB")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9FAFB")),
                    ("FONTNAME", (0, 1), (-1, -1), font_name),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        story.append(damage_table)
        story.append(Spacer(1, 0.25 * inch))

    #####################################################
    # Build PDF
    #####################################################

    doc.build(story)

    pdf = buffer.getvalue()

    buffer.close()

    response = HttpResponse(
        pdf,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = 'attachment; filename="inspection_report.pdf"'

    return response
