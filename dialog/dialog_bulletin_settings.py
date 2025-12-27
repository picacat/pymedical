
# 設定抽成人員 2021-11-12
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog
import os
import json

from libs import class_utils

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import dialog_utils


# 主視窗
class DialogBulletinSettings(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogBulletinSettings, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.voice_client = class_utils.get_voice_client()

        self._set_ui()
        self._set_signal()
        self._read_settings()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_BULLETIN_SETTINGS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.table_widget_marquee = class_utils.get_table_widget(self.ui.tableWidget_marquee, self.database)
        self.table_widget_marquee.set_table_heading_width([500])

        self.table_widget_image_list = class_utils.get_table_widget(self.ui.tableWidget_image_list, self.database)
        self.table_widget_image_list.set_table_heading_width([350, 150])

        self.table_widget_video_list = class_utils.get_table_widget(self.ui.tableWidget_video_list, self.database)
        self.table_widget_video_list.set_table_heading_width([500])

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.horizontalSlider_volume.valueChanged.connect(self._volume_changed)
        self.ui.pushButton_speak_test.clicked.connect(self._speak_test)
        self.ui.toolButton_open_schedule_file.clicked.connect(self._open_schedule_file)
        self.ui.toolButton_open_fixed_image.clicked.connect(self._open_fixed_image)

        self.ui.toolButton_add_marquee.clicked.connect(self._add_marquee)
        self.ui.toolButton_remove_marquee.clicked.connect(self._remove_marquee)
        self.ui.toolButton_add_image_list.clicked.connect(self._add_image_list)
        self.ui.toolButton_add_stream_list.clicked.connect(self._add_stream_list)
        self.ui.toolButton_remove_image_list.clicked.connect(self._remove_image_list)
        self.ui.toolButton_add_video_list.clicked.connect(self._add_video_list)
        self.ui.toolButton_remove_video_list.clicked.connect(self._remove_video_list)

    def _volume_changed(self):
        self.ui.label_volume.setText(str(self.ui.horizontalSlider_volume.value()))

    def accepted_button_clicked(self):
        self._save_settings()

    # 讀取 radio_button
    def _set_radio_button(self, radio_buttons, values, field):
        for radio_button, value in zip(radio_buttons, values):
            if self.system_settings.field(field) == value:
                radio_button.setChecked(True)
                break

    # 寫入 radio_button
    def _save_radio_button(self, radio_buttons, values, field):
        select_value = None
        for radio_button, value in zip(radio_buttons, values):
            if radio_button.isChecked():
                select_value = value
                break

        self.system_settings.post(field, select_value)

    def _read_settings(self):
        self._set_radio_button(
            [
                self.ui.radioButton_video_stream,
                self.ui.radioButton_video_file,
                self.ui.radioButton_image_file,
            ],
            ['串流位址', '輪播影片', '輪播圖片'],
            '媒體播放來源'
        )
        self.ui.lineEdit_media_path.setText(self.system_settings.field('媒體播放位址'))
        self.ui.lineEdit_schedule_file_path.setText(self.system_settings.field('門診表圖檔名'))
        self.ui.lineEdit_fixed_image.setText(self.system_settings.field('固定圖檔名'))
        self.ui.horizontalSlider_volume.setValue(
            number_utils.get_integer(self.system_settings.field('媒體播放音量'))
        )
        self.ui.spinBox_monitor.setValue(
            number_utils.get_integer(self.system_settings.field('候診系統顯示器編號'))
        )
        self.ui.spinBox_image_list_time.setValue(
            number_utils.get_integer(self.system_settings.field('輪播圖片間隔秒數'))
        )
        self._read_marquee()
        self._read_image_list()
        self._read_video_list()
        self._read_misc()

    def _read_marquee(self):
        sql = '''
            SELECT * FROM system_settings
            WHERE
                Field LIKE "跑馬燈訊息-%"
            ORDER BY Field
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.tableWidget_marquee.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            self.ui.tableWidget_marquee.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row['Value']))
            )
        self.ui.tableWidget_marquee.resizeRowsToContents()

    def _read_image_list(self):
        sql = '''
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播圖片檔-%"
            ORDER BY Field
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.tableWidget_image_list.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            filename = string_utils.xstr(row['Value'])
            self.ui.tableWidget_image_list.setItem(row_no, 0, QtWidgets.QTableWidgetItem(filename))
            if os.path.isfile(filename):
                ui_utils.set_table_widget_image(
                    self.ui.tableWidget_image_list, row_no, 1, filename, 128)

        self.ui.tableWidget_image_list.resizeRowsToContents()

    def _read_video_list(self):
        sql = '''
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播影片檔-%"
            ORDER BY Field
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.tableWidget_video_list.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            filename = string_utils.xstr(row['Value'])
            self.ui.tableWidget_video_list.setItem(row_no, 0, QtWidgets.QTableWidgetItem(filename))

        self.ui.tableWidget_video_list.resizeRowsToContents()

    def _read_misc(self):
        self._set_check_box(self.ui.checkBox_show_name_only, '候診名單只顯示名字')

    def _save_settings(self):
        self._save_radio_button(
            [
                self.ui.radioButton_video_stream,
                self.ui.radioButton_video_file,
                self.ui.radioButton_image_file,
            ],
            ['串流位址', '輪播影片', '輪播圖片'],
            '媒體播放來源'
        )

        self.system_settings.post('媒體播放位址', self.ui.lineEdit_media_path.text())
        self.system_settings.post('門診表圖檔名', self.ui.lineEdit_schedule_file_path.text())
        self.system_settings.post('固定圖檔名', self.ui.lineEdit_fixed_image.text())
        self.system_settings.post('媒體播放音量', self.ui.horizontalSlider_volume.value())
        self.system_settings.post('候診系統顯示器編號', self.ui.spinBox_monitor.value())
        self.system_settings.post('輪播圖片間隔秒數', self.ui.spinBox_image_list_time.value())
        self._save_marquee()
        self._save_image_list()
        self._save_video_list()
        self._save_misc()

    def _save_marquee(self):
        self.database.exec_sql('DELETE FROM system_settings WHERE Field LIKE "跑馬燈訊息-%"')

        for row_no in range(self.ui.tableWidget_marquee.rowCount()):
            item = self.ui.tableWidget_marquee.item(row_no, 0)
            if item is None:
                continue

            field_name = f'跑馬燈訊息-{row_no}'
            marquee_text = item.text().strip()
            self.system_settings.post(field_name, marquee_text)

    def _save_image_list(self):
        self.database.exec_sql('DELETE FROM system_settings WHERE Field LIKE "輪播圖片檔-%"')

        for row_no in range(self.ui.tableWidget_image_list.rowCount()):
            item = self.ui.tableWidget_image_list.item(row_no, 0)
            if item is None:
                continue

            filename_field = f'輪播圖片檔-{row_no}'
            filename = item.text().strip()
            self.system_settings.post(filename_field, filename)

    def _save_video_list(self):
        self.database.exec_sql('DELETE FROM system_settings WHERE Field LIKE "輪播影片檔-%"')

        for row_no in range(self.ui.tableWidget_video_list.rowCount()):
            item = self.ui.tableWidget_video_list.item(row_no, 0)
            if item is None:
                continue

            filename_field = f'輪播影片檔-{row_no}'
            filename = item.text().strip()
            self.system_settings.post(filename_field, filename)

    def _save_misc(self):
        self._save_check_box(self.ui.checkBox_show_name_only, '候診名單只顯示名字')

    def _open_schedule_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "開啟圖片檔",
            '', "JPG檔(*.jpg);;JPEG檔(*.jpeg);;PNG檔(*.png);;所有檔案 (*.*)", options=options
        )
        if not filename:
            return

        self.ui.lineEdit_schedule_file_path.setText(filename)

    def _open_fixed_image(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "開啟圖片檔",
            '', "JPG檔(*.jpg);;JPEG檔(*.jpeg);;PNG檔(*.png);;所有檔案 (*.*)", options=options
        )
        if not filename:
            return

        self.ui.lineEdit_fixed_image.setText(filename)

    def _add_marquee(self):
        self.ui.tableWidget_marquee.setRowCount(
            self.ui.tableWidget_marquee.rowCount() + 1
        )
        self.ui.tableWidget_marquee.resizeRowsToContents()

    def _remove_marquee(self):
        if self.ui.tableWidget_marquee.rowCount() <= 0:
            return

        current_row = self.ui.tableWidget_marquee.currentRow()
        self.ui.tableWidget_marquee.removeRow(current_row)

    def _add_image_list(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "開啟影片檔",
            '', "JPG檔(*.jpg);;JPEG檔(*.jpeg);;PNG檔(*.png);;所有檔案 (*.*)", options=options
        )
        if not filename:
            return

        row_no = self.ui.tableWidget_image_list.rowCount()
        self.ui.tableWidget_image_list.setRowCount(row_no + 1)
        self.ui.tableWidget_image_list.setItem(row_no, 0, QtWidgets.QTableWidgetItem(filename))
        ui_utils.set_table_widget_image(self.ui.tableWidget_image_list, row_no, 1, filename, 128)

        self.ui.tableWidget_image_list.resizeRowsToContents()

    def _remove_image_list(self):
        if self.ui.tableWidget_image_list.rowCount() <= 0:
            return

        current_row = self.ui.tableWidget_image_list.currentRow()
        self.ui.tableWidget_image_list.removeRow(current_row)

    def _add_video_list(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "開啟圖片檔",
            '', "MP4檔(*.mp4);;WAV檔(*.wav);;MOV檔(*.mov);;AVI檔(*.avi);;所有檔案 (*.*)", options=options
        )
        if not filename:
            return

        row_no = self.ui.tableWidget_video_list.rowCount()
        self.ui.tableWidget_video_list.setRowCount(row_no + 1)
        self.ui.tableWidget_video_list.setItem(row_no, 0, QtWidgets.QTableWidgetItem(filename))

        self.ui.tableWidget_video_list.resizeRowsToContents()

    def _add_stream_list(self):
        input_dialog = dialog_utils.get_dialog(
            '輸入網路串流位址',
            '請輸入網路串流位址',
            None, QInputDialog.TextInput, 500, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        filename = input_dialog.textValue()
        if filename in ['', None]:
            return

        row_no = self.ui.tableWidget_video_list.rowCount()
        self.ui.tableWidget_video_list.setRowCount(row_no + 1)
        self.ui.tableWidget_video_list.setItem(row_no, 0, QtWidgets.QTableWidgetItem(filename))

        self.ui.tableWidget_video_list.resizeRowsToContents()

    def _remove_video_list(self):
        if self.ui.tableWidget_video_list.rowCount() <= 0:
            return

        current_row = self.ui.tableWidget_video_list.currentRow()
        self.ui.tableWidget_video_list.removeRow(current_row)

    def _get_voice_dict(self):
        voice_dict = {
            'clinic_name': self.system_settings.field('院所名稱'),
            'regist_no': 1,
            'name': '廣播測試',
            'room': 1,
            'program_name': '醫師看診作業',
        }

        return voice_dict

    def _get_voice_sentence(self):
        voice_dict = self._get_voice_dict()
        room = voice_dict['room']
        regist_no = voice_dict['regist_no']
        name = voice_dict['name']

        sentence = f"{room}診 {regist_no}號 {name}"

        return sentence

    def _speak_test(self):
        voice_dict = self._get_voice_dict()
        sentence = self._get_voice_sentence()
        voice_dict['sentence'] = sentence

        broadcast_json = json.dumps(voice_dict)
        self.voice_client.send_data(broadcast_json)

    ###########################################################################################################
    # 讀取 check_box 的資料
    def _set_check_box(self, check_box, field):
        if self.system_settings.field(field) == 'Y':
            check_box.setChecked(True)
        else:
            check_box.setChecked(False)

    # 寫入 check_box 的資料
    def _save_check_box(self, check_box, field):
        if check_box.isChecked():
            self.system_settings.post(field, 'Y')
        else:
            self.system_settings.post(field, 'N')
