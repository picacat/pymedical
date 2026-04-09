# -*- coding: UTF-8 -*-

import datetime
import hashlib
import io
import ntpath
import os
import os.path
import shutil
import socket
import stat
import subprocess
import urllib.error
import urllib.request
from os import listdir

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton

from libs import class_utils, string_utils, system_utils, ui_utils, update_utils


# 醫療系統更新
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
        self.git_exe = os.path.join(self.base_path, "PortableGit", "bin", "git.exe")

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
        width = [200, 220, 350, 200]
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

    # 開始更新軟體
    def accepted_button_clicked(self):
        if os.path.exists(self.git_exe) and self.ui.radioButton_auto_update.isChecked():
            self.ui.label_status.setText("正在執行增量更新...")
            self._run_git(["reset", "--hard", "origin/main"])
        else:
            # 原本的 Dropbox / 手動 ZIP 更新邏輯
            self._update_files()

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

    def _update_files(self):
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

    def _prepare_git_engine(self):
        # 如果 git.exe 已經在那裡了，直接通過
        if os.path.exists(self.git_exe):
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

    # 檢查環境
    def _check_environment(self):
        dot_git = os.path.join(self.base_path, ".git")
        repo_url = "https://github.com/picacat/pymedical.git"

        if not os.path.exists(dot_git):
            self.ui.label_status.setText("正在配置更新引擎...")
            self._run_git(["init"])
            self._run_git(["remote", "add", "origin", repo_url])
            self._run_git(["config", "user.email", "clinic@update.local"])
            self._run_git(["config", "user.name", "ClinicUser"])
            self._run_git(["config", "core.autocrlf", "false"])
            self._run_git(["update-index", "--skip-worktree", "pymedical.win32.bat"])

        # 這裡只做 fetch，把雲端資訊抓回來儲存在 FETCH_HEAD
        # 絕對不要在這裡跑 update-ref 或 reset --hard
        self.ui.label_status.setText("正在同步雲端資料...")
        self._run_git(["fetch", "origin", "main"])

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
                ":(exclude)pymedical.win32.bat",
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
        else:
            self.ui.label_status.setText("系統已是最新狀態")
            QMessageBox.information(self, "更新", "系統目前已是最新狀態。")

    def _download_by_dropbox(self):
        dropbox_file = self._download_dropbox_file()

        self._check_files(dropbox_file)
