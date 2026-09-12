# -*- coding: UTF-8 -*-
"""候診看板的音量控制 (各版 pybulletin 共用)

兩個音量各自獨立, 互不影響:
    語音播放音量 -> 叫號語音 (voice_utils / pygame mixer)
    媒體播放音量 -> 電視畫面的影片/YouTube/串流 (VLC)

看板端用法 (以 self.mediaplayer 為例):
from libs import volume_utils

    # __init__ 裡, 播放器還沒建立也沒關係
    self.volume_controller = volume_utils.VolumeController(
        self,
        database=self.database,
        get_player=lambda: getattr(self, "mediaplayer", None),
    )

    # VLC play() 之後
    self.volume_controller.start_media_volume_timer()

    # 叫號
    self.volume_controller.speak(sentence)

    # CHANNEL_BULLETIN 進來的訊息
    if self.volume_controller.handle_bulletin_message(message):
        return

系統設定端用法:

    self.notification_client.broadcast(
        notification_utils.CHANNEL_BULLETIN,
        volume_utils.build_preview_message(media_volume, voice_volume),
    )
    # 按確定或取消之後
    self.notification_client.broadcast(
        notification_utils.CHANNEL_BULLETIN, volume_utils.REFRESH_VOLUME_MESSAGE
    )
"""

import json
import time

from PyQt5 import QtCore

from libs import string_utils, voice_utils

FIELD_VOICE_VOLUME = "語音播放音量"
FIELD_MEDIA_VOLUME = "媒體播放音量"

DEFAULT_VOLUME = 100  # 欄位沒填時的音量, 不要讓它變成 0 (靜音)

# 叫號時媒體音量壓低到原音量的比例, 以及最低值
DUCK_RATIO = 0.15
DUCK_MIN_VOLUME = 5
DUCK_POLL_MSEC = 500  # 每 0.5 秒檢查一次語音播完了沒
DUCK_MIN_SECONDS = 2  # 至少壓低 2 秒, 避免語音還沒開始就還原
DUCK_MAX_SECONDS = 60  # 保險上限, 語音卡住也不會一直壓著

# 串流剛開始播時 VLC 的 audio output 還沒建立, 音量設不進去, 要重試
RETRY_MSEC = 300
MAX_RETRY = 40  # 約 12 秒後放棄, 避免無限輪詢

# CHANNEL_BULLETIN 用的訊息
REFRESH_VOLUME_MESSAGE = "refresh_volume"  # 重新讀資料庫
PREVIEW_VOLUME_ACTION = "preview_volume"  # 滑桿試聽, 不存檔


def clamp(volume, default=DEFAULT_VOLUME):
    """把任意輸入夾到 0~100

    None、空白、看不懂的值一律回傳 default, 不要因為解析失敗就變成靜音。
    """
    if volume is None:
        return default

    text = string_utils.xstr(volume).strip()
    if text == "":
        return default

    try:
        value = int(float(text))
    except (TypeError, ValueError):
        return default

    return max(0, min(value, 100))


def build_preview_message(media_volume, voice_volume):
    """系統設定滑桿試聽用的訊息"""
    return json.dumps(
        {
            "action": PREVIEW_VOLUME_ACTION,
            "media_volume": clamp(media_volume),
            "voice_volume": clamp(voice_volume),
        }
    )


def get_volume_from_database(database, field_name, default=DEFAULT_VOLUME):
    """讀音量設定 (0~100)

    欄位不存在或沒填 -> 回傳 default;
    真的填 0 -> 就是 0 (靜音), 不要自己改成 100。
    """
    if database is None:
        return default

    sql = f'''
        SELECT Value FROM system_settings
        WHERE
            Field = "{field_name}"
    '''
    try:
        rows = database.select_record(sql)
    except Exception:
        return default

    if len(rows) <= 0:
        return default

    value = string_utils.xstr(rows[0]["Value"]).strip()
    if value == "":
        return default

    return clamp(value, default)


