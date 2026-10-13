# -*- coding: UTF-8 -*-
# 候診資訊系統 直立版 (1080x1920) - 獨立程式
#   上方: 標題 + 媒體 (輪播圖片 / 輪播影片 / 串流)
#   下方: 左右兩個診間, 只顯示診號, 不顯示姓名 (隱私), 超過一頁自動換頁
#   底部: 跑馬燈

import configparser
import datetime
import json
import os
import sys
import threading

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDesktopWidget

if sys.platform == "win32":
    os.environ["PYTHON_VLC_MODULE_PATH"] = "./vlc"

import yt_dlp

import vlc
from libs import (
    class_utils,
    notification_utils,
    number_utils,
    registration_utils,
    string_utils,
    volume_utils,
)

PORTRAIT_ROOMS = 2  # 下方顯示幾個診間
NUMBER_COLUMNS = 2  # 候診號每列幾個
NUMBER_ROWS = 6  # 候診號幾列 -> 一頁 10 個, 超過自動換頁
PAGE_SIZE = NUMBER_COLUMNS * NUMBER_ROWS
PAGE_SECONDS = 5000  # 換頁間隔 (毫秒)
HEADER_HEIGHT = 110
MARQUEE_HEIGHT = 90
MEDIA_HEIGHT = 608  # 1080 寬的 16:9 剛好約 608, 再小影片左右會出現黑邊
MAX_ROOM_NO = 100
MAX_SCHEDULE_ROOM = 10  # 班表檢查到第幾診


