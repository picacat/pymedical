import sys
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt
import importlib
import os
import datetime

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import module_utils

HOME_WIDGET = 1


# class ClockWorker(QtCore.QObject):
#     update_time = QtCore.pyqtSignal(str)

#     def run(self):
#         while True:
#             # 獲取當前時間
#             current_time = datetime.datetime.now().strftime('%Y-%m-%d - %H:%M:%S')
#             self.update_time.emit(current_time)  # 發送信號更新界面
#             QtCore.QThread.sleep(1)  # 讓線程每秒鐘執行一次

class ClockWorker(QtCore.QObject):
    update_time = QtCore.pyqtSignal(str)
    stop_signal = QtCore.pyqtSignal()  # 用於停止執行緒的信號

    def __init__(self):
        super().__init__()
        self.running = True  # 新增標誌位

    def run(self):
        while self.running:  # 檢查標誌位
            # 獲取當前時間
            current_time = datetime.datetime.now().strftime('%Y-%m-%d - %H:%M:%S')
            self.update_time.emit(current_time)  # 發送信號更新界面
            QtCore.QThread.sleep(1)  # 讓線程每秒鐘執行一次

    def stop(self):
        """停止執行緒"""
        self.running = False


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
                font: 75 20pt "源泉圓體月 H";  /* 設置字體和字號 */
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


