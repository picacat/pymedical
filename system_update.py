# -*- coding: UTF-8 -*-

import base64
import datetime
import hashlib
import io
import ntpath
import os
import os.path
import platform
import shutil
import socket
import stat
import subprocess
import urllib.error
import urllib.request
from os import listdir

import mysql.connector
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton

from libs import class_utils, string_utils, system_utils, ui_utils, update_utils


# 醫療系統更新 2026-04-29 更新.
class SystemUpdate(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(SystemUpdate, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self.restart_pymedical = False

        self._set_ui()
        self._set_signal()

        # 1. 定義程式根目錄 (pymedical/)
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # 如果你擔心未來目錄又變，可以用這個「自動偵測」邏輯：
        possible_paths = [
            os.path.join(self.base_path, "PortableGit", "bin", "git.exe"),
            os.path.join(self.base_path, "PortableGit", "cmd", "git.exe"),
            os.path.join(self.base_path, "PortableGit", "mingw32", "bin", "git.exe"),
        ]

        self.git_exe = None
        for path in possible_paths:
            if os.path.exists(path):
                self.git_exe = path
                break

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉G
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_SYSTEM_UPDATE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("開始更新")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.ui.toolButton_open_file.clicked.connect(self._open_file)
        self.ui.lineEdit_file_name.textChanged.connect(self._file_name_changed)

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
        self.ui.pushButton_download.clicked.connect(self._check_downloaded_file)

    def _set_radio_buttons(self):
        self.ui.pushButton_download.setEnabled(False)
        self.ui.lineEdit_file_name.setEnabled(False)
        self.ui.toolButton_open_file.setEnabled(False)

        if self.ui.radioButton_auto_update.isChecked():
            self.ui.pushButton_download.setEnabled(True)
        else:
            self.ui.lineEdit_file_name.setEnabled(True)
            self.ui.toolButton_open_file.setEnabled(True)

    def _set_table_width(self):
        width = [300, 180, 150, 200]
        self.table_widget_file_list.set_table_heading_width(width)

    def _run_git(self, args):
        """核心：執行內置 Git 指令"""
        if not os.path.exists(self.git_exe):
            print(f"找不到 Git 執行檔: {self.git_exe}")
            return None

        try:
            # 加上 creationflags=0x08000000 隱藏黑色視窗
            # 使用 env 隔離環境，避免受到使用者電腦原本 Git 設定的影響
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"  # 禁用任何互動式提示

            result = subprocess.check_output(
                [self.git_exe] + args,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=self.base_path,  # 務必在 pymedical 根目錄執行
                env=env,
                creationflags=0x08000000,
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Git 錯誤: {e.output}")
            return None

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

        file_name = self.ui.lineEdit_file_name.text()
        if file_name == "":
            return

        if not os.path.isfile(file_name):
            return

        zip_file_name = self.ui.lineEdit_file_name.text()
        self._check_files(zip_file_name)

    # 開始更新
    def accepted_button_clicked(self):
        if os.path.exists(self.git_exe) and self.ui.radioButton_auto_update.isChecked():
            self._update_github()
        else:
            self._update_dropbox_files()

        update_utils.update_database(self.parent, self.database)

        self.restart_pymedical = True  # 暫時全部重新啟動

        if self.restart_pymedical:
            information = "為了讓更新檔生效, 即將重新啟動醫療系統."
        else:
            information = "系統更新完成, 請繼續使用醫療系統."

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("系統更新完成")
        msg_box.setText(
            "<font size='4'><b>恭喜您! 系統已更新至最新檔, 系統檔案全部更新成功.</b></font>"
        )
        msg_box.setInformativeText(information)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

        if self.restart_pymedical:
            self.parent.restart_pymedical()
        else:
            self.parent.close_all_tabs()

    # def _update_github(self):
    #     # --- 1. 全域物理防護：解除整個專案目錄的鎖定 ---
    #     self.ui.label_status.setText("正在解除全系統檔案鎖定...")

    #     # 定義需要排除的目錄，避免掃描到 .git 內部資料庫 (節省時間)
    #     exclude_dirs = {".git", "PortableGit", "_temp"}

    #     for root, dirs, files in os.walk(self.base_path):
    #         # 過濾不需要解鎖的系統目錄
    #         dirs[:] = [d for d in dirs if d not in exclude_dirs]

    #         for f in files:
    #             full_path = os.path.join(root, f)
    #             try:
    #                 # 核心動作：強制拔掉「唯讀」屬性，確保 Git 有最高寫入權
    #                 current_mode = os.stat(full_path).st_mode
    #                 if not (current_mode & stat.S_IWRITE):
    #                     os.chmod(full_path, current_mode | stat.S_IWRITE)
    #             except Exception:
    #                 pass  # 遇到系統鎖定檔案跳過即可

    #     self._run_git(["fetch", "origin", "main"])

    #     self.ui.label_status.setText("正在執行強制更新...")

    #     # --- 2. 執行核心更新組合拳 ---
    #     # (A) 強制對齊指針與索引
    #     self._run_git(["reset", "--hard", "FETCH_HEAD"])

    #     # (B) 暴力覆蓋實體檔案 (解決你說的 ui/ 沒拷貝過去的問題)
    #     self._run_git(["checkout", "-f", "FETCH_HEAD", "--", "."])

    #     # (C) 修正分支指針 (確保 HEAD 乖乖待在 main 上)
    #     self._run_git(["update-ref", "refs/heads/main", "FETCH_HEAD"])
    #     self._run_git(["symbolic-ref", "HEAD", "refs/heads/main"])

    #     self._report_to_zoho_server()

    def _update_github(self):
        # --- 1. 全域物理防護：解除整個專案目錄的鎖定 ---
        self.ui.label_status.setText("正在解除檔案鎖定並備份設定...")

        exclude_dirs = {".git", "PortableGit", "_temp"}

        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                full_path = os.path.join(root, f)
                try:
                    current_mode = os.stat(full_path).st_mode
                    if not (current_mode & stat.S_IWRITE):
                        os.chmod(full_path, current_mode | stat.S_IWRITE)
                except Exception:
                    pass

        # --- 🛡️ 核心新增：物理保險箱 (備份重要設定) ---
        # 這些檔案無論 Git 怎麼改，我們都要保住診所原本的內容
        protect_files = [
            "pymedical.win32.bat",
            "pybulletin.win32.bat",
            "pymedical.conf",
            "qingtian.conf",
            "mingi.conf",
            "nd.conf",
            "nw.conf",
        ]
        vault = {}
        for f_name in protect_files:
            p = os.path.join(self.base_path, f_name)
            if os.path.exists(p):
                try:
                    with open(p, "rb") as f:
                        vault[f_name] = f.read()
                except Exception:
                    pass

        # --- 2. 執行 Git 更新 ---
        self.ui.label_status.setText("正在從雲端同步資料...")
        self._run_git(["fetch", "origin", "main"])
        self.ui.label_status.setText("正在執行強制更新組合拳...")

        # (A) 強制對齊
        self._run_git(["reset", "--hard", "FETCH_HEAD"])
        # (B) 暴力覆蓋
        self._run_git(["checkout", "-f", "FETCH_HEAD", "--", "."])
        # (C) 修正指針
        self._run_git(["update-ref", "refs/heads/main", "FETCH_HEAD"])
        self._run_git(["symbolic-ref", "HEAD", "refs/heads/main"])

        # --- 3. 智慧還原邏輯 ---
        self.ui.label_status.setText("正在檢查並修復必要檔案...")
        for f_name, content in vault.items():
            p = os.path.join(self.base_path, f_name)

            # 策略 A：如果是 .conf 結尾的，無論如何都要還原 (因為診所設定唯一)
            if f_name.endswith(".conf"):
                try:
                    with open(p, "wb") as f:
                        f.write(content)
                    print(f"🛡️ 強制還原設定檔: {f_name}")
                except Exception:
                    pass

            # 策略 B：如果是 .bat，只有在「檔案不見了」的時候才還原
            elif f_name == "pymedical.win32.bat":
                if not os.path.exists(p):
                    try:
                        with open(p, "wb") as f:
                            f.write(content)
                        print(f"🛡️ 偵測到啟動檔遺失，已從備份還原: {f_name}")
                    except Exception:
                        pass
                else:
                    print("✅ 啟動檔已由 Git 同步完成，無需還原")

        # --- 🚀 額外加強：暴力修正 .bat 啟動參數 ---
        # 這是為了確保萬一保險箱還原回來的 .bat 還是舊的 py -3 指令，我們現場幫他改掉
        self._fix_bat_launch_parameters()

        # 回報至後台
        self._report_to_zoho_server()

    def _fix_bat_launch_parameters(self):
        """專門暴力修正 .bat 檔案的內容"""
        bat_path = os.path.join(self.base_path, "pymedical.win32.bat")
        if os.path.exists(bat_path):
            try:
                # 使用 cp950 (Big5) 讀取繁體中文 Windows 的 .bat
                with open(bat_path, "r", encoding="cp950", errors="ignore") as f:
                    content = f.read()

                if "py -3 -32" in content or "py -3" in content:
                    new_content = content.replace("py -3 -32", "pythonw").replace(
                        "py -3", "pythonw"
                    )
                    with open(bat_path, "w", encoding="cp950", errors="ignore") as f:
                        f.write(new_content)
                    print("🛡️ 已自動將啟動指令優化為 pythonw")
            except Exception:
                pass

    def _update_dropbox_files(self):
        row_count = self.ui.tableWidget_file_list.rowCount()
        self.ui.progressBar.setMaximum(row_count)

        for row_no in range(row_count):
            self.ui.progressBar.setValue(row_no)
            source_dir = self.ui.tableWidget_file_list.item(row_no, 1).text()
            dest_dir = self.ui.tableWidget_file_list.item(row_no, 2).text()

            if not os.path.exists(dest_dir):
                os.mkdir(dest_dir)

            source_file_name = os.path.join(
                source_dir, self.ui.tableWidget_file_list.item(row_no, 0).text()
            )
            dest_file_name = os.path.join(
                dest_dir, self.ui.tableWidget_file_list.item(row_no, 0).text()
            )

            # --- 新增的部分：解除唯讀屬性 ---
            if os.path.exists(dest_file_name):
                # 取得目前的權限狀態
                current_mode = os.stat(dest_file_name).st_mode
                # 使用位元運算移除「唯讀」標誌 (S_IWRITE 代表可寫入)
                os.chmod(dest_file_name, current_mode | stat.S_IWRITE)
            # ----------------------------

            shutil.copy2(source_file_name, dest_file_name)

    def _check_files(self, zip_file_name):
        dest_root = os.path.dirname(os.path.abspath(__file__))
        temp_dir = os.path.join(dest_root, "_temp")

        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            os.mkdir(temp_dir)
        except PermissionError:
            pass

        system_utils.unzip_file(zip_file_name, temp_dir)

        zip_dir = ntpath.basename(zip_file_name).split(".")[0]
        zip_source_root = os.path.join(temp_dir, zip_dir)

        self.ui.tableWidget_file_list.setRowCount(0)

        self._list_files(zip_source_root, dest_root, "")
        self._list_files(zip_source_root, dest_root, "classes")
        self._list_files(zip_source_root, dest_root, "convert")
        self._list_files(zip_source_root, dest_root, "css")
        self._list_files(zip_source_root, dest_root, "dialog")
        self._list_files(zip_source_root, dest_root, "libs")
        self._list_files(zip_source_root, dest_root, "slot_machine")
        self._list_files(zip_source_root, dest_root, "mysql")
        self._list_files(zip_source_root, dest_root, "mysql//default")
        self._list_files(zip_source_root, dest_root, "printer")
        self._list_files(zip_source_root, dest_root, "ui")
        self._list_files(zip_source_root, dest_root, "images")
        self._list_files(zip_source_root, dest_root, "icons")
        self._list_files(zip_source_root, dest_root, "tables")
        self._list_files(zip_source_root, dest_root, "payment_machine")
        self._list_files(zip_source_root, dest_root, "kiosk")

        self.ui.tableWidget_file_list.resizeRowsToContents()

        if self.ui.tableWidget_file_list.rowCount() <= 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("系統更新完成")
            msg_box.setText(
                "<font size='4'><b>經過檢查更新檔案, 發現系統已經是最新檔, 不需更新.</b></font>"
            )
            msg_box.setInformativeText("請按取消鍵結束系統更新.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.exec_()
            return

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def get_file_hash(self, file_path):
        """計算檔案的 MD5 雜湊值"""
        if not os.path.isfile(file_path):
            return None
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # 分塊讀取，避免大檔案佔用過多記憶體
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    # 列出需要更新的檔案
    def _list_files(self, zip_source_root, dest_root, dir_name):
        source_dir = os.path.join(zip_source_root, dir_name)
        dest_dir = os.path.join(dest_root, dir_name)

        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)

        source_files = [
            f
            for f in listdir(source_dir)
            if os.path.isfile(os.path.join(source_dir, f))
        ]

        # for file in source_files:
        #     source_file_name = file
        #     source_file_date = datetime.datetime.fromtimestamp(
        #         self.creation_date(os.path.join(source_dir, source_file_name)))
        #     row = [source_file_name, source_dir, dest_dir, source_file_date]

        #     dest_file_name = os.path.join(dest_dir, source_file_name)
        #     if not os.path.isfile(dest_file_name):
        #         self._add_list(row)
        #         continue

        #     dest_file_date = datetime.datetime.fromtimestamp(
        #         self.creation_date(os.path.join(dest_dir, dest_file_name)))
        #     if source_file_date > dest_file_date:
        #         if source_file_name in ['pymedical.py'] or 'libs' in dest_dir:
        #             self.restart_pymedical = True

        #         self._add_list(row)
        for file in source_files:
            source_full_path = os.path.join(source_dir, file)
            dest_full_path = os.path.join(dest_dir, file)

            # 取得來源檔的日期 (維持顯示用)
            source_file_date = datetime.datetime.fromtimestamp(
                self.creation_date(source_full_path)
            )
            row = [file, source_dir, dest_dir, source_file_date]

            # 如果目標檔案不存在，直接加入更新清單
            if not os.path.isfile(dest_full_path):
                self._add_list(row)
                continue

            # --- 優化點：改用 Hash 比對 ---
            source_hash = self.get_file_hash(source_full_path)
            dest_hash = self.get_file_hash(dest_full_path)

            if source_hash != dest_hash:
                # 如果是核心檔案變更，標記需要重啟
                if file == "pymedical.py" or "libs" in dest_dir:
                    self.restart_pymedical = True

                self._add_list(row)

    # 顯示需要更新的檔案
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
        # if sys.platform == 'win32':
        #     return os.path.getctime(file_name)
        # else:
        #     return os.stat(file_name).st_mtime

        return os.stat(file_name).st_mtime

    def _get_latest_url(self):
        # 這是你在 GitHub 點擊 "Raw" 後取得的網址
        raw_url = "https://raw.githubusercontent.com/picacat/pymedical_update/refs/heads/main/update.txt"
        try:
            # 讀取網路上的純文字內容
            with urllib.request.urlopen(raw_url, timeout=5) as response:
                # 讀取並去掉換行與空格
                latest_url = response.read().decode("utf-8").strip()
                return latest_url
        except Exception as e:
            print(f"無法取得更新網址: {e}")
            return None

    def _download_dropbox_file(self, timeout=10):
        import ssl

        context = ssl._create_unverified_context()

        # --- 修改部分：動態獲取網址 ---
        dynamic_url = self._get_latest_url()
        if not dynamic_url:
            url = "https://www.dropbox.com/s/4h4a35ygzqx7duc/pymedical.zip?dl=1"
        else:
            url = dynamic_url

        try:
            response = urllib.request.urlopen(url, context=context, timeout=timeout)
        except (urllib.error.URLError, socket.timeout) as e:
            QtWidgets.QMessageBox.warning(
                self, "錯誤", "❌ 下載更新檔失敗，請檢查網路狀態。"
            )
            print(f"⚠️ 網路錯誤：{e}")
            return None

        try:
            length = int(response.getheader("X-Dropbox-Content-Length"))
        except Exception:
            length = 8767142

        block_size = max(4096, length // 100)

        progress_dialog = QtWidgets.QProgressDialog(
            "正在下載系統更新檔中, 請稍後...", "取消", 0, length, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        buf = io.BytesIO()
        size = 0
        while True:
            buf1 = response.read(block_size)
            if not buf1:
                break

            buf.write(buf1)
            size += len(buf1)
            if length:
                progress_dialog.setValue(size)

        progress_dialog.setValue(length)
        progress_dialog.deleteLater()
        download_file_name = "pymedical.zip"
        with open(download_file_name, "wb") as f:
            f.write(buf.getbuffer())

        return download_file_name

    def _check_downloaded_file(self):
        # 1. 不管有沒有 git.exe，先嘗試準備環境 (包含解壓 PortableGit.exe)
        git_ready = self._prepare_git_engine()

        # 2. 根據準備結果決定路徑
        if git_ready:
            # 這裡進去後，self.git_exe 應該已經存在了
            self._download_by_git()
        else:
            # 如果連解壓都沒辦法 (沒安裝檔)，才走舊路徑
            self._download_by_dropbox()

    # 新增git更新方式 2026-04-09
    def _download_by_git(self):
        self._check_environment()
        self._check_for_updates()

    # 安裝 portable git
    def _prepare_git_engine(self):
        # 如果 git.exe 已經在那裡了，直接通過
        if self.git_exe is not None and os.path.exists(self.git_exe):
            return True

        # 如果沒有 git.exe，看看有沒有自解壓檔
        installer = os.path.join(self.base_path, "PortableGit.exe")
        if os.path.exists(installer):
            self.ui.label_status.setText("正在初始化更新引擎 (第一次執行較慢)...")
            try:
                # 執行靜默解壓 (解壓到 PortableGit 資料夾)
                # 注意：這裡的 -o. 會解壓出一個 PortableGit 目錄
                subprocess.run([installer, "-y"], check=True, creationflags=0x08000000)

                # 再次確認解壓後 git.exe 是否真的出現了
                if os.path.exists(self.git_exe):
                    # 成功後刪除安裝檔
                    try:
                        os.remove(installer)
                    except Exception:
                        pass
                    return True
            except Exception as e:
                print(f"解壓失敗: {e}")

        return False

    # 檢查git環境
    def _check_environment(self):
        dot_git = os.path.join(self.base_path, ".git")
        repo_url = "https://github.com/picacat/pymedical.git"

        # 1. 修正安全性設定重複的問題
        # 使用 --replace-all 確保把之前亂掉的設定全部清掉，只保留一個 "*"
        self._run_git(["config", "--global", "--replace-all", "safe.directory", "*"])

        # 2. 初始化檢查
        if not os.path.exists(dot_git):
            self.ui.label_status.setText("正在配置更新引擎...")
            self._run_git(["init"])

        # 3. 強制校正 Remote (解決 'origin' 不存在或讀不到的問題)
        # 先嘗試移除，再重新加入，確保 origin 乾乾淨淨
        self._run_git(["remote", "remove", "origin"])
        self._run_git(["remote", "add", "origin", repo_url])

        # 4. 基本配置
        self._run_git(["config", "user.email", "clinic@update.local"])
        self._run_git(["config", "user.name", "ClinicUser"])
        self._run_git(["config", "core.autocrlf", "false"])

        # 5. 執行 Fetch (這步成功後才會產生 FETCH_HEAD)
        self.ui.label_status.setText("正在同步雲端資料...")
        fetch_res = self._run_git(["fetch", "origin", "main"])

        if fetch_res is None:
            print("無法連接到 GitHub，請檢查診所網路環境。")
            return

        # 6. 建立 HEAD 起點 (解決 bad revision 'HEAD')
        check_head = self._run_git(["rev-parse", "HEAD"])
        if check_head is None:
            self.ui.label_status.setText("正在建立本地起點...")
            # 先建立分支紀錄
            self._run_git(["update-ref", "refs/heads/main", "FETCH_HEAD"])
            # 強制對齊內容
            self._run_git(["reset", "--hard", "FETCH_HEAD"])
            # 鎖定 HEAD 指標
            self._run_git(["symbolic-ref", "HEAD", "refs/heads/main"])

        # 7. 最後才標記跳過更新 (檔案必須在 Git 追蹤內才能 mark)
        # self._run_git(["update-index", "--skip-worktree", "pymedical.win32.bat"])

    # 檢查更新
    def _check_for_updates(self):
        self.ui.label_status.setText("正在檢查雲端版本...")
        self._run_git(["fetch", "origin", "main"])
        diff = self._run_git(
            [
                "diff",
                "HEAD",
                "FETCH_HEAD",
                "--name-only",
                "--",
                ".",
                # ":(exclude)pymedical.win32.bat",
            ]
        )
        # 檢查檔案的不同
        if diff and diff.strip():
            files = diff.strip().splitlines()
            self.ui.tableWidget_file_list.setRowCount(0)
            for f in files:
                self._add_list([f, "GitHub 伺服器", "本地系統", "待更新"])
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
            count = len(files)
            self.ui.label_status.setText(f"發現 {count} 個檔案需要更新")
            self.ui.tableWidget_file_list.resizeRowsToContents()
        else:
            self.ui.label_status.setText("系統已是最新狀態")
            QMessageBox.information(self, "更新", "系統目前已是最新狀態。")

    # 開始下載
    def _download_by_dropbox(self):
        dropbox_file = self._download_dropbox_file()

        self._check_files(dropbox_file)

    # 回報更新.
    def _report_to_zoho_server(self):
        """將更新結果回報至 www.zoho.net.tw 的 MariaDB"""
        conn = None
        try:
            # 取得診所基本資訊
            clinic_name = self.system_settings.field("院所名稱")
            current_user = self.system_settings.field("使用者")
            pc_name = socket.gethostname()
            os_info = self._get_os_info()
            commit_msg = self._get_commit_msg()
            ip_address = self._get_ip_address(pc_name)

            # 建立連線
            conn = self._get_db_connection()
            if not conn:
                return

            cursor = conn.cursor()

            # 寫入記錄
            # REPLACE 會自動判斷：如果 key 重複就刪除舊的再插入新的，如果不重複就直接插入
            query = """
                REPLACE INTO update_logs
                (clinic_name, pc_name, login_user, current_version, os_version, ip_address, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(
                query,
                (clinic_name, pc_name, current_user, commit_msg, os_info, ip_address),
            )
            conn.commit()

            cursor.close()
        except Exception as e:
            print(f"遠端回報失敗 (zoho.net.tw): {e}")
        finally:
            if conn and conn.is_connected():
                conn.close()

        version_info = commit_msg
        with open(
            os.path.join(self.base_path, "version.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(version_info)

    # 取得客戶端的作業系統版本
    def _get_os_info(self):
        system = platform.system()  # 通常是 "Windows"
        release = platform.release()  # 在 Win11 可能還是會回傳 "10"
        version = platform.version()  # 這裡會拿到 Build number，例如 "10.0.22621"

        # 邏輯判斷：如果 Build number >= 22000 就是 Windows 11
        actual_os = f"{system} {release}"
        try:
            build_number = int(version.split(".")[-1])
            if system == "Windows" and release == "10" and build_number >= 22000:
                actual_os = "Windows 11"
            else:
                actual_os = f"{system} {release}"
        except Exception:
            actual_os = f"{system} {release}"

        os_info = f"{actual_os} (Build {version})"

        return os_info

    def _get_commit_msg(self):
        # 抓取最新的 Commit 標題 (-1 代表只抓一筆, %s 代表主旨)
        commit_msg = "Unknown"
        try:
            commit_msg = self._run_git(["log", "-1", "--pretty=%s"]).strip()
        except Exception:
            pass

        return commit_msg

    # 取得資料庫連線
    def _get_db_connection(self):
        u_b64 = "cm9vdA=="
        p_b64 = "MTUzZmlzaA=="

        uid = base64.b64decode(u_b64).decode("utf-8")
        pwd = base64.b64decode(p_b64).decode("utf-8")

        try:
            conn = mysql.connector.connect(
                host="www.zoho.net.tw",
                user=uid,
                password=pwd,
                database="zoho",
                connect_timeout=5,
            )
            return conn
        except Exception:
            # 在診所端建議把這個 print 拿掉，或寫入 log 檔，避免使用者看到錯誤訊息
            return None

    # 取得本機ip
    def _get_ip_address(self, pc_name):
        local_ip = "127.0.0.1"
        try:
            # 建立一個 UDP socket，不需要真的連通，只是為了誘騙系統回傳目前的網卡 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # 這裡可以用任何外部 IP，不會真的傳送資料
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            # 如果完全沒網路，就抓基本的 hostname IP
            try:
                local_ip = socket.gethostbyname(pc_name)
            except Exception:
                pass

        return local_ip
