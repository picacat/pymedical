# -*- coding: UTF-8 -*-

import asyncio
import hashlib
import os
import platform
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import pygame

from libs import system_utils

if sys.platform == "win32":
    os.environ["PYTHON_VLC_MODULE_PATH"] = "./vlc"

from io import BytesIO

try:
    import edge_tts

    USE_EDGE_TTS = True
except ModuleNotFoundError:
    USE_EDGE_TTS = False

try:
    from gtts import gTTS
    from pygame import mixer
except ModuleNotFoundError:
    system_utils.pip3_install("gtts")
    system_utils.pip3_install("pygame")
    from gtts import gTTS
    from pygame import mixer

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname("__file__")))


# ---------------------------------------------------------------------------
# 語音音量 (0~100)
#
# 這裡控制的只有「叫號語音」自己的大小聲 (pygame mixer 的音樂通道),
# 不會動到 VLC/YouTube, 也不會動到作業系統的主音量。
# 其他媒體的音量請直接用電腦的系統音量調整。
# ---------------------------------------------------------------------------
DEFAULT_VOICE_VOLUME = 100
_voice_volume = DEFAULT_VOICE_VOLUME
_voice_volume_lock = threading.Lock()


def _clamp_volume(volume):
    """把 0~100 的整數音量轉成 pygame 用的 0.0~1.0"""
    try:
        volume = int(volume)
    except (TypeError, ValueError):
        volume = DEFAULT_VOICE_VOLUME

    if volume < 0:
        volume = 0
    elif volume > 100:
        volume = 100

    return volume / 100.0


def set_voice_volume(volume):
    """設定預設語音音量 (0~100), 之後沒指定音量的播報都用這個值"""
    global _voice_volume

    try:
        volume = int(volume)
    except (TypeError, ValueError):
        return

    with _voice_volume_lock:
        _voice_volume = max(0, min(volume, 100))


def get_voice_volume():
    with _voice_volume_lock:
        return _voice_volume


def _apply_volume(volume=None):
    """套用音量到 mixer.music, 要在 load() 之後、play() 之前呼叫"""
    if volume is None:
        volume = get_voice_volume()

    try:
        mixer.music.set_volume(_clamp_volume(volume))
    except Exception:
        pass


def install_pycaw():
    try:
        # 嘗試導入 pycaw，如果未安裝則安裝
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    except ImportError:
        print("未找到 pycaw 套件，正在安裝...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pycaw"])
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume  # 安裝後重新導入

    return AudioUtilities, ISimpleAudioVolume


# Windows: 獲取與設定音量
def get_volume_windows():
    AudioUtilities, ISimpleAudioVolume = install_pycaw()
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        return volume.GetMasterVolume()


# Linux: 使用 amixer 或 pactl 獲取與設定音量
def get_volume_linux():
    if shutil.which("pactl"):
        result = subprocess.run(
            "pactl get-sink-volume @DEFAULT_SINK@",
            shell=True,
            capture_output=True,
            text=True,
        )
        return int(result.stdout.split("/")[1].strip().replace("%", "")) / 100
    elif shutil.which("amixer"):
        result = subprocess.run(
            "amixer get Master", shell=True, capture_output=True, text=True
        )
        return int(result.stdout.split("[")[1].split("%")[0]) / 100
    return None


# 保存和設定音量的主函數
def save_volume():
    system = platform.system()

    if system == "Windows":
        return get_volume_windows()
    elif system == "Linux":
        return get_volume_linux()
    elif system == "Darwin":
        return get_volume_mac()
    else:
        print("不支援的作業系統")
        return None


def restore_volume(volume_level):
    system = platform.system()

    if system == "Windows":
        set_volume_windows(volume_level)
    elif system == "Linux":
        set_volume_linux(volume_level)
    elif system == "Darwin":
        set_volume_mac(volume_level)
    else:
        print("不支援的作業系統")


# macOS: 使用 osascript 獲取與設定音量
def get_volume_mac():
    result = subprocess.run(
        "osascript -e 'output volume of (get volume settings)'",
        shell=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip()) / 100


def set_volume_windows(volume_level=0.2):
    AudioUtilities, ISimpleAudioVolume = install_pycaw()
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMasterVolume(volume_level, None)


def set_volume_linux(volume_level):
    # 根據可用的工具選擇 amixer 或 pactl
    if shutil.which("pactl"):
        os.system(f"pactl set-sink-volume @DEFAULT_SINK@ {int(volume_level * 100)}%")
    elif shutil.which("amixer"):
        os.system(f"amixer -D pulse sset Master {int(volume_level * 100)}%")
    else:
        print("無法找到適合的音量控制工具")


def set_volume_mac(volume_level):
    # macOS 使用 AppleScript 控制音量
    os.system(f"osascript -e 'set volume output volume {int(volume_level * 100)}'")


def set_volume(volume_level=0.2):
    system = platform.system()

    if system == "Windows":
        set_volume_windows(volume_level)
    elif system == "Linux":
        set_volume_linux(volume_level)
    elif system == "Darwin":
        set_volume_mac(volume_level)
    else:
        print("不支援的作業系統")


