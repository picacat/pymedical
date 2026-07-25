
# 播放youtube
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import sys
import vlc

from libs import ui_utils
from libs import system_utils

try:
    import yt_dlp
except Exception:
    system_utils.pip3_install('yt_dlp')


# 教學影片
class DialogYouTube(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogYouTube, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_YOUTUBE, self)
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def closeEvent(self, event):
        self.mediaplayer.stop()

    def accepted_button_clicked(self):
        self.mediaplayer.stop()
        self.close()

    def play_youtube(self, url):
        self._init_vlc()
        self._embed_player()
        stream_url = self._get_best_stream_url(url)
        self._play_stream(stream_url)
        self.showNormal()

    def _init_vlc(self):
        self.vlc_instance = vlc.Instance()
        self.mediaplayer = self.vlc_instance.media_player_new()

    def _embed_player(self):
        win_id = int(self.ui.frame_youtube.winId())
        if sys.platform.startswith('win'):
            self.mediaplayer.set_hwnd(win_id)
        elif sys.platform.startswith('linux'):
            self.mediaplayer.set_xwindow(win_id)
        elif sys.platform == 'darwin':
            self.mediaplayer.set_nsobject(win_id)

    def _get_best_stream_url(self, url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get("formats", [])

                # 優先：有聲有影 + 非 webp
                for f in sorted(formats, key=lambda x: x.get("height", 0), reverse=True):
                    if f.get("vcodec") != "none" and f.get("acodec") != "none":
                        url = f.get("url", "")
                        if not url.endswith(".webp"):
                            return url

                # 次選：只有影像也接受（防止播放失敗）
                for f in sorted(formats, key=lambda x: x.get("height", 0), reverse=True):
                    if f.get("vcodec") != "none":
                        url = f.get("url", "")
                        if not url.endswith(".webp"):
                            return url

                # fallback
                url = info.get("url")
                if url and not url.endswith(".webp"):
                    return url

                print("⚠️ 找不到合適的影音格式，播放取消")
                return None

        except Exception as e:
            print(f"⚠️ 無法取得影片串流網址: {e}")
            return None

    def _play_stream(self, stream_url):
        if not stream_url:
            print("⚠️ 無效的影片串流網址，播放取消")
            return

        media = self.vlc_instance.media_new(stream_url)

        # ✅ 關閉 VLC 嘗試載入 metadata、封面、自動字幕等功能
        media.add_option(":no-video-title-show")
        media.add_option(":no-metadata-network-access")
        media.add_option(":no-sub-autodetect-file")
        media.add_option(":no-playlist-autostart")

        self.mediaplayer.set_media(media)
        self.mediaplayer.play()

