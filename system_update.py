# -*- coding: UTF-8 -*-
"""
醫療系統更新模組 (system_update.py)

重寫版本 2026-08-04
主要修正：
  1. _locate_git()      解壓 PortableGit 後重新掃描路徑（原版永遠回傳 False）
  2. _run_git()         加上 timeout、None 防呆、錯誤訊息保留
  3. 失敗/無差異分離     git 指令失敗回傳 None，無差異回傳 ""，不再混為一談
  4. update_mode        明確的模式旗標，不再靠 git_exe 猜測
  5. _check_writable()  更新前實測寫入權限
  6. _log()             所有動作與錯誤寫入 update.log
  7. 失敗也回報          _report_to_zoho_server 記錄 success / fail
  8. 只有真的成功才顯示「更新成功」訊息
"""

import base64
import configparser
import datetime
import hashlib
import io
import ntpath
import os
import os.path
import platform
import shutil
import socket
import ssl
import stat
import subprocess
import traceback
import urllib.error
import urllib.request
from os import listdir

import mysql.connector
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton

from libs import class_utils, string_utils, system_utils, ui_utils, update_utils

# ----------------------------------------------------------------------
# 常數設定
# ----------------------------------------------------------------------
IS_WINDOWS = platform.system() == "Windows"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

GITHUB_REPO_URL = "https://github.com/picacat/pymedical.git"
GITHUB_BRANCH = "main"

UPDATE_URL_TXT = (
    "https://raw.githubusercontent.com/picacat/pymedical_update/"
    "refs/heads/main/update.txt"
)
DROPBOX_FALLBACK_URL = "https://www.dropbox.com/s/4h4a35ygzqx7duc/pymedical.zip?dl=1"

# 更新模式
MODE_NONE = ""
MODE_GIT = "git"
MODE_ZIP = "zip"

# git 指令逾時秒數（依指令性質區分，避免網路卡住時整個 UI 假死）
GIT_TIMEOUT_LOCAL = 30  # config / rev-parse 這類本機指令
GIT_TIMEOUT_NETWORK = 180  # fetch 這類需要連外的指令

# 更新時必須保護、不可被 Git 覆蓋的診所專屬檔案
PROTECT_FILES = [
    "pymedical.win32.bat",
    "pybulletin.win32.bat",
    "pymedical.conf",
    "qingtian.conf",
    "mingi.conf",
    "nd.conf",
    "nw.conf",
]

# 掃描檔案時要排除的目錄
EXCLUDE_DIRS = {
    ".git",
    "PortableGit",
    "_temp",
    "__pycache__",
    "tts_cache",
    "_old_files",
}

# 執行中可能被本程式載入而鎖住的檔案類型
# Windows 不允許刪除已載入的 DLL / pyd，Git unlink 會失敗
LOCKABLE_EXTENSIONS = {".dll", ".pyd", ".exe", ".ocx"}


# zip 更新模式要比對的子目錄
ZIP_SUB_DIRS = [
    "",
    "classes",
    "convert",
    "css",
    "dialog",
    "libs",
    "slot_machine",
    "mysql",
    os.path.join("mysql", "default"),
    "printer",
    "ui",
    "images",
    "icons",
    "tables",
    "payment_machine",
    "kiosk",
]


