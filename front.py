import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

API_URL = "http://127.0.0.1:8000/predict"
HEALTH_URL = "http://127.0.0.1:8000/health"


# ── Worker thread so the UI doesn't freeze during network calls ──────────────
class PredictWorker(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            resp = requests.post(API_URL, json={"text": self.text}, timeout=5)
            resp.raise_for_status()
            self.result_ready.emit(resp.json())
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit(
                "❌  Cannot reach the backend.\n"
                "Make sure backend.py is running:\n\n"
                "    python backend.py"
            )
        except Exception as exc:
            self.error_occurred.emit(f"❌  Unexpected error:\n{exc}")


# ── Stat card widget ─────────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, label: str, color: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            StatCard {{
                background: {color};
                border-radius: 10px;
                padding: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.value_label = QLabel("—")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: white;")

        self.desc_label = QLabel(label)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setFont(QFont("Segoe UI", 9))
        self.desc_label.setStyleSheet("color: rgba(255,255,255,0.80);")

        layout.addWidget(self.value_label)
        layout.addWidget(self.desc_label)

    def set_value(self, v):
        self.value_label.setText(str(v))


# ── Main window ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("String Analyser")
        self.setMinimumWidth(520)
        self.worker = None
        self._build_ui()
        self._check_health()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Title
        title = QLabel("String Analyser")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # Status bar
        self.status_label = QLabel("Checking backend…")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: grey; font-size: 11px;")
        root.addWidget(self.status_label)

        # Input row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a string here…")
        self.input_field.setFont(QFont("Segoe UI", 12))
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self._predict)

        self.predict_btn = QPushButton("Predict")
        self.predict_btn.setMinimumHeight(40)
        self.predict_btn.setMinimumWidth(100)
        self.predict_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.predict_btn.setStyleSheet("""
            QPushButton {
                background: #4f46e5;
                color: white;
                border-radius: 8px;
                padding: 0 18px;
            }
            QPushButton:hover  { background: #4338ca; }
            QPushButton:pressed { background: #3730a3; }
            QPushButton:disabled { background: #a5a5a5; }
        """)
        self.predict_btn.clicked.connect(self._predict)

        input_row.addWidget(self.input_field)
        input_row.addWidget(self.predict_btn)
        root.addLayout(input_row)

        # Stat cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_total = StatCard("Total characters", "#4f46e5")
        self.card_words  = StatCard("Words",           "#0891b2")
        self.card_ws     = StatCard("Whitespace",      "#059669")
        self.card_nws    = StatCard("Non-whitespace",  "#d97706")
        for card in (self.card_total, self.card_words, self.card_ws, self.card_nws):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        # Log / response area
        log_label = QLabel("Response log")
        log_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        root.addWidget(log_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Courier New", 10))
        self.log_box.setMinimumHeight(130)
        self.log_box.setStyleSheet(
            "background:#f8f8f8; border:1px solid #ddd; border-radius:6px;"
        )
        root.addWidget(self.log_box)

    # ── Backend health check ─────────────────────────────────────────────────
    def _check_health(self):
        try:
            r = requests.get(HEALTH_URL, timeout=2)
            if r.ok:
                self.status_label.setText("✅  Backend connected  •  http://127.0.0.1:8000")
                self.status_label.setStyleSheet("color: green; font-size: 11px;")
                return
        except Exception:
            pass
        self.status_label.setText("⚠️  Backend offline — run: python backend.py")
        self.status_label.setStyleSheet("color: #c0392b; font-size: 11px;")

    # ── Prediction ───────────────────────────────────────────────────────────
    def _predict(self):
        text = self.input_field.text()
        if not text:
            self._log("⚠️  Please enter a string first.")
            return

        self.predict_btn.setEnabled(False)
        self.predict_btn.setText("Loading…")
        self._log(f"→ POST {API_URL}\n   payload: {{'text': {text!r}}}")

        self.worker = PredictWorker(text)
        self.worker.result_ready.connect(self._on_result)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(self._reset_button)
        self.worker.start()

    def _on_result(self, data: dict):
        self.card_total.set_value(data["character_count"])
        self.card_words.set_value(data["word_count"])
        self.card_ws.set_value(data["whitespace_count"])
        self.card_nws.set_value(data["non_whitespace_count"])
        self._log(
            f"✅  Result:\n"
            f"   character_count   = {data['character_count']}\n"
            f"   word_count        = {data['word_count']}\n"
            f"   whitespace_count  = {data['whitespace_count']}\n"
            f"   non_whitespace    = {data['non_whitespace_count']}"
        )

    def _on_error(self, msg: str):
        self._log(msg)

    def _reset_button(self):
        self.predict_btn.setEnabled(True)
        self.predict_btn.setText("Predict")

    def _log(self, msg: str):
        self.log_box.append(msg + "\n")


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())