class PyBulletinPortrait(QtWidgets.QMainWindow):
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.args = args

        self._set_db()
        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(
            self.database, self.config_file
        )

        self.waiting_number = [0 for _ in range(MAX_ROOM_NO)]  # 各診叫號廣播記下的號碼
        self.room_page = {}
        self.room_page_count = {}
        self.current_rooms = []
        self.last_period_check = None

        # 兩個音量各自獨立: 語音播放音量 -> 叫號語音, 媒體播放音量 -> VLC
        self.volume_controller = volume_utils.VolumeController(
            self,
            database=self.database,
            get_player=lambda: getattr(self, "vlc_player", None),
        )

        self.url = self.system_settings.field("媒體播放位址")
        self.media_type = self.system_settings.field("媒體播放來源")
        self.image_list_time = number_utils.get_integer(
            self.system_settings.field("輪播圖片間隔秒數")
        )
        if self.image_list_time == 0:
            self.image_list_time = 10000
        else:
            self.image_list_time *= 1000

        self.period_times = [
            self.system_settings.field("早班時間"),
            self.system_settings.field("午班時間"),
            self.system_settings.field("晚班時間"),
        ]

        self._set_ui()
        self._set_notification_server()

        monitor = QDesktopWidget().screenGeometry(self._get_monitor_number())
        self.move(monitor.left(), monitor.top())
        self.showFullScreen()

    def __del__(self):
        try:
            self.vlc_player.stop()
            self.vlc_player.release()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 資料庫 / 設定
    # ------------------------------------------------------------------

    def _set_db(self):
        try:
            config_file = self.args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.database = class_utils.get_db(
                host=config_dict["host"],
                user=config_dict["user"],
                database=config_dict["database"],
                password=config_dict["password"],
                charset=config_dict["charset"],
                buffered=config_dict["buffered"],
            )
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE

    @staticmethod
    def _parse_config_file(config_file, db_section="db"):
        config = configparser.ConfigParser()
        config.read(config_file)

        return {
            "host": config[db_section]["host"],
            "user": config[db_section]["user"],
            "database": config[db_section]["database"],
            "password": config[db_section]["password"],
            "charset": config[db_section]["charset"],
            "buffered": True,
        }

    def _get_monitor_number(self):
        return number_utils.get_integer(
            self.system_settings.field("候診系統顯示器編號")
        )

    def _get_settings_values(self, field_prefix):
        sql = f"""
            SELECT Value FROM system_settings
            WHERE
                Field LIKE "{field_prefix}%"
            ORDER BY Field
        """
        rows = self.database.select_record(sql)

        return [string_utils.xstr(row["Value"]) for row in rows]

    # ------------------------------------------------------------------
    # 版面
    # ------------------------------------------------------------------

    def _set_ui(self):
        central = QtWidgets.QWidget(self)
        central.setObjectName("central")
        central.setAttribute(Qt.WA_StyledBackground, True)
        central.setStyleSheet("#central { background-color: #ccc; }")
        self.setCentralWidget(central)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setCursor(Qt.BlankCursor)

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 標題列: 院所名稱 + 時鐘
        header = QtWidgets.QFrame()
        header.setObjectName("header")
        header.setFixedHeight(HEADER_HEIGHT)
        header.setStyleSheet("#header { background-color: navy; }")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        label_style = (
            "color: white; font-size: 44px; font-weight: bold;"
            "font-family: 'Microsoft JhengHei';"
        )
        self.label_title = QtWidgets.QLabel()
        self.label_title.setStyleSheet(label_style)
        self.label_clock = QtWidgets.QLabel()
        self.label_clock.setStyleSheet(label_style)
        self.label_clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(self.label_title, 1)
        header_layout.addWidget(self.label_clock, 0)

        # 媒體區 (VLC 直接畫在這個 frame 上; 輪播圖片用 border-image)
        self.frame_media = QtWidgets.QFrame()
        self.frame_media.setStyleSheet("background-color: black;")
        self.frame_media.setFixedHeight(MEDIA_HEIGHT)

        # 診間區: 左右各一個 QTextBrowser
        rooms_widget = QtWidgets.QWidget()
        rooms_layout = QtWidgets.QHBoxLayout(rooms_widget)
        rooms_layout.setContentsMargins(8, 8, 8, 8)
        rooms_layout.setSpacing(8)
        self.room_browsers = []
        for _ in range(PORTRAIT_ROOMS):
            browser = QtWidgets.QTextBrowser()
            browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            browser.setStyleSheet("background-color: #ccc; border: none;")
            rooms_layout.addWidget(browser)
            self.room_browsers.append(browser)

        # 跑馬燈: label 不放進 layout, 由 timer 用 move() 移動
        self.marquee_frame = QtWidgets.QFrame()
        self.marquee_frame.setObjectName("marquee")
        self.marquee_frame.setFixedHeight(MARQUEE_HEIGHT)
        self.marquee_frame.setStyleSheet("#marquee { background-color: navy; }")
        self.label_marquee = QtWidgets.QLabel(self.marquee_frame)
        self.label_marquee.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_marquee.setStyleSheet(
            "color: yellow; font-size: 56px; font-weight: bold;"
            "font-family: 'Microsoft JhengHei';"
        )

        # 媒體固定高度, 剩下的空間全部給診間
        layout.addWidget(header, 0)
        layout.addWidget(self.frame_media, 0)
        layout.addWidget(rooms_widget, 1)
        layout.addWidget(self.marquee_frame, 0)

    def show_bulletin(self):
        self.label_title.setText(
            self.system_settings.field("院所名稱") + " 候診資訊系統"
        )
        self._play_media()
        self._play_marquee()
        self._show_waiting_list()
        self._set_clock()
        self._set_page_timer()

    # ------------------------------------------------------------------
    # 通知 / 叫號
    # ------------------------------------------------------------------

    def _set_notification_server(self):
        channels = [
            notification_utils.CHANNEL_WAITING_LIST,
            notification_utils.CHANNEL_BULLETIN,
            notification_utils.CHANNEL_CALL_NUMBER,
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
            self._show_waiting_list()
        elif channel == notification_utils.CHANNEL_BULLETIN:
            # 音量相關的訊息先攔下來
            if self.volume_controller.handle_bulletin_message(message):
                return

            self._broadcast_speech(message)
        elif channel == notification_utils.CHANNEL_CALL_NUMBER:
            self._broadcast_speech(message)

    def _broadcast_speech(self, json_data):
        json_data = string_utils.xstr(json_data).strip()

        if json_data == "refresh_wait":
            self._show_waiting_list()
            return

        try:
            voice_dict = json.loads(json_data)
        except Exception:
            print("json error: ", json_data)
            return

        regist_no = number_utils.get_integer(voice_dict["regist_no"])
        room = number_utils.get_integer(voice_dict["room"])
        sentence = voice_dict["sentence"]

        # 設定「候診語音不念姓名」= Y 時, 只念號碼
        if string_utils.xstr(self.system_settings.field("候診語音不念姓名")) == "Y":
            sentence = f"請 {regist_no} 號 到 {room} 診"

        if 0 <= room < MAX_ROOM_NO:
            self.waiting_number[room] = regist_no

        self._show_waiting_list()
        QtWidgets.qApp.processEvents()

        # 壓低電視音量 + 用語音播放音量播報, 念完自動還原
        self.volume_controller.speak(sentence)

    # ------------------------------------------------------------------
    # 媒體
    # ------------------------------------------------------------------

    def _play_media(self):
        if self.media_type == "輪播圖片":
            self._play_images()
        elif self.media_type == "輪播影片":
            self._play_videos()
        else:
            self._play_url_stream()

    # 輪播圖片
    def _play_images(self):
        self.image_list = self._get_settings_values("輪播圖片檔")
        if len(self.image_list) <= 0:
            return

        self.image_list_index = 0
        self._display_image()

        self.image_list_timer = QtCore.QTimer(self)
        self.image_list_timer.timeout.connect(self._image_list_timeout)
        self.image_list_timer.start(self.image_list_time)

    def _image_list_timeout(self):
        self.image_list_index = (self.image_list_index + 1) % len(self.image_list)
        self._display_image()

    def _display_image(self):
        image_file = self.image_list[self.image_list_index]
        self.frame_media.setStyleSheet(f"border-image: url({image_file})")

    # VLC 共用
    def _new_vlc_player(self):
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        win_id = int(self.frame_media.winId())
        if sys.platform == "win32":
            self.vlc_player.set_hwnd(win_id)
        elif sys.platform == "linux":
            self.vlc_player.set_xwindow(win_id)
        elif sys.platform == "darwin":
            self.vlc_player.set_nsobject(win_id)

    # 輪播影片 (本機檔案)
    def _play_videos(self):
        video_list = self._get_settings_values("輪播影片檔-")
        if len(video_list) <= 0:
            return

        self._new_vlc_player()

        media_list = self.vlc_instance.media_list_new()
        for filename in video_list:
            media_list.add_media(self.vlc_instance.media_new(filename))

        self.media_list_player = vlc.MediaListPlayer()
        self.media_list_player.set_playback_mode(vlc.PlaybackMode.loop)
        self.media_list_player.set_media_list(media_list)
        self.media_list_player.set_media_player(self.vlc_player)
        self.media_list_player.play()

        self.volume_controller.start_media_volume_timer()

    # 串流 (YouTube 等網址)
    @staticmethod
    def _is_url(source):
        return source.lower().startswith(
            ("http://", "https://", "rtsp://", "rtmp://", "mms://")
        )

    def _play_url_stream(self):
        self.stream_index = 0
        self.stream_list = []
        if self.url not in ["", None]:
            self.stream_list.append(self.url)
        for url in self._get_settings_values("輪播影片檔"):
            if self._is_url(url):
                self.stream_list.append(url)

        if len(self.stream_list) <= 0:
            return

        self._new_vlc_player()

        self.media = self._new_stream_media(self.stream_index)
        self.vlc_player.set_media(self.media)

        events = self.vlc_player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

        self.vlc_player.play()
        self.volume_controller.start_media_volume_timer()

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

    def _new_stream_media(self, index):
        """依索引取得串流網址並建立 media, 影音分離時補上 input-slave"""
        video_url, audio_url = self._get_stream_url(index)

        media = self.vlc_instance.media_new(video_url)
        if audio_url is not None:
            media.add_option(f":input-slave={audio_url}")

        media.add_option(":network-caching=3000")
        media.add_option(":audio-desync=-200")  # 毫秒

        return media

    def _on_end_reached(self, event):
        self.stream_index = (self.stream_index + 1) % len(self.stream_list)
        index = self.stream_index

        # VLC 的 callback 不能直接呼叫 player 的方法, 另開執行緒處理
        def restart_media():
            try:
                self.vlc_player.stop()
                self.media = self._new_stream_media(index)
                self.vlc_player.set_media(self.media)
                self.vlc_player.play()
                # set_media() 之後 VLC 會重建 audio output, 音量要重設
                self.volume_controller.apply_media_volume_blocking()
            except Exception as e:
                print(f"切換串流失敗: {e}")

        threading.Thread(target=restart_media, daemon=True).start()

    # ------------------------------------------------------------------
    # 跑馬燈 / 時鐘
    # ------------------------------------------------------------------

    def _play_marquee(self):
        self.marquee_list = self._get_settings_values("跑馬燈訊息-")
        if len(self.marquee_list) <= 0:
            self.marquee_list = [
                self.system_settings.field("院所名稱") + " 關心您的健康"
            ]

        self.marquee_index = 0
        screen = QDesktopWidget().screenGeometry(self._get_monitor_number())
        self.marquee_start = screen.width() + 100

        self._set_marquee_text()
        self.current_x = self.marquee_start
        self.label_marquee.move(self.current_x, 0)

        self.marquee_timer = QtCore.QTimer(self)
        self.marquee_timer.timeout.connect(self._marquee_timeout)
        self.marquee_timer.start(9)

    def _marquee_timeout(self):
        self.current_x -= 1
        if self.current_x <= -self.marquee_text_width:
            self.current_x = self.marquee_start
            self.marquee_index = (self.marquee_index + 1) % len(self.marquee_list)
            self._set_marquee_text()

        self.label_marquee.move(self.current_x, 0)

    def _set_marquee_text(self):
        self.label_marquee.setText(self.marquee_list[self.marquee_index])
        self.label_marquee.adjustSize()
        # adjustSize() 之後高度會縮, 撐回整條跑馬燈高度讓文字垂直置中
        self.label_marquee.resize(self.label_marquee.width(), MARQUEE_HEIGHT)
        self.marquee_text_width = self.label_marquee.width() + 100

    def _set_clock(self):
        self._clock_timeout()
        self.clock_timer = QtCore.QTimer(self)
        self.clock_timer.timeout.connect(self._clock_timeout)
        self.clock_timer.start(1000)

    def _clock_timeout(self):
        current_time = datetime.datetime.now().strftime("%H:%M")
        self.label_clock.setText(current_time)

        # 換班時間到刷新一次 (同一分鐘只刷一次)
        if current_time in self.period_times and current_time != self.last_period_check:
            self.last_period_check = current_time
            self.room_page.clear()
            self._show_waiting_list()

    # ------------------------------------------------------------------
    # 候診名單
    # ------------------------------------------------------------------

    def _get_portrait_rooms(self):
        """
        決定要顯示哪幾診 (最多 PORTRAIT_ROOMS 診):
          1. 系統設定「直立看板診間」有設定 (例如 "1,3") -> 固定顯示
          2. 否則抓本班醫師班表有排醫師的診間
          3. 班表也沒有 -> 抓候診名單裡有掛號的診間
        """
        setting = string_utils.xstr(self.system_settings.field("直立看板診間"))
        rooms = [number_utils.get_integer(x) for x in setting.split(",") if x.strip()]
        rooms = [room for room in rooms if 0 < room < MAX_ROOM_NO]
        if len(rooms) > 0:
            return rooms[:PORTRAIT_ROOMS]

        current_period = registration_utils.get_current_period(self.system_settings)

        rooms = []
        for room in range(1, MAX_SCHEDULE_ROOM + 1):
            doctor = string_utils.xstr(
                registration_utils.get_schedule_doctor(
                    self.database, room, current_period
                )
            ).strip()
            if doctor not in ["", "None"]:
                rooms.append(room)
                if len(rooms) >= PORTRAIT_ROOMS:
                    return rooms

        if len(rooms) > 0:
            return rooms

        sql = f'''
            SELECT Room FROM wait
            WHERE
                Period = "{current_period}" AND
                Doctor != "全部醫師"
            GROUP BY Room ORDER BY Room
        '''
        rows = self.database.select_record(sql)
        rooms = [number_utils.get_integer(row["Room"]) for row in rows]
        rooms = [room for room in rooms if 0 < room < MAX_ROOM_NO]

        return rooms[:PORTRAIT_ROOMS]

    def _get_room_doctor(self, room):
        current_period = registration_utils.get_current_period(self.system_settings)
        sql = f'''
            SELECT Doctor FROM wait
            WHERE
                Period = "{current_period}" AND
                Doctor != "全部醫師" AND
                Room = {room}
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return string_utils.xstr(rows[0]["Doctor"])

        return string_utils.xstr(
            registration_utils.get_schedule_doctor(self.database, room, current_period)
        )

    def _get_called_number(self, room):
        sql = f"""
            SELECT SeqNumber FROM seq_number
            WHERE
                Room = {room}
        """
        try:
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                seq_number = number_utils.get_integer(rows[0]["SeqNumber"])
                if seq_number > 0:
                    return seq_number
        except Exception:
            pass

        return self.waiting_number[room]

    def _get_waiting_numbers(self, room):
        current_period = registration_utils.get_current_period(self.system_settings)
        sql = f'''
            SELECT RegistNo FROM wait
            WHERE
                Room = {room} AND
                Period = "{current_period}" AND
                Doctor != "全部醫師" AND
                DoctorDone = "False"
            ORDER BY RegistNo
        '''
        rows = self.database.select_record(sql)

        return [number_utils.get_integer(row["RegistNo"]) for row in rows]

    # 刷新時重新決定診間 (班表一個診 -> 只顯示左邊, 右邊空白)
    def _show_waiting_list(self):
        self.current_rooms = self._get_portrait_rooms()
        for index in range(len(self.room_browsers)):
            self._show_room(index)

    def _show_room(self, index):
        browser = self.room_browsers[index]
        if index >= len(self.current_rooms):
            # 沒有這一診: 表格照畫, 內容空白, 左右版面才平衡
            browser.setHtml(self._build_room_html("&nbsp;", "&nbsp;", "", []))
            return

        browser.setHtml(self._get_room_html(self.current_rooms[index]))

    def _set_page_timer(self):
        self.page_timer = QtCore.QTimer(self)
        self.page_timer.timeout.connect(self._next_page)
        self.page_timer.start(PAGE_SECONDS)

    # 每 PAGE_SECONDS 換一頁, 只重畫有分頁的診間
    def _next_page(self):
        for index, room in enumerate(self.current_rooms[: len(self.room_browsers)]):
            page_count = self.room_page_count.get(room, 1)
            if page_count <= 1:
                continue

            self.room_page[room] = (self.room_page.get(room, 0) + 1) % page_count
            self._show_room(index)

    def _get_room_html(self, room):
        doctor = self._get_room_doctor(room)
        called_number = self._get_called_number(room)
        called_text = called_number if called_number > 0 else "--"

        next_numbers = [
            n for n in self._get_waiting_numbers(room) if n != called_number
        ]

        # 計算頁數; 人數變少時頁碼要拉回範圍內
        page_count = max(1, -(-len(next_numbers) // PAGE_SIZE))
        page = self.room_page.get(room, 0)
        if page >= page_count:
            page = 0
        self.room_page[room] = page
        self.room_page_count[room] = page_count

        start = page * PAGE_SIZE
        page_numbers = next_numbers[start : start + PAGE_SIZE]
        page_text = f" ({page + 1}/{page_count})" if page_count > 1 else ""

        return self._build_room_html(
            f"{room}診 {doctor}醫師", called_text, page_text, page_numbers
        )

    def _build_room_html(self, title, called_text, page_text, page_numbers):
        # 候診號垂直排列: 由上至下, 再由左至右
        #   1  6
        #   2  7
        #   3  8 ...
        number_rows = ""
        for r in range(NUMBER_ROWS):
            cells = ""
            for c in range(NUMBER_COLUMNS):
                i = c * NUMBER_ROWS + r
                n = str(page_numbers[i]) if i < len(page_numbers) else "&nbsp;"
                cells += (
                    f'<td width="{100 // NUMBER_COLUMNS}%" align="center" '
                    f'style="font-size: 72px; color: navy">{n}</td>'
                )
            number_rows += f'<tr bgcolor="LightCyan">{cells}</tr>'

        return f"""
            <table width="100%" cellspacing="4"
                style="font-weight: bold; font-family: Microsoft JhengHei">
                <tr bgcolor="Navy">
                    <td colspan="{NUMBER_COLUMNS}" align="center" style="font-size: 44px; color: white">
                        {title}
                    </td>
                </tr>
                <tr bgcolor="LightCyan">
                    <td colspan="{NUMBER_COLUMNS}" align="center" style="font-size: 36px; color: navy">
                        目前看診號
                    </td>
                </tr>
                <tr bgcolor="LightCyan">
                    <td colspan="{NUMBER_COLUMNS}" align="center" style="font-size: 140px; color: red">
                        {called_text}
                    </td>
                </tr>
                <tr bgcolor="Navy">
                    <td colspan="{NUMBER_COLUMNS}" align="center" style="font-size: 36px; color: white">
                        候診號碼{page_text}
                    </td>
                </tr>
                {number_rows}
            </table>
        """


def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletinPortrait(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
