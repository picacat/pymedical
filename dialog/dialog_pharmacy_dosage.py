
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
from pygame import mixer
import serial
import sys
import time
import threading

from libs import system_utils
from libs import ui_utils
from libs import case_utils
from libs import string_utils
from libs import number_utils
from libs import prescript_utils


# 新增盤點記錄
class DialogPharmacyDosage(QtWidgets.QDialog):
    update_dosage_signal = QtCore.pyqtSignal(str)

    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPharmacyDosage, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.prescript_key = args[2]
        self.medicine_key = args[3]
        self.medicine_code = args[4]
        self.medicine_set = args[5]
        self.scale_time = args[6]
        self.qrcode = ''

        self.ui = None
        self.running = True  # 用於控制執行緒的旗標
        try:
            mixer.init()
            mixer.music.load('./icq.mp3')
            self.sound_played = False
        except Exception:
            pass

        self._set_ui()
        self._set_signal()
        self._set_data()

        com_port = self._get_com_port()
        try:
            self.ser = serial.Serial(
                port=com_port,       # 串口號
                baudrate=9600,     # 波特率，根據你的設備進行設定
                timeout=1          # 讀取超時時間
            )
        except Exception:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '電子秤有誤',
                '<h1>無法連線至電子秤，請檢查電子秤的電源是否開啟或連接線是否接妥。</h1>',
                '無法連接至電子秤.'
            )

        response = self.ser.read(10)
        if len(response) == 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '電子秤有誤',
                '<h1>無法連線至電子秤，請檢查電子秤的電源是否開啟或連接線是否接妥。</h1>',
                '無法連接至電子秤.'
            )
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()

        if self.ser:
            self.update_dosage_signal.connect(self._update_dosage_label)
            serial_thread = threading.Thread(target=self._get_weight)
            serial_thread.daemon = True
            serial_thread.start()

    def _get_com_port(self):
        com = self.system_settings.field('電子秤連接埠')
        if sys.platform == 'win32':
            com_port = f'COM{com}'
        elif sys.platform == 'linux':
            com_port = f'/dev/ttyUSB{com}'

        return com_port

    # 解構
    def __del__(self):
        self.close_all()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PHARMACY_DOSAGE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self._set_font_size()

    def _set_font_size(self):
        font_size = 18
        self.ui.setStyleSheet(f'font-family: "Microsoft JhengHei"; font-size: {font_size}pt;')

        font_size = 96
        self.ui.label_medicine_name.setStyleSheet(f'font-size: {font_size}pt; font-weight: bold')

        font_size = 64
        label_list = [
            self.ui.label_2,
            self.ui.label_3,
            self.ui.label_4,
            self.ui.label_5,
            self.ui.label_dosage,
            self.ui.label_current_dosage,
        ]
        for widget in label_list:
            widget.setStyleSheet(f'font-size: {font_size}pt;')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.keyPressEvent = self.keyPressEvent

    # def keyPressEvent(self, event):
    #     if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
    #         self._check_dosage(self.qrcode)
    #         self.qrcode = ''
    #     else:
    #         self.qrcode += event.text()

    def _check_dosage_ok(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        weight = abs(number_utils.get_float(self.total_dosage) - number_utils.get_float(self.current_weight))
        if abs(round(weight, 1)) > 0.1:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '劑量錯誤',
                '<h1>劑量誤差超過0.1，請重新調整劑量。</h1>',
                '請再確認劑量是否正確.'
            )
            return

        # if self.medicine_code != qrcode:
        #     system_utils.show_message_box(
        #         QMessageBox.Critical,
        #         '查無此藥',
        #         '<h1>查無此藥，請重新掃描.</h1>',
        #         '請再確認是否拿錯.'
        #     )
        #     return

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.accept()

    def _set_data(self):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = {self.medicine_key}
        '''
        medicine_rows = self.database.select_record(sql)
        if len(medicine_rows) <= 0:
            return

        medicine_row = medicine_rows[0]
        medicine_name = string_utils.xstr(medicine_row['MedicineName'])
        self.ui.label_medicine_name.setText(medicine_name)

        sql = f'''
            SELECT * FROM prescript
            WHERE
                PrescriptKey = {self.prescript_key}
        '''
        prescript_rows = self.database.select_record(sql)
        if len(prescript_rows) <= 0:
            return

        prescript_row = prescript_rows[0]
        dosage = number_utils.get_float(prescript_row['Dosage'])
        self.case_key = prescript_row['CaseKey']
        pres_days = case_utils.get_pres_days(self.database, self.case_key, self.medicine_set)
        self.total_dosage = round(number_utils.get_float(dosage * pres_days), 1)

        self.ui.label_dosage.setText(string_utils.xstr(self.total_dosage))
        self.ui.progressBar_scale.setMaximum(int(self.total_dosage * 100))
        self.ui.progressBar_scale.setValue(0)

    def _get_weight(self):
        last_weight = None
        self.current_weight = 0
        stable_count = 0

        while self.running:  # 只在running為True時執行
            try:
                if self.ser and self.ser.in_waiting:  # 檢查是否有資料等待讀取
                    data = self.ser.readline().decode('utf-8').strip()
                    if 'No.' in data:
                        continue

                    data = data.replace('g', '')
                    self.update_dosage_signal.emit(data)
                    current_weight = self.current_weight

                    if last_weight is not None and current_weight == last_weight:
                        stable_count += 1
                    else:
                        stable_count = 0

                    if stable_count >= (self.scale_time * 10):  # 穩定重量2.5秒  time sleep 0.01 要加上運算的損耗，大約等於0.1
                        deviation = number_utils.get_float(current_weight) - number_utils.get_float(self.total_dosage)
                        if abs(round(deviation, 1)) <= 0.1:
                            self.save_pres_extend()
                            self._beep()
                            # self._check_dosage_ok()
                            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
                            self.accept()
                            break

                        stable_count = 0

                    last_weight = current_weight

            except serial.SerialException as e:
                print(f"init com port failed: {e}")
                break

            time.sleep(0.01)

    def _update_dosage_label(self, data):
        self.current_weight = number_utils.get_float(data)
        self.ui.label_current_dosage.setText(string_utils.xstr(self.current_weight))
        weight = int(number_utils.get_float(self.current_weight) * 100)

        if weight < self.ui.progressBar_scale.maximum():
            self._display_image('./icons/emblem-synchronizing.png')
            self.sound_played = False
            self.ui.progressBar_scale.setStyleSheet(None)
            self._show_current_dosage(None)
        elif weight > self.ui.progressBar_scale.maximum():
            self._display_image('./icons/emblem-important.png')
            self.sound_played = False
            self.ui.progressBar_scale.setStyleSheet('''
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: transparent; /* 無進度時背景透明 */
                }
                QProgressBar::chunk {
                    background-color: red;  /* 有進度時的顏色 */
                    width: 20px;
                }
            ''')
            self._show_current_dosage('red')
        else:
            self.ui.progressBar_scale.setStyleSheet('''
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: transparent; /* 無進度時背景透明 */
                }
                QProgressBar::chunk {
                    background-color: green;  /* 有進度時的顏色 */
                    width: 20px;
                }
            ''')
            self._show_current_dosage('green')
            if not self.sound_played:
                self._display_image('./icons/emblem-default.png')

        self.ui.progressBar_scale.setValue(weight)

        percentage = (weight / self.ui.progressBar_scale.maximum()) * 100
        self.ui.progressBar_scale.setFormat(f"{percentage:.0f}%")  # 設置顯示格式

    def _show_current_dosage(self, color):
        font_size = 64

        if color is None:
            style = f'font-size: {font_size}pt;'
        else:
            style = f'font-size: {font_size}pt; color: {color}; font-weight: bold'

        self.ui.label_current_dosage.setStyleSheet(style)
        self.ui.label_3.setStyleSheet(style)
        self.ui.label_4.setStyleSheet(style)

    def _display_image(self, filename):
        icon_size = 320
        self.ui.label_image.setPixmap(QtGui.QPixmap(filename))
        self.ui.label_image.setMaximumWidth(icon_size)
        self.ui.label_image.setMaximumHeight(icon_size)
        self.ui.label_image.setScaledContents(True)

    def _beep(self):
        try:
            mixer.music.play()
        except Exception:
            pass

    # 關閉
    def close_all(self):
        self.running = False  # 停止執行緒
        if self.ser:
            self.ser.close()

    def closeEvent(self, event):
        self.close_all()
        event.accept()

    def accept(self):
        self.close_all()
        super().accept()

    def reject(self):
        self.close_all()
        super().reject()

    def accepted_button_clicked(self):
        self.close_all()
        self.accept()

    def reeject_button_clicked(self):
        self.close_all()
        self.reject()

    def save_pres_extend(self):
        try:
            prescript_utils.remove_pres_extend_row(self.database, self.prescript_key, '調劑完成')
        except Exception:
            pass

        try:
            prescript_utils.insert_pres_extend_row(self.database, self.prescript_key, '調劑完成', '是')
        except Exception:
            pass