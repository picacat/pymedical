# 掛號機退出密碼視窗
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSizePolicy, QSpacerItem,
                             QVBoxLayout)
from PyQt5.QtCore import Qt
from libs import system_utils


class PasswordDialog(QDialog):
    TEXT_FONT = "jf open 粉圓 2.1"
    FONT_SIZE = 42

    BUTTON_FONT = "jf open 粉圓 2.1"
    BUTTON_FONT_SIZE = 24
    BUTTON_HEIGHT = 80

    RED = '#e4442e'
    DARK_GREEN = '#1e4f0a'
    LIGHT_GREEN = '#4bab56'
    BUTTON_FONT_COLOR = DARK_GREEN

    STYLE_SHEET = f"""
        background-color: {BUTTON_FONT_COLOR};  /* 正常狀態背景顏色 */
        border: 2px solid {BUTTON_FONT_COLOR};  /* 邊框顏色 */
        border-radius: 10px;        /* 圓角 */
        color: white;               /* 字體顏色 */
        font: 75 {BUTTON_FONT_SIZE}pt "{BUTTON_FONT}";
    """

    def __init__(self, correct_password, parent=None):
        super().__init__(parent)
        self.correct_password = correct_password
        self.setWindowTitle("輸入密碼")
        self.setFixedSize(400, 600)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)  # 無邊框

        # 密碼框
        self.password_label = QLabel("請輸入密碼：", self)
        self.password_label.setAlignment(Qt.AlignCenter)
        self.password_label.setStyleSheet("""
            QLabel {
                font: 75 24pt "源泉圓體月 H";  /* 設置字體和字號 */
                font-weight: bold;
                color: #333333;  /* 字體顏色 */
                background-color: #f0f0f0;  /* 背景顏色 */
                padding: 10px;  /* 內邊距 */
                border-radius: 8px;  /* 圓角 */
            }
        """)  # 設置密碼標籤的樣式

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)  # 顯示為密碼
        self.password_input.setReadOnly(True)  # 禁止直接編輯，只能通過按鈕輸入
        self.password_input.setStyleSheet("""
            QLineEdit {
                font: 75 18pt "源泉圓體月 H";  /* 設置字體和字號 */
                color: #333333;  /* 字體顏色 */
                background-color: #f9f9f9;  /* 背景顏色 */
                padding: 10px;  /* 內邊距 */
                border: 2px solid #D0D0D0;  /* 邊框顏色 */
                border-radius: 8px;  /* 圓角 */
            }
        """)  # 設置密碼輸入框的樣式

        # 數字鍵盤佈局
        self.keyboard_layout = QVBoxLayout()
        self.keyboard_layout.addWidget(self.password_label)
        self.keyboard_layout.addWidget(self.password_input)

        # 定義數字鍵盤佈局
        grid_layout = QVBoxLayout()
        numbers = [
            ('1', '2', '3'),
            ('4', '5', '6'),
            ('7', '8', '9'),
            ('清除', '0', '確定')
        ]

        for row in numbers:
            row_layout = QHBoxLayout()
            for key in row:
                button = QPushButton(key, self)
                button.setFixedSize(80, 80)
                button.setStyleSheet(self.STYLE_SHEET)
                system_utils.shadow_widget(self, button)
                button.clicked.connect(lambda _, k=key: self.handle_key_press(k))
                row_layout.addWidget(button)

            # 增加行與行之間的垂直間隔
            grid_layout.addLayout(row_layout)
            grid_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))  # 修改間隔大小

        self.keyboard_layout.addLayout(grid_layout)

        # 使用 spacer來確保數字鍵盤和取消按鈕的間距
        self.keyboard_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # 取消按鈕
        cancel_button = QPushButton("取消", self)
        cancel_button.setFixedSize(80, 80)
        cancel_button.clicked.connect(self.reject)  # 點擊取消，關閉對話框
        cancel_button.setStyleSheet(self.STYLE_SHEET)

        # 創建一個新的水平佈局來放置取消按鈕
        cancel_layout = QHBoxLayout()
        cancel_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        cancel_layout.addWidget(cancel_button)
        cancel_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # 添加取消按鈕到鍵盤佈局
        self.keyboard_layout.addLayout(cancel_layout)

        self.setLayout(self.keyboard_layout)

    def handle_key_press(self, key):
        if key == "清除":
            self.password_input.clear()
        elif key == "確定":
            self.check_password()
        else:
            self.password_input.setText(self.password_input.text() + key)

    def check_password(self):
        self.eject_coins = False
        self.eject_coin5 = False
        self.eject_coin10 = False
        self.eject_coin50 = False

        if self.password_input.text() == '16888':
            self.eject_coins = True
            self.accept()  # 正確密碼，關閉對話框
        elif self.password_input.text() == '168885':
            self.eject_coin5 = True
            self.accept()  # 正確密碼，關閉對話框
        elif self.password_input.text() == '1688810':
            self.eject_coin10 = True
            self.accept()  # 正確密碼，關閉對話框
        elif self.password_input.text() == '1688850':
            self.eject_coin50 = True
            self.accept()  # 正確密碼，關閉對話框
        elif self.password_input.text() == self.correct_password:
            self.accept()  # 正確密碼，關閉對話框
        else:
            self.password_input.clear()
            self.password_label.setText("密碼錯誤，請重試！")