EDGE_TTS_VOICE = "zh-TW-HsiaoChenNeural"  # 曉臻(女) / zh-TW-HsiaoYuNeural 曉雨(女) / zh-TW-YunJheNeural 雲哲(男)
EDGE_TTS_RATE = "-30%"  # 語速: '+0%' 原速, '-20%' 放慢
TTS_CACHE_DIR = os.path.join(BASE_DIR, "tts_cache")


def tts_engine_name():
    """目前實際使用的語音引擎, 現場診斷用"""
    return "edge-tts" if USE_EDGE_TTS else "gTTS"


def _get_tts_cache_filename(sentence):
    """快取檔名把引擎、語音與語速一起算進 hash, 改設定不會播到舊快取

    引擎也要算進去: 同一句話 gTTS 與 edge-tts 的聲音不同, 客戶端日後補裝
    edge-tts 時才不會一直播到之前 gTTS 產生的舊快取。

    音量不必算進 hash: 音量是播放時才套用的, 同一個 mp3 可以用任何音量播。
    """
    key_source = f"{sentence}|{tts_engine_name()}|{EDGE_TTS_VOICE}|{EDGE_TTS_RATE}"
    key = hashlib.md5(key_source.encode("utf-8")).hexdigest()

    return os.path.join(TTS_CACHE_DIR, f"{key}.mp3")


def _edge_tts_save(sentence, filename):
    async def _run():
        communicate = edge_tts.Communicate(
            sentence,
            EDGE_TTS_VOICE,
            rate=EDGE_TTS_RATE,
        )
        await communicate.save(filename)

    asyncio.run(_run())


def _make_tts_mp3(sentence):
    """
    回傳 mp3 檔案路徑, 失敗回傳 None
    順序: 快取 -> edge-tts -> gTTS (備援)
    """
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    filename = _get_tts_cache_filename(sentence)

    if os.path.exists(filename):
        return filename

    # tmp 檔名加入 pid 與 thread id, 避免同一句同時產生時互撞
    tmp_filename = f"{filename}.{os.getpid()}.{threading.get_ident()}.tmp"

    ok = False
    if USE_EDGE_TTS:  # 沒裝就別試, 免得每次都印一行錯誤
        try:
            _edge_tts_save(sentence, tmp_filename)
            ok = True
        except Exception as e:
            print(f"edge-tts 產生語音失敗, 改用 gTTS: {e}")

    if not ok:
        try:
            tts = gTTS(text=sentence, lang="zh-tw", slow=False)
            tts.save(tmp_filename)
        except Exception as e2:
            print(f"gTTS 也失敗, 放棄本次播報: {e2}")
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)
            return None

    # Windows 上防毒可能短暫鎖住剛寫完的檔案, 改名失敗就重試
    for _ in range(5):
        try:
            os.replace(tmp_filename, filename)
            return filename
        except PermissionError:
            time.sleep(0.2)

    # 重試都失敗: 別人可能已經放好快取了, 有就直接用
    if os.path.exists(filename):
        try:
            os.remove(tmp_filename)
        except OSError:
            pass
        return filename

    # 快取進不去沒關係, 這次直接播 tmp 檔, 叫號不能停
    return tmp_filename


def _play_mp3(filename, volume=None):
    for attempt in range(2):
        try:
            if not mixer.get_init():
                mixer.init()

            mixer.music.load(filename)
            _apply_volume(volume)  # load 之後、play 之前套用語音音量
            mixer.music.play()
            while mixer.music.get_busy():
                time.sleep(0.05)

            # unload() 是 pygame 2.0 才有, 舊版沒有這個方法
            if hasattr(mixer.music, "unload"):
                mixer.music.unload()
            return
        except pygame.error as e:
            print(f"播放失敗 ({attempt + 1}/2): {e}")
            try:
                mixer.quit()  # 丟掉壞掉的裝置, 下一輪重新 init
            except Exception:
                pass
            time.sleep(0.3)


_tts_queue = queue.Queue()
_tts_worker_lock = threading.Lock()
_tts_worker_started = False
_tts_playing = False


def is_busy():
    """還有沒有語音正在播或排隊等著播

    候診看板用它來決定背景影片要壓低到什麼時候, 不必猜固定秒數。
    """
    if _tts_playing:
        return True

    if not _tts_queue.empty():
        return True

    try:
        if mixer.get_init() and mixer.music.get_busy():
            return True
    except Exception:
        pass

    return False


def _tts_worker():
    global _tts_playing

    while True:
        item = _tts_queue.get()
        try:
            # 舊呼叫端可能直接丟字串進來, 兩種格式都吃
            if isinstance(item, tuple):
                sentence, volume = item
            else:
                sentence, volume = item, None

            _tts_playing = True
            filename = _make_tts_mp3(sentence)
            if filename:
                _play_mp3(filename, volume)
        except Exception as e:
            print(f"語音播報失敗: {e}")
        finally:
            _tts_playing = False
            _tts_queue.task_done()


