# -*- coding: UTF-8 -*-


import configparser
import datetime
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMessageBox

from libs import db_utils, nhi_utils, system_utils


# 系統設定 2018.03.19
class Backup(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Backup, self).__init__(parent)
        self.database = args[0]
        self.system_settings = args[1]
        self.parent = parent

        self._set_ui()

        if self.system_settings.field("使用docker") == "Y":
            self.use_docker = True
        else:
            self.use_docker = False

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _set_ui(self):
        system_utils.center_window(self)

    def start_backup(self):
        self._default_backup()
        try:
            self._external_backup()
        except Exception:
            pass

    def _default_backup(self):
        if self.system_settings.field("資料路徑") == "不備份":
            return

        backup_dir = nhi_utils.get_dir(self.system_settings, "備份路徑")
        if backup_dir in ["", None]:
            return

        self._backup_files(backup_dir)

    def _external_backup(self):
        backup_dir = self.system_settings.field("異地備份路徑")
        if backup_dir in ["", None]:
            return

        self._backup_files(backup_dir)

    def _backup_files(self, data_dir):
        backup_date = datetime.datetime.today().strftime("%Y-%m-%d")
        backup_path = os.path.join(data_dir, backup_date)

        sql = "SHOW TABLES"
        rows = self.database.select_record(sql)

        backup_list = []
        for row in rows:
            table_name = f"{list(row.values())[0]}.sql"
            backup_list.append([table_name, None])

        max_progress = len(backup_list) + 1

        config = configparser.ConfigParser()
        config.read(self.database.CONFIG_FILE)

        host_name = config["db"]["host"]
        if host_name in ["localhost", "127.0.0.1"]:  # 伺服器每天備份完整資料
            physical_dir = self.system_settings.field("伺服器物理備份路徑")
            if physical_dir not in ["", None]:
                if not os.path.isdir(physical_dir):
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "備份路徑錯誤",
                        '<font size="5" color="red"><b>找不到物理磁碟備份路徑, 無法備份資料.</b></font>',
                        "請重新檢查物理磁碟備份路徑是存在.",
                    )
                else:
                    physical_backup_dir = os.path.join(physical_dir, backup_date)
                    progress_dialog = QtWidgets.QProgressDialog(
                        "系統正在備份資料至物理磁碟，請耐心等候...",
                        "取消",
                        0,
                        max_progress,
                        self,
                    )

                    progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
                    progress_dialog.setValue(0)
                    progress_dialog.show()
                    QApplication.processEvents()

                    version = system_utils.get_mariadb_version(self.database)
                    self._check_backup_path(physical_backup_dir)
                    for i, filename in enumerate(backup_list):
                        try:
                            system_utils.dump_table(
                                self.database,
                                version,
                                physical_backup_dir,
                                filename[0],
                                where_script=None,
                                use_docker=self.use_docker,
                            )
                        except Exception:
                            pass

                        QApplication.processEvents()
                        progress_dialog.setValue(i + 1)

        progress_dialog = QtWidgets.QProgressDialog(
            "系統正在備份大型資料表，可能需要較多的時間，請耐心等候...",
            "取消",
            0,
            max_progress,
            self,
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        progress_dialog.show()
        QApplication.processEvents()

        version = system_utils.get_mariadb_version(self.database)
        self._check_backup_path(backup_path)
        for i, filename in enumerate(backup_list):
            try:
                system_utils.dump_table(
                    self.database,
                    version,
                    backup_path,
                    filename[0],
                    where_script=None,
                    use_docker=self.use_docker,
                )
            except Exception:
                pass

            QApplication.processEvents()
            progress_dialog.setValue(i + 1)

        system_utils.delete_old_backup_folders(data_dir, keep_days=30)
        self._backup_json(backup_path)

        progress_dialog.setValue(max_progress)
        progress_dialog.deleteLater()

        database_dir = self.system_settings.field("伺服器資料來源")
        if datetime.date.today().weekday() == 1 and database_dir not in [
            "",
            None,
        ]:  # 每星期二做伺服器備份
            database_backup_dir = os.path.join(backup_path, "database")
            self._check_backup_path(database_backup_dir)
            system_utils.backup_mariadb(
                self, self.database, database_backup_dir, db_dir=database_dir
            )

    def _backup_json(self, backup_path):
        filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d')}.json"
        full_filename = os.path.join(backup_path, filename)

        case_key_list = self._get_case_key_list()
        db_utils.export_medical_record_to_json(
            self, self.database, full_filename, case_key_list
        )

    def _get_case_key_list(self):
        case_key_list = []

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        sql = f"""
            SELECT CaseKey FROM cases
            WHERE
                DATE(CaseDate) = '{today}'
            ORDER BY CaseKey
        """
        rows = self.database.select_record(sql)
        for row in rows:
            case_key_list.append(row["CaseKey"])

        return case_key_list

    def _check_backup_path(self, backup_path):
        try:
            os.stat(backup_path)
        except Exception:
            os.mkdir(backup_path)
