# -*- coding: UTF-8 -*-

import sys
import pygame
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtCore import Qt
from pygame import mixer
import os
import datetime
import json

if sys.platform == 'win32':
    os.environ["PYTHON_VLC_MODULE_PATH"] = './vlc'

import vlc
try:
    import yt_dlp
except Exception:
    pass

import configparser

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import registration_utils
from libs import date_utils
from libs import string_utils
from libs import number_utils

MAX_WAITING_ROWS = 12
ROTATION_SECONDS = 10000
BG_COLOR = '#DAE7C1'
BORDER_COLOR = '#1D3609'
TEXT_COLOR = '#315415'
LATE_COLOR = '#C0392B'
HEADER_COLOR = '#DAE6BF'


# 悅兒親子系列診所專用
class PyBulletin3(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PyBulletin3, self).__init__(parent)
        self.args = args

        self._set_db()
        if not self.database.connected():
            sys.exit(0)

        self.system_settings = class_utils.get_system_settings(self.database, self.config_file)
        self.ui = None

        self.waiting_number = [0 for x in range(100)]
        self.audio_timer = QtCore.QTimer(self)
        self.volume = number_utils.get_integer(self.system_settings.field('媒體播放音量'))
        self.url = self.system_settings.field('媒體播放位址')
        self.schedule_file = self.system_settings.field('門診表圖檔名')

        self.period1 = self.system_settings.field('早班時間')
        self.period2 = self.system_settings.field('午班時間')
        self.period3 = self.system_settings.field('晚班時間')

        self.rotation_timer1 = QtCore.QTimer(self)
        self.rotation_timer1.timeout.connect(self._rotation_wait_list1)
        self.rotation_timer2 = QtCore.QTimer(self)
        self.rotation_timer2.timeout.connect(self._rotation_wait_list2)
        self.rotation_timer = [None, self.rotation_timer1, self.rotation_timer2]

        self.current_page1 = 1
        self.current_page2 = 1
        self.current_page = [None, self.current_page1, self.current_page2]

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
        return number_utils.get_integer(self.system_settings.field('候診系統顯示器編號'))

    def _set_db(self):
        self.host = None
        config_file = None

        try:
            config_file = self.args[0][1]
        except IndexError:
            config_file = None

        if config_file is not None:
            self.config_file = config_file
            config_dict = self._parse_config_file(self.config_file)
            self.host = config_dict['host']
            self.database = class_utils.get_db(
                host=self.host,
                user=config_dict['user'],
                database=config_dict['database'],
                password=config_dict['password'],
                charset=config_dict['charset'],
                buffered=config_dict['buffered'],
            )
            self.server_ip = config_dict['host']
        else:
            self.database = class_utils.get_db()
            self.config_file = self.database.CONFIG_FILE
            self.host = self.database.host

    def show_bulletin(self):
        self._show_title()
        self._play_media()
        self._play_marquee()
        self._show_waiting_list()
        self._set_image_list()
        self._set_qrcode()

    def _show_title(self):
        # title = self.system_settings.field('院所名稱') + ' 候診資訊'
        title = self.system_settings.field('院所名稱')
        self.ui.label_title.setText(title)

    def _play_media(self):
        if self.system_settings.field('媒體播放來源') == '輪播影片':
            self._play_video_file()
        else:
            self._play_url_stream()

    @staticmethod
    def _parse_config_file(config_file, db_section='db'):
        config = configparser.ConfigParser()
        config.read(config_file)

        config_dict = {
            'host': config[db_section]['host'],
            'user': config[db_section]['user'],
            'database': config[db_section]['database'],
            'password': config[db_section]['password'],
            'charset': config[db_section]['charset'],
            'buffered': True
        }

        return config_dict

    # 解構
    def __del__(self):
        self.mediaplayer.stop()
        self.mediaplayer.release()

    def _close_socket(self):
        self.socket_server.stop_thread()
        self.voice_server.stop_thread()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_BULLETIN3, self)
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
        system_utils.set_background_image(
            self.ui.tab_home, self.system_settings)
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
            mixer.music.load('./icq.mp3')
            mixer.music.play()
        except pygame.error:
            pass

    def _set_lower_audio(self):
        if self.url in ['', None]:
            return

        self.mediaplayer.audio_set_volume(5)

        self.audio_timer.start(6000)
        self.audio_timer.timeout.connect(self._normal_audio)

    def _normal_audio(self):
        self.mediaplayer.audio_set_volume(self.volume)
        self.audio_timer.stop()

    # 廣播叫號
    def _broadcast_speech(self, json_data):
        if json_data == 'refresh_wait':
            self._show_waiting_list()
            return

        voice_dict = json.loads(json_data)

        regist_no = number_utils.get_integer(voice_dict['regist_no'])
        room = number_utils.get_integer(voice_dict['room'])
        sentence = voice_dict['sentence']

        self.waiting_number[room] = regist_no

        self._show_waiting_list()
        QtWidgets.qApp.processEvents()
        self._set_lower_audio()
        system_utils.speak(sentence)

    def _get_video_list(self):
        sql = '''
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播影片檔-%"
            ORDER BY Field
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return []

        video_list = []
        for row in rows:
            video_list.append(string_utils.xstr(row['Value']))

        return video_list

    def _play_video_file(self):
        self.vlc_instance = vlc.Instance()
        self.mediaplayer = self.vlc_instance.media_player_new()
        self.mediaplayer.audio_set_volume(self.volume)
        # events = self.mediaplayer.event_manager()
        # events.event_attach(vlc.EventType.MediaPlayerEndReached, self.video_finished)

        win_id = int(self.ui.frame_youtube.winId())
        if sys.platform == 'win32':
            self.mediaplayer.set_hwnd(win_id)
        elif sys.platform == 'linux':
            self.mediaplayer.set_xwindow(win_id)
        elif sys.platform == 'darwin':
            self.mediaplayer.set_nsobject(win_id)

        media_list = self.vlc_instance.media_list_new()
        video_list = self._get_video_list()
        for filename in video_list:
            media_list.add_media(self.vlc_instance.media_new(filename))

        self.media_list_player = vlc.MediaListPlayer()
        self.media_list_player.set_playback_mode(vlc.PlaybackMode.loop)
        self.media_list_player.set_media_list(media_list)
        self.media_list_player.set_media_player(self.mediaplayer)
        self.media_list_player.play()

    def video_finished(self, data):
        self.video_index += 1
        if self.video_index >= len(self.media_list):
            self.video_index = 0

        filename = self.media_list[self.video_index]
        self._play_video(filename)

    def _play_url_stream(self):
        if self.url in ['', None]:
            return

        self.vlc_instance = vlc.Instance()
        self.mediaplayer = self.vlc_instance.media_player_new()

        win_id = int(self.ui.frame_youtube.winId())
        if sys.platform == 'win32':
            self.mediaplayer.set_hwnd(win_id)
        elif sys.platform == 'linux':
            self.mediaplayer.set_xwindow(win_id)
        elif sys.platform == 'darwin':
            self.mediaplayer.set_nsobject(win_id)

        # 獲取視頻的播放地址
        ydl_opts = {'format': 'best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=False)
            video_url = info['url']

        self.media = self.vlc_instance.media_new(video_url)

        self.media.get_mrl()
        self.mediaplayer.set_media(self.media)
        self.mediaplayer.play()
        self.mediaplayer.audio_set_volume(self.volume)

    # def _play_stream(self):
    #     if self.url in ['', None]:
    #         return

    #     self.vlc_instance = vlc.Instance('--repeat')
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

    #         self._play_stream()

    #     self.media.get_mrl()
    #     self.mediaplayer.set_media(self.media)
    #     self.mediaplayer.play()
    #     self.mediaplayer.audio_set_volume(self.volume)

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
        current_time = datetime.datetime.now().strftime('%H:%M')
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
                Room <= 2 AND
                Period = "{period}" AND
                {weekday} IS NOT NULL AND
                LENGTH({weekday}) > 0
            GROUP BY Room
            ORDER BY Room
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            sql = f'''
                SELECT * FROM doctor_schedule
                WHERE
                    {weekday} IS NOT NULL AND
                    LENGTH({weekday}) > 0
                GROUP BY Room
                ORDER BY Room
            '''
            rows = self.database.select_record(sql)

        return rows

    # 取得候診名單 (最多12個)
    def _get_waiting_rows(self, room, late=False):
        called_regist_no = self._get_called_regist_no(room)

        condition = f'RegistNo >= {called_regist_no}'
        if late:
            condition = f'RegistNo < {called_regist_no}'

        if self.current_page[room] == 1 or late:
            sql = f'''
                SELECT RegistNo, Name FROM wait
                WHERE
                    Room = {room} AND
                    {condition} AND
                    DoctorDone = "False"
                ORDER BY RegistNo LIMIT 12
            '''
        else:
            sql = f'''
                SELECT RegistNo, Name FROM wait
                WHERE
                    Room = {room} AND
                    {condition} AND
                    DoctorDone = "False"
                ORDER BY RegistNo LIMIT 12, 12
            '''
        rows = self.database.select_record(sql)

        return rows

    def _rotation_wait_list1(self):
        self.current_page[1] += 1
        if self.current_page[1] > 2:
            self.current_page[1] = 1

        self._show_waiting_list()

    def _rotation_wait_list2(self):
        self.current_page[2] += 1
        if self.current_page[2] > 2:
            self.current_page[2] = 1

        self._show_waiting_list()

    def _mask_name(self, name):
        mask_name = name[0] + '〇' + name[2:6]

        return mask_name

    def _get_total_waiting_count(self, room):
        called_regist_no = self._get_called_regist_no(room)

        sql = f'''
            SELECT RegistNo, Name FROM wait
            WHERE
                Room = {room} AND
                RegistNo >= {called_regist_no} AND
                DoctorDone = "False"
            ORDER BY RegistNo
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _get_waiting_html(self):
        rows = self._get_current_room_rows()
        if len(rows) <= 0:
            return ''

        html = ''
        for row in rows:
            html += self._get_room_html(row, len(rows))

            room = row['Room']
            total_row_count = self._get_total_waiting_count(room)
            if total_row_count > MAX_WAITING_ROWS:
                if not self.rotation_timer[room].isActive():
                    self.rotation_timer[room].start(ROTATION_SECONDS)
            elif self.current_page[room] == 1:
                self.rotation_timer[room].stop()

        return html

    def _get_schedule_table_html(self):
        html = f'''
            <tr>
                <td colspan="3" align="center">
                    <img src="{self.schedule_file}" width="1180" height="490">
                </td>
            </tr>
        '''

        return html

    def _get_waiting_list_html(self, room):
        waiting_rows = self._get_waiting_rows(room)
        html = self._set_waiting_list_html(room, waiting_rows)

        return html

    def _set_waiting_list_html(self, room, waiting_rows):
        called_regist_no = self._get_called_regist_no(room)

        waiting_list = []
        for row_no, row in enumerate(waiting_rows):
            if row_no > MAX_WAITING_ROWS:
                break

            name = self._mask_name(string_utils.xstr(row["Name"]))
            regist_no = f'{number_utils.get_integer(row["RegistNo"]):0>3}'

            name_width = '60px'
            if len(name) == 4:
                name_width = '50px'
            elif len(name) == 5:
                name_width = '40px'

            if regist_no == called_regist_no:
                color = LATE_COLOR
            else:
                color = TEXT_COLOR

            waiting_list.append({
                'name': name,
                'regist_no': regist_no,
                'name_width': name_width,
                'color': color,
            })

        if len(waiting_list) < MAX_WAITING_ROWS:
            for row_no in range(MAX_WAITING_ROWS - len(waiting_list)):
                waiting_list.append({
                    'name': '',
                    'regist_no': '',
                    'name_width': '60px',
                    'color': TEXT_COLOR,
                })

        block_list1 = [0, 1, 2, 3, 4, 5]
        block_list2 = [6, 7, 8, 9, 10, 11]

        waiting_html = ''
        for i in range(len(block_list1)):
            block1 = block_list1[i]
            block2 = block_list2[i]

            waiting_html += f'''
                <tr bgcolor="{BG_COLOR}">
                    <td style="color: {waiting_list[block1]["color"]}; font-size: {waiting_list[block1]["name_width"]};
                     font-weight: bold" align="left">
                        {waiting_list[block1]["regist_no"]}{waiting_list[block1]["name"]}
                    </td>
                    <td style="color: {waiting_list[block2]["color"]}; font-size: {waiting_list[block2]["name_width"]};
                     font-weight: bold" align="left">
                        {waiting_list[block2]["regist_no"]}{waiting_list[block2]["name"]}
                    </td>
                </tr>
            '''

        html = f'''
            <table width="100%" cellspacing="0" cellpadding="0"
             style="font-weight:bold; font-family:Microsoft JhengHei">
                <tbody>
                    {waiting_html}
                </tbody>
            </table>
        '''

        return html

    def _get_late_waiting_list_html(self, room):
        waiting_list = []
        waiting_rows = self._get_waiting_rows(room, late=True)
        for row_no, row in enumerate(waiting_rows):
            if row_no > MAX_WAITING_ROWS / 2:
                break

            name = self._mask_name(string_utils.xstr(row["Name"]))
            regist_no = f'{number_utils.get_integer(row["RegistNo"]):0>3}'

            name_width = '60px'
            if len(name) == 4:
                name_width = '50px'
            elif len(name) == 5:
                name_width = '40px'

            color = LATE_COLOR
            waiting_list.append({
                'name': name,
                'regist_no': regist_no,
                'name_width': name_width,
                'color': color,
            })

        if len(waiting_list) < MAX_WAITING_ROWS / 2:
            for row_no in range(MAX_WAITING_ROWS - len(waiting_list)):
                waiting_list.append({
                    'name': '',
                    'regist_no': '',
                    'name_width': '60px',
                    'color': TEXT_COLOR,
                })

        block_list1 = [0, 1, 2, 3, 4, 5]

        waiting_html = ''
        for i in range(len(block_list1)):
            block1 = block_list1[i]

            waiting_html += f'''
                <tr bgcolor="{BG_COLOR}">
                    <td style="color: {waiting_list[block1]["color"]}; font-size: {waiting_list[block1]["name_width"]};
                     font-weight: bold" align="left">
                        {waiting_list[block1]["regist_no"]}{waiting_list[block1]["name"]}
                    </td>
                </tr>
            '''

        html = f'''
            <table width="100%" cellspacing="0" cellpadding="0"
             style="font-weight:bold; font-family:Microsoft JhengHei">
                <tbody>
                    {waiting_html}
                </tbody>
            </table>
        '''

        return html

    def _get_called_regist_no(self, room):
        today = datetime.datetime.today().strftime('%Y-%m-%d')

        sql = f'''
            SELECT SeqNumber FROM seq_number
            WHERE
                DATE(CaseDate) = "{today}" AND
                Room =  {room}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            called_regist_no = 0
        else:
            called_regist_no = number_utils.get_integer(rows[0]['SeqNumber'])

        return called_regist_no

    def _get_doctor(self, row, weekday, room):
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        period = registration_utils.get_current_period(self.system_settings)

        sql = f'''
            SELECT Name FROM temporary_schedule
            WHERE
                CaseDate = "{today}" AND
                Period = "{period}" AND
                ScheduleType = "代班" AND
                Room = {room} AND
                Position = "醫師"
        '''
        rows = self.database.select_record(sql)
        if len(rows) >= 1:
            row = rows[0]
            doctor = string_utils.xstr(row['Name'])
            return doctor

        sql = f'''
            SELECT Name FROM temporary_schedule
            WHERE
                CaseDate = "{today}" AND
                Period = "{period}" AND
                ScheduleType = "請假" AND
                Room = {room} AND
                Position = "醫師"
        '''
        rows = self.database.select_record(sql)
        if len(rows) >= 1:
            return None

        doctor = string_utils.xstr(row[weekday])

        return doctor

    def _get_agent_doctor(self, doctor):
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        period = registration_utils.get_current_period(self.system_settings)
        sql = f'''
            SELECT * FROM temporary_schedule
            WHERE
                CaseDate = "{today}" AND
                Period = "{period}" AND
                ScheduleType IN ("請假", "代班") AND
                Position = "醫師" AND
                Name = "{doctor}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return doctor

        row = rows[0]
        doctor = string_utils.xstr(row['Agent'])
        return doctor

    def _get_room_html(self, row, room_count):
        weekday = date_utils.WEEK_DAY_LIST[datetime.datetime.now().weekday()]
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        period = registration_utils.get_current_period(self.system_settings)

        room = number_utils.get_integer(row['Room'])
        # doctor = self._get_doctor(row, weekday, room)
        doctor = string_utils.xstr(row[weekday])
        doctor, room = registration_utils.get_agent_doctor(self.database, today, period, doctor, room)

        if doctor is None:
            return ''

        waiting_list_html = self._get_waiting_list_html(room)
        late_waiting_list_html = self._get_late_waiting_list_html(room)

        schedule_table_html = ''
        if room_count == 1:
            schedule_table_html = self._get_schedule_table_html()

        called_regist_no = self._get_called_regist_no(room)
        html = f'''
            <tr>
                <td>
                    <table width="100%" cellspacing="1" cellpadding="0"
                     style="font-weight:bold; font-family:Microsoft JhengHei; border-width: 1px;border: {BORDER_COLOR}">
                        <tr bgcolor="{BORDER_COLOR}" style="color: {HEADER_COLOR}">
                            <th width="23%" style="font-size: 28px; font-weight: bold;" text-align: center>
                                診療室
                            </th>
                            <th style="font-size: 28px; font-weight: bold;" text-align: center>
                                候診號碼
                            </th>
                            <th width="25%" style="font-size: 28px; font-weight: bold;" text-align: center>
                                過號號碼
                            </th>
                        </tr>
                        <tbody>
                            <tr bgcolor="{BG_COLOR}" style="color: {TEXT_COLOR}">
                                <td style="vertical-align: middle; font-size: 48px; font-weight: bold" align="center">
                                    <a style="font-size: 72px; font-weight: bold" align="center">
                                        {room}診
                                    </a><br>
                                    <a style="font-size: 128px; font-weight: bold" align="center">
                                        {called_regist_no:0>3}
                                    </a><br>
                                    {doctor}醫師<br>
                                    目前看診號
                                </td>
                                <td style="font-size: 60px; font-weight: bold" align="center">
                                    {waiting_list_html}
                                </td>
                                <td style="font-size: 60px; red; font-weight: bold" align="center">
                                    {late_waiting_list_html}
                                </td>
                            </tr>
                            {schedule_table_html}
                        </tbody>
                    </table>
                </td>
            </tr>
        '''

        return html

    def _show_waiting_list(self):
        waiting_html = self._get_waiting_html()

        html = f'''
            <table align=center cellpadding="0" cellspacing="0" width="100%"
                style=" background-color: {BG_COLOR};
                        border: 1px solid {BORDER_COLOR};
                        border-color: {BORDER_COLOR};
                        padding: 10px;">
                <tbody>
                    {waiting_html}
                </tbody>
            </table>
        '''
        self.ui.textBrowser_waiting_list.setHtml(html)

    def _set_image_list_filename(self):
        self.image_list = []
        sql = '''
            SELECT * FROM system_settings
            WHERE
                Field LIKE "輪播圖片檔-%"
            ORDER BY Field
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        for row in rows:
            self.image_list.append(string_utils.xstr(row['Value']))

    def _set_image_list(self):
        self._set_image_list_filename()
        if len(self.image_list) <= 0:
            return

        filename = self.image_list[0]
        self._display_image(filename)

        self.image_list_index = 1
        self._set_image_list_timer()

    def _set_image_list_timer(self):
        self.image_list_timer = QtCore.QTimer(self)
        self.image_list_timer.start(10000)
        self.image_list_timer.timeout.connect(self._image_list_timeout)

    def _image_list_timeout(self):
        self.image_list_index += 1
        if self.image_list_index >= len(self.image_list):
            self.image_list_index = 0

        filename = self.image_list[self.image_list_index]
        self._display_image(filename)

    def _display_image(self, filename):
        icon_size = 320
        self.ui.label_image_list.setPixmap(QtGui.QPixmap(filename))
        self.ui.label_image_list.setMaximumWidth(icon_size)
        self.ui.label_image_list.setMaximumHeight(icon_size)
        self.ui.label_image_list.setScaledContents(True)

    def _set_qrcode(self):
        icon_size = 320

        fixed_image = self.system_settings.field('固定圖檔名')
        if fixed_image in ['', None]:
            return

        self.ui.label_qrcode.setPixmap(QtGui.QPixmap(fixed_image))
        self.ui.label_qrcode.setMaximumWidth(icon_size)
        self.ui.label_qrcode.setMaximumHeight(icon_size)
        self.ui.label_qrcode.setScaledContents(True)


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin3(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


# 程式開始
if __name__ == '__main__':
    main()
