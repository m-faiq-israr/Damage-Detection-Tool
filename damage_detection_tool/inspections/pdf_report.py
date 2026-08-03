from io import BytesIO
from datetime import datetime

from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


def generate_pdf(inspection_results):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    story = []

    #####################################################
    # Title
    #####################################################

    story.append(
        Paragraph(
            "<b>CAR DAMAGE INSPECTION REPORT</b>",
            styles["Title"],
        )
    )

    story.append(Spacer(1, 0.3 * inch))

    #####################################################
    # Date
    #####################################################

    story.append(
        Paragraph(
            f"<b>Inspection Date:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 0.3 * inch))

    #####################################################
    # Summary
    #####################################################

    total_parts = len(inspection_results)
    total_new = 0

    for result in inspection_results.values():
        total_new += len(result["new_damage"])

    summary_data = [
        ["Metric", "Value"],
        ["New Damages Detected", str(total_new)],
        ["Inspection Status", "Completed"],
    ]

    summary_table = Table(summary_data, colWidths=[250, 150])

    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),

            ("GRID", (0,0), (-1,-1), 1, colors.black),

            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),

            ("ALIGN", (0,0), (-1,-1), "CENTER"),

            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

            ("BOTTOMPADDING", (0,0), (-1,0), 10),
        ])
    )

    story.append(summary_table)

    story.append(Spacer(1, 0.4 * inch))

    #####################################################
    # Results
    #####################################################

    for part, result in inspection_results.items():

        story.append(
            Paragraph(
                f"<b>{part.upper()}</b>",
                styles["Heading2"],
            )
        )

        image_row = []

            # Before Image

        if result.get("before_annotated_path"):

            before_img = Image(
                result["before_annotated_path"],
                width=2.8 * inch,
                height=2.2 * inch,
            )

            image_row.append(before_img)

        else:

            image_row.append(
                Paragraph(
                    "No Image",
                    styles["BodyText"],
                )
            )

        # After Image

        if result.get("after_annotated_path"):

            after_img = Image(
                result["after_annotated_path"],
                width=2.8 * inch,
                height=2.2 * inch,
            )

            image_row.append(after_img)

        else:

            image_row.append(
                Paragraph(
                    "No Image",
                    styles["BodyText"],
                )
            )

        image_table = Table(
            [image_row],
            colWidths=[3 * inch, 3 * inch],
        )

        image_table.setStyle(
            TableStyle([
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("BOTTOMPADDING", (0,0), (-1,-1), 12),
            ])
        )

        story.append(image_table)

        if result["new_damage"]:

            damage_data = [["Damage", "Confidence"]]

            for damage in result["new_damage"]:

                damage_data.append([
                    damage["type"],
                    f"{damage['confidence']:.2f}",
                ])

        else:

            damage_data = [
                ["Status"],
                ["No new damage detected"],
            ]

        damage_table = Table(
            damage_data,
            colWidths=[250,120],
        )

        damage_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("GRID", (0,0), (-1,-1), 1, colors.black),
                ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
                ("BOTTOMPADDING", (0,0), (-1,0), 8),
            ])
        )

        story.append(damage_table)

        story.append(
            Spacer(1, 0.35 * inch)
        )

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

    response["Content-Disposition"] = (
        'attachment; filename="inspection_report.pdf"'
    )

    return response