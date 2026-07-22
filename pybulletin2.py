# -*- coding: UTF-8 -*-

import datetime
import json
import os
import sys

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
    date_utils,
    number_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
    voice_utils,
)

MAX_WAITING_ROWS = 7


# 候診資訊系統 單診間輪播版
class PyBulletin2(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PyBulletin2, self).__init__(parent)
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
        self.mediaplayer = None
        self.image_list_time = number_utils.get_integer(
            self.system_settings.field("輪播圖片間隔秒數")
        )
        if self.image_list_time == 0:
            self.image_list_time = 10000
        else:
            self.image_list_time *= 1000

        self.period1 = self.system_settings.field("早班時間")
        self.period2 = self.system_settings.field("午班時間")
        self.period3 = self.system_settings.field("晚班時間")

        self._set_ui()
        self._set_udp_server()
        self._set_signal()
        self._start_udp_server()

        monitor_number = self.get_monitor_number()
        monitor = QDesktopWidget().screenGeometry(monitor_number)
        self.move(monitor.left(), monitor.top())
        self.showMaximized()

    def _set_udp_server(self):
        self.socket_server = class_utils.get_socket_server(self, 8880)
        self.voice_server = class_utils.get_voice_server(self, 9990)

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
        if self.mediaplayer is not None:
            self.mediaplayer.stop()
            self.mediaplayer.release()

    def _close_socket(self):
        self.socket_server.stop_thread()
        self.voice_server.stop_thread()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_BULLETIN1, self)
        self.ui.setWindowFlags(Qt.FramelessWindowHint)  # 無視窗邊框
        self.setCursor(Qt.BlankCursor)

    # 設定信號
    def _set_signal(self):
        self.voice_server.update_signal.connect(self._broadcast_speech)
        self.socket_server.update_signal.connect(self._show_waiting_list)

    def _close(self):
        self.close()

    # 設定 css style
    def _set_style(self):
        system_utils.set_background_image(self.ui.tab_home, self.system_settings)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        system_utils.set_theme(self.ui, self.system_settings)

    def _start_udp_server(self):
        self.socket_server.start()
        self.voice_server.start()

    @staticmethod
    def _notify_wait_arrive():
        try:
            mixer.init()
            mixer.music.load("./icq.mp3")
            mixer.music.play()
        except pygame.error:
            pass

    def _set_lower_audio(self):
        if self.mediaplayer is None:
            return

        if self.url in ["", None]:
            return

        self.mediaplayer.audio_set_volume(5)
        self.audio_timer.start(6000)
        self.audio_timer.timeout.connect(self._normal_audio)

    def _normal_audio(self):
        if self.mediaplayer is None:
            return

        self.mediaplayer.audio_set_volume(self.volume)
        self.audio_timer.stop()

    # 廣播叫號
    def _broadcast_speech(self, json_data):
        voice_dict = json.loads(json_data)

        regist_no = number_utils.get_integer(voice_dict["regist_no"])
        room = number_utils.get_integer(voice_dict["room"])
        sentence = voice_dict["sentence"]

        self.waiting_number[room] = regist_no

        self._show_waiting_list()
        QtWidgets.qApp.processEvents()

        try:
            if self.media_type not in ["輪播圖片"]:
                self._set_lower_audio()
        except Exception:
            pass

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

    def _play_videos(self):
        self._set_video_list()
        self._display_video()

    def _display_video(self):
        pass

    def _display_image(self, image_file=None):
        if image_file is None:
            self.image_list_index = 0
            image_file = self.image_list[self.image_list_index]

        self.ui.frame_youtube.setStyleSheet(f"border-image: url({image_file})")

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

    def _set_video_list(self):
        self.video_list_index = 1

        sql = """
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播影片檔%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)

        self.video_list = []
        for row in rows:
            self.video_list.append(row["Value"])

    def _play_url_stream(self):
        if self.url in ["", None]:
            return

        self.vlc_instance = vlc.Instance()
        self.mediaplayer = self.vlc_instance.media_player_new()

        win_id = int(self.ui.frame_youtube.winId())
        if sys.platform == "win32":
            self.mediaplayer.set_hwnd(win_id)
        elif sys.platform == "linux":
            self.mediaplayer.set_xwindow(win_id)
        elif sys.platform == "darwin":
            self.mediaplayer.set_nsobject(win_id)

        # 獲取視頻的播放地址
        ydl_opts = {"format": "best"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=False)
            video_url = info["url"]

        self.media = self.vlc_instance.media_new(video_url)

        self.media.get_mrl()
        self.mediaplayer.set_media(self.media)
        self.mediaplayer.play()
        self.mediaplayer.audio_set_volume(self.volume)

    # def _play_url_stream(self):
    #     if self.url in ['', None]:
    #         return

    #     self.vlc_instance = vlc.Instance()
    #     self.mediaplayer = self.vlc_instance.media_player_new()
    #     if self.mediaplayer is None:
    #         return

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

    def _set_clock(self):
        current_time = datetime.datetime.now().strftime("%H:%M")
        self.ui.label_clock.setText(current_time)

        self.clock_timer = QtCore.QTimer(self)
        self.clock_timer.start(1000)
        self.clock_timer.timeout.connect(self._clock_timeout)

    def _clock_timeout(self):
        current_time = datetime.datetime.now().strftime("%H:%M")
        self.ui.label_clock.setText(current_time)

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

        if len(rows) <= 0:
            sql = f"""
                SELECT * FROM doctor_schedule
                WHERE
                    {weekday} IS NOT NULL AND
                    LENGTH({weekday}) > 0
                GROUP BY Room
                ORDER BY Room
            """
            rows = self.database.select_record(sql)

        return rows

    def _get_waiting_rows(self):
        # current_period = registration_utils.get_current_period(self.system_settings)

        sql = """
            SELECT RegistNo, Name FROM wait
            WHERE
                DoctorDone = "False"
            ORDER BY RegistNo
        """
        rows = self.database.select_record(sql)

        return rows

    def _mask_name(self, name):
        mask_name = name[0] + "〇" + name[2:6]

        return mask_name

    def _get_waiting_html(self):
        rows = self._get_current_room_rows()
        if len(rows) <= 0:
            return ""

        row = rows[0]
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]

        html = ""
        room = number_utils.get_integer(row["Room"])
        doctor = string_utils.xstr(row[weekday])
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

        waiting_rows = self._get_waiting_rows()
        waiting_html = ""
        for row_no, row in enumerate(waiting_rows):
            if row_no >= MAX_WAITING_ROWS:
                break

            regist_no = number_utils.get_integer(row["RegistNo"])
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
                        {self._mask_name(string_utils.xstr(row["Name"]))}
                    </td>
                </tr>
            """

        html += f"""
            <tr>
                <td>
                    <table width="98%" style="font-weight:bold; font-family:Microsoft JhengHei">
                        <thead>
                            <tr bgcolor="Navy" style="color: white">
                                <th width="40%" style="font-size: 48px; font-weight: bold;"
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

    def _show_waiting_list(self):
        waiting_html = self._get_waiting_html()

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


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin2(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


# 程式開始
if __name__ == "__main__":
    main()