# 悅兒親子中醫預約報到繳費機 2024.08.11
class Kiosk(QtWidgets.QMainWindow):
    BASE_DIR = os.getcwd()
    UI_DIR = os.path.join(BASE_DIR, 'kiosk1', 'ui')
    IMAGE_DIR = os.path.join(BASE_DIR, 'kiosk1', 'images')
    TEXT_FONT = "jf open 粉圓 2.1"
    FONT_SIZE = 42
    BUTTON_FONT = "jf open 粉圓 2.1"
    BUTTON_FONT_SIZE = 24
    BUTTON_HEIGHT = 80
    ROOM_DICT = {
        1: '一診',
        2: '二診',
        3: '三診',
        4: '四診',
        5: '五診',
        6: '六診',
        7: '七診',
        8: '八診',
        9: '九診',
        10: '十診',
    }

    DARK_RED = '#e4442e'
    RED = '#FF0000'
    DARK_GREEN = '#1e4f0a'
    LIGHT_GREEN = '#4bab56'

    LIGHT_TEXT_COLOR = '#333339'
    TEXT_COLOR = '#000000'

    # 初始化
    def __init__(self, parent=None, *args):
        super(Kiosk, self).__init__(parent)
        self.args = args

        try:
            config_file = args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.host = config_dict['host']
            self.database = class_utils.get_db(
                host=self.host,
                user=config_dict['user'],
                database=config_dict['database'],
                password=config_dict['password'],
                charset=config_dict['charset'],
                buffered=config_dict['buffered'],
            )
            self.server_ip = config_dict['host']
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(self.database, self.config_file)
        self.ui = None
        self.clinic_name = self.system_settings.field('院所名稱')
        self.clinic_name = self.clinic_name.replace('診所', '')

        # os.system('C:\\NHI\\UTILITY\\csResetFsim.exe')
        self.ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        self.socket_client = class_utils.get_socket_client()

        self._set_ui()
        self._set_signal()
        self.close_kiosk_slot()

    # 解構
    def __del__(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_KIOSK, self)
        self.ui.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # 無視窗邊框
        self.set_background()
        self._set_clock()

        self._set_stacked_widget()

    def close_kiosk_slot(self):
        kiosk = class_utils.get_jetway(self.system_settings)
        kiosk.close_cash_in_machine()
        del kiosk

    def set_background(self):
        self.exit_area = QtCore.QRect(0, 0, 100, 100)
        self.click_count = 0
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(2000)  # 2 秒
        self.timer.timeout.connect(self.reset_click_count)
        self.mousePressEvent = self.label_clicked

    def label_clicked(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.exit_area.contains(event.pos()):
            self.timer.start()
            self.click_count += 1
            if self.click_count >= 5:
                self.show_password_dialog()
        else:
            # 點擊不在區域內，立即歸零
            self.reset_click_count()

    def show_password_dialog(self):
        dialog = PasswordDialog("1234", self)

        if dialog.exec_() == QDialog.Accepted:
            kiosk = class_utils.get_jetway(self.system_settings)
            if dialog.eject_coins:
                kiosk.clear_coin_out_machine(50)
                kiosk.clear_coin_out_machine(10)
                kiosk.clear_coin_out_machine(5)
            elif dialog.eject_coin5:
                kiosk.clear_coin_out_machine(5)
            elif dialog.eject_coin10:
                kiosk.clear_coin_out_machine(10)
            elif dialog.eject_coin50:
                kiosk.clear_coin_out_machine(50)

            kiosk.close_cash_in_machine()
            del kiosk

            self.close_app()

    def reset_click_count(self):
        """重置點擊次數並停止計時器"""
        self.click_count = 0
        self.timer.stop()

    def _set_clock(self):
        x, y = 65, 130
        self.label_clock = QtWidgets.QLabel(self)
        self.label_clock.setFixedWidth(300)
        self.label_clock.setStyleSheet(f"""
            color: {self.TEXT_COLOR};  /* 正常狀態背景顏色 */
            font: 75 18pt "{self.TEXT_FONT}";
        """)
        self.label_clock.move(x, y)

        self.thread = QtCore.QThread()
        self.worker = ClockWorker()
        self.worker.moveToThread(self.thread)
        self.worker.update_time.connect(self.update_clock)  # 連接信號與槽

        # 啟動線程
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def update_clock(self, current_time):
        # 更新 QLabel 的文字
        self.label_clock.setText(current_time)

    # 設定信號
    def _set_signal(self):
        pass

    def close_app(self):
        self.database.close_database()
        self.ic_card.close_com()
        self.close()

    # 設定 css style
    def _set_style(self):
        system_utils.set_theme(self.ui, self.system_settings)

    def _set_stacked_widget(self):
        self._set_kiosk_home()
        self._set_kiosk_registration()
        self._set_kiosk_payment()
        self._set_kiosk_completed()

    def _set_kiosk_home(self):
        self.widget_home = module_utils.get_kiosk1_home(self, self.database, self.system_settings, self.ic_card)
        self.ui.stackedWidget.addWidget(self.widget_home)

    def _set_kiosk_registration(self):
        self.widget_registration = module_utils.get_kiosk1_registration(
            self, self.database, self.system_settings, self.ic_card
        )
        self.ui.stackedWidget.addWidget(self.widget_registration)

    def _set_kiosk_payment(self):
        self.widget_payment = module_utils.get_kiosk1_payment(
            self, self.database, self.system_settings, self.ic_card
        )
        self.ui.stackedWidget.addWidget(self.widget_payment)

    def _set_kiosk_completed(self):
        self.widget_completed = module_utils.get_kiosk1_completed(
            self, self.database, self.system_settings
        )
        self.ui.stackedWidget.addWidget(self.widget_completed)

    def open_kiosk_home(self):
        self.close_kiosk_slot()
        self.ui.stackedWidget.setCurrentIndex(0)

    def open_kiosk_registration(self, treat_type):
        self.close_kiosk_slot()
        self.ui.stackedWidget.setCurrentIndex(1)
        self.widget_registration.set_registration_data(treat_type=treat_type)

    def open_kiosk_payment(self, patient_key, treat_type, card, course, regist_fee, diag_share_fee):
        self.ui.stackedWidget.setCurrentIndex(2)
        self.widget_payment.set_payment_data(
            patient_key, treat_type, card, course, regist_fee, diag_share_fee)

    def open_kiosk_completed(self, treat_type):
        self.close_kiosk_slot()
        self.ui.stackedWidget.setCurrentIndex(3)
        self.widget_completed.set_completed(treat_type)

    # 安全模組卡認證
    def setup_ic_card(self):
        self.ic_card.close_com()
        self.ic_card.open_com()
        error_code = self.ic_card.verify_sam(show_message=False)
        if error_code != 0:
            sys.exit(0)

    def show_in_progress(self):
        from kiosk1.dialog import dialog_message_box

        module = importlib.reload(dialog_message_box)
        dialog = module.DialogMessageBox(self, self.database, self.system_settings)
        dialog.set_in_progress()
        dialog.show()

        return dialog


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_SynthesizeTouchForUnhandledMouseEvents, True)
    app.setAttribute(QtCore.Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True)

    kiosk = Kiosk()
    kiosk.showFullScreen()
    # kiosk.setup_ic_card()
    kiosk.open_kiosk_home()

    sys.exit(app.exec_())


# 程式開始
if __name__ == '__main__':
    main()
