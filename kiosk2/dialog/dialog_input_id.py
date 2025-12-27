# dialog_input_id.py

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from libs import system_utils


class DialogInputID(QtWidgets.QDialog):
    def __init__(self, parent, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.id_digits = ""  # 存放使用者輸入的 9 碼數字

        self.setWindowTitle("身分證末九碼")
        self.setFixedSize(500, 700)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 提示文字
        self.label_msg = QtWidgets.QLabel("請輸入身分證末九碼", self)
        self.label_msg.setAlignment(Qt.AlignCenter)
        self.label_msg.setStyleSheet(f"""
            QLabel {{
                font: 75 36pt "{self.parent.TEXT_FONT}";
                color: {self.parent.TEXT_COLOR};
            }}
        """)
        layout.addWidget(self.label_msg)

        # 顯示輸入內容
        self.edit = QtWidgets.QLineEdit(self)
        self.edit.setReadOnly(True)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setFixedHeight(80)
        self.edit.setStyleSheet(f"""
            QLineEdit {{
                font: 100 42pt "{self.parent.TEXT_FONT}";
                border: 2px solid #D0D0D0;
                border-radius: 10px;
                background-color: #f9f9f9;
            }}
        """)
        layout.addWidget(self.edit)

        # 數字鍵盤
        grid = QtWidgets.QGridLayout()
        buttons = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("清除", 3, 0), ("0", 3, 1), ("確定", 3, 2),
        ]

        for text, r, c in buttons:
            btn = QtWidgets.QPushButton(text, self)
            btn.setFixedSize(120, 90)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.parent.DARK_GREEN};
                    border: 2px solid {self.parent.DARK_GREEN};
                    border-radius: 10px;
                    color: white;
                    font: 75 32pt "{self.parent.BUTTON_FONT}";
                }}
            """)
            system_utils.shadow_widget(self, btn)

            if text == "清除":
                btn.clicked.connect(self._on_clear)
            elif text == "確定":
                btn.clicked.connect(self._on_ok)
            else:
                btn.clicked.connect(lambda _, t=text: self._on_digit(t))

            grid.addWidget(btn, r, c)

        layout.addLayout(grid)

        # 取消按鈕（給病人想放棄時用）
        cancel_button_text = '取消'
        wait_seconds = 30

        btn_cancel = QtWidgets.QPushButton(f'{cancel_button_text}({wait_seconds}s)', self)
        btn_cancel.setFixedHeight(80)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.parent.DARK_RED};
                border: 2px solid {self.parent.DARK_RED};
                border-radius: 10px;
                color: white;
                font: 75 32pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        system_utils.shadow_widget(self, btn_cancel)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

        # 設定倒數時間===========================================================
        self.home_timer = QtCore.QTimer(self)
        self.home_timer.start(1000)

        def _timeout():
            nonlocal wait_seconds

            # 如果視窗已經被關掉 / 看不到，就不要再跑倒數
            if not self.isVisible():
                self.home_timer.stop()
                return

            wait_seconds -= 1
            btn_cancel.setText(f'{cancel_button_text}({wait_seconds}s)')
            if wait_seconds == 0:
                self.home_timer.stop()
                self._back_to_home()

        self.home_timer.timeout.connect(_timeout)

    def _stop_home_timer(self):
        if hasattr(self, 'home_timer') and self.home_timer.isActive():
            self.home_timer.stop()

    def _back_to_home(self):
        self._stop_home_timer()

        self.close()
        self.parent.open_kiosk_home()

    def _on_digit(self, d: str):
        text = self.edit.text()
        if len(text) >= 9:
            return  # 最多 9 碼

        self.edit.setText(text + d)

    def _on_clear(self):
        self.edit.clear()

    def _on_ok(self):
        text = self.edit.text()
        if not text.isdigit():
            self.label_msg.setText("請輸入正確的數字")
            return

        self.id_digits = text
        self._stop_home_timer()
        self.accept()

    def get_id_digits(self):
        return self.id_digits
