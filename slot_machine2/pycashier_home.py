# -*- coding: UTF-8 -*-

import threading
import datetime

from PyQt5 import QtWidgets, QtCore

from libs import ui_utils
from libs import string_utils
from libs import registration_utils
from libs import date_utils
from libs import web_utils


class DetectCardThread(QtCore.QThread):
    card_detected = QtCore.pyqtSignal('QString')

    def __init__(self, parent, ic_card):
        super(DetectCardThread, self).__init__()
        self.parent = parent
        self.ic_card = ic_card

    def run(self):
        self.ic_card.close_com()
        self.ic_card.open_com()

        while True:
            QtCore.QCoreApplication.processEvents()

            error_code = self.ic_card.get_ic_card_status(manual_open_com=True)
            if error_code == 4000:
                self.ic_card.close_com()
                self.ic_card.open_com()

            if error_code == 2:
                self.ic_card.close_com()
                self.card_detected.emit('card_inserted')
                break


# 樣板 2018.01.31
class PyCashierHome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PyCashierHome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ic_card = args[2]
        self.ui = None
        self.detect_ic_thread = DetectCardThread(self, self.ic_card)
        self.detect_ic_thread.card_detected.connect(self.card_detected)

        self._set_ui()
        self._set_signal()
        self._set_doctor_schedule()
        self._set_period_timer()
        # self._play_marquee()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _close_app(self):
        self.parent.close_app()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PYCASHIER_HOME3, self)
        style = '''
            QMainWindow#WindowHome
            {border-image: url(./images/pycashier_home3.jpg);}
        '''
        self.ui.setStyleSheet(style)
        self.ui.label_doctor1.move(370, 270)
        self.ui.label_doctor2.move(370, 525)
        self.ui.label_doctor3.move(370, 775)
        self.ui.label_doctor5.move(370, 1025)

        self.ui.pushButton_reservation.setStyleSheet('''
            color: rgb(0, 0, 127);
            font-weight: bold;
        ''')

        self.ui.pushButton_reservation.move(243, 1240)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_quit.clicked.connect(self._close_app)
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

        return rows

    def _set_doctor_schedule(self):
        self.ui.label_doctor1.setText('')
        self.ui.label_doctor2.setText('')
        self.ui.label_doctor3.setText('')
        self.ui.label_doctor5.setText('')

        period = registration_utils.get_current_period(self.system_settings)
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]
        rows = self._get_doctor_schedule_rows(period, weekday)

        for row in rows:
            doctor = string_utils.xstr(row[weekday])
            doctor = ' '.join(doctor)
            if row['Room'] == 1 and doctor != '':
                self.ui.label_doctor1.setText(doctor)
            elif row['Room'] == 2 and doctor != '':
                self.ui.label_doctor2.setText(doctor)
            elif row['Room'] == 3 and doctor != '':
                self.ui.label_doctor3.setText(doctor)
            elif row['Room'] == 5 and doctor != '':
                self.ui.label_doctor5.setText(doctor)

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
        self.current_y = 590
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

    def card_detected(self, detected):
        if detected == 'card_inserted':
            self.parent.open_pycashier_registration()

    def detect_ic_card_insertion(self):
        self.detect_ic_thread.start()

    def _open_reservation_web(self):
        web_utils.open_address('http://zencmc.idv.tw')