class VolumeController(QtCore.QObject):
    """管兩個音量: 語音交給 voice_utils, 媒體交給 VLC"""

    def __init__(self, parent=None, database=None, get_player=None):
        super().__init__(parent)

        self.database = database
        # 播放器是後來才建立的, 所以用 callable 取, 不要直接存參考
        self.get_player = get_player

        self.voice_volume = DEFAULT_VOLUME
        self.media_volume = DEFAULT_VOLUME

        self.duck_active = False
        self.duck_min_time = 0
        self.duck_deadline = 0

        self.duck_timer = QtCore.QTimer(self)
        self.duck_timer.timeout.connect(self._check_restore_audio)

        self.retry_timer = QtCore.QTimer(self)
        self.retry_timer.timeout.connect(self._retry_timeout)
        self.retry_count = 0

        self.reload(apply_media=False)  # 這時候播放器通常還沒建立

    def set_player_getter(self, get_player):
        self.get_player = get_player

    def _player(self):
        if self.get_player is None:
            return None

        try:
            return self.get_player()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 讀取設定
    # ------------------------------------------------------------------
    def reload(self, apply_media=True):
        """重新從資料庫讀兩個音量, 馬上生效, 不必重開程式"""
        self.voice_volume = get_volume_from_database(self.database, FIELD_VOICE_VOLUME)
        self.media_volume = get_volume_from_database(self.database, FIELD_MEDIA_VOLUME)

        voice_utils.set_voice_volume(self.voice_volume)
        if apply_media:
            self.apply_media_volume()

        print(f"音量設定: 語音={self.voice_volume}, 媒體={self.media_volume}")

    def preview(self, data):
        """套用系統設定滑桿的值, 只改記憶體, 不寫資料庫"""
        if "voice_volume" in data:
            self.voice_volume = clamp(data.get("voice_volume"))
            voice_utils.set_voice_volume(self.voice_volume)

        if "media_volume" in data:
            self.media_volume = clamp(data.get("media_volume"))
            self.apply_media_volume()

    def handle_bulletin_message(self, message):
        """處理 CHANNEL_BULLETIN 的音量訊息

        回傳 True 表示這則訊息是音量用的, 呼叫端不用再處理;
        回傳 False 表示跟音量無關 (refresh_wait、叫號 JSON 等), 照原本流程走。
        """
        message = string_utils.xstr(message).strip()

        if message == REFRESH_VOLUME_MESSAGE:
            self.reload()
            return True

        if not message.startswith("{"):
            return False

        try:
            data = json.loads(message)
        except Exception:
            return False

        if isinstance(data, dict) and data.get("action") == PREVIEW_VOLUME_ACTION:
            self.preview(data)
            return True

        return False

    # ------------------------------------------------------------------
    # 媒體音量
    # ------------------------------------------------------------------
    def target_media_volume(self):
        if not self.duck_active:
            return self.media_volume

        duck_volume = int(self.media_volume * DUCK_RATIO)
        if duck_volume < DUCK_MIN_VOLUME:
            # 設定值本來就很小 (甚至 0) 的時候, 別反而把音量調大
            duck_volume = min(DUCK_MIN_VOLUME, self.media_volume)

        return duck_volume

    def apply_media_volume(self):
        player = self._player()
        if player is None:  # 輪播圖片模式沒有播放器
            return

        try:
            player.audio_set_volume(self.target_media_volume())
        except Exception:
            pass

    def start_media_volume_timer(self):
        """剛開始播放時反覆設定音量, 直到設定成功 (主執行緒用)"""
        self.apply_media_volume()
        self.retry_count = 0
        self.retry_timer.start(RETRY_MSEC)

    def _retry_timeout(self):
        self.retry_count += 1
        self.apply_media_volume()

        player = self._player()
        try:
            done = (
                player is not None
                and player.audio_get_volume() == self.target_media_volume()
            )
        except Exception:
            done = False

        if done or self.retry_count >= MAX_RETRY:
            self.retry_timer.stop()

    def apply_media_volume_blocking(self):
        """背景執行緒版: set_media() 之後音量會掉回預設, 在那邊重設

        背景執行緒不能碰 QTimer, 所以這裡直接 sleep 等。
        """
        player = self._player()
        if player is None:
            return

        for _ in range(MAX_RETRY):
            target = self.target_media_volume()
            try:
                player.audio_set_volume(target)
                if player.audio_get_volume() == target:
                    return
            except Exception:
                return

            time.sleep(RETRY_MSEC / 1000)

    # ------------------------------------------------------------------
    # 叫號: 壓低媒體音量 -> 念完還原
    # ------------------------------------------------------------------
    def speak(self, sentence):
        """叫號: 壓低媒體音量, 用語音音量播報"""
        self.duck()
        voice_utils.speak(sentence, threading=True, volume=self.voice_volume)

    def duck(self):
        if self._player() is None:
            return

        self.duck_active = True
        self.apply_media_volume()

        now = time.time()
        self.duck_min_time = now + DUCK_MIN_SECONDS
        self.duck_deadline = now + DUCK_MAX_SECONDS
        self.duck_timer.start(DUCK_POLL_MSEC)

    def _check_restore_audio(self):
        now = time.time()

        if now < self.duck_deadline:
            if now < self.duck_min_time:
                return
            if voice_utils.is_busy():  # 還在念, 繼續壓著
                return

        self.duck_timer.stop()
        self.restore()

    def restore(self):
        self.duck_active = False
        self.apply_media_volume()

    # ------------------------------------------------------------------
    # 提示音 (icq.mp3 之類), 音量比照語音
    # ------------------------------------------------------------------
    def play_sound_file(self, filename):
        voice_utils.play_sound_file(filename, self.voice_volume)
