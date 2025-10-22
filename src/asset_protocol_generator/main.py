from __future__ import annotations
import sys
import base64
from pathlib import Path
from datetime import date
from typing import List, cast

from PySide6.QtCore import Qt, QUrl, QIODevice
from PySide6.QtGui import QAction, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QTextEdit, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QSplitter, QFileDialog, QMessageBox, QLabel, QFrame, QCheckBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from .renderer import TemplateRenderer, ProtocolData, Employee, Item, load_file_as_b64, Mode
from .license_gate import is_usage_allowed

APP_NAME = "Asset Protocol Generator"


class SignaturePad(QFrame):
    """Einfache Zeichenfläche für Unterschriften, liefert PNG als Base64."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setMinimumHeight(100)
        self._image: QImage | None = None
        self._last_pos = None
        self._init_canvas()

    def _init_canvas(self) -> None:
        self._image = QImage(600, 140, QImage.Format.Format_ARGB32)
        self._image.fill(0xFFFFFFFF)

    def paintEvent(self, event):  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), 0xFFFFFFFF)
        if self._image is not None:
            p.drawImage(0, 0, self._image)

    def resizeEvent(self, event):  # type: ignore[override]
        if self._image is None:
            return
        new_img = QImage(self.width(), self.height(), QImage.Format.Format_ARGB32)
        new_img.fill(0xFFFFFFFF)
        qp = QPainter(new_img)
        qp.drawImage(0, 0, self._image)
        qp.end()
        self._image = new_img

    def _to_point(self, event):
        if hasattr(event, "position"):
            return event.position().toPoint()
        return event.pos()

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._last_pos = self._to_point(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if (event.buttons() & Qt.MouseButton.LeftButton) and self._image is not None and self._last_pos is not None:
            painter = QPainter(self._image)
            pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            curr = self._to_point(event)
            painter.drawLine(self._last_pos, curr)
            painter.end()
            self._last_pos = curr
            self.update()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._last_pos = None

    def clear(self) -> None:
        self._init_canvas()
        self.update()

    def to_base64(self) -> str | None:
        if self._image is None:
            return None
        from PySide6.QtCore import QBuffer, QByteArray
        from PySide6.QtGui import QImageWriter
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        writer = QImageWriter(buf, b"PNG")
        if not writer.write(self._image):
            buf.close()
            return None
        buf.close()
        return base64.b64encode(ba.data()).decode("ascii")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)

        # Renderer
        template_dir = Path(__file__).parent / "templates"
        self.renderer = TemplateRenderer(template_dir)
        self.logo_b64 = None
        logo_path = Path(__file__).parent / "Bilder" / "Logo.png"
        if logo_path.exists():
            self.logo_b64 = load_file_as_b64(logo_path)

        # UI
        self._build_ui()
        self._populate_demo()
        self._refresh_preview()

    def _build_ui(self) -> None:
        splitter = QSplitter()

        # Left: form
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)

        form = QFormLayout()
        self.mode = QComboBox(); self.mode.addItems(["Übergabe", "Rückgabe"])
        self.title = QLineEdit("Übergabe-/Rückgabeprotokoll")
        self.date = QLineEdit(date.today().isoformat())
        self.emp_name = QLineEdit(); self.emp_dept = QLineEdit(); self.emp_loc = QLineEdit()
        self.emp_street = QLineEdit(); self.emp_city = QLineEdit()
        self.giver_name = QLineEdit(); self.receiver_name = QLineEdit()
        self.include_agreement = QCheckBox("Vereinbarung über die Überlassung eines Dienstgerätes anhängen")
        form.addRow("Vorgang", self.mode)
        form.addRow("Titel", self.title)
        form.addRow("Datum", self.date)
        form.addRow("Mitarbeiter", self.emp_name)
        form.addRow("Abteilung", self.emp_dept)
        form.addRow("Standort", self.emp_loc)
        form.addRow("Straße", self.emp_street)
        form.addRow("PLZ/Ort", self.emp_city)
        form.addRow("Übergebende Person", self.giver_name)
        form.addRow("Empfangende Person", self.receiver_name)
        form.addRow(self.include_agreement)

        self.items = QTableWidget(0, 4)
        self.items.setHorizontalHeaderLabels(["Bezeichnung", "Seriennummer", "Zustand", "Bemerkung"])
        self.items.horizontalHeader().setStretchLastSection(True)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Position hinzufügen")
        del_btn = QPushButton("Ausgewählte löschen")
        add_btn.clicked.connect(self._add_row)
        del_btn.clicked.connect(self._del_rows)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)

        self.notes = QTextEdit(); self.notes.setPlaceholderText("Hinweise…")
        self.return_req = QTextEdit(); self.return_req.setPlaceholderText("Rückgabe-Zustand / Auflagen…")

        form_layout.addLayout(form)
        form_layout.addWidget(self.items)
        form_layout.addLayout(btn_row)
        form_layout.addWidget(self.notes)
        form_layout.addWidget(self.return_req)

        # Signatures
        sigs_row = QHBoxLayout()
        self.sig_giver = SignaturePad()
        self.sig_receiver = SignaturePad()
        sigs_row.addWidget(self._with_label("Unterschrift Übergebende", self.sig_giver))
        sigs_row.addWidget(self._with_label("Unterschrift Empfangende", self.sig_receiver))
        form_layout.addLayout(sigs_row)

        # Right: preview
        self.preview = QWebEngineView()

        splitter.addWidget(form_widget)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Toolbar
        refresh_act = QAction("Aktualisieren", self)
        refresh_act.triggered.connect(self._refresh_preview)
        export_act = QAction("Als PDF exportieren…", self)
        export_act.triggered.connect(self._export_pdf)

        tb = self.addToolBar("Aktionen")
        tb.addAction(refresh_act)
        tb.addAction(export_act)
        clear_sig_act = QAction("Unterschriften löschen", self)
        clear_sig_act.triggered.connect(self._clear_signatures)
        tb.addAction(clear_sig_act)

        # Live refresh on edits
        for w in [self.mode, self.title, self.date, self.emp_name, self.emp_dept, self.emp_loc, self.emp_street, self.emp_city, self.giver_name, self.receiver_name, self.include_agreement]:
            if hasattr(w, "textChanged"):
                w.textChanged.connect(self._refresh_preview)
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._refresh_preview)
            if hasattr(w, "stateChanged"):
                w.stateChanged.connect(self._refresh_preview)
        # Agreement checkbox nur bei Übergabe erlauben
        self.mode.currentIndexChanged.connect(self._update_agreement_enabled)
        self._update_agreement_enabled()
        self.notes.textChanged.connect(self._refresh_preview)
        self.return_req.textChanged.connect(self._refresh_preview)
        self.items.itemChanged.connect(lambda _: self._refresh_preview())

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

    def _populate_demo(self) -> None:
        demo = [
            ("Laptop", "SN123", "Neu", "inkl. Netzteil"),
            ("Monitor", "SN987", "Gebraucht", "24 Zoll"),
        ]
        for row in demo:
            self._add_row(row)

    def _add_row(self, values: tuple[str, str, str, str] | None = None) -> None:
        r = self.items.rowCount()
        self.items.insertRow(r)
        defaults = values or ("", "", "", "")
        for c, val in enumerate(defaults):
            item = QTableWidgetItem(val)
            self.items.setItem(r, c, item)

    def _del_rows(self) -> None:
        for idx in sorted({i.row() for i in self.items.selectedIndexes()}, reverse=True):
            self.items.removeRow(idx)
        self._refresh_preview()

    def _collect_data(self) -> ProtocolData:
        rows: List[Item] = []
        for r in range(self.items.rowCount()):
            def val(c: int) -> str:
                it = self.items.item(r, c)
                return it.text() if it else ""
            rows.append(Item(name=val(0), serial=val(1), condition=val(2), note=val(3)))
        return ProtocolData(
            title=self.title.text(),
            date=self.date.text(),
            mode=cast(Mode, self.mode.currentText()),
            employee=Employee(
                name=self.emp_name.text(),
                department=self.emp_dept.text(),
                location=self.emp_loc.text(),
            ),
            items=rows,
            notes=self.notes.toPlainText(),
            return_requirements=self.return_req.toPlainText(),
            logo_b64=self.logo_b64,
            sig_giver_b64=self.sig_giver.to_base64(),
            sig_receiver_b64=self.sig_receiver.to_base64(),
            giver_name=self.giver_name.text(),
            receiver_name=self.receiver_name.text(),
            include_agreement=(self.include_agreement.isChecked() and self.mode.currentText() == "Übergabe"),
            emp_street=self.emp_street.text(),
            emp_city=self.emp_city.text(),
        )

    def _update_agreement_enabled(self) -> None:
        is_uebergabe = self.mode.currentText() == "Übergabe"
        self.include_agreement.setEnabled(is_uebergabe)
        if not is_uebergabe and self.include_agreement.isChecked():
            self.include_agreement.setChecked(False)
        # Vorschau aktualisieren
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        html = self.renderer.render_html(self._collect_data())
        self.preview.setHtml(html, baseUrl=QUrl.fromLocalFile(str(Path.cwd())))

    def _export_pdf(self) -> None:
        out, _ = QFileDialog.getSaveFileName(self, "PDF exportieren", "protokoll.pdf", "PDF (*.pdf)")
        if not out:
            return
        try:
            # Render HTML then ask QWebEngineView to print to PDF
            html = self.renderer.render_html(self._collect_data())
            def _on_load(_: bool) -> None:
                self.preview.page().printToPdf(out)
                QMessageBox.information(self, APP_NAME, f"PDF gespeichert: {out}")
                try:
                    self.preview.loadFinished.disconnect(_on_load)
                except Exception:
                    pass
            self.preview.setHtml(html)
            self.preview.loadFinished.connect(_on_load)
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"Fehler beim Export: {e}")

    def _with_label(self, text: str, widget: QWidget) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(QLabel(text))
        v.addWidget(widget)
        return w

    def _clear_signatures(self) -> None:
        self.sig_giver.clear()
        self.sig_receiver.clear()
        self._refresh_preview()


def main() -> int:
    app = QApplication(sys.argv)
    # Gate-Check: bei Nicht-Erlaubnis still ablehnen (nur "error" anzeigen)
    if not is_usage_allowed():
        QMessageBox.critical(None, APP_NAME, "error")
        return 1
    win = MainWindow()
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
