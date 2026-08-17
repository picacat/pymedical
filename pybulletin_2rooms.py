import datetime
import json
import os
import sys

from pygame import mixer
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtWidgets import QDesktopWidget

if sys.platform == "win32":
    os.environ["PYTHON_VLC_MODULE_PATH"] = "./vlc"

import configparser
import time

import yt_dlp

import vlc
from libs import (
    class_utils,
    date_utils,
    notification_utils,
    number_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
    voice_utils,
)


class BellThread(QThread):
    """播放音效的子執行緒"""

    def run(self):
        try:
            mixer.init()
            mixer.music.load("./dingdong.mp3")
            mixer.music.play()

            while mixer.music.get_busy():
                time.sleep(0.01)  # 避免過度佔用 CPU
        except Exception as e:
            print("播放音效時發生錯誤:", e)


# 主程式
class PyBulletin_2rooms(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.args = args

        self._set_db()
        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )
        self.ui = None

        self.waiting_number = [0 for x in range(100)]
        self.audio_timer = QtCore.QTimer(self)
        self.volume = number_utils.get_integer(
            self.system_settings.field("媒體播放音量")
        )
        self.url = self.system_settings.field("媒體播放位址")

        self.media_type = self.system_settings.field("媒體播放來源")
        self.image_list_time = number_utils.get_integer(
            self.system_settings.field("輪播圖片間隔秒數")
        )
        self.show_name_only = self.system_settings.field("候診名單只顯示名字")
        self.show_seq_number = False
        if self.image_list_time == 0:
            self.image_list_time = 10000
        else:
            self.image_list_time *= 1000

        self.period1 = self.system_settings.field("早班時間")
        self.period2 = self.system_settings.field("午班時間")
        self.period3 = self.system_settings.field("晚班時間")

        self._set_ui()
        self._set_notification_server()
        self._set_signal()
        self._init_wait_list()

        # 設定 QTimer 讓 QLabel_room 閃爍
        self.label_room = None
        self.blink_state = False
        self.label_timer = QTimer(self)
        self.label_timer.timeout.connect(self.toggle_background)
        self.blink_count = 0
        self.max_blinks = 20

        monitor_number = self.get_monitor_number()
        monitor = QDesktopWidget().screenGeometry(monitor_number)
        self.move(monitor.left(), monitor.top())
        self.showFullScreen()
        self._show_waiting_records()
        self.ui.label_doctor1.setFocus()

    def _set_notification_server(self):
        channels = [
            notification_utils.CHANNEL_WAITING_LIST,  # 原 8880
            notification_utils.CHANNEL_BULLETIN,  # 原 9990 的 refresh_wait
            notification_utils.CHANNEL_CALL_NUMBER,  # UDP 下線後才打開，否則會念兩次
        ]
        self.notification_server = notification_utils.NotificationServer(
            self,
            database=self.database,
            station="pybulletin",
            channels=channels,
        )
        self.notification_server.update_signal.connect(self._on_notification)

    def _on_notification(self, channel, message):
        if channel == notification_utils.CHANNEL_WAITING_LIST:
            self._show_waiting_list()  # 原本 8880 就是忽略內容直接刷新
        elif channel == notification_utils.CHANNEL_BULLETIN:
            self._broadcast_voice(message)  # 內容是 refresh_wait，它自己會分辨
        elif channel == notification_utils.CHANNEL_CALL_NUMBER:
            self._broadcast_voice(message)

    def _clear_wait_list(self):
        row_count = 8
        self.ui.tableWidget_room1.setRowCount(0)
        self.ui.tableWidget_room2.setRowCount(0)
        self.ui.tableWidget_room1.setRowCount(row_count)
        self.ui.tableWidget_room2.setRowCount(row_count)

    def _init_wait_list(self):
        self._clear_wait_list()

        width = [
            200,
            350,
            200,
            350,
        ]
        self.table_widget_room1 = class_utils.get_table_widget(
            self.ui.tableWidget_room1, self.database
        )
        self.table_widget_room2 = class_utils.get_table_widget(
            self.ui.tableWidget_room2, self.database
        )

        self.table_widget_room1.set_table_heading_width(width)
        self.table_widget_room2.set_table_heading_width(width)

    def get_monitor_number(self):
        return number_utils.get_integer(
            self.system_settings.field("候診系統顯示器編號")
        )

    def _set_db(self):
        self.host = None
        try:
            config_file = self.args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.host = config_dict["host"]
            self.database = class_utils.get_db(
                host=self.host,
                user=config_dict["user"],
                database=config_dict["database"],
                password=config_dict["password"],
                charset=config_dict["charset"],
                buffered=config_dict["buffered"],
            )
            self.server_ip = config_dict["host"]
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

    def show_bulletin(self):
        self._show_title()
        # self._play_media()
        self._play_marquee()

    def _show_title(self):
        title = self.system_settings.field("院所名稱") + " 候診資訊系統"
        self.ui.label_title.setText(title)

    @staticmethod
    def _parse_config_file(config_file, db_section="db"):
        config = configparser.ConfigParser()
        config.read(config_file)

        config_dict = {
            "host": config[db_section]["host"],
            "user": config[db_section]["user"],
            "database": config[db_section]["database"],
            "password": config[db_section]["password"],
            "charset": config[db_section]["charset"],
            "buffered": True,
        }

        return config_dict

    # 解構
    def __del__(self):
        pass
        # self.mediaplayer.stop()
        # self.mediaplayer.release()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_BULLETIN_2ROOMS, self)
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        self._set_label_room()
        self._set_label_html()
        self.setCursor(Qt.BlankCursor)

    def _set_label_room(self):
        self.color = """
            qlineargradient(
                spread:pad, x1:1, y1:0, x2:0.969388, y2:1, stop:0 rgba(236, 223, 0, 255),
            stop:1 rgba(255, 255, 184, 255));
        """
        self.style_sheet = f"background-color: {self.color}"
        self.ui.label_room1.setStyleSheet(self.style_sheet)
        self.ui.label_room2.setStyleSheet(self.style_sheet)

        doctor_color = """
            qlineargradient(
                spread:pad, x1:1, y1:0, x2:0.969388, y2:1, stop:0 rgba(206, 183, 0, 255),
            stop:1 rgba(255, 255, 184, 255));
        """
        style_sheet_doctor = f"background-color: {doctor_color}"
        self.ui.label_doctor1.setStyleSheet(style_sheet_doctor)
        self.ui.label_doctor2.setStyleSheet(style_sheet_doctor)

    def _set_label_html(self):
        self._show_doctors()
        label_room_list = [
            self.ui.label_room1,
            self.ui.label_room2,
        ]
        sequence = "&nbsp;&nbsp;"
        for label_room in label_room_list:
            html = self._get_sequence_html(sequence)
            label_room.setText(html)

    # 設定信號
    def _set_signal(self):
        pass

    def _close(self):
        self.close()

    # 設定 css style
    def _set_style(self):
        system_utils.set_background_image(self.ui.tab_home, self.system_settings)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        system_utils.set_theme(self.ui, self.system_settings)

    def _set_lower_audio(self):
        if self.url in ["", None]:
            return

        try:
            self.vlc_player.audio_set_volume(5)
        except Exception:
            pass

        self.audio_timer.start(6000)
        self.audio_timer.timeout.connect(self._normal_audio)

    def _normal_audio(self):
        try:
            self.vlc_player.audio_set_volume(self.volume)
        except Exception:
            pass

        self.audio_timer.stop()

    # 廣播叫號
    def _broadcast_voice(self, json_data):
        # 增加防呆：檢查是否為空值
        if not json_data:
            print("收到空的 json_data，跳過處理")
            return

        try:
            voice_dict = json.loads(json_data)
        except json.JSONDecodeError as e:
            print(f"JSON 解析失敗！錯誤訊息: {e}")
            print(
                f"實際收到的資料內容為: {json_data!r}"
            )  # repr 可以看出是不是空字串或夾雜怪字元
            return  # 結束此函式，不往下執行

        sentence = voice_dict.get(
            "sentence", ""
        )  # 使用 .get() 比較安全，防止 key 不存在

        # 確保 key 存在才讀取，避免 KeyError
        if "regist_no" in voice_dict and "room" in voice_dict:
            regist_no = number_utils.get_integer(voice_dict["regist_no"])
            room = number_utils.get_integer(voice_dict["room"])

            self.waiting_number[room] = regist_no

            self._set_lower_audio()
            QtWidgets.qApp.processEvents()
            self._show_doctors()
            self._show_sequence(room)

            # self.ring_bell()
            self.start_blinking()

            voice_utils.speak(sentence, threading=True)
        else:
            print("JSON 格式正確，但缺少必要的欄位 (regist_no 或 room)")

    def ring_bell(self):
        """播放音效（使用子執行緒）"""
        self.bell_thread = BellThread()
        self.bell_thread.start()

    def _play_media(self):
        if self.media_type == "輪播圖片":
            self._play_images()
        elif self.media_type == "輪播影片":
            self._play_videos()
        else:
            self._play_url_stream()

    def _play_images(self):
        self._set_image_list()
        self._set_image_list_timer()
        self._display_image()

    def _set_image_list(self):
        self.image_list_index = 1

        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播圖片檔%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)

        self.image_list = []
        for row in rows:
            self.image_list.append(row["Value"])

    def _image_list_timeout(self):
        self.image_list_index += 1
        if self.image_list_index >= len(self.image_list):
            self.image_list_index = 0

        image_file = self.image_list[self.image_list_index]
        self._display_image(image_file)

    def _set_image_list_timer(self):
        self.image_list_timer = QtCore.QTimer(self)
        self.image_list_timer.start(self.image_list_time)
        self.image_list_timer.timeout.connect(self._image_list_timeout)

    def _display_image(self, image_file=None):
        if image_file is None:
            self.image_list_index = 0
            image_file = self.image_list[self.image_list_index]

        self.ui.frame_youtube.setStyleSheet(f"border-image: url({image_file})")

    def _get_video_list(self):
        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播影片檔-%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return []

        video_list = []
        for row in rows:
            video_list.append(string_utils.xstr(row["Value"]))

        return video_list

    def _play_videos(self):
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.audio_set_volume(self.volume)
        # events = self.mediaplayer.event_manager()
        # events.event_attach(vlc.EventType.MediaPlayerEndReached, self.video_finished)

        win_id = int(self.ui.frame_youtube.winId())
        if sys.platform == "win32":
            self.vlc_player.set_hwnd(win_id)
        elif sys.platform == "linux":
            self.vlc_player.set_xwindow(win_id)
        elif sys.platform == "darwin":
            self.vlc_player.set_nsobject(win_id)

        media_list = self.vlc_instance.media_list_new()
        video_list = self._get_video_list()
        for filename in video_list:
            media_list.add_media(self.vlc_instance.media_new(filename))

        self.media_list_player = vlc.MediaListPlayer()
        self.media_list_player.set_playback_mode(vlc.PlaybackMode.loop)
        self.media_list_player.set_media_list(media_list)
        self.media_list_player.set_media_player(self.vlc_player)
        self.media_list_player.play()

    def video_finished(self, data):
        self.video_index += 1
        if self.video_index >= len(self.media_list):
            self.video_index = 0

        filename = self.media_list[self.video_index]
        self._play_video(filename)

    def _set_stream_list(self):
        self.stream_index = 0

        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播影片檔%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)

        self.stream_list = []
        if self.url not in ["", None]:
            self.stream_list.append(self.url)

        for row in rows:
            self.stream_list.append(row["Value"])

    def _play_url_stream(self):
        self._set_stream_list()

        if len(self.stream_list) <= 0:
            return

        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        win_id = int(self.ui.frame_youtube.winId())
        if sys.platform == "win32":
            self.vlc_player.set_hwnd(win_id)
        elif sys.platform == "linux":
            self.vlc_player.set_xwindow(win_id)
        elif sys.platform == "darwin":
            self.vlc_player.set_nsobject(win_id)

        stream_url = self._get_stream_url(self.stream_index)
        self.media = self.vlc_instance.media_new(stream_url)
        self.media.get_mrl()

        self.vlc_player.set_media(self.media)

        events = self.vlc_player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

        self.vlc_player.play()
        self.vlc_player.audio_set_volume(self.volume)

    def _get_stream_url(self, index):
        url = self.stream_list[index]

        ydl_opts = {
            "format": "best",
            "buffer-size": "4096",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info["url"]

        return stream_url

    def _on_end_reached(self, event):
        self.stream_index += 1
        if self.stream_index >= len(self.stream_list):
            self.stream_index = 0

        stream_url = self._get_stream_url(self.stream_index)

        def restart_media():
            self.vlc_player.stop()
            self.media = self.vlc_instance.media_new(stream_url)
            self.vlc_player.set_media(self.media)
            self.vlc_player.play()

        # 在新线程中執行停止和重新播放操作
        threading.Thread(target=restart_media).start()

    def _set_marquee_list(self):
        self.marquee_list = []
        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "跑馬燈訊息-%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            marquee = self.system_settings.field("院所名稱") + " 關心您的健康"
            self.marquee_list.append(marquee)
            return

        for row in rows:
            self.marquee_list.append(string_utils.xstr(row["Value"]))

    def _play_marquee(self):
        self._set_marquee_list()
        self.marquee_index = 0
        self.marquee_start = QtWidgets.QDesktopWidget().screenGeometry(-1).width()

        self._set_marquee_text()

        self.current_x = self.marquee_start
        self.current_y = 10
        self.ui.label_marquee.move(self.current_x, self.current_y)
        self._set_timer()

    def _set_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.start(9)
        self.timer.timeout.connect(self._timeout)

    def _timeout(self):
        try:
            current_time = datetime.datetime.now().strftime("%H:%M")
            if current_time in [self.period1, self.period2, self.period3]:
                self._show_waiting_list()

            self.current_x -= 1
            if self.current_x <= -self.marquee_text_width:
                self.current_x = self.marquee_start
                self.marquee_index += 1
                if self.marquee_index >= len(self.marquee_list):
                    self.marquee_index = 0

                self._set_marquee_text()

            self.ui.label_marquee.move(self.current_x, self.current_y)
        except Exception:
            pass

    def _set_marquee_text(self):
        self.ui.label_marquee.setText(self.marquee_list[self.marquee_index])
        self.ui.label_marquee.adjustSize()
        self.marquee_text_width = self.ui.label_marquee.width()

    def _get_current_room_rows(self):
        period = registration_utils.get_current_period(self.system_settings)
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]

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

    def _get_sequence_html(self, sequence):
        html = f"""
            <table border="0" width="100%"
                style="font-weight:bold; font-family:Microsoft JhengHei">
                <tbody>
                    <tr>
                        <td width="15%" style="padding-left: 30px; font-size: 42px; font-weight: bold;
                            text-align: center; vertical-align: middle;">
                            <table style="border-collapse: collapse; padding: 0;">
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">就</td>
                                </tr>
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">診</td>
                                </tr>
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">號</td>
                                </tr>
                            </table>
                        </td>
                        <td width="85%" style="font-size: 130px; font-weight: bold; vertical-align: middle;
                            text-align: center">
                            {sequence}
                        </td>
                    </tr>
                </tbody>
            </table>
        """

        return html

    def _show_waiting_list(self, room=None):
        self._show_waiting_records()

    # def _show_sequence(self, room):
    #     if room is None:
    #         return

    #     label_room_list = [
    #         None,
    #         self.ui.label_room1,
    #         self.ui.label_room2,
    #     ]

    #     self.label_room = label_room_list[room]
    #     sequence = self.waiting_number[room]
    #     html = self._get_sequence_html(sequence)
    #     self.label_room.setText(html)

    def _show_sequence(self, room):
        if room is None:
            return

        label_room_list = [
            None,
            self.ui.label_room1,
            self.ui.label_room2,
        ]

        # 確保傳入的 room 編號在範圍內
        if 0 < room < len(label_room_list):
            self.label_room = label_room_list[room]
            sequence = self.waiting_number[room]
            html = self._get_sequence_html(sequence)
            self.label_room.setText(html)

    def _show_waiting_records(self):
        self._clear_wait_list()

        row_no = {
            0: 0,
            1: 1,
            2: 2,
            3: 3,
            4: 4,
            5: 5,
            6: 6,
            7: 7,
            8: 0,
            9: 1,
            10: 2,
            11: 3,
            12: 4,
            13: 5,
            14: 6,
            15: 7,
        }
        col_no = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            6: 0,
            7: 0,
            8: 2,
            9: 2,
            10: 2,
            11: 2,
            12: 2,
            13: 2,
            14: 2,
            15: 2,
        }
        table_widget_room = [None, self.ui.tableWidget_room1, self.ui.tableWidget_room2]
        for room in [1, 2]:
            sql = f"""
                SELECT RegistNo, Name FROM wait
                Where
                    Room = {room} AND
                    DoctorDone = "False"
                ORDER BY RegistNo
            """
            rows = self.database.select_record(sql)
            for i, row in enumerate(rows):
                if i >= 16:
                    break

                regist_no = number_utils.get_integer(row["RegistNo"])
                name = string_utils.get_mask_name(row["Name"])

                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, regist_no)
                table_widget_room[room].setItem(row_no[i], col_no[i], item)
                table_widget_room[room].item(row_no[i], col_no[i]).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, name)
                table_widget_room[room].setItem(row_no[i], col_no[i] + 1, item)
                table_widget_room[room].item(row_no[i], col_no[i] + 1).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _get_doctor_html(self, room, doctor):
        html = f"""
            <table border="0" width="100%"
                style="font-weight:bold; font-family:Microsoft JhengHei">
                <tbody>
                    <tr>
                        <td width="15%" style="padding-left: 30px; font-size: 42px; font-weight: bold;
                            text-align: center; vertical-align: middle;">
                            <table style="border-collapse: collapse; padding: 0;">
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">{room}</td>
                                </tr>
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">診</td>
                                </tr>
                            </table>
                        </td>
                        <td width="70%" style="font-size: 120px; font-weight: bold; vertical-align: middle;
                            text-align: center">
                            {doctor[:3]}
                        </td>
                        <td width="15%" style="padding-right: 30px; font-size: 42px; font-weight: bold;
                            text-align: center; vertical-align: middle;">
                            <table style="border-collapse: collapse; padding: 0;">
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">醫</td>
                                </tr>
                                <tr>
                                    <td style="text-align: center; vertical-align: middle;">師</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </tbody>
            </table>
        """

        return html

    def _show_doctors(self):
        doctor1 = ""
        doctor2 = ""

        html = self._get_doctor_html(room=1, doctor=doctor1)
        self.ui.label_doctor1.setText(html)
        html = self._get_doctor_html(room=2, doctor=doctor2)
        self.ui.label_doctor2.setText(html)

        label_room_list = [
            None,
            self.ui.label_doctor1,
            self.ui.label_doctor2,
        ]

        rows = self._get_current_room_rows()
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]
        for row in rows:
            room = row["Room"]
            if room not in [1, 2]:
                continue

            doctor = string_utils.xstr(row[weekday])
            if room == 1:
                doctor1 = doctor
            elif room == 2:
                doctor2 = doctor

            html = self._get_doctor_html(room, doctor)
            label_room_list[room].setText(html)

        if doctor1 == "":
            html = self._get_sequence_html("")
            self.ui.label_room1.setText(html)
        if doctor2 == "":
            html = self._get_sequence_html("")
            self.ui.label_room2.setText(html)

    def start_blinking(self, interval=250):
        self.ui.label_room1.setStyleSheet(self.style_sheet)
        self.ui.label_room2.setStyleSheet(self.style_sheet)

        """開始閃爍"""
        self.blink_count = 0
        self.label_timer.start(interval)

    # def toggle_background(self):
    #     """切換 QLabel_room 的背景顏色"""
    #     self.blink_state = not self.blink_state
    #     color = "green" if self.blink_state else self.color
    #     self.label_room.setStyleSheet(f"background-color: {color}; font-size: 30px;")

    #     self.blink_count += 1
    #     if self.blink_count >= self.max_blinks:
    #         self.stop_blinking()

    # def stop_blinking(self):
    #     """停止閃爍，恢復背景顏色"""
    #     self.label_timer.stop()
    #     self.label_room.setStyleSheet(self.style_sheet)

    def toggle_background(self):
        """切換 QLabel_room 的背景顏色"""
        # 安全檢查：如果 label_room 還沒被指派，或是物件已經被銷毀，就直接停止
        if self.label_room is None:
            self.stop_blinking()
            return

        try:
            self.blink_state = not self.blink_state
            # 使用你原本定義好的 self.color 作為還原色
            color = "green" if self.blink_state else self.color

            # 這裡建議保留原本的 style，只改 background-color
            self.label_room.setStyleSheet(f"background-color: {color};")
            # self.label_room.setStyleSheet(
            #     f"background-color: {color}; font-size: 30px;"
            # )

            self.blink_count += 1
            if self.blink_count >= self.max_blinks:
                self.stop_blinking()
        except Exception as e:
            print(f"閃爍邏輯發生錯誤: {e}")
            self.stop_blinking()

    def stop_blinking(self):
        """停止閃爍，恢復原本的背景顏色"""
        self.label_timer.stop()
        if self.label_room is not None:
            try:
                self.label_room.setStyleSheet(self.style_sheet)
            except Exception:
                pass


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin_2rooms(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


# 程式開始
if __name__ == "__main__":
    main()
