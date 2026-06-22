import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from libs import cshis_utils, number_utils, string_utils, system_utils, ui_utils


# 輸入分院資料
class DialogMessageBox(QtWidgets.QDialog):
    TITLE_Y = 140
    LINE1_Y = 260
    LINE2_Y = 350
    LINE3_Y = 440
    LINE4_Y = 530
    BUTTON_Y = 550
    ICON_Y = 140
    ICON_W = 160
    ICON_H = 160

    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMessageBox, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(
            os.path.join(self.parent.UI_DIR, "dialog_message_box.ui"), self
        )
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        image_file = os.path.join(
            self.parent.BASE_DIR, "joytcm_kiosk", "images", "message_box.png"
        )
        image_file = image_file.replace("\\", "/")

        self.setStyleSheet(f"""
            QDialog {{
                background-image: url({image_file});  /* 設置背景圖片路徑 */
                background-repeat: no-repeat;
                background-position: center;
                font: 75 32pt "{self.parent.TEXT_FONT}";
            }}
        """)

    # 設定信號
    def _set_signal(self):
        pass

    def _set_back_home_button(self, button_text):
        color = self.parent.DARK_GREEN
        x, y = 0, self.BUTTON_Y
        push_button = QtWidgets.QPushButton(self)
        push_button.resize(340, self.parent.BUTTON_HEIGHT)
        push_button.setText("返回首頁(10s)")
        push_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};  /* 正常狀態背景顏色 */
                border: 2px solid {color};  /* 邊框顏色 */
                border-radius: 10px;        /* 圓角 */
                color: white;               /* 字體顏色 */
                font: 75 {self.parent.BUTTON_FONT_SIZE}pt "{self.parent.BUTTON_FONT}";
            }}
        """)
        parent_width = self.width()
        button_width = push_button.width()
        x = (parent_width - button_width) // 2

        push_button.move(x, y)
        push_button.clicked.connect(self.close)

        wait_seconds = 10
        timer = QtCore.QTimer(self)
        timer.start(1000)

        def _timeout():
            nonlocal wait_seconds
            wait_seconds -= 1
            push_button.setText(f"{button_text}({wait_seconds}s)")
            if wait_seconds == 0:
                timer.stop()
                self.close()

        timer.timeout.connect(_timeout)

    def set_no_iccard(self):
        system_utils.set_label(
            self,
            "系統未偵測到健保卡！",
            0,
            self.TITLE_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請重新插入健保卡進行預約報到",
            0,
            self.LINE1_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        system_utils.set_label(
            self,
            "（未帶健保卡請至櫃檯進行報到）",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.LIGHT_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_not_on_time(self):
        png_filename = self._get_png_file_name("cancel.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_W,
            center=True,
        )
        system_utils.set_label(
            self,
            "您已超過預約截止時間報到！",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請找現場服務人員協助",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.LIGHT_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_write_iccard_error(self, errror_code):
        try:
            error_message = cshis_utils.ERROR_MESSAGE[errror_code][0]
        except Exception:
            error_message = "未知錯誤"

        system_utils.set_label(
            self,
            "健保卡寫卡錯誤！",
            0,
            self.TITLE_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            f"錯誤原因: {error_message}",
            0,
            self.LINE1_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        system_utils.set_label(
            self,
            "（請帶健保卡請至櫃檯進行報到）",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.LIGHT_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_no_patient(self):
        system_utils.set_label(
            self,
            "系統找不到您的資料！",
            0,
            self.TITLE_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請攜帶健保卡至櫃檯辦理初診掛號",
            0,
            self.LINE1_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_no_reservation(self):
        # system_utils.set_label(
        #     self, '預約系統查無您的預約記錄！', 0, self.TITLE_Y,
        #     self.parent.TEXT_FONT, self.parent.FONT_SIZE, self.parent.RED, center=True)
        # system_utils.set_label(
        #     self, '請攜帶健保卡找現場服務人員協助', 0, self.LINE1_Y,
        #     self.parent.TEXT_FONT, self.parent.FONT_SIZE, self.parent.DARK_GREEN, center=True)
        # self._set_back_home_button('返回首頁')

        png_filename = self._get_png_file_name("cancel.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_W,
            center=True,
        )
        system_utils.set_label(
            self,
            "預約系統查無您的預約記錄！",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請攜帶健保卡找現場服務人員協助",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_already_arrival(self):
        system_utils.set_label(
            self,
            "您已經完成預約報到的作業！",
            0,
            self.TITLE_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "如有問題，請找現場服務人員協助",
            0,
            self.LINE1_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_not_doctor_done(self):
        png_filename = self._get_png_file_name("cancel.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_W,
            center=True,
        )
        system_utils.set_label(
            self,
            "您的批價作業尚未完成",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請稍後再進行現金繳費",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_already_payment(self):
        png_filename = self._get_png_file_name("ok.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_H,
            center=True,
        )
        system_utils.set_label(
            self,
            "您已經完成批價作業",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請勿再次繳費，謝謝",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_no_case_record(self):
        png_filename = self._get_png_file_name("cancel.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_H,
            center=True,
        )
        system_utils.set_label(
            self,
            "您本日未有看診記錄",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請稍後再進行現金繳費",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def _get_png_file_name(self, filename):
        png_name = os.path.join(self.parent.IMAGE_DIR, filename)

        return png_name

    def set_arrival_done(self):
        png_filename = self._get_png_file_name("ok.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_H,
            center=True,
        )
        system_utils.set_label(
            self,
            "預約報到完成，請查看候診螢幕",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def set_payment_done(self):
        png_filename = self._get_png_file_name("ok.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_H,
            center=True,
        )
        system_utils.set_label(
            self,
            "繳費已完成，請取回繳費收據及",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        system_utils.set_label(
            self,
            "健保卡，並稍後櫃台通知領藥",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def arrival_checkin(self, reserve_row):
        reserve_date = reserve_row["ReserveDate"].strftime("%Y-%m-%d")
        name = string_utils.get_mask_name(reserve_row["Name"])
        doctor = string_utils.xstr(reserve_row["Doctor"])
        reserve_no = number_utils.get_integer(reserve_row["ReserveNo"])
        room = number_utils.get_integer(reserve_row["Room"])

        x, y, height = 100, self.TITLE_Y, self.parent.BUTTON_HEIGHT
        font_color = self.parent.DARK_GREEN
        reserve_data = [
            f"日期：{reserve_date}",
            f"姓名：{name}",
            f"醫師：{doctor}",
            f"號碼：{reserve_no:0>3}",
            f"診間：{self.parent.ROOM_DICT[room]}",
        ]
        for i, data in enumerate(reserve_data):
            system_utils.set_label(
                self,
                data,
                x,
                y + i * height,
                self.parent.TEXT_FONT,
                self.parent.FONT_SIZE,
                font_color,
            )

        cancel_seconds = 10
        button_text = "取消預約報到"
        push_button = system_utils.set_button(
            self,
            f"{button_text}({cancel_seconds}s)",
            "white",
            100,
            self.BUTTON_Y,
            self.parent.BUTTON_FONT,
            self.parent.RED,
            self.parent.BUTTON_FONT_SIZE,
            430,
            self.parent.BUTTON_HEIGHT,
            lambda: self._set_arrival(False),
        )

        timer = QtCore.QTimer(self)
        timer.start(1000)

        def _timeout():
            nonlocal cancel_seconds
            cancel_seconds -= 1
            push_button.setText(f"{button_text}({cancel_seconds}s)")
            if cancel_seconds == 0:
                timer.stop()
                self._set_arrival(False)

        timer.timeout.connect(_timeout)

        system_utils.set_button(
            self,
            "確定預約報到",
            "white",
            560,
            self.BUTTON_Y,
            self.parent.BUTTON_FONT,
            self.parent.DARK_GREEN,
            self.parent.BUTTON_FONT_SIZE,
            340,
            self.parent.BUTTON_HEIGHT,
            lambda: self._set_arrival(True),
        )

    def _set_arrival(self, arrival):
        self.arrival = arrival
        self.close()

    def get_arrival(self):
        return self.arrival

    def query_self_pay_case(
        self, reserve_row, start_date, end_date, pres_days, remain_days
    ):
        name = string_utils.xstr(reserve_row["Name"])

        x, y, height = 45, self.TITLE_Y, self.parent.BUTTON_HEIGHT
        font_color = self.parent.DARK_GREEN
        highlight_color = self.parent.LIGHT_GREEN
        reserve_data = [
            f'''{name}在<font color="{highlight_color}">{start_date}</font>開了
                <font color="{highlight_color}">{pres_days}日</font>藥''',
            f'''至<font color="{highlight_color}">{end_date}</font>
                為止尚有<font color="{highlight_color}">{remain_days}</font>日藥未服用''',
            f'完畢，依健保署規範<font color="{highlight_color}">今日看診需使用</font>',
            f'<font color="{highlight_color}">全自費身份看診。</font>',
        ]
        for i, data in enumerate(reserve_data):
            system_utils.set_label(
                self,
                data,
                x,
                y + i * height,
                self.parent.TEXT_FONT,
                self.parent.FONT_SIZE,
                font_color,
            )

        cancel_seconds = 30
        button_text = "不接受自費看診"
        push_button = system_utils.set_button(
            self,
            f"{button_text}({cancel_seconds}s)",
            "white",
            100,
            self.BUTTON_Y,
            self.parent.BUTTON_FONT,
            self.parent.RED,
            self.parent.BUTTON_FONT_SIZE,
            430,
            self.parent.BUTTON_HEIGHT,
            lambda: self._set_self_pay(False),
        )
        push_button.clicked.connect(self.close)

        timer = QtCore.QTimer(self)
        timer.start(1000)

        def _timeout():
            nonlocal cancel_seconds
            cancel_seconds -= 1
            push_button.setText(f"{button_text}({cancel_seconds}s)")
            if cancel_seconds == 0:
                timer.stop()
                self._set_self_pay(False)

        timer.timeout.connect(_timeout)

        system_utils.set_button(
            self,
            "接受自費看診",
            "white",
            560,
            self.BUTTON_Y,
            self.parent.BUTTON_FONT,
            self.parent.DARK_GREEN,
            self.parent.BUTTON_FONT_SIZE,
            340,
            self.parent.BUTTON_HEIGHT,
            lambda: self._set_self_pay(True),
        )

    def _set_self_pay(self, self_pay):
        self.self_pay = self_pay
        self.close()

    def get_self_pay_case(self):
        return self.self_pay

    def set_in_progress(self):
        png_filename = self._get_png_file_name("in_progress.png")
        system_utils.set_image(
            self, png_filename, 420, 200, width=180, height=180, center=False
        )

        system_utils.set_label(
            self,
            "健保卡讀卡中...",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        system_utils.set_label(
            self,
            "請勿取出您的健保卡",
            0,
            self.LINE4_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )

    def set_vhc_in_progress(self):
        png_filename = self._get_png_file_name("qr-code.png")
        system_utils.set_image(
            self, png_filename, 420, 200, width=180, height=180, center=False
        )

        system_utils.set_label(
            self,
            "虛擬健保卡讀卡中...",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        system_utils.set_label(
            self,
            "請掃描虛擬健保卡的QR Code",
            0,
            self.LINE4_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )

    def set_cancel_not_today(self):
        png_filename = self._get_png_file_name("cancel.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_W,
            center=True,
        )
        system_utils.set_label(
            self,
            "預約系統不開放取消當日預約",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.RED,
            center=True,
        )
        system_utils.set_label(
            self,
            "請聯繫現場服務人員",
            0,
            self.LINE3_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")

    def cancel_reservation(self, reserve_row):
        reserve_date = reserve_row["ReserveDate"].strftime("%Y-%m-%d")
        name = string_utils.get_mask_name(reserve_row["Name"])
        doctor = string_utils.xstr(reserve_row["Doctor"])
        reserve_no = number_utils.get_integer(reserve_row["ReserveNo"])
        room = number_utils.get_integer(reserve_row["Room"])

        x, y, height = 100, self.TITLE_Y, self.parent.BUTTON_HEIGHT
        font_color = self.parent.DARK_GREEN
        reserve_data = [
            f"日期：{reserve_date}",
            f"姓名：{name}",
            f"醫師：{doctor}",
            f"號碼：{reserve_no:0>3}",
            f"診間：{self.parent.ROOM_DICT[room]}",
        ]
        for i, data in enumerate(reserve_data):
            system_utils.set_label(
                self,
                data,
                x,
                y + i * height,
                self.parent.TEXT_FONT,
                self.parent.FONT_SIZE,
                font_color,
            )

        cancel_seconds = 10
        button_text = "返回首頁"
        push_button = system_utils.set_button(
            self,
            f"{button_text}({cancel_seconds}s)",
            "white",
            100,
            self.BUTTON_Y,
            self.parent.BUTTON_FONT,
            self.parent.DARK_GREEN,
            self.parent.BUTTON_FONT_SIZE,
            430,
            self.parent.BUTTON_HEIGHT,
            lambda: self._set_cancel(False),
        )

        timer = QtCore.QTimer(self)
        timer.start(1000)

        def _timeout():
            nonlocal cancel_seconds
            cancel_seconds -= 1
            push_button.setText(f"{button_text}({cancel_seconds}s)")
            if cancel_seconds == 0:
                timer.stop()
                self._set_cancel(False)

        timer.timeout.connect(_timeout)

        system_utils.set_button(
            self,
            "確定取消預約",
            "white",
            560,
            self.BUTTON_Y,
            self.parent.BUTTON_FONT,
            self.parent.RED,
            self.parent.BUTTON_FONT_SIZE,
            340,
            self.parent.BUTTON_HEIGHT,
            lambda: self._set_cancel(True),
        )

    def _set_cancel(self, cancel):
        self.cancel = cancel
        self.close()

    def get_cancel(self):
        return self.cancel

    def set_cancel_done(self):
        png_filename = self._get_png_file_name("ok.png")
        system_utils.set_image(
            self,
            png_filename,
            0,
            self.ICON_Y,
            width=self.ICON_W,
            height=self.ICON_H,
            center=True,
        )
        system_utils.set_label(
            self,
            "您的預約取消完成，請取回健保卡",
            0,
            self.LINE2_Y,
            self.parent.TEXT_FONT,
            self.parent.FONT_SIZE,
            self.parent.DARK_GREEN,
            center=True,
        )
        self._set_back_home_button("返回首頁")
