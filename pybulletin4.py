import datetime
import json
import os
import sys
import threading

import pygame
from pygame import mixer
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDesktopWidget

if sys.platform == "win32":
    os.environ["PYTHON_VLC_MODULE_PATH"] = "./vlc"

import configparser

import yt_dlp

import vlc
from libs import (
    class_utils,
    notification_utils,
    number_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
    voice_utils,
)

MAX_ROOM = 10
MAX_WAITING_ROWS = 7  # 候診一頁顯示人數
ROTATION_SECONDS = 5000


# 候診資訊系統 多診間輪播版
class PyBulletin4(QtWidgets.QMainWindow):
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

        self.rotation_timer = QtCore.QTimer(self)
        self.rotation_timer.timeout.connect(self._rotation_wait_list)
        self.sub_rotation_timer = QtCore.QTimer(self)
        self.sub_rotation_timer.timeout.connect(self._sub_rotation_wait_list)
        self.current_room = 1

        self._set_ui()
        self._set_notification_server()
        self._set_signal()

        monitor_number = self.get_monitor_number()
        monitor = QDesktopWidget().screenGeometry(monitor_number)
        self.move(monitor.left(), monitor.top())
        self.showFullScreen()

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
            self._broadcast_speech(message)  # 內容是 refresh_wait，它自己會分辨
        elif channel == notification_utils.CHANNEL_CALL_NUMBER:
            self._broadcast_speech(message)

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
        self._play_media()
        self._play_marquee()
        self._show_waiting_list()
        self._set_clock()

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
        try:
            self.vlc_player.stop()
            self.vlc_player.release()
        except Exception:
            pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_BULLETIN1, self)
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        self.setCursor(Qt.BlankCursor)

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

    @staticmethod
    def _notify_wait_arrive():
        try:
            mixer.init()
            mixer.music.load("./icq.mp3")
            mixer.music.play()
        except pygame.error:
            pass

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
    def _broadcast_speech(self, json_data):
        if json_data == "refresh_wait":
            self.show_seq_number = True
            self._show_waiting_list()
            self.show_seq_number = False
            return

        try:
            voice_dict = json.loads(json_data)
        except Exception:
            print("json error: ", json_data)
            return

        regist_no = number_utils.get_integer(voice_dict["regist_no"])
        room = number_utils.get_integer(voice_dict["room"])
        sentence = voice_dict["sentence"]

        self.waiting_number[room] = regist_no

        rows = self._get_wait_rows(room)
        if len(rows) > 0:
            self._current_room = room
            row = rows[0]
            self._show_waiting_list_html(row)

        QtWidgets.qApp.processEvents()
        self._set_lower_audio()
        voice_utils.speak(sentence, threading=True)

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

    def _is_url(self, source):
        return source.lower().startswith(
            ("http://", "https://", "rtsp://", "rtmp://", "mms://")
        )

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
            url = row["Value"]
            if self._is_url(url):
                self.stream_list.append(url)

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

        # stream_url = self._get_stream_url(self.stream_index)
        # self.media = self.vlc_instance.media_new(stream_url)
        # self.vlc_player.set_media(self.media)

        video_url, audio_url = self._get_stream_url(self.stream_index)
        self.media = self.vlc_instance.media_new(video_url)
        if audio_url is not None:
            self.media.add_option(f":input-slave={audio_url}")

        self.media.add_option(":network-caching=3000")
        self.media.add_option(":audio-desync=-200")  # 毫秒
        self.vlc_player.set_media(self.media)

        events = self.vlc_player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

        self.vlc_player.play()
        self._start_volume_timer()

    def _start_volume_timer(self):
        self.volume_retry = 0
        self.volume_timer = QtCore.QTimer(self)
        self.volume_timer.timeout.connect(self._apply_volume)
        self.volume_timer.start(300)

    def _apply_volume(self):
        self.volume_retry += 1
        self.vlc_player.audio_set_volume(self.volume)

        if self.vlc_player.audio_get_volume() == self.volume:
            self.volume_timer.stop()  # 設定成功
        elif self.volume_retry > 30:
            self.volume_timer.stop()  # 約 9 秒後放棄,避免無限輪詢

    # def _get_stream_url(self, index):
    #     url = self.stream_list[index]

    #     ydl_opts = {
    #         "format": "best",
    #         "buffer-size": "4096",
    #     }
    #     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #         info = ydl.extract_info(url, download=False)
    #         stream_url = info["url"]

    #     return stream_url

    def _get_stream_url(self, index):
        url = self.stream_list[index]

        ydl_opts = {"format": "bestvideo+bestaudio/best"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if "requested_formats" in info:  # 影音分離
            video_url = info["requested_formats"][0]["url"]
            audio_url = info["requested_formats"][1]["url"]
        else:  # 傳統合流格式
            video_url = info["url"]
            audio_url = None

        return video_url, audio_url

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

    # def _play_media(self):
    #     if self.url in ['', None]:
    #         return

    #     self.vlc_instance = vlc.Instance()
    #     self.mediaplayer = self.vlc_instance.media_player_new()

    #     win_id = int(self.ui.frame_youtube.winId())
    #     if sys.platform == 'win32':
    #         self.mediaplayer.set_hwnd(win_id)
    #     elif sys.platform == 'linux':
    #         self.mediaplayer.set_xwindow(win_id)
    #     elif sys.platform == 'darwin':
    #         self.mediaplayer.set_nsobject(win_id)

    #     try:
    #         video = pafy.new(self.url)
    #         best = video.getbest()
    #         self.media = self.vlc_instance.media_new(best.url)
    #     except Exception:
    #         try:
    #             self.media.release()
    #         except Exception:
    #             pass

    #         self._play_media()

    #     self.media.get_mrl()
    #     self.mediaplayer.set_media(self.media)
    #     self.mediaplayer.play()
    #     self.mediaplayer.audio_set_volume(self.volume)

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
        self.marquee_start = QtWidgets.QDesktopWidget().screenGeometry(-1).width() + 100

        self._set_marquee_text()

        self.current_x = self.marquee_start
        self.ui.label_marquee.move(self.current_x, 0)
        self._set_timer()

    def _set_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.start(9)
        self.timer.timeout.connect(self._timeout)

    def _timeout(self):
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

        self.ui.label_marquee.move(self.current_x, 0)

    def _set_marquee_text(self):
        self.ui.label_marquee.setText(self.marquee_list[self.marquee_index])
        self.ui.label_marquee.adjustSize()
        self.marquee_text_width = self.ui.label_marquee.width() + 100

    def _get_waiting_rows(self, room, current_page=None):
        current_period = registration_utils.get_current_period(self.system_settings)

        if current_page is None:
            limit_script = ""
        else:
            start = current_page * MAX_WAITING_ROWS
            limit_script = f"LIMIT {start}, {MAX_WAITING_ROWS}"

        sql = f'''
            SELECT PatientKey, RegistNo, Name, Remark FROM wait
            WHERE
                Room = {room} AND
                Period = "{current_period}" AND
                Doctor != "全部醫師" AND
                DoctorDone = "False"
            ORDER BY RegistNo
            {limit_script}
        '''
        rows = self.database.select_record(sql)

        return rows

    def _mask_name(self, name):
        name = string_utils.remove_not_chinese_character(name)
        mask_name = name[0] + "〇" + name[2:6]

        return mask_name

    def _get_seq_number(self, room):
        sql = f"""
            SELECT SeqNumber FROM seq_number
            WHERE
                Room = {room}
        """
        try:
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                seq_number = 0
            else:
                seq_number = number_utils.get_integer(rows[0]["SeqNumber"])
        except Exception:
            seq_number = 0

        return seq_number

    def _get_waiting_html(self, row, current_page=None):
        html = ""
        room = number_utils.get_integer(row["Room"])
        doctor = string_utils.xstr(row["Doctor"])
        seq_number = self._get_seq_number(room)

        # if self.show_seq_number:
        #     called_regist_no = self._get_seq_number(room)
        # else:
        #     called_regist_no = self.waiting_number[room]

        if seq_number > 0:
            called_regist_no = seq_number
        else:
            called_regist_no = self.waiting_number[room]

        html += f"""
            <tr>
                <td>
                    <table width="98%" style="font-weight:bold; font-family:Microsoft JhengHei">
                        <thead>
                            <tr bgcolor="Navy" style="color: white">
                                <th style="font-size: 48px; font-weight: bold;"
                                    text-align: center; padding-left: 8px>
                                    {room}診 {doctor}醫師
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr bgcolor="LightCyan" style="color: red">
                                <td style="font-size: 128px; font-weight: bold" align="center">
                                    {called_regist_no}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </td>
            </tr>
        """

        waiting_rows = self._get_waiting_rows(room, current_page=current_page)
        waiting_html = ""
        for row_no, row in enumerate(waiting_rows):
            if row_no >= MAX_WAITING_ROWS:
                break

            patient_key = string_utils.xstr(row["PatientKey"])
            regist_no = number_utils.get_integer(row["RegistNo"])
            remark = string_utils.xstr(row["Remark"])

            label_remark = ""
            if registration_utils.is_in_reservation_list(
                self.database, patient_key, datetime.datetime.now().date()
            ):
                label_remark = "預約"

            if "過號" in remark:
                label_remark += "過號"

            if self.show_name_only == "Y":
                label_remark = ""

            if regist_no == called_regist_no:
                color = "red"
            else:
                color = "navy"

            waiting_html += f"""
                <tr bgcolor="LightCyan" style="color: {color}">
                    <td style="font-size: 72px; font-weight: bold" align="center">
                        {regist_no}
                    </td>
                    <td style="font-size: 72px; font-weight: bold" align="center">
                        {self._mask_name(string_utils.xstr(row["Name"]))}<font size="7" color="magenta">{label_remark}</font>
                    </td>
                </tr>
            """

        html += f"""
            <tr>
                <td>
                    <table width="98%" style="font-weight:bold; font-family:Microsoft JhengHei">
                        <thead>
                            <tr bgcolor="Navy" style="color: white">
                                <th width="30%" style="font-size: 48px; font-weight: bold;"
                                    text-align: center; padding-left: 8px>
                                    診號
                                </th>
                                <th style="font-size: 48px; font-weight: bold;"
                                    text-align: center; padding-left: 8px>
                                    姓名
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {waiting_html}
                        </tbody>
                    </table>
                </td>
            </tr>
        """

        return html

    def _get_wait_rows(self, room=None):
        current_period = registration_utils.get_current_period(self.system_settings)
        if room is None:
            room = self.current_room

        sql = f'''
            SELECT * FROM wait
            WHERE
                Period = "{current_period}" AND
                Doctor != "全部醫師" AND
                Room = {room}
            GROUP BY Room
        '''
        rows = self.database.select_record(sql)

        return rows

    def _rotation_wait_list(self):
        while True:
            self.current_room += 1
            if self.current_room > MAX_ROOM:
                self.current_room = 1

            rows = self._get_wait_rows()
            if len(rows) > 0:
                row = rows[0]
                break

        self._show_waiting_list_html(row)

    def _get_room_rows(self):
        current_period = registration_utils.get_current_period(self.system_settings)

        sql = f'''
            SELECT Room, Doctor FROM wait
            WHERE
                Period = "{current_period}" AND
                Doctor != "全部醫師"
            GROUP BY Room ORDER BY Room
        '''
        rows = self.database.select_record(sql)

        return rows

    # 顯示候診名單
    def _show_waiting_list(self, row=None):
        self.rotation_timer.stop()
        if row is None:
            rows = self._get_room_rows()
            if len(rows) <= 0:
                room = 1
                period = registration_utils.get_current_period(self.system_settings)
                doctor = registration_utils.get_schedule_doctor(
                    self.database, room, period
                )

                row = {"Room": room, "Doctor": doctor}
            else:
                row = rows[0]
        else:
            rows = [row]

        if len(rows) >= 2:  # 超過兩個診間，啟動輪播機制
            self.rotation_timer.start(ROTATION_SECONDS)

        self._show_waiting_list_html(row)

    def _show_waiting_list_html(self, row):
        room = number_utils.get_integer(row["Room"])
        waiting_rows_count = len(self._get_waiting_rows(room))

        if (
            waiting_rows_count > MAX_WAITING_ROWS
        ):  # 超過一頁, 停止全域輪播, 改單一診間輪播
            self.rotation_timer.stop()
            self.current_row = row
            self.current_page = 0
            self.pages = int(waiting_rows_count / MAX_WAITING_ROWS)
            if waiting_rows_count % MAX_WAITING_ROWS > 0:
                self.pages += 1

            self.sub_rotation_timer.start(ROTATION_SECONDS)
        else:
            self._show_waiting_list_row(row)

    def _sub_rotation_wait_list(self):
        self._show_waiting_list_row(self.current_row, self.current_page)
        self.current_page += 1

        if self.current_page >= self.pages:
            self.sub_rotation_timer.stop()
            self.rotation_timer.start(ROTATION_SECONDS)

    def _show_waiting_list_row(self, row, current_page=None):
        waiting_html = self._get_waiting_html(row, current_page=current_page)

        html = f"""
            <table align=center cellpadding="2" cellspacing="2" width="98%"
                style=" background-color: #ccc;
                        -moz-border-radius: 5px;
                        -webkit-border-radius: 5px;
                        border: 1px solid #000;
                        padding: 10px;">
                <tbody>
                    {waiting_html}
                </tbody>
            </table>
        """
        self.ui.textBrowser_waiting_list.setHtml(html)

    def _set_clock(self):
        current_time = datetime.datetime.now().strftime("%H:%M")
        self.ui.label_clock.setText(current_time)

        self.clock_timer = QtCore.QTimer(self)
        self.clock_timer.start(1000)
        self.clock_timer.timeout.connect(self._clock_timeout)

    def _clock_timeout(self):
        current_time = datetime.datetime.now().strftime("%H:%M")
        self.ui.label_clock.setText(current_time)


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin4(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


# 程式開始
if __name__ == "__main__":
    main()