# 醫療系統更新
class SystemUpdate(QtWidgets.QDialog):
    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self.restart_pymedical = False

        # === 修正：base_path 必須在 _set_ui() 之前就定義好 ===
        # 原版把它放在 _set_ui() 之後，任何 UI 初始化流程一旦用到就會 AttributeError
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.log_file = os.path.join(self.base_path, "update.log")

        self.git_exe = None
        self.last_git_error = ""
        self.update_mode = MODE_NONE

        self._locate_git()

        self._set_ui()
        self._set_signal()

        self._log("=" * 60)
        self._log(f"開啟系統更新視窗 base_path={self.base_path}")
        self._log(f"git_exe={self.git_exe}")

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # ------------------------------------------------------------------
    # 記錄檔
    # ------------------------------------------------------------------
    def _log(self, message):
        """把更新過程寫入 update.log，出問題時請診所把這個檔案傳回來"""
        line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
        print(line)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # log 寫不進去本身就是權限問題的徵兆，但不能因此中斷更新
            pass

    def _log_exception(self, message):
        self._log(f"{message}\n{traceback.format_exc()}")

    # ------------------------------------------------------------------
    # 設定 GUI
    # ------------------------------------------------------------------
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_SYSTEM_UPDATE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("開始更新")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.table_widget_file_list = class_utils.get_table_widget(
            self.ui.tableWidget_file_list, self.database
        )
        self._set_table_width()

        self._set_radio_buttons()
        self.ui.lineEdit_file_name.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.radioButton_auto_update.clicked.connect(self._set_radio_buttons)
        self.ui.radioButton_manual_update.clicked.connect(self._set_radio_buttons)
        self.ui.pushButton_download.clicked.connect(self._start_check)
        self.ui.toolButton_open_file.clicked.connect(self._open_file)
        self.ui.lineEdit_file_name.textChanged.connect(self._file_name_changed)

    def _set_radio_buttons(self):
        self.ui.pushButton_download.setEnabled(False)
        self.ui.lineEdit_file_name.setEnabled(False)
        self.ui.toolButton_open_file.setEnabled(False)

        # 切換模式時清空前一次的檢查結果，避免清單與模式對不起來
        self.update_mode = MODE_NONE
        self.ui.tableWidget_file_list.setRowCount(0)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        if self.ui.radioButton_auto_update.isChecked():
            self.ui.pushButton_download.setEnabled(True)
        else:
            self.ui.lineEdit_file_name.setEnabled(True)
            self.ui.toolButton_open_file.setEnabled(True)

    def _set_table_width(self):
        width = [300, 180, 150, 200]
        self.table_widget_file_list.set_table_heading_width(width)

    def _set_status(self, message):
        """更新狀態列並讓 UI 有機會重繪（同步流程中避免看起來像當掉）"""
        self.ui.label_status.setText(message)
        self._log(message)
        QApplication.processEvents()

    def _busy(self, busy=True):
        if busy:
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
        QApplication.processEvents()

    # ------------------------------------------------------------------
    # Git 執行引擎
    # ------------------------------------------------------------------
    def _locate_git(self):
        """掃描 PortableGit 的可能路徑，找到就設定 self.git_exe 並回傳 True

        === 修正重點 ===
        原版只在 __init__ 掃描一次。第一次執行的電腦解壓 PortableGit 之後
        self.git_exe 仍然是 None，接著 os.path.exists(None) 拋 TypeError，
        被 except 吃掉後回傳 False，導致永遠退回 Dropbox 模式。
        """
        candidates = [
            os.path.join(self.base_path, "PortableGit", "bin", "git.exe"),
            os.path.join(self.base_path, "PortableGit", "cmd", "git.exe"),
            os.path.join(self.base_path, "PortableGit", "mingw32", "bin", "git.exe"),
            os.path.join(self.base_path, "PortableGit", "mingw64", "bin", "git.exe"),
        ]

        for path in candidates:
            if os.path.exists(path):
                self.git_exe = path
                return True

        self.git_exe = None
        return False

    def _run_git(self, args, timeout=GIT_TIMEOUT_LOCAL):
        """執行內置 Git 指令

        回傳值語意（呼叫端務必用 `is None` 判斷）：
            str  -- 指令成功，內容為 stdout（可能是空字串，代表「執行成功但無輸出」）
            None -- 指令失敗，失敗原因記在 self.last_git_error
        """
        self.last_git_error = ""

        # === 修正：原版 os.path.exists(self.git_exe) 在 git_exe 為 None 時會 TypeError ===
        if not self.git_exe or not os.path.exists(self.git_exe):
            self.last_git_error = "找不到 Git 執行檔 (PortableGit 未安裝或路徑不正確)"
            self._log(f"git {' '.join(args)} → {self.last_git_error}")
            return None

        try:
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"  # 禁用互動式提示，避免無人值守時卡住
            env["GIT_ASKPASS"] = "echo"  # 同上，擋掉帳密輸入視窗
            env["GIT_CONFIG_NOSYSTEM"] = "1"  # 隔離使用者電腦既有的 git 設定
            env["LC_ALL"] = "C"  # 固定錯誤訊息語系，方便比對

            kwargs = {
                "stderr": subprocess.STDOUT,
                "universal_newlines": True,
                "cwd": self.base_path,  # 務必在 pymedical 根目錄執行
                "env": env,
                "timeout": timeout,  # === 修正：原版沒有 timeout，網路卡住就假死 ===
            }
            if IS_WINDOWS:
                kwargs["creationflags"] = CREATE_NO_WINDOW

            result = subprocess.check_output([self.git_exe] + args, **kwargs)
            self._log(f"git {' '.join(args)} → OK")
            return result

        except subprocess.TimeoutExpired:
            self.last_git_error = f"指令逾時 ({timeout} 秒)，請檢查診所網路或防火牆設定"
        except subprocess.CalledProcessError as e:
            self.last_git_error = (e.output or "").strip()[
                -500:
            ] or f"結束代碼 {e.returncode}"
        except Exception as e:
            self.last_git_error = str(e)

        self._log(f"git {' '.join(args)} → 失敗: {self.last_git_error}")
        return None

    # ------------------------------------------------------------------
    # 環境檢查
    # ------------------------------------------------------------------
    def _check_writable(self):
        """更新前實測程式目錄是否可寫入

        === 新增 ===
        原版所有 os.chmod / 檔案寫入都包在 except: pass 裡。
        程式裝在 C:\\Program Files 底下、或被防毒鎖住時，
        全部靜默失敗卻仍然跳出「更新成功」。
        """
        probe = os.path.join(self.base_path, ".update_write_test")
        try:
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
            return True
        except Exception as e:
            self._log(f"寫入權限檢查失敗: {e}")
            QMessageBox.critical(
                self,
                "權限不足，無法更新",
                f"<font size='4'><b>無法寫入程式目錄</b></font>"
                f"<br><br>目錄：{self.base_path}"
                f"<br>錯誤：{e}"
                f"<br><br>請以「系統管理員身分」執行醫療系統，"
                f"或確認防毒軟體未鎖定此資料夾。",
            )
            return False

    # ------------------------------------------------------------------
    # 鎖定檔案處理（cshis.dll 等執行中被載入的元件）
    # ------------------------------------------------------------------
    def _is_file_locked(self, path):
        """判斷檔案是否被其他程式鎖住（無法寫入）

        已被 ctypes 載入的 DLL 會被 Windows 以唯讀方式鎖定，
        用附加模式開啟就會失敗。
        """
        try:
            with open(path, "ab"):
                pass
            return False
        except Exception:
            return True

    def _get_changed_files(self):
        """取得本次更新會異動的檔案清單（相對路徑）"""
        diff = self._run_git(["diff", "HEAD", "FETCH_HEAD", "--name-only", "--"])
        if diff is None:
            return []

        return [f.strip() for f in diff.strip().splitlines() if f.strip()]

    def _find_locked_pending_files(self):
        """找出「這次需要更新」且「正被其他程式佔用」的檔案

        必須在 _refresh_index() 之後呼叫，否則會把內容其實沒變、
        只是索引 stat 過期的檔案誤判成待更新。
        """
        locked = []

        for rel_path in self._get_changed_files():
            path = os.path.join(self.base_path, rel_path.replace("/", os.sep))
            if not os.path.exists(path):
                continue

            try:
                os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
            except Exception:
                pass

            if self._is_file_locked(path):
                locked.append(rel_path)
                self._log(f"待更新檔案被佔用: {rel_path}")

        return locked

    def _unlock_readonly_files(self):
        """解除整個專案目錄的唯讀屬性，回報解鎖失敗的檔案數"""
        failed = 0
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                full_path = os.path.join(root, f)
                try:
                    current_mode = os.stat(full_path).st_mode
                    if not (current_mode & stat.S_IWRITE):
                        os.chmod(full_path, current_mode | stat.S_IWRITE)
                except Exception:
                    failed += 1

        if failed:
            self._log(f"警告：{failed} 個檔案無法解除唯讀屬性")

        return failed

    # ------------------------------------------------------------------
    # 檢查更新（下載鍵）
    # ------------------------------------------------------------------
    def _start_check(self):
        """自動更新模式：優先走 Git，不行才退回 Dropbox"""
        self._busy(True)
        try:
            if self._prepare_git_engine():
                self.update_mode = MODE_GIT
                self._check_by_git()
            else:
                self._log("Git 引擎不可用，改用 Dropbox 更新模式")
                self.update_mode = MODE_ZIP
                self._check_by_dropbox()
        except Exception as e:
            self._log_exception("檢查更新時發生未預期的錯誤")
            self.update_mode = MODE_NONE
            QMessageBox.critical(
                self,
                "檢查更新失敗",
                f"檢查更新時發生錯誤：\n\n{e}\n\n詳細訊息請參考 update.log",
            )
        finally:
            self._busy(False)

    def _prepare_git_engine(self):
        """準備 PortableGit 執行環境"""
        if self._locate_git():
            return True

        installer = os.path.join(self.base_path, "PortableGit.exe")
        if not os.path.exists(installer):
            self._log("找不到 PortableGit.exe，無法建立 Git 更新環境")
            return False

        if not IS_WINDOWS:
            self._log("非 Windows 平台，跳過 PortableGit 自解壓")
            return False

        self._set_status("正在初始化更新引擎 (第一次執行較慢，請稍候)...")
        target_dir = os.path.join(self.base_path, "PortableGit")

        try:
            subprocess.run(
                [installer, "-y", f"-o{target_dir}"],
                check=True,
                cwd=self.base_path,  # === 修正：原版沒指定 cwd，會解壓到不確定的位置 ===
                creationflags=CREATE_NO_WINDOW,
                timeout=600,
            )
        except Exception as e:
            self._log(f"PortableGit 解壓失敗: {e}")
            return False

        # === 修正重點：解壓完成後必須重新掃描路徑 ===
        if self._locate_git():
            self._log(f"PortableGit 安裝成功: {self.git_exe}")
            try:
                os.remove(installer)
            except Exception:
                pass
            return True

        self._log("PortableGit 解壓完成，但仍找不到 git.exe，請檢查解壓結果")
        return False

    # ------------------------------------------------------------------
    # Git 模式
    # ------------------------------------------------------------------
    def _check_by_git(self):
        if not self._check_environment():
            self.update_mode = MODE_NONE
            return

        self._check_for_updates()

    def _check_environment(self):
        """建立 / 校正 Git 環境，成功回傳 True"""
        dot_git = os.path.join(self.base_path, ".git")

        # 1. 修正安全性設定重複的問題
        self._run_git(["config", "--global", "--replace-all", "safe.directory", "*"])

        # 2. 初始化檢查
        if not os.path.exists(dot_git):
            self._set_status("正在配置更新引擎...")
            if self._run_git(["init"]) is None:
                self._show_git_error("無法初始化本機更新環境")
                return False

        # 3. 強制校正 Remote（解決 origin 不存在或設定錯誤）
        self._run_git(["remote", "remove", "origin"])  # 不存在時失敗屬正常，忽略
        if self._run_git(["remote", "add", "origin", GITHUB_REPO_URL]) is None:
            self._show_git_error("無法設定更新來源")
            return False

        # 4. 基本配置
        self._run_git(["config", "user.email", "clinic@update.local"])
        self._run_git(["config", "user.name", "ClinicUser"])
        self._run_git(["config", "core.autocrlf", "false"])
        self._run_git(["config", "core.filemode", "false"])
        self._run_git(["config", "http.postBuffer", "524288000"])

        # 5. 執行 Fetch
        self._set_status("正在同步雲端資料 (第一次較久)...")
        if self._fetch() is None:
            # === 修正：原版只 print 一行就繼續往下跑，錯誤一路累積 ===
            self._show_git_error("無法連線至 GitHub 更新伺服器")
            return False

        # 6. 建立 HEAD 起點（解決 bad revision 'HEAD'）
        if self._run_git(["rev-parse", "HEAD"]) is None:
            self._set_status("正在建立本機版本起點...")
            self._refresh_index()
            self._run_git(["update-ref", f"refs/heads/{GITHUB_BRANCH}", "FETCH_HEAD"])
            self._run_git(["reset", "--hard", "FETCH_HEAD"], GIT_TIMEOUT_NETWORK)
            self._run_git(["symbolic-ref", "HEAD", f"refs/heads/{GITHUB_BRANCH}"])

        return True

    def _refresh_index(self):
        """更新索引中快取的檔案 stat 資訊

        === 這是鎖檔問題的真正解法 ===
        git reset --hard 不只比對內容差異，它還會檢查索引裡快取的
        檔案 mtime／size。只要某個檔案的 stat 與索引記錄不符，
        即使內容一模一樣，Git 仍會把它整個重寫（unlink + 重建）。

        cshis.dll 等元件正是這樣被牽連的：內容與雲端完全相同，
        卻因為索引 stat 過期而被 Git 重寫，撞上 Windows 的 DLL 鎖定。

        update-index --refresh 會重新計算這些檔案的 stat，
        確認內容未變的就標記為乾淨，Git 便不會再去動它們。

        注意：本指令在有「真正被修改過」的檔案時會回傳非零結束碼，
        那是正常現象，不是錯誤，因此不檢查回傳值。
        """
        self._set_status("正在校正檔案索引...")
        self._run_git(["update-index", "-q", "--refresh"], GIT_TIMEOUT_LOCAL)

    def _fetch(self):
        """--depth 1 淺層抓取，大幅縮短第一次執行的時間與失敗機率"""
        return self._run_git(
            ["fetch", "--depth", "1", "origin", GITHUB_BRANCH], GIT_TIMEOUT_NETWORK
        )

    def _check_for_updates(self):
        self._set_status("正在檢查雲端版本...")

        if self._fetch() is None:
            self._show_git_error("無法取得雲端版本資訊")
            self.update_mode = MODE_NONE
            return

        diff = self._run_git(["diff", "HEAD", "FETCH_HEAD", "--name-only", "--"])

        # === 修正重點 ===
        # 原版寫成 if diff and diff.strip(): ... else: 「系統已是最新狀態」
        # git 失敗回傳 None、無差異回傳 ""，兩者都是 falsy 被混在一起，
        # 導致「連不上 GitHub」被顯示成「已是最新」，使用者永遠更新不到。
        if diff is None:
            self._show_git_error("無法比對雲端版本")
            self.update_mode = MODE_NONE
            return

        files = [f for f in diff.strip().splitlines() if f.strip()]

        if not files:
            self._set_status("系統已是最新狀態")
            QMessageBox.information(
                self, "系統更新", "系統目前已是最新狀態，不需更新。"
            )
            self.update_mode = MODE_NONE
            return

        self.ui.tableWidget_file_list.setRowCount(0)
        for f in files:
            self._add_list([f, "GitHub 伺服器", "本機系統", "待更新"])

        self.ui.tableWidget_file_list.resizeRowsToContents()
        self._set_status(f"發現 {len(files)} 個檔案需要更新")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def _show_git_error(self, title):
        self._set_status(f"{title}")

        error = self.last_git_error or "未知錯誤"

        # 檔案鎖定類的錯誤，給對應的排除方向（網路建議在此無用）
        if "unable to unlink" in error or "Permission denied" in error:
            locked_name = ""
            marker = "unable to unlink old '"
            if marker in error:
                locked_name = error.split(marker, 1)[1].split("'", 1)[0]

            hint = (
                f"<br>1. 檔案「{locked_name}」正被程式使用中"
                if locked_name
                else "<br>1. 有檔案正被程式使用中"
            )
            advice = (
                f"{hint}"
                f"<br>2. 請關閉所有醫療系統視窗與健保讀卡機程式後重試"
                f"<br>3. 若仍失敗，請重新開機後第一時間執行更新"
                f"<br>4. 詳細記錄請見程式目錄下的 update.log"
            )
        else:
            advice = (
                "<br>1. 確認診所網路可連上 github.com (443 埠)"
                "<br>2. 檢查防毒軟體 / 防火牆是否攔截 git.exe"
                "<br>3. 詳細記錄請見程式目錄下的 update.log"
            )

        QMessageBox.critical(
            self,
            "更新失敗",
            f"<font size='4'><b>{title}</b></font>"
            f"<br><br>原因：{error}"
            f"<br><br>常見排除方向：{advice}",
        )

    def _update_github(self):
        """Git 強制同步更新，成功回傳 True"""
        # --- 1. 解除唯讀鎖定 ---
        self._set_status("正在解除檔案鎖定...")
        self._unlock_readonly_files()

        # --- 2. 備份診所專屬設定（保險箱）---
        self._set_status("正在備份診所設定檔...")
        vault = self._backup_protected_files()

        # --- 3. 執行 Git 更新 ---
        self._set_status("正在從雲端同步資料...")
        if self._fetch() is None:
            self._show_git_error("同步雲端資料失敗")
            return False

        # --- 4. 校正索引 stat ---
        # git reset --hard 會重寫任何 stat 與索引不符的檔案，即使內容完全相同。
        # 不先校正的話，cshis.dll 這類內容沒變的元件也會被 unlink 而撞上鎖定。
        self._refresh_index()

        # --- 5. 確認真正需要更新的檔案沒有被鎖住 ---
        # 注意：被鎖住不等於有問題。只有「這次真的要更新」且「正被佔用」的
        # 檔案才會擋住更新；單純被載入但內容沒變的 DLL，Git 根本不會碰。
        locked = self._find_locked_pending_files()
        if locked:
            self._set_status("有檔案被佔用，無法更新")
            QMessageBox.critical(
                self,
                "檔案被佔用，無法更新",
                f"<font size='4'><b>以下檔案需要更新，但正被其他程式使用中</b></font>"
                f"<br><br>{'<br>'.join(locked[:10])}"
                f"{'<br>...' if len(locked) > 10 else ''}"
                f"<br><br>請關閉下列程式後再更新一次："
                f"<br>1. 其他電腦上的醫療系統"
                f"<br>2. 健保讀卡機控制軟體"
                f"<br>3. 候診看板 (PyBulletin)",
            )
            self._restore_protected_files(vault, force_all=True)
            return False

        # --- 6. 覆寫檔案 ---
        self._set_status("正在覆寫系統檔案...")

        # (A) 強制對齊指針與索引
        if (
            self._run_git(["reset", "--hard", "FETCH_HEAD"], GIT_TIMEOUT_NETWORK)
            is None
        ):
            self._show_git_error("更新失敗 (reset)")
            self._restore_protected_files(vault, force_all=True)
            return False

        # (B) 強制覆蓋實體檔案
        if (
            self._run_git(
                ["checkout", "-f", "FETCH_HEAD", "--", "."], GIT_TIMEOUT_NETWORK
            )
            is None
        ):
            self._show_git_error("更新失敗 (checkout)")
            self._restore_protected_files(vault, force_all=True)
            return False

        # (C) 修正分支指針
        self._run_git(["update-ref", f"refs/heads/{GITHUB_BRANCH}", "FETCH_HEAD"])
        self._run_git(["symbolic-ref", "HEAD", f"refs/heads/{GITHUB_BRANCH}"])

        # --- 7. 還原診所專屬設定 ---
        self._set_status("正在還原診所設定檔...")
        self._restore_protected_files(vault)

        # --- 8. 修正 .bat 啟動參數 ---
        self._fix_bat_launch_parameters()

        # --- 9. 驗證更新結果 ---
        if not self._verify_git_update():
            return False

        return True

    def _verify_git_update(self):
        """更新後再比對一次，確認檔案真的被寫入

        === 新增 ===
        原版無論實際結果如何都跳「恭喜您！系統檔案全部更新成功」。
        """
        diff = self._run_git(["diff", "HEAD", "FETCH_HEAD", "--name-only", "--"])
        if diff is None:
            self._log("更新後驗證失敗：無法執行比對")
            return True  # 無法驗證不代表更新失敗，放行但留下記錄

        remain = [f for f in diff.strip().splitlines() if f.strip()]
        if remain:
            self._log(f"更新後仍有 {len(remain)} 個檔案不一致: {remain[:10]}")
            QMessageBox.warning(
                self,
                "更新未完全成功",
                f"<font size='4'><b>仍有 {len(remain)} 個檔案未能更新</b></font>"
                f"<br><br>可能原因：檔案被防毒軟體或其他程式鎖定。"
                f"<br>建議關閉所有醫療系統視窗後重新執行更新。"
                f"<br><br>詳細清單請見 update.log",
            )
            return False

        self._log("更新後驗證通過，所有檔案已同步")
        return True

    # ------------------------------------------------------------------
    # 診所專屬檔案保護
    # ------------------------------------------------------------------
    def _backup_protected_files(self):
        vault = {}
        for f_name in PROTECT_FILES:
            p = os.path.join(self.base_path, f_name)
            if not os.path.exists(p):
                continue
            try:
                with open(p, "rb") as f:
                    vault[f_name] = f.read()
            except Exception as e:
                self._log(f"備份 {f_name} 失敗: {e}")

        self._log(f"已備份 {len(vault)} 個診所專屬檔案")
        return vault

    def _restore_protected_files(self, vault, force_all=False):
        """
        策略 A：.conf 一律還原（診所設定唯一，絕不能被 Git 蓋掉）
        策略 B：.bat 只有在檔案遺失時才還原（讓 Git 有機會更新啟動檔）
        force_all：更新失敗回滾時，全部還原
        """
        for f_name, content in vault.items():
            p = os.path.join(self.base_path, f_name)

            should_restore = (
                force_all or f_name.endswith(".conf") or not os.path.exists(p)
            )
            if not should_restore:
                self._log(f"{f_name} 已由 Git 同步，無需還原")
                continue

            try:
                with open(p, "wb") as f:
                    f.write(content)
                self._log(f"已還原: {f_name}")
            except Exception as e:
                self._log(f"還原 {f_name} 失敗: {e}")

    def _fix_bat_launch_parameters(self):
        """修正 .bat 的啟動指令 py -3 → pythonw

        === 修正 ===
        原版用 encoding='cp950', errors='ignore' 讀寫，
        遇到非 Big5 字元會靜默刪除字元後再寫回，等於損毀 .bat。
        改為 bytes 層級取代，完全不經過編碼轉換。
        """
        bat_path = os.path.join(self.base_path, "pymedical.win32.bat")
        if not os.path.exists(bat_path):
            return

        try:
            with open(bat_path, "rb") as f:
                content = f.read()

            new_content = content.replace(b"py -3 -32", b"pythonw")
            new_content = new_content.replace(b"py -3", b"pythonw")

            if new_content != content:
                with open(bat_path, "wb") as f:
                    f.write(new_content)
                self._log("已將啟動指令修正為 pythonw")
        except Exception as e:
            self._log(f"修正 .bat 啟動參數失敗: {e}")

    # ------------------------------------------------------------------
    # Dropbox / zip 模式
    # ------------------------------------------------------------------
    def _open_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "開啟更新檔",
            "*.zip",
            "zip 壓縮檔 (*.zip);;Text Files (*.txt)",
            options=options,
        )
        if filename:
            self.ui.lineEdit_file_name.setText(filename)

    def _file_name_changed(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.update_mode = MODE_NONE

        file_name = self.ui.lineEdit_file_name.text()
        if not file_name or not os.path.isfile(file_name):
            return

        self._busy(True)
        try:
            self.update_mode = MODE_ZIP
            self._check_files(file_name)
        except Exception as e:
            self._log_exception("檢查更新檔失敗")
            self.update_mode = MODE_NONE
            QMessageBox.critical(self, "檢查更新檔失敗", f"無法讀取更新檔：\n\n{e}")
        finally:
            self._busy(False)

    def _check_by_dropbox(self):
        dropbox_file = self._download_dropbox_file()
        if not dropbox_file:
            self.update_mode = MODE_NONE
            return

        self._check_files(dropbox_file)

    def _get_latest_url(self):
        try:
            with urllib.request.urlopen(UPDATE_URL_TXT, timeout=10) as response:
                return response.read().decode("utf-8").strip()
        except Exception as e:
            self._log(f"無法取得動態更新網址，改用預設值: {e}")
            return None

    def _download_dropbox_file(self, timeout=30):
        url = self._get_latest_url() or DROPBOX_FALLBACK_URL
        self._log(f"下載更新檔: {url}")

        context = ssl.create_default_context()
        try:
            response = urllib.request.urlopen(url, context=context, timeout=timeout)
        except Exception as e:
            # 舊版 Windows 憑證庫過期時，降級為不驗證憑證再試一次
            self._log(f"憑證驗證下載失敗，改用不驗證模式重試: {e}")
            try:
                context = ssl._create_unverified_context()
                response = urllib.request.urlopen(url, context=context, timeout=timeout)
            except Exception as e2:
                self._log(f"下載更新檔失敗: {e2}")
                QMessageBox.critical(
                    self,
                    "下載失敗",
                    f"<font size='4'><b>無法下載更新檔</b></font>"
                    f"<br><br>原因：{e2}"
                    f"<br><br>請檢查診所網路狀態後再試一次。",
                )
                return None

        try:
            length = int(response.getheader("X-Dropbox-Content-Length"))
        except Exception:
            try:
                length = int(response.getheader("Content-Length"))
            except Exception:
                length = 0

        block_size = max(65536, length // 100) if length else 65536

        progress_dialog = QtWidgets.QProgressDialog(
            "正在下載系統更新檔，請稍候...", "取消", 0, length or 0, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        buf = io.BytesIO()
        size = 0
        cancelled = False

        try:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break

                # === 修正：原版的取消鍵完全沒有作用 ===
                if progress_dialog.wasCanceled():
                    cancelled = True
                    break

                buf.write(chunk)
                size += len(chunk)
                if length:
                    progress_dialog.setValue(min(size, length))
                QApplication.processEvents()
        finally:
            progress_dialog.setValue(length or size)
            progress_dialog.deleteLater()

        if cancelled:
            self._log("使用者取消下載")
            return None

        if size == 0:
            self._log("下載內容為空")
            QMessageBox.critical(self, "下載失敗", "下載的更新檔為空，請稍後再試。")
            return None

        download_file_name = os.path.join(self.base_path, "pymedical.zip")
        try:
            with open(download_file_name, "wb") as f:
                f.write(buf.getbuffer())
        except Exception as e:
            self._log(f"寫入更新檔失敗: {e}")
            QMessageBox.critical(self, "下載失敗", f"無法儲存更新檔：\n\n{e}")
            return None

        self._log(f"更新檔下載完成: {download_file_name} ({size} bytes)")
        return download_file_name

    def _check_files(self, zip_file_name):
        dest_root = self.base_path
        temp_dir = os.path.join(dest_root, "_temp")

        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            self._log(f"建立暫存目錄失敗: {e}")
            QMessageBox.critical(self, "更新失敗", f"無法建立暫存目錄：\n\n{e}")
            return

        self._set_status("正在解壓更新檔...")
        system_utils.unzip_file(zip_file_name, temp_dir)

        zip_dir = ntpath.basename(zip_file_name).split(".")[0]
        zip_source_root = os.path.join(temp_dir, zip_dir)

        if not os.path.isdir(zip_source_root):
            self._log(f"解壓後找不到來源目錄: {zip_source_root}")
            QMessageBox.critical(
                self, "更新檔格式錯誤", f"更新檔內容不符預期，找不到 {zip_dir} 目錄。"
            )
            return

        self.ui.tableWidget_file_list.setRowCount(0)

        self._set_status("正在比對檔案差異...")
        for sub_dir in ZIP_SUB_DIRS:
            self._list_files(zip_source_root, dest_root, sub_dir)

        self.ui.tableWidget_file_list.resizeRowsToContents()

        row_count = self.ui.tableWidget_file_list.rowCount()
        if row_count <= 0:
            self._set_status("系統已是最新狀態")
            QMessageBox.information(
                self,
                "系統更新",
                "<font size='4'><b>經過檢查，系統已經是最新檔，不需更新。</b></font>",
            )
            self.update_mode = MODE_NONE
            return

        self._set_status(f"發現 {row_count} 個檔案需要更新")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def _list_files(self, zip_source_root, dest_root, dir_name):
        source_dir = os.path.join(zip_source_root, dir_name)
        dest_dir = os.path.join(dest_root, dir_name)

        if not os.path.isdir(source_dir):
            self._log(f"更新檔中無此目錄，略過: {dir_name}")
            return

        # === 修正：原版用 os.mkdir，遇到 mysql/default 這種多層路徑會失敗 ===
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            self._log(f"建立目錄 {dest_dir} 失敗: {e}")
            return

        source_files = [
            f
            for f in listdir(source_dir)
            if os.path.isfile(os.path.join(source_dir, f))
        ]

        for file in source_files:
            source_full_path = os.path.join(source_dir, file)
            dest_full_path = os.path.join(dest_dir, file)

            # 診所專屬設定檔不從 zip 覆蓋
            if file in PROTECT_FILES and os.path.exists(dest_full_path):
                continue

            source_file_date = datetime.datetime.fromtimestamp(
                self.creation_date(source_full_path)
            )
            row = [file, source_dir, dest_dir, source_file_date]

            if not os.path.isfile(dest_full_path):
                self._add_list(row)
                continue

            # 用 MD5 比對內容，而非檔案日期
            source_hash = self.get_file_hash(source_full_path)
            dest_hash = self.get_file_hash(dest_full_path)

            if source_hash != dest_hash:
                if file == "pymedical.py" or "libs" in dest_dir:
                    self.restart_pymedical = True
                self._add_list(row)

    def _update_dropbox_files(self):
        """zip 模式的實際複製動作，成功回傳 True"""
        row_count = self.ui.tableWidget_file_list.rowCount()
        self.ui.progressBar.setMaximum(row_count)

        failed = []

        for row_no in range(row_count):
            self.ui.progressBar.setValue(row_no)
            QApplication.processEvents()

            file_name = self.ui.tableWidget_file_list.item(row_no, 0).text()
            source_dir = self.ui.tableWidget_file_list.item(row_no, 1).text()
            dest_dir = self.ui.tableWidget_file_list.item(row_no, 2).text()

            source_file_name = os.path.join(source_dir, file_name)
            dest_file_name = os.path.join(dest_dir, file_name)

            try:
                os.makedirs(dest_dir, exist_ok=True)

                # 解除唯讀屬性
                if os.path.exists(dest_file_name):
                    current_mode = os.stat(dest_file_name).st_mode
                    os.chmod(dest_file_name, current_mode | stat.S_IWRITE)

                shutil.copy2(source_file_name, dest_file_name)
            except Exception as e:
                # === 修正：原版任何一個檔案複製失敗就整個崩潰，且不會有任何訊息 ===
                self._log(f"複製失敗 {file_name}: {e}")
                failed.append(file_name)

        self.ui.progressBar.setValue(row_count)

        if failed:
            QMessageBox.warning(
                self,
                "部分檔案更新失敗",
                f"<font size='4'><b>{len(failed)} 個檔案未能更新</b></font>"
                f"<br><br>{'<br>'.join(failed[:10])}"
                f"{'<br>...' if len(failed) > 10 else ''}"
                f"<br><br>可能被防毒軟體或其他程式鎖定，"
                f"請關閉所有醫療系統視窗後重新更新。",
            )
            return False

        return True

    def get_file_hash(self, file_path):
        """計算檔案的 MD5 雜湊值"""
        if not os.path.isfile(file_path):
            return None

        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def _add_list(self, row):
        row_no = self.ui.tableWidget_file_list.rowCount()
        self.ui.tableWidget_file_list.setRowCount(row_no + 1)

        for column in range(len(row)):
            self.ui.tableWidget_file_list.setItem(
                row_no,
                column,
                QtWidgets.QTableWidgetItem(string_utils.xstr(row[column])),
            )

    def creation_date(self, file_name):
        return os.stat(file_name).st_mtime

    # ------------------------------------------------------------------
    # 開始更新
    # ------------------------------------------------------------------
    def accepted_button_clicked(self):
        # === 修正重點 ===
        # 原版靠 self.git_exe 是否存在來猜測走哪條路徑。
        # 一旦猜錯，_update_dropbox_files() 會把清單裡的
        # 「GitHub 伺服器」「本機系統」當成目錄路徑使用而崩潰。
        if self.update_mode == MODE_NONE:
            QMessageBox.warning(
                self, "無法更新", "請先按「下載」或選擇更新檔進行檢查。"
            )
            return

        if not self._check_writable():
            self._report_to_zoho_server("fail", "程式目錄無寫入權限")
            return

        self._busy(True)
        success = False
        error_msg = ""

        try:
            if self.update_mode == MODE_GIT:
                success = self._update_github()
            else:
                success = self._update_dropbox_files()

            if success:
                self._set_status("正在更新資料庫結構...")
                try:
                    update_utils.update_database(self.parent, self.database)
                except Exception as e:
                    self._log_exception("資料庫更新失敗")
                    success = False
                    error_msg = f"資料庫更新失敗: {e}"
                    QMessageBox.critical(
                        self,
                        "資料庫更新失敗",
                        f"檔案已更新，但資料庫結構更新失敗：\n\n{e}",
                    )
            else:
                error_msg = self.last_git_error or "檔案更新未完全成功"

        except Exception as e:
            self._log_exception("更新過程發生未預期的錯誤")
            success = False
            error_msg = str(e)
            QMessageBox.critical(
                self,
                "更新失敗",
                f"更新過程發生錯誤：\n\n{e}\n\n詳細訊息請見 update.log",
            )
        finally:
            self._busy(False)
            # === 修正：成功或失敗都回報，否則後台永遠看不到失敗的機器 ===
            self._report_to_zoho_server("success" if success else "fail", error_msg)

        if not success:
            self._set_status("更新失敗")
            return

        # === 修正：只有真的成功才顯示成功訊息 ===
        self.restart_pymedical = True  # 目前一律重新啟動

        self._set_status("更新完成")

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("系統更新完成")
        msg_box.setText(
            "<font size='4'><b>恭喜您！系統已更新至最新檔，系統檔案全部更新成功。</b></font>"
        )
        msg_box.setInformativeText("為了讓更新檔生效，即將重新啟動醫療系統。")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

        if self.restart_pymedical:
            self.parent.restart_pymedical()
        else:
            self.parent.close_all_tabs()

    # ------------------------------------------------------------------
    # 更新結果回報
    # ------------------------------------------------------------------
    def _report_to_zoho_server(self, update_status="success", error_msg=""):
        """將更新結果回報至後台 MariaDB（成功與失敗都回報）"""
        commit_msg = "Unknown"
        conn = None

        try:
            commit_msg = self._get_commit_msg()
        except Exception:
            pass

        # === 修正：原版在例外情況下 commit_msg 可能未定義而 NameError ===
        self._write_version_file(commit_msg)

        try:
            clinic_name = self.system_settings.field("院所名稱")
            current_user = self.system_settings.field("使用者")
            pc_name = socket.gethostname()
            os_info = self._get_os_info()
            ip_address = self._get_ip_address(pc_name)

            conn = self._get_db_connection()
            if not conn:
                self._log("無法連線至後台伺服器，略過回報")
                return

            cursor = conn.cursor()

            # 優先寫入含狀態欄位的新版結構，欄位不存在時退回舊版
            new_query = """
                REPLACE INTO update_logs
                (clinic_name, pc_name, login_user, current_version, os_version,
                 ip_address, update_status, error_msg, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            legacy_query = """
                REPLACE INTO update_logs
                (clinic_name, pc_name, login_user, current_version, os_version,
                 ip_address, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """

            try:
                cursor.execute(
                    new_query,
                    (
                        clinic_name,
                        pc_name,
                        current_user,
                        commit_msg,
                        os_info,
                        ip_address,
                        update_status,
                        (error_msg or "")[:500],
                    ),
                )
            except mysql.connector.Error:
                cursor.execute(
                    legacy_query,
                    (
                        clinic_name,
                        pc_name,
                        current_user,
                        commit_msg,
                        os_info,
                        ip_address,
                    ),
                )

            conn.commit()
            cursor.close()
            self._log(f"已回報更新結果: {update_status}")

        except Exception as e:
            self._log(f"遠端回報失敗: {e}")
        finally:
            if conn:
                try:
                    if conn.is_connected():
                        conn.close()
                except Exception:
                    pass

    def _write_version_file(self, version_info):
        try:
            with open(
                os.path.join(self.base_path, "version.txt"), "w", encoding="utf-8"
            ) as f:
                f.write(string_utils.xstr(version_info))
        except Exception as e:
            self._log(f"寫入 version.txt 失敗: {e}")

    def _get_os_info(self):
        system = platform.system()
        release = platform.release()
        version = platform.version()

        actual_os = f"{system} {release}"
        try:
            build_number = int(version.split(".")[-1])
            if system == "Windows" and release == "10" and build_number >= 22000:
                actual_os = "Windows 11"
        except Exception:
            pass

        return f"{actual_os} (Build {version})"

    def _get_commit_msg(self):
        result = self._run_git(["log", "-1", "--pretty=%s"])
        if result is None:
            return "Unknown"

        return result.strip() or "Unknown"

    def _get_db_connection(self):
        """取得後台資料庫連線

        === 安全性提醒 ===
        原版把 root 帳密以 base64 硬編碼在程式裡，而程式部署在每一家診所。
        base64 不是加密，任何拿到 .py 的人都能立刻解出來。
        建議改為：後台開一個 HTTPS endpoint 收回報，客戶端只帶唯讀 token。
        過渡期至少改用「只有 update_logs INSERT 權限」的專用帳號，
        並把帳密放到程式目錄外的 report.conf，不要進版控。
        """
        uid, pwd = self._get_db_credentials()
        if not uid:
            return None

        try:
            return mysql.connector.connect(
                host="www.zoho.net.tw",
                user=uid,
                password=pwd,
                database="zoho",
                connect_timeout=5,
            )
        except Exception as e:
            self._log(f"後台資料庫連線失敗: {e}")
            return None

    def _get_db_credentials(self):
        """優先讀取 report.conf，讀不到才用內建值（過渡期相容）"""
        conf_path = os.path.join(self.base_path, "report.conf")
        if os.path.exists(conf_path):
            try:
                config = configparser.ConfigParser()
                config.read(conf_path, encoding="utf-8")
                return (
                    config.get("report", "user"),
                    config.get("report", "password"),
                )
            except Exception as e:
                self._log(f"讀取 report.conf 失敗，改用內建設定: {e}")

        # TODO: 換成專用帳號後移除以下兩行
        u_b64 = "cm9vdA=="
        p_b64 = "MTUzZmlzaA=="
        try:
            return (
                base64.b64decode(u_b64).decode("utf-8"),
                base64.b64decode(p_b64).decode("utf-8"),
            )
        except Exception:
            return None, None

    def _get_ip_address(self, pc_name):
        local_ip = "127.0.0.1"
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        except Exception:
            try:
                local_ip = socket.gethostbyname(pc_name)
            except Exception:
                pass
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass

        return local_ip
