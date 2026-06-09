from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .logger import get_logger, log_exceptions
from .models import MedicalTerm


class Exporter(ABC):
    extension: str = ""
    description: str = ""

    @abstractmethod
    def export(self, terms: list[MedicalTerm], filepath: str | Path) -> Path:
        raise NotImplementedError


class CSVExporter(Exporter):
    extension = ".csv"
    description = "CSV file"

    @log_exceptions
    def export(self, terms: list[MedicalTerm], filepath: str | Path) -> Path:
        path = Path(filepath)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=MedicalTerm.fieldnames())
            writer.writeheader()
            for term in terms:
                writer.writerow(term.as_row())
        get_logger().info("CSV exported: %s (%d terms).", path, len(terms))
        return path


class PDFExporter(Exporter):
    extension = ".pdf"
    description = "PDF document"

    @log_exceptions
    def export(self, terms: list[MedicalTerm], filepath: str | Path) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        path = Path(filepath)
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        story = [
            Paragraph("Report: medical terms", styles["Title"]),
            Paragraph(
                f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S} &nbsp;|&nbsp; "
                f"Number of terms: {len(terms)}",
                styles["Normal"],
            ),
            Spacer(1, 0.5 * cm),
        ]

        header = ["Term", "Category", "Confidence", "Description"]
        rows = [header]
        cell = styles["BodyText"]
        for t in terms:
            rows.append(
                [
                    Paragraph(t.text, cell),
                    Paragraph(t.category, cell),
                    f"{t.score:.2f}",
                    Paragraph(t.description or "-", cell),
                ]
            )

        table = Table(rows, colWidths=[3.5 * cm, 2.5 * cm, 2 * cm, 8.5 * cm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c6e91")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5f9")]),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        get_logger().info("PDF exported: %s (%d terms).", path, len(terms))
        return path


EXPORTERS: dict[str, Exporter] = {
    "CSV": CSVExporter(),
    "PDF": PDFExporter(),
}
