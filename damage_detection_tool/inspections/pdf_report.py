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


def generate_pdf(
    inspection_results,
    report_type="comparison",
):

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

    # =====================================================
    # TITLE
    # =====================================================

    if report_type == "single":

        title = "CAR DAMAGE INSPECTION REPORT"

    else:

        title = "CAR DAMAGE COMPARISON REPORT"

    story.append(
        Paragraph(
            f"<b>{title}</b>",
            styles["Title"],
        )
    )

    story.append(Spacer(1, 0.3 * inch))

    # =====================================================
    # DATE
    # =====================================================

    story.append(
        Paragraph(
            "<b>Inspection Date:</b> " + datetime.now().strftime("%d-%m-%Y %H:%M"),
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 0.3 * inch))

    # =====================================================
    # SINGLE IMAGE REPORT
    # =====================================================

    if report_type == "single":

        total_damages = 0

        for result in inspection_results.values():

            total_damages += len(result.get("damage", []))

        summary_data = [
            ["Metric", "Value"],
            ["Images Inspected", str(len(inspection_results))],
            ["Damages Detected", str(total_damages)],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[250, 150],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.darkblue,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        1,
                        colors.black,
                    ),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, -1),
                        colors.whitesmoke,
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        10,
                    ),
                ]
            )
        )

        story.append(summary_table)

        story.append(Spacer(1, 0.4 * inch))

        # =================================================
        # SINGLE IMAGE RESULTS
        # =================================================

        for part, result in inspection_results.items():

            story.append(
                Paragraph(
                    f"<b>{part.replace('_', ' ').upper()}</b>",
                    styles["Heading2"],
                )
            )

            story.append(Spacer(1, 0.1 * inch))

            # ---------------------------------------------
            # ANNOTATED IMAGE
            # ---------------------------------------------

            annotated_path = result.get("annotated_path")

            if annotated_path:

                try:

                    annotated_img = Image(
                        annotated_path,
                        width=5.5 * inch,
                        height=4.0 * inch,
                    )

                    story.append(annotated_img)

                    story.append(Spacer(1, 0.2 * inch))

                except Exception as e:

                    story.append(
                        Paragraph(
                            f"Unable to load image: {e}",
                            styles["BodyText"],
                        )
                    )

            # ---------------------------------------------
            # DAMAGE TABLE
            # ---------------------------------------------

            damages = result.get("damage", [])

            if damages:

                damage_data = [
                    [
                        "Damage",
                        "Confidence",
                    ]
                ]

                for damage in damages:

                    damage_type = damage.get("type", "Unknown")

                    confidence = damage.get("confidence", 0)

                    damage_data.append(
                        [
                            damage_type,
                            f"{confidence:.2f}",
                        ]
                    )

            else:

                damage_data = [
                    ["Status"],
                    ["No damage detected"],
                ]

            damage_table = Table(
                damage_data,
                colWidths=[
                    250,
                    120,
                ],
            )

            damage_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.darkblue,
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.white,
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            1,
                            colors.black,
                        ),
                        (
                            "BACKGROUND",
                            (0, 1),
                            (-1, -1),
                            colors.whitesmoke,
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, 0),
                            8,
                        ),
                    ]
                )
            )

            story.append(damage_table)

            story.append(Spacer(1, 0.4 * inch))

    # =====================================================
    # COMPARISON REPORT
    # =====================================================

    else:

        total_parts = len(inspection_results)

        total_new = 0

        for result in inspection_results.values():

            total_new += len(result.get("new_damage", []))

        summary_data = [
            ["Metric", "Value"],
            ["New Damages Detected", str(total_new)],
        ]

        summary_table = Table(
            summary_data,
            colWidths=[250, 150],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.darkblue,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        1,
                        colors.black,
                    ),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, -1),
                        colors.whitesmoke,
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        10,
                    ),
                ]
            )
        )

        story.append(summary_table)

        story.append(Spacer(1, 0.4 * inch))

        # =================================================
        # COMPARISON RESULTS
        # =================================================

        for part, result in inspection_results.items():

            story.append(
                Paragraph(
                    f"<b>{part.upper()}</b>",
                    styles["Heading2"],
                )
            )

            image_row = []

            # ---------------------------------------------
            # BEFORE IMAGE
            # ---------------------------------------------

            before_path = result.get("before_annotated_path")

            if before_path:

                try:

                    before_img = Image(
                        before_path,
                        width=2.8 * inch,
                        height=2.2 * inch,
                    )

                    image_row.append(before_img)

                except Exception:

                    image_row.append(
                        Paragraph(
                            "Unable to load image",
                            styles["BodyText"],
                        )
                    )

            else:

                image_row.append(
                    Paragraph(
                        "No Image",
                        styles["BodyText"],
                    )
                )

            # ---------------------------------------------
            # AFTER IMAGE
            # ---------------------------------------------

            after_path = result.get("after_annotated_path")

            if after_path:

                try:

                    after_img = Image(
                        after_path,
                        width=2.8 * inch,
                        height=2.2 * inch,
                    )

                    image_row.append(after_img)

                except Exception:

                    image_row.append(
                        Paragraph(
                            "Unable to load image",
                            styles["BodyText"],
                        )
                    )

            else:

                image_row.append(
                    Paragraph(
                        "No Image",
                        styles["BodyText"],
                    )
                )

            image_table = Table(
                [image_row],
                colWidths=[
                    3 * inch,
                    3 * inch,
                ],
            )

            image_table.setStyle(
                TableStyle(
                    [
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            12,
                        ),
                    ]
                )
            )

            story.append(image_table)

            # ---------------------------------------------
            # NEW DAMAGE TABLE
            # ---------------------------------------------

            new_damage = result.get("new_damage", [])

            if new_damage:

                damage_data = [
                    [
                        "Damage",
                        "Confidence",
                    ]
                ]

                for damage in new_damage:

                    damage_data.append(
                        [
                            damage.get("type", "Unknown"),
                            f"{damage.get('confidence', 0):.2f}",
                        ]
                    )

            else:

                damage_data = [
                    ["Status"],
                    ["No new damage detected"],
                ]

            damage_table = Table(
                damage_data,
                colWidths=[
                    250,
                    120,
                ],
            )

            damage_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.darkblue,
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.white,
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            1,
                            colors.black,
                        ),
                        (
                            "BACKGROUND",
                            (0, 1),
                            (-1, -1),
                            colors.whitesmoke,
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, 0),
                            8,
                        ),
                    ]
                )
            )

            story.append(damage_table)

            story.append(Spacer(1, 0.35 * inch))

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(story)

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/pdf",
    )

    if report_type == "single":

        response["Content-Disposition"] = (
            "attachment; " 'filename="single_damage_report.pdf"'
        )

    else:

        response["Content-Disposition"] = (
            "attachment; " 'filename="car_damage_comparison_report.pdf"'
        )

    return response
