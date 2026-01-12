# -*- coding: UTF-8 -*-

import json
import datetime
import yt_dlp
import cv2
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFrame, QDesktopWidget
from pygame import mixer
from libs import class_utils, ui_utils, system_utils, string_utils, number_utils, registration_utils

MAX_ROOM = 10
MAX_WAITING_ROWS = 7
ROTATION_SECONDS = 5000

class PyBulletin5(QtWidgets.QWidget):
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.args = args
        self._initialize_db()
        self._initialize_system_settings()
        self._initialize_ui()
        self._initialize_udp_server()
        self._initialize_timers()

        self.showMaximized()

    def _initialize_db(self):
        config_file = self.args[0][1] if len(self.args) > 1 else None
        self.config_file = config_file or class_utils.get_db().CONFIG_FILE
        config_dict = self._parse_config_file(self.config_file)
        self.database = class_utils.get_db(**config_dict)

    def _initialize_system_settings(self):
        self.system_settings = class_utils.get_system_settings(self.database, self.config_file)
        self.waiting_number = [0] * 100
        self.volume = number_utils.get_integer(self.system_settings.field('媒體播放音量'))
        self.url = self.system_settings.field('媒體播放位址')
        self.periods = [
            self.system_settings.field('早班時間'),
            self.system_settings.field('午班時間'),
            self.system_settings.field('晚班時間')
        ]
        self.current_room = 1

    def _initialize_ui(self):
        self.frame = QFrame(self)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.frame)

        self.ui = ui_utils.load_ui_file(ui_utils.UI_PY_BULLETIN1, self.frame)
        self.ui.setWindowFlags(Qt.FramelessWindowHint)
        self.setCursor(Qt.BlankCursor)

    def _initialize_udp_server(self):
        self.socket_server = class_utils.get_socket_server(self, 8880)
        self.voice_server = class_utils.get_voice_server(self, 9990)
        self.voice_server.update_signal.connect(self._broadcast_speech)
        self.socket_server.update_signal.connect(self._show_waiting_list)
        self._start_udp_server()

    def _initialize_timers(self):
        self.rotation_timer = QtCore.QTimer(self)
        self.rotation_timer.timeout.connect(self._rotation_wait_list)
        self.sub_rotation_timer = QtCore.QTimer(self)
        self.sub_rotation_timer.timeout.connect(self._sub_rotation_wait_list)
        self.audio_timer = QtCore.QTimer(self)

    def show_bulletin(self):
        self._show_title()
        self._play_media()
        self._play_marquee()
        self._show_waiting_list()
        self._set_clock()

    def _show_title(self):
        self.ui.label_title.setText(f"{self.system_settings.field('院所名稱')} 候診資訊系統")

    def _close_socket(self):
        self.socket_server.stop_thread()
        self.voice_server.stop_thread()

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
        if not self.url:
            return
        self.mediaplayer.audio_set_volume(5)
        self.audio_timer.timeout.connect(self._normal_audio)
        self.audio_timer.start(6000)

    def _normal_audio(self):
        self.mediaplayer.audio_set_volume(self.volume)
        self.audio_timer.stop()

    def _broadcast_speech(self, json_data):
        if json_data == 'refresh_wait':
            self._show_waiting_list()
            return

        voice_dict = json.loads(json_data)
        regist_no = number_utils.get_integer(voice_dict['regist_no'])
        room = number_utils.get_integer(voice_dict['room'])
        sentence = voice_dict['sentence']

        self.waiting_number[room] = regist_no
        rows = self._get_wait_rows(room)
        if rows:
            self.current_room = room
            self._show_waiting_list_html(rows[0])

        QtWidgets.qApp.processEvents()
        self._set_lower_audio()
        system_utils.speak(sentence)

    def _play_media(self):
        if not self.url:
            return
        
        video_url = self._get_video_url(self.url)
        self._play_video(video_url)

    def _get_video_url(self, url):
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)
            return video_info['url']

    def _play_video(self, video_url):
        cap = cv2.VideoCapture(video_url)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow('YouTube Video', frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

    def _set_marquee_list(self):
        self.marquee_list = []
        sql = '''SELECT * FROM system_settings WHERE Field LIKE "跑馬燈訊息-%" ORDER BY Field'''
        rows = self.database.select_record(sql)
        if not rows:
            self.marquee_list.append(f"{self.system_settings.field('院所名稱')} 關心您的健康")
            return

        for row in rows:
            self.marquee_list.append(string_utils.xstr(row['Value']))

    def _play_marquee(self):
        self._set_marquee_list()
        self.marquee_index = 0
        self.marquee_start = QDesktopWidget().screenGeometry(-1).width() + 100
        self._set_marquee_text()
        self.current_x = self.marquee_start
        self._set_timer()

    def _set_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.start(9)
        self.timer.timeout.connect(self._timeout)

    def _timeout(self):
        if datetime.datetime.now().strftime('%H:%M') in self.periods:
            self._show_waiting_list()

        self.current_x -= 1
        if self.current_x <= -self.marquee_text_width:
            self.current_x = self.marquee_start
            self.marquee_index = (self.marquee_index + 1) % len(self.marquee_list)
            self._set_marquee_text()

        self.ui.label_marquee.move(self.current_x, 0)

    def _set_marquee_text(self):
        self.ui.label_marquee.setText(self.marquee_list[self.marquee_index])
        self.ui.label_marquee.adjustSize()
        self.marquee_text_width = self.ui.label_marquee.width() + 100

    def _get_waiting_rows(self, room, current_page=None):
        current_period = registration_utils.get_current_period(self.system_settings)
        limit_script = f'LIMIT {current_page * MAX_WAITING_ROWS}, {MAX_WAITING_ROWS}' if current_page else ''
        sql = f'''
            SELECT PatientKey, RegistNo, Name, Remark FROM wait
            WHERE Room = {room} AND Period = "{current_period}" AND Doctor != "全部醫師" AND DoctorDone = "False"
            ORDER BY RegistNo {limit_script}
        '''
        return self.database.select_record(sql)

    def _mask_name(self, name):
        return f"{name[0]}〇{name[2:6]}"

    def _get_waiting_html(self, row, current_page=None):
        html = ''
        room = number_utils.get_integer(row['Room'])
        doctor = string_utils.xstr(row['Doctor'])
        called_regist_no = self.waiting_number[room]

        html += f'''
            <tr>
                <td>
                    <table width="98%" style="font-weight:bold; font-family:Microsoft JhengHei; text-align:left;">
                        <tr>
                            <td width="50%">號碼: {called_regist_no}</td>
                            <td width="50%">醫師: {doctor}</td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td>
                    <table width="98%" style="font-family:Microsoft JhengHei; text-align:left;">
                        <tr>
                            <td>病人: {self._mask_name(row['Name'])} {row['Remark']}</td>
                        </tr>
                    </table>
                </td>
            </tr>
        '''
        return html

    def _show_waiting_list(self):
        current_period = registration_utils.get_current_period(self.system_settings)
        html = f'''
            <html>
            <head>
                <style>
                body {{ font-family: Microsoft JhengHei; }}
                </style>
            </head>
            <body>
                <table width="100%" border="0">
                    <tr><td colspan="2" style="font-weight:bold; text-align:center;">{self.system_settings.field('院所名稱')}</td></tr>
                    <tr><td colspan="2" style="font-weight:bold; text-align:center;">{current_period} 候診名單</td></tr>
        '''

        for room in range(1, MAX_ROOM + 1):
            rows = self._get_waiting_rows(room)
            if rows:
                for row in rows:
                    html += self._get_waiting_html(row)
        
        html += '</table></body></html>'
        self.ui.label_waiting_list.setText(html)
        self.ui.label_waiting_list.adjustSize()
        self.ui.label_waiting_list.setVisible(True)

    def _rotation_wait_list(self):
        # Implementation for rotation wait list
        pass

    def _sub_rotation_wait_list(self):
        # Implementation for sub-rotation wait list
        pass

    def closeEvent(self, event):
        self._close_socket()
        event.accept()

# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    py_bulletin = PyBulletin5(None, sys.argv)
    py_bulletin.show_bulletin()

    sys.exit(app.exec_())


    # 程式開始
    if __name__ == '__main__':
        main()