def speak_queued(sentence, volume=None):
    """把語句丟進佇列, 由單一背景執行緒依序播放, 不會卡 UI

    pygame 的 mixer.music 只有「一個」音樂通道: 正在播的時候再 load/play,
    前一句會立刻被切掉。所以叫號一定要走這條佇列, 不能每次叫號各開一個
    執行緒去播 (那就是一診播到一半被二診搶走的原因)。

    volume: 0~100, 不指定就用 set_voice_volume() 設定的預設值。
    """
    global _tts_worker_started

    with _tts_worker_lock:
        if not _tts_worker_started:
            thread = threading.Thread(target=_tts_worker, daemon=True)
            thread.start()
            _tts_worker_started = True
            print(f"語音播報啟動, 引擎: {tts_engine_name()}")

    _tts_queue.put((sentence, volume))


def speak_edge(sentence, threaded=True, volume=None):
    """保留舊名稱, 避免其他站台的程式呼叫不到"""
    speak_queued(sentence, volume)


def speak(sentence, threading=False, volume=None):
    """叫號播報唯一入口

    不論有沒有裝 edge-tts, 一律走同一條佇列, 保證前一句播完才播下一句。
    threading 參數保留只是為了相容舊呼叫端, 行為已經一律是非阻塞。
    volume 為 0~100, 只影響語音本身, 不影響 VLC/YouTube 與系統音量。
    """
    speak_queued(sentence, volume)


def speak_linux(sentence, volume=None):
    tts = gTTS(text=sentence, lang="zh-tw")
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)

    # ------------------ 替換 pydub ------------------
    # 1. 載入音訊
    pygame.mixer.init()
    pygame.mixer.music.load(fp, "mp3")
    _apply_volume(volume)

    # 2. 播放
    pygame.mixer.music.play()

    # 3. 等待播放完成 (這是必要的，否則程式會直接退出)
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    # ------------------------------------------------


def speak_linux_thread(sentence, volume=None):
    def _play_audio():
        tts = gTTS(text=sentence, lang="zh-tw")
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        # 載入音訊
        pygame.mixer.music.load(fp, "mp3")
        _apply_volume(volume)
        # 播放
        pygame.mixer.music.play()
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    # 確保 mixer.init() 已在主執行緒執行
    thread = threading.Thread(target=_play_audio, daemon=True)
    thread.start()


# 💡 備註：pygame.mixer.music.load() 不支援音量正規化 (voice.normalize())。
# gTTS 的音量通常是固定的，如果需要正規化，則需要額外的步驟。


def speak_win32(sentence, volume=None):
    # original_volume = save_volume()  # 保存原始音量

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        filename = f"{fp.name}.mp3"
        tts = gTTS(text=sentence, lang="zh-tw", slow=False)
        tts.save(filename)

        try:
            mixer.init()
            mixer.music.load(filename)
            _apply_volume(volume)
            mixer.music.play()
            while mixer.music.get_busy():
                time.sleep(0.1)
        except pygame.error:
            pass

    # restore_volume(original_volume)  # 恢復到原始音量


def speak_win32_thread(sentence, volume=None):
    def _play_audio():
        with tempfile.NamedTemporaryFile(delete=True) as fp:
            filename = f"{fp.name}.mp3"
            tts = gTTS(text=sentence, lang="zh-tw", slow=False)
            tts.save(filename)

            try:
                mixer.init()
                mixer.music.load(filename)
                _apply_volume(volume)
                mixer.music.play()
                while mixer.music.get_busy():
                    time.sleep(0.1)
            except mixer.error:
                pass

    thread = threading.Thread(target=_play_audio, daemon=True)
    thread.start()


def play_sound_file(filename, volume=None):
    """播放提示音 (例如 icq.mp3), 音量比照語音音量

    注意: 跟語音共用同一個 mixer.music 通道, 正在播語音時呼叫會把語音切掉。
    """
    if not os.path.exists(filename):
        return

    try:
        if not mixer.get_init():
            mixer.init()

        mixer.music.load(filename)
        _apply_volume(volume)
        mixer.music.play()
    except pygame.error:
        pass


TTS_CACHE_MAX_AGE_DAYS = 1
TTS_CACHE_MAX_FILES = 2000


def cleanup_tts_cache(
    max_age_days=TTS_CACHE_MAX_AGE_DAYS, max_files=TTS_CACHE_MAX_FILES
):
    """啟動時清一次: 刪過期 mp3、殘留 tmp, 並限制總檔數"""
    if not os.path.isdir(TTS_CACHE_DIR):
        return

    now = time.time()
    entries = []

    for name in os.listdir(TTS_CACHE_DIR):
        path = os.path.join(TTS_CACHE_DIR, name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue

        if name.endswith(".tmp"):  # 殘留 tmp 超過 1 小時就刪
            if now - mtime > 3600:
                try:
                    os.remove(path)
                except OSError:
                    pass
            continue

        if not name.endswith(".mp3"):
            continue

        if now - mtime > max_age_days * 86400:
            try:
                os.remove(path)
            except OSError:
                pass
        else:
            entries.append((mtime, path))

    if len(entries) > max_files:  # 超量就砍最舊的
        entries.sort()
        for _, path in entries[: len(entries) - max_files]:
            try:
                os.remove(path)
            except OSError:
                pass
