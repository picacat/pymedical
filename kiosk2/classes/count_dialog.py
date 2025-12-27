
# 掛號機退出密碼視窗
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout)
from PyQt5.QtCore import Qt
import json
import os
from libs import system_utils
from kiosk2.classes.password_dialog import PasswordDialog


class CountPasswordDialog(PasswordDialog):
    def __init__(self, correct_password, parent=None):
        super().__init__(correct_password, parent)
        self.setWindowTitle("輸入密碼 (清點)")
        self.password_label.setText("請輸入清點密碼：")
        
    def check_password(self):
        # 這裡只檢查管理員密碼
        # 為了簡化，使用跟退出密碼相同的密碼
        if self.password_input.text() == self.correct_password:
            self.accept()
        else:
            self.password_input.clear()
            self.password_label.setText("密碼錯誤，請重試！")


# =========================================================================
# 修改：紙鈔/硬幣計數輸入對話框 (CountDialog)
# =========================================================================

class CountDialog(QDialog):
    DARK_GREEN = '#1e4f0a'
    BUTTON_FONT = "jf open 粉圓 2.1"
    BUTTON_FONT_SIZE = 24

    # 定義 JSON 檔案路徑
    COUNT_FILE = 'kiosk_count_data.json'  # 儲存在與程式碼相同的目錄，或者使用絕對路徑

    STYLE_SHEET = f"""
        background-color: {DARK_GREEN};
        border: 2px solid {DARK_GREEN};
        border-radius: 10px;
        color: white;
        font: 75 {BUTTON_FONT_SIZE}pt "{BUTTON_FONT}";
    """

    KEYBOARD_STYLE_SHEET = f"""
        QPushButton {{
            background-color: {DARK_GREEN};
            border: 1px solid #D0D0D0;
            border-radius: 8px;
            color: white;
            font: 75 22pt "jf open 粉圓 2.1";
            min-width: 80px;
            min-height: 80px;
        }}
        QPushButton:pressed {{
            background-color: #dcdcdc;
        }}
    """

    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.setWindowTitle("清點/補鈔計數")
        # 調整尺寸，容納左右兩側佈局
        self.setFixedSize(850, 550)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        self.count_data = {
            "100_bill": 0,
            "50_coin": 0,
            "10_coin": 0,
        }
        self._load_count_data()

        self.inputs = {}  # 儲存 QLineEdit 物件
        self.target_input: QLineEdit = None  # 當前焦點所在的輸入框

        self._setup_ui()

    # -------------------------------------------------------------
    # 從 JSON 檔案讀取清點數據
    # -------------------------------------------------------------
    def _load_count_data(self):
        """從 JSON 檔案讀取清點數據，如果檔案不存在則使用預設值"""
        if os.path.exists(self.COUNT_FILE):
            try:
                with open(self.COUNT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 檢查並更新數據，確保結構正確
                    for key in self.count_data.keys():
                        if key in data:
                            self.count_data[key] = data[key]
            except json.JSONDecodeError:
                print(f"Warning: Failed to decode JSON from {self.COUNT_FILE}. Using default data.")
            except Exception as e:
                print(f"An error occurred while loading count data: {e}")
        else:
            # 如果檔案不存在，則使用預設值 (0)，並可選擇創建一個包含預設值的檔案
            print(f"Info: {self.COUNT_FILE} not found. Using default data and creating file.")
            self._write_count_data()  # 第一次執行時創建檔案

    # -------------------------------------------------------------
    # 將清點數據寫入 JSON 檔案
    # -------------------------------------------------------------
    def _write_count_data(self):
        """將 count_data 寫入 JSON 檔案"""
        try:
            with open(self.COUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.count_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "寫入錯誤", f"無法保存清點數據到檔案: {e}")
            print(f"Error saving count data: {e}")

    # -------------------------------------------------------------
    # 設置界面
    # -------------------------------------------------------------
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 標題
        title_label = QLabel("請輸入找鈔找幣機清點數量", self)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('font: 75 30pt "源泉圓體月 H"; color: #1e4f0a; font-weight: bold;')
        main_layout.addWidget(title_label)

        # 左右佈局 (輸入欄位 + 數字鍵盤)
        content_layout = QHBoxLayout()

        # 1. 左側：數量輸入欄位
        input_widget = QtWidgets.QWidget()
        input_layout = QtWidgets.QGridLayout(input_widget)
        input_layout.setSpacing(15)

        denominations = [
            ("100元紙鈔 (張):", "100_bill"),
            ("50元硬幣 (枚):", "50_coin"),
            ("10元硬幣 (枚):", "10_coin"),
        ]

        for i, (label_text, key) in enumerate(denominations):
            label = QLabel(label_text)
            label.setStyleSheet('font: 75 18pt "源泉圓體月 H"; font-weight: bold; color: #333333;')
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"存量：{self.count_data[key]}")
            line_edit.setClearButtonEnabled(True)
            line_edit.setStyleSheet("""
                QLineEdit {
                    font: 75 18pt "源泉圓體月 H";
                    font-weight: bold;
                    padding: 10px;
                    border: 1px solid #D0D0D0;
                    border-radius: 5px;
                }
            """)
            line_edit.setValidator(QtGui.QIntValidator(0, 9999))
            line_edit.setFocusPolicy(Qt.ClickFocus)

            # 將焦點事件連結到鍵盤目標設定函數
            line_edit.focusInEvent = lambda event, le=line_edit: self._line_edit_focus_in(le, event)

            input_layout.addWidget(label, i, 0)
            input_layout.addWidget(line_edit, i, 1)
            self.inputs[key] = line_edit

        content_layout.addWidget(input_widget, 1)  # 權重 1

        # 2. 右側：虛擬數字鍵盤
        self.keyboard_widget = QtWidgets.QWidget()
        self.keyboard_widget.setStyleSheet(self.KEYBOARD_STYLE_SHEET)
        content_layout.addWidget(self._create_keyboard(), 1)  # 權重 1

        main_layout.addLayout(content_layout)

        # 3. 底部：按鈕佈局 (確認/取消)
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("取消", self)
        cancel_button.setFixedSize(120, 50)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet(self.STYLE_SHEET.replace(self.DARK_GREEN, "red"))

        confirm_button = QPushButton("確認", self)
        confirm_button.setFixedSize(120, 50)
        confirm_button.clicked.connect(self._save_and_accept)
        confirm_button.setStyleSheet(self.STYLE_SHEET)

        button_layout.addStretch(1)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)

        # 預設讓第一個輸入框獲得焦點
        if self.inputs:
            list(self.inputs.values())[0].setFocus()

    # -------------------------------------------------------------
    # 創建虛擬鍵盤佈局
    # -------------------------------------------------------------
    def _create_keyboard(self):
        keyboard_layout = QtWidgets.QGridLayout(self.keyboard_widget)
        keyboard_layout.setSpacing(10)

        # 鍵盤佈局: 1-9, 0, 清除 (C), 退格 (⌫)
        keys = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('清除', 3, 0), ('0', 3, 1), ('⌫', 3, 2), # 清除和退格
        ]

        for key, row, col in keys:
            button = QPushButton(key)
            # 使用 lambda 函式將按鍵值傳遞給 _key_pressed 處理
            button.clicked.connect(lambda _, k=key: self._key_pressed(k))
            system_utils.shadow_widget(self, button)
            keyboard_layout.addWidget(button, row, col)

        return self.keyboard_widget

    # -------------------------------------------------------------
    # 鍵盤輸入事件處理
    # -------------------------------------------------------------
    def _line_edit_focus_in(self, line_edit, event):
        """處理 QLineEdit 獲得焦點的事件，並將其設定為鍵盤目標"""
        self.target_input = line_edit
        # 呼叫原始的 focusInEvent 處理邏輯
        QLineEdit.focusInEvent(line_edit, event)

    def _key_pressed(self, key):
        if not self.target_input:
            # 如果沒有輸入框被選中，提示用戶點擊輸入框
            QtWidgets.QMessageBox.warning(self, "提示", "請先點擊左側的輸入框以選擇要輸入的數量。")
            return

        current_text = self.target_input.text()

        if key.isdigit():
            # 輸入數字，並限制長度（例如不超過 4 位數，因為 validator 已經設置了 9999）
            if len(current_text) < 4:
                self.target_input.setText(current_text + key)
        elif key == '清除':
            # 清除所有
            self.target_input.clear()
        elif key == '⌫':
            # 退格
            self.target_input.setText(current_text[:-1])

    # -------------------------------------------------------------
    # 保存數據
    # -------------------------------------------------------------
    def _save_and_accept(self):
        """保存輸入的數據並接受對話框"""
        try:
            for key, input_widget in self.inputs.items():
                text = input_widget.text()
                if text != '':
                    self.count_data[key] = int(text) if text else 0

            self._write_count_data()
            self.accept()
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "錯誤", "請確保所有欄位都輸入了有效的純數字。")
