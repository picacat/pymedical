# 候診系統設定
# -*- coding: UTF-8 -*-

import json
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog

from libs import (
    class_utils,
    dialog_utils,
    notification_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
    voice_utils,
    volume_utils,
)

# 音量的欄位名稱、預設值、訊息格式都放在 volume_utils, 兩邊不會走鐘
DEFAULT_VOLUME = volume_utils.DEFAULT_VOLUME
FIELD_VOICE_VOLUME = volume_utils.FIELD_VOICE_VOLUME
FIELD_MEDIA_VOLUME = volume_utils.FIELD_MEDIA_VOLUME

# 滑桿停下來這麼久之後才廣播, 拖動過程中不會一直發訊息
VOLUME_PREVIEW_DELAY_MSEC = 200


# 主視窗
class DialogBulletinSettings(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station="系統設定",
        )
        channels = [notification_utils.CHANNEL_CALL_NUMBER]
        self.notification_server = notification_utils.NotificationServer(
            self,
            database=self.database,
            station="候診系統設定",
            channels=channels,
        )
        self.notification_server.update_signal.connect(self._on_notification)

        # 滑桿即時試聽用
        self.settings_loaded = False  # 讀取設定的過程中不要廣播
        self.volume_restored = False  # 避免取消時重複廣播還原
        self.volume_preview_timer = QtCore.QTimer(self)
        self.volume_preview_timer.setSingleShot(True)
        self.volume_preview_timer.timeout.connect(self._broadcast_volume_preview)

        self._set_ui()
        self._set_signal()
        self._read_settings()
        self.settings_loaded = True

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _on_notification(self, channel, message):
        print(channel, message)
        if channel == notification_utils.CHANNEL_CALL_NUMBER:
            self._broadcast_speech(message)

    def _broadcast_speech(self, json_data):
        try:
            voice_dict = json.loads(json_data)
        except Exception:
            return

        voice_data = voice_dict["sentence"]

        # 用滑桿「現在」的值試聽, 還沒按確定就能聽出差別
        voice_utils.speak(
            voice_data,
            threading=True,
            volume=self.ui.horizontalSlider_voice_volume.value(),
        )

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_BULLETIN_SETTINGS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("確定")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

        # 兩條滑桿一律 0~100, 避免 designer 裡設錯範圍
        self.ui.horizontalSlider_media_volume.setRange(0, 100)
        self.ui.horizontalSlider_voice_volume.setRange(0, 100)

        self.table_widget_marquee = class_utils.get_table_widget(
            self.ui.tableWidget_marquee, self.database
        )
        self.table_widget_marquee.set_table_heading_width([500])

        self.table_widget_image_list = class_utils.get_table_widget(
            self.ui.tableWidget_image_list, self.database
        )
        self.table_widget_image_list.set_table_heading_width([350, 150])

        self.table_widget_video_list = class_utils.get_table_widget(
            self.ui.tableWidget_video_list, self.database
        )
        self.table_widget_video_list.set_table_heading_width([500])

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

        # 按取消或 Esc 關掉: 叫看板還原成資料庫裡的音量
        # (兩個都接, 因為 .ui 檔有沒有把 buttonBox 接到 reject() 不一定)
        self.ui.buttonBox.rejected.connect(self._restore_volume_settings)
        self.rejected.connect(self._restore_volume_settings)

        self.ui.horizontalSlider_media_volume.valueChanged.connect(
            self._media_volume_changed
        )
        self.ui.horizontalSlider_voice_volume.valueChanged.connect(
            self._voice_volume_changed
        )
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

    def _media_volume_changed(self):
        self.ui.label_media_volume.setText(
            str(self.ui.horizontalSlider_media_volume.value())
        )
        self._schedule_volume_preview()

    def _voice_volume_changed(self):
        self.ui.label_voice_volume.setText(
            str(self.ui.horizontalSlider_voice_volume.value())
        )
        self._schedule_volume_preview()

    # ------------------------------------------------------------------
    # 滑桿即時試聽
    #
    # 滑桿一動就通知候診看板馬上套用, 但不寫進資料庫:
    #   按確定 -> 存檔, 叫看板重新讀資料庫
    #   按取消 -> 不存檔, 叫看板重新讀資料庫 (等於還原)
    # ------------------------------------------------------------------
    def _schedule_volume_preview(self):
        if not self.settings_loaded:  # 開窗時讀設定不算調整
            return

        self.volume_preview_timer.start(VOLUME_PREVIEW_DELAY_MSEC)

    def _broadcast_volume_preview(self):
        message = volume_utils.build_preview_message(
            self.ui.horizontalSlider_media_volume.value(),
            self.ui.horizontalSlider_voice_volume.value(),
        )

        try:
            self.notification_client.broadcast(
                notification_utils.CHANNEL_BULLETIN, message
            )
        except Exception as e:
            print(f"音量試聽通知失敗: {e}")

    def accepted_button_clicked(self):
        self.volume_preview_timer.stop()
        self.volume_restored = True  # 已經存檔, 不需要再還原

        self._save_settings()
        self._notify_volume_changed()

    def _restore_volume_settings(self):
        """取消時叫看板把音量讀回資料庫的值, 丟掉試聽中的設定"""
        if self.volume_restored:
            return

        self.volume_restored = True
        self.volume_preview_timer.stop()
        self._notify_volume_changed()

    def _notify_volume_changed(self):
        """通知候診看板重新讀取音量, 不用重開看板程式"""
        try:
            self.notification_client.broadcast(
                notification_utils.CHANNEL_BULLETIN,
                volume_utils.REFRESH_VOLUME_MESSAGE,
            )
        except Exception as e:
            print(f"音量設定通知失敗: {e}")

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

    def _get_volume_setting(self, field_name, default=DEFAULT_VOLUME):
        """讀取音量設定 (0~100)

        欄位不存在或沒填 -> 回傳 default;
        真的填 0 -> 就是 0 (靜音)。
        新診所第一次進來時不會因為欄位空白就被當成靜音。
        """
        try:
            value = self.system_settings.field(field_name)
        except Exception:
            value = None

        if value is None or string_utils.xstr(value).strip() == "":
            return default

        volume = number_utils.get_integer(value)

        return max(0, min(volume, 100))

    def _read_settings(self):
        self._set_radio_button(
            [
                self.ui.radioButton_video_stream,
                self.ui.radioButton_video_file,
                self.ui.radioButton_image_file,
            ],
            ["串流位址", "輪播影片", "輪播圖片"],
            "媒體播放來源",
        )
        self.ui.lineEdit_media_path.setText(self.system_settings.field("媒體播放位址"))
        self.ui.lineEdit_schedule_file_path.setText(
            self.system_settings.field("門診表圖檔名")
        )
        self.ui.lineEdit_fixed_image.setText(self.system_settings.field("固定圖檔名"))

        self.ui.horizontalSlider_media_volume.setValue(
            self._get_volume_setting(FIELD_MEDIA_VOLUME)
        )
        self.ui.horizontalSlider_voice_volume.setValue(
            self._get_volume_setting(FIELD_VOICE_VOLUME)
        )
        # setValue() 的值如果剛好等於原值不會觸發 valueChanged, 旁邊的數字會對不上
        self._media_volume_changed()
        self._voice_volume_changed()

        self.ui.spinBox_monitor.setValue(
            number_utils.get_integer(self.system_settings.field("候診系統顯示器編號"))
        )
        self.ui.spinBox_image_list_time.setValue(
            number_utils.get_integer(self.system_settings.field("輪播圖片間隔秒數"))
        )
        self._read_marquee()
        self._read_image_list()
        self._read_video_list()
        self._read_misc()

    def _read_marquee(self):
        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "跑馬燈訊息-%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.tableWidget_marquee.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            self.ui.tableWidget_marquee.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row["Value"]))
            )
        self.ui.tableWidget_marquee.resizeRowsToContents()

    def _read_image_list(self):
        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播圖片檔-%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.tableWidget_image_list.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            filename = string_utils.xstr(row["Value"])
            self.ui.tableWidget_image_list.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(filename)
            )
            if os.path.isfile(filename):
                ui_utils.set_table_widget_image(
                    self.ui.tableWidget_image_list, row_no, 1, filename, 128
                )

        self.ui.tableWidget_image_list.resizeRowsToContents()

    def _read_video_list(self):
        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播影片檔-%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.ui.tableWidget_video_list.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            filename = string_utils.xstr(row["Value"])
            self.ui.tableWidget_video_list.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(filename)
            )

        self.ui.tableWidget_video_list.resizeRowsToContents()

    def _read_misc(self):
        self._set_check_box(self.ui.checkBox_show_name_only, "候診名單只顯示名字")

    def _save_settings(self):
        self._save_radio_button(
            [
                self.ui.radioButton_video_stream,
                self.ui.radioButton_video_file,
                self.ui.radioButton_image_file,
            ],
            ["串流位址", "輪播影片", "輪播圖片"],
            "媒體播放來源",
        )

        self.system_settings.post("媒體播放位址", self.ui.lineEdit_media_path.text())
        self.system_settings.post(
            "門診表圖檔名", self.ui.lineEdit_schedule_file_path.text()
        )
        self.system_settings.post("固定圖檔名", self.ui.lineEdit_fixed_image.text())
        self.system_settings.post(
            FIELD_MEDIA_VOLUME, self.ui.horizontalSlider_media_volume.value()
        )
        self.system_settings.post(
            FIELD_VOICE_VOLUME, self.ui.horizontalSlider_voice_volume.value()
        )
        self.system_settings.post("候診系統顯示器編號", self.ui.spinBox_monitor.value())
        self.system_settings.post(
            "輪播圖片間隔秒數", self.ui.spinBox_image_list_time.value()
        )
        self._save_marquee()
        self._save_image_list()
        self._save_video_list()
        self._save_misc()

    def _save_marquee(self):
        self.database.exec_sql(
            'DELETE FROM system_settings WHERE Field LIKE "跑馬燈訊息-%"'
        )

        for row_no in range(self.ui.tableWidget_marquee.rowCount()):
            item = self.ui.tableWidget_marquee.item(row_no, 0)
            if item is None:
                continue

            field_name = f"跑馬燈訊息-{row_no}"
            marquee_text = item.text().strip()
            self.system_settings.post(field_name, marquee_text)

    def _save_image_list(self):
        self.database.exec_sql(
            'DELETE FROM system_settings WHERE Field LIKE "輪播圖片檔-%"'
        )

        for row_no in range(self.ui.tableWidget_image_list.rowCount()):
            item = self.ui.tableWidget_image_list.item(row_no, 0)
            if item is None:
                continue

            filename_field = f"輪播圖片檔-{row_no}"
            filename = item.text().strip()
            self.system_settings.post(filename_field, filename)

    def _save_video_list(self):
        self.database.exec_sql(
            'DELETE FROM system_settings WHERE Field LIKE "輪播影片檔-%"'
        )

        for row_no in range(self.ui.tableWidget_video_list.rowCount()):
            item = self.ui.tableWidget_video_list.item(row_no, 0)
            if item is None:
                continue

            filename_field = f"輪播影片檔-{row_no}"
            filename = item.text().strip()
            self.system_settings.post(filename_field, filename)

    def _save_misc(self):
        self._save_check_box(self.ui.checkBox_show_name_only, "候診名單只顯示名字")

    def _open_schedule_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "開啟圖片檔",
            "",
            "JPG檔(*.jpg);;JPEG檔(*.jpeg);;PNG檔(*.png);;所有檔案 (*.*)",
            options=options,
        )
        if not filename:
            return

        self.ui.lineEdit_schedule_file_path.setText(filename)

    def _open_fixed_image(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "開啟圖片檔",
            "",
            "JPG檔(*.jpg);;JPEG檔(*.jpeg);;PNG檔(*.png);;所有檔案 (*.*)",
            options=options,
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
            self,
            "開啟圖片檔",
            "",
            "JPG檔(*.jpg);;JPEG檔(*.jpeg);;PNG檔(*.png);;所有檔案 (*.*)",
            options=options,
        )
        if not filename:
            return

        row_no = self.ui.tableWidget_image_list.rowCount()
        self.ui.tableWidget_image_list.setRowCount(row_no + 1)
        self.ui.tableWidget_image_list.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(filename)
        )
        ui_utils.set_table_widget_image(
            self.ui.tableWidget_image_list, row_no, 1, filename, 128
        )

        self.ui.tableWidget_image_list.resizeRowsToContents()

    def _remove_image_list(self):
        if self.ui.tableWidget_image_list.rowCount() <= 0:
            return

        current_row = self.ui.tableWidget_image_list.currentRow()
        self.ui.tableWidget_image_list.removeRow(current_row)

    def _add_video_list(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "開啟影片檔",
            "",
            "MP4檔(*.mp4);;WAV檔(*.wav);;MOV檔(*.mov);;AVI檔(*.avi);;所有檔案 (*.*)",
            options=options,
        )
        if not filename:
            return

        row_no = self.ui.tableWidget_video_list.rowCount()
        self.ui.tableWidget_video_list.setRowCount(row_no + 1)
        self.ui.tableWidget_video_list.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(filename)
        )

        self.ui.tableWidget_video_list.resizeRowsToContents()

    def _add_stream_list(self):
        input_dialog = dialog_utils.get_dialog(
            "輸入網路串流位址",
            "請輸入網路串流位址",
            None,
            QInputDialog.TextInput,
            500,
            200,
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        filename = input_dialog.textValue()
        if filename in ["", None]:
            return

        row_no = self.ui.tableWidget_video_list.rowCount()
        self.ui.tableWidget_video_list.setRowCount(row_no + 1)
        self.ui.tableWidget_video_list.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(filename)
        )

        self.ui.tableWidget_video_list.resizeRowsToContents()

    def _remove_video_list(self):
        if self.ui.tableWidget_video_list.rowCount() <= 0:
            return

        current_row = self.ui.tableWidget_video_list.currentRow()
        self.ui.tableWidget_video_list.removeRow(current_row)

    def _get_voice_dict(self):
        voice_dict = {
            "clinic_name": self.system_settings.field("院所名稱"),
            "regist_no": 1,
            "name": "廣播測試",
            "room": 1,
            "program_name": "醫師看診作業",
        }

        return voice_dict

    def _get_voice_sentence(self):
        voice_dict = self._get_voice_dict()
        room = voice_dict["room"]
        regist_no = voice_dict["regist_no"]
        name = voice_dict["name"]

        sentence = f"{room}診 {regist_no}號 {name}"

        return sentence

    def _speak_test(self):
        voice_dict = self._get_voice_dict()
        sentence = self._get_voice_sentence()
        voice_dict["sentence"] = sentence

        broadcast_json = json.dumps(voice_dict)
        self.notification_client.broadcast(
            notification_utils.CHANNEL_CALL_NUMBER, broadcast_json
        )

    ###########################################################################################################
    # 讀取 check_box 的資料
    def _set_check_box(self, check_box, field):
        if self.system_settings.field(field) == "Y":
            check_box.setChecked(True)
        else:
            check_box.setChecked(False)

    # 寫入 check_box 的資料
    def _save_check_box(self, check_box, field):
        if check_box.isChecked():
            self.system_settings.post(field, "Y")
        else:
            self.system_settings.post(field, "N")
