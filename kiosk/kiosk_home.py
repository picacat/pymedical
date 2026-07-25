# -*- coding: UTF-8 -*-
from PyQt5 import QtWidgets, QtCore
import datetime

from classes import smart_card
from libs import ui_utils
from libs import string_utils
from libs import registration_utils
from libs import date_utils
from libs import web_utils


# 掛號機首頁 2024.06.23
class KioskHome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KioskHome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.ui = None

        self.card_observer = smart_card.SmartCardObserver()
        self.card_observer.card_removed.connect(self._card_removed)
        self.card_observer.card_inserted.connect(self._card_inserted)

        self._set_ui()
        self._set_signal()
        self._set_doctor_schedule()
        self._set_period_timer()
        self._play_marquee()

    # 解構
    def __del__(self):
        del self.card_observer

        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _close_app(self):
        self.parent.close_app()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_KIOSK_HOME, self)
        self.set_style()

    def set_style(self):
        style = '''
            QMainWindow#WindowHome
            {border-image: url(./images/kiosk_home.jpg);}
        '''
        self.ui.setStyleSheet(style)

        style_sheet = '''
            color: rgb(0, 0, 127);
            font-weight: bold;
        '''
        self.ui.label_doctor1.setStyleSheet(style_sheet)
        self.ui.label_doctor2.setStyleSheet(style_sheet)
        self.ui.label_doctor3.setStyleSheet(style_sheet)

        self.ui.pushButton_reservation.setStyleSheet('''
            color: rgb(0, 0, 127);
            font-weight: bold;
        ''')

        x = 400
        self.ui.label_doctor1.move(x, 250)
        self.ui.label_doctor2.move(x, 570)
        self.ui.label_doctor3.move(x, 880)

        self.ui.label_doctor1.adjustSize()
        self.ui.label_doctor2.adjustSize()
        self.ui.label_doctor3.adjustSize()

        self.ui.pushButton_reservation.move(243, 1140)
        self.ui.pushButton_quit.move(15, 15)

        self.ui.label_marquee.setVisible(False)

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_quit.clicked.connect(self._close_app)
        self.ui.pushButton_reservation.clicked.connect(self._open_reservation_web)

    def _open_system_settings(self):
        self.parent.open_system_settings()

    def _registration_clicked(self):
        self.parent.open_registration_insert_card('門診掛號')

    def _charge_clicked(self):
        self.parent.open_registration_insert_card('批價給藥')

    def _reservation_arrival_clicked(self):
        self.parent.open_registration_insert_card('預約報到')

    def _get_doctor_schedule_rows(self, period, weekday):
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        available_rows = []
        sql = f'''
            SELECT * FROM doctor_schedule
            WHERE
                Period = "{period}" AND
                {weekday} IS NOT NULL AND
                LENGTH({weekday}) > 0
            GROUP BY Room
            ORDER BY Room
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            doctor = string_utils.xstr(row[weekday])
            if doctor != '':
                sql = f'''
                    SELECT * FROM temporary_schedule
                    WHERE
                        CaseDate = "{today}" AND
                        Period = "{period}" AND
                        Name = "{doctor}" AND
                        Position = "醫師" AND
                        ScheduleType = "請假"
                '''
                schedule_rows = self.database.select_record(sql)
                if len(schedule_rows) <= 0:
                    available_rows.append(row)

        sql = f'''
            SELECT * FROM temporary_schedule
            WHERE
                CaseDate = "{today}" AND
                Period = "{period}" AND
                Position = "醫師" AND
                ScheduleType = "加診"
        '''
        schedule_rows = self.database.select_record(sql)
        for row in schedule_rows:
            this_row = {
                'Room': row['Room'],
                'Period': row['Period'],
                weekday: row['Name'],
            }

            available_rows.append(this_row)

        return available_rows

    def _set_doctor_schedule(self):
        self.ui.label_doctor1.setText('')
        self.ui.label_doctor2.setText('')
        self.ui.label_doctor3.setText('')

        period = registration_utils.get_current_period(self.system_settings)
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]
        rows = self._get_doctor_schedule_rows(period, weekday)

        for row in rows:
            doctor = string_utils.xstr(row[weekday])
            if row['Room'] == 1 and doctor != '':
                self.ui.label_doctor1.setText(doctor)
            elif row['Room'] == 2 and doctor != '':
                self.ui.label_doctor2.setText(doctor)
            elif row['Room'] == 3 and doctor != '':
                self.ui.label_doctor3.setText(doctor)

    def _set_period_timer(self):
        timer = QtCore.QTimer(self)
        timer.start(60000)
        timer.timeout.connect(self._set_doctor_schedule)

    def _set_marquee_list(self):
        self.marquee_list = []
        sql = '''
            SELECT * FROM system_settings
            WHERE
                Field LIKE "跑馬燈訊息-%"
            ORDER BY Field
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            marquee = self.system_settings.field('院所名稱') + ' 關心您的健康'
            self.marquee_list.append(marquee)
            return

        for row in rows:
            self.marquee_list.append(string_utils.xstr(row['Value']))

    def _play_marquee(self):
        self.ui.label_marquee.setVisible(True)

        self.current_y = 1810
        self._set_marquee_list()
        self.marquee_index = 0
        self.marquee_start = QtWidgets.QDesktopWidget().screenGeometry(-1).width() + 100

        self._set_marquee_text()

        self.current_x = self.marquee_start
        self.ui.label_marquee.move(self.current_x, self.current_y)
        self._set_timer()

    def _set_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.start(9)
        self.timer.timeout.connect(self._timeout)

    def _timeout(self):
        QtCore.QCoreApplication.processEvents()
        self.current_x -= 1
        if self.current_x <= -self.marquee_text_width:
            self.current_x = self.marquee_start
            self.marquee_index += 1
            if self.marquee_index >= len(self.marquee_list):
                self.marquee_index = 0

            self._set_marquee_text()

        self.ui.label_marquee.move(self.current_x, self.current_y)

    def _set_marquee_text(self):
        self.ui.label_marquee.setText(self.marquee_list[self.marquee_index])
        self.ui.label_marquee.adjustSize()
        self.marquee_text_width = self.ui.label_marquee.width() + 100

    def _open_reservation_web(self):
        web_utils.open_address('http://122.116.140.238:5000')

    def _card_removed(self, message):
        pass

    def _card_inserted(self, message):
        self.parent.open_kiosk_registration()
