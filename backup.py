# -*- coding: UTF-8 -*-
"""pymedical 每日備份.

全部改用 mysqldump，不再複製 .MYD/.MYI/.frm 實體檔案。

流程：
    1. 判定資料庫引擎（全 InnoDB / 全 MyISAM / 混合）
    2. 逐表 dump
         - InnoDB：靠 MVCC 不取鎖，只保單表一致
         - MyISAM／混合：取全域讀鎖換跨表一致性；
           取不到鎖時退回 mysqldump 的單表鎖，至少保住單表一致
    3. 逐檔驗證（存在、非空、有 dump 結束標記），通過才覆蓋正式檔
    4. 匯出非資料表物件（資料庫字元集、檢視表、routines、權限）
    5. 匯出當日病歷 JSON（失敗算警告，一定讓人看得到）
    6. 把整個備份資料夾複製到其他備份目標（先進 .tmp，成功才換掉舊的）
    7. 全部成功才清理舊備份，結果寫入 backup_log.json

呼叫方式：
    Backup(parent, database, system_settings).start_backup()
    Backup(parent, database, system_settings).start_backup(unattended=True)
        → 排程觸發用：不開進度視窗、不跳任何對話框，只寫 log。
          隔天啟動時由 check_backup_health() 提醒。

需要 system_utils 提供：get_mariadb_dump(version)、get_mariadb_version(database)、
center_window(widget)、show_message_box(...)
"""

import configparser
import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMessageBox

from libs import db_utils, nhi_utils, system_utils

logger = logging.getLogger(__name__)

# ── 檔名 ───────────────────────────────────────────────────────────────
BACKUP_LOG_FILENAME = "backup_log.json"
MANIFEST_FILENAME = "00_manifest.txt"
SCHEMA_FILENAME = "00_schema.sql"
VIEWS_FILENAME = "zz_views.sql"
ROUTINES_FILENAME = "zz_routines.sql"
GRANTS_FILENAME = "zz_grants.sql"

# 非資料表的物件檔，restore_sql.py 必須認得、不可當成資料表匯入。
# 前綴刻意設計成可排序：00_ 先還原，zz_ 最後還原。
OBJECT_FILENAMES = (
    SCHEMA_FILENAME,
    VIEWS_FILENAME,
    ROUTINES_FILENAME,
    GRANTS_FILENAME,
)

# ── 參數 ───────────────────────────────────────────────────────────────
DUMP_COMPLETE_MARKER = "Dump completed"  # mysqldump 正常結束時的檔尾標記
KEEP_DAYS = 14  # 一般備份保留天數
MONTHLY_KEEP_DAYS = 400  # 每月 1 號的備份額外保留天數
WARN_DAYS = 2  # 超過幾天沒有成功備份就示警
LOCK_WAIT_TIMEOUT = 60  # 取全域讀鎖的等待秒數
LOG_KEEP_RECORDS = 500
DUMP_POLL_SECONDS = 0.2  # 等待 mysqldump 時每隔多久檢查一次取消

# 進度視窗固定尺寸，避免訊息長短造成視窗忽大忽小
PROGRESS_WIDTH = 520
PROGRESS_HEIGHT = 190

# 避免資料在匯出時被轉碼（Big5 舊資料含非法位元組時尤其重要）。
# 還原端必須用相同設定；若 restore_sql.py 尚未確認支援，可暫時改成空清單。
CHARSET_ARGS = ["--default-character-set=binary", "--hex-blob"]

BACKUP_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ENGINE_INNODB = "innodb"
ENGINE_MYISAM = "myisam"
ENGINE_MIXED = "mixed"


class BackupCancelled(Exception):
    """使用者於備份過程中按下取消."""


# ===========================================================================
# 備份日誌（模組層函式，主程式啟動時可直接呼叫）
# ===========================================================================
def read_backup_log(data_dir):
    try:
        with open(os.path.join(data_dir, BACKUP_LOG_FILENAME), encoding="utf-8") as f:
            records = json.load(f)
        return records if isinstance(records, list) else []
    except Exception:
        return []


def append_backup_log(data_dir, record):
    log_file = os.path.join(data_dir, BACKUP_LOG_FILENAME)
    records = [
        r
        for r in read_backup_log(data_dir)
        if not (
            r.get("date") == record.get("date")
            and r.get("label") == record.get("label")
        )
    ]
    records.append(record)
    records = sorted(records, key=lambda r: r.get("date", ""))[-LOG_KEEP_RECORDS:]

    try:
        os.makedirs(data_dir, exist_ok=True)
        tmp_file = f"{log_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=1)
        os.replace(tmp_file, log_file)
    except Exception as error:  # noqa: BLE001
        logger.warning("寫入備份日誌失敗: %s", error)


def last_successful_backup(data_dir):
    """回傳最近一次完全成功的備份日期（datetime.date），沒有則 None."""
    latest = None
    for record in read_backup_log(data_dir):
        if not record.get("ok"):
            continue
        try:
            backup_date = datetime.datetime.strptime(record["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if latest is None or backup_date > latest:
            latest = backup_date
    return latest


def get_backup_dirs(system_settings):
    """回傳所有已設定的備份根目錄（順序同 Backup._get_targets，不檢查存在）."""
    data_dirs = []

    physical_dir = system_settings.field("伺服器物理備份路徑")
    if physical_dir not in ["", None]:
        data_dirs.append(physical_dir)

    backup_dir = nhi_utils.get_dir(system_settings, "備份路徑")
    if backup_dir not in ["", None]:
        data_dirs.append(backup_dir)

    external_dir = system_settings.field("異地備份路徑")
    if external_dir not in ["", None]:
        data_dirs.append(external_dir)

    seen, unique_dirs = set(), []
    for data_dir in data_dirs:
        key = os.path.normcase(os.path.abspath(data_dir))
        if key in seen:
            continue
        seen.add(key)
        unique_dirs.append(data_dir)

    return unique_dirs


def check_backup_health(system_settings, warn_days=WARN_DAYS):
    """主程式啟動時呼叫，回傳 (ok, message).

    任何一個備份目標有近期的成功紀錄就算通過——主要目標可能是
    「伺服器物理備份路徑」而不是「備份路徑」，只看後者會誤報。
    """
    data_dirs = get_backup_dirs(system_settings)
    if not data_dirs:
        return False, "尚未設定任何備份路徑，系統目前沒有任何自動備份。"

    latest = None
    for data_dir in data_dirs:
        found = last_successful_backup(data_dir)
        if found is not None and (latest is None or found > latest):
            latest = found

    if latest is None:
        return False, "找不到任何成功的備份紀錄，請立即檢查備份設定。"

    days = (datetime.date.today() - latest).days
    if days > warn_days:
        return (
            False,
            f"距離上次成功備份已經 {days} 天（{latest:%Y-%m-%d}），請立即檢查備份設定。",
        )

    return True, ""


# ===========================================================================
# 結果物件
# ===========================================================================
class TableResult:
    def __init__(self, name, ok, size=0, error=""):
        self.name = name
        self.ok = ok
        self.size = size
        self.error = error


class TargetResult:
    def __init__(self, label, data_dir):
        self.label = label
        self.data_dir = data_dir
        self.backup_path = ""
        self.ok = False
        self.cancelled = False
        self.tables_total = 0
        self.failed = []  # 資料表失敗 → 致命
        self.warnings = []  # 物件檔／病歷 JSON 失敗 → 警告，不阻擋備份
        self.error = ""
        self.seconds = 0.0

    def to_record(self, backup_date, engine_mode):
        return {
            "date": backup_date,
            "label": self.label,
            "ok": self.ok,
            "cancelled": self.cancelled,
            "path": self.backup_path,
            "engine": engine_mode,
            "tables_total": self.tables_total,
            "tables_failed": len(self.failed),
            "failed": [f"{t.name}: {t.error}" for t in self.failed[:20]],
            "warnings": [f"{t.name}: {t.error}" for t in self.warnings[:20]],
            "error": self.error,
            "seconds": round(self.seconds, 1),
            "finished_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# ===========================================================================
# 系統設定 2018.03.19
# ===========================================================================
class Backup(QtWidgets.QDialog):
    # 同一個行程同時只能有一個備份在跑。備份迴圈裡的 processEvents()
    # 會讓 QTimer 的整點 tick 在備份途中被派送出去，沒有這道防線
    # 就可能再進一次 start_backup，兩個 dump 同時寫同一個目錄。
    _running = False

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.database = args[0]
        self.system_settings = args[1]
        # 注意：不可用 self.parent，會蓋掉 QWidget.parent() 方法
        self._parent = parent

        self._set_ui()

        self.use_docker = self.system_settings.field("使用docker") == "Y"

        config = configparser.ConfigParser()
        config.read(self.database.CONFIG_FILE)
        self._host = config["db"]["host"]
        self._user = config["db"]["user"]
        self._password = config["db"]["password"]
        self._database_name = config["db"]["database"]

        self._version = None
        self._backup_date = ""
        self._engine_mode = ""
        self._progress = None
        self._step = 0
        self._stage_prefix = ""
        self._cancelled = False
        self._global_locked = False
        self._unattended = False

    # 關閉（保留給外部呼叫的介面，不再從 __del__ 觸發）
    def close_all(self):
        pass

    def _set_ui(self):
        system_utils.center_window(self)

    # -------------------------------------------------------------------
    # 主流程
    # -------------------------------------------------------------------
    def start_backup(self, unattended=False):
        """執行完整備份，回傳 True 表示所有目標都成功.

        unattended=True：排程觸發用。不開進度視窗、不跳任何對話框，
        結果只寫 log 與 backup_log.json，凌晨沒人在場也不會卡住那台電腦。
        """
        if Backup._running:
            logger.warning("已有備份正在執行，本次略過")
            return False

        Backup._running = True
        self._unattended = unattended
        try:
            return self._run_backup()
        finally:
            Backup._running = False

    def _run_backup(self):
        self._backup_date = datetime.datetime.today().strftime("%Y-%m-%d")

        table_names, view_names = self._load_object_names()
        if not table_names:
            self._show_error(
                "備份失敗",
                "無法取得資料表清單，本次沒有執行任何備份。",
                "請檢查資料庫連線是否正常。",
            )
            return False

        targets = self._get_targets()
        if not targets:
            self._show_error(
                "沒有備份目標",
                "找不到任何可用的備份路徑，本次沒有執行任何備份。",
                "請到系統設定確認備份路徑、異地備份路徑。",
            )
            return False

        self._version = system_utils.get_mariadb_version(self.database)

        # 只 dump 一次到第一個目標，其餘目標用複製的
        primary_label, primary_dir = targets[0]
        others = targets[1:]

        self._cancelled = False
        self._start_progress()

        results = []
        try:
            primary = self._backup_primary(
                primary_label, primary_dir, table_names, view_names, len(targets)
            )
            results.append(primary)
            if primary.ok:
                results.extend(self._copy_to_others(primary, others, len(targets)))
        finally:
            self._finish_progress()

        for result in results:
            if result.ok:
                self._purge_old_backups(result.data_dir)
            append_backup_log(
                result.data_dir, result.to_record(self._backup_date, self._engine_mode)
            )

        self._report(results, len(targets))
        return len(results) == len(targets) and all(r.ok for r in results)

    # -------------------------------------------------------------------
    # 引擎判定與物件清單
    # -------------------------------------------------------------------
    def _load_object_names(self):
        """回傳 (資料表清單, 檢視表清單)，同時判定整庫引擎模式.

        忽略 ENGINE 為 NULL 的殘骸表（引擎裡沒有實體的表，錯誤 1932）。
        """
        sql = """
            SELECT TABLE_NAME, TABLE_TYPE, ENGINE
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
        """
        try:
            rows = self.database.select_record(sql, (self._database_name,))
        except Exception as error:  # noqa: BLE001
            logger.error("無法取得資料表清單: %s", error)
            return [], []

        table_names, view_names, engines = [], [], set()
        for row in rows:
            name = row["TABLE_NAME"]
            if row["TABLE_TYPE"] == "VIEW":
                view_names.append(name)
                continue
            if row["TABLE_TYPE"] != "BASE TABLE":
                # MariaDB 的 SEQUENCE 也會出現在這裡，不是資料表
                logger.info("略過非資料表物件: %s (%s)", name, row["TABLE_TYPE"])
                continue
            if not row["ENGINE"]:
                logger.warning("略過沒有引擎實體的資料表: %s", name)
                continue
            table_names.append(name)
            engines.add(row["ENGINE"].upper())

        if engines == {"INNODB"}:
            self._engine_mode = ENGINE_INNODB
        elif engines == {"MYISAM"}:
            self._engine_mode = ENGINE_MYISAM
        else:
            self._engine_mode = ENGINE_MIXED

        logger.info(
            "引擎判定 %s，資料表 %d 張、檢視表 %d 個",
            self._engine_mode,
            len(table_names),
            len(view_names),
        )
        return sorted(table_names), sorted(view_names)

    # -------------------------------------------------------------------
    # 備份目標
    # -------------------------------------------------------------------
    def _get_targets(self):
        """回傳 [(標籤, 備份根目錄), ...]，第一個為主要目標."""
        targets = []

        if self._host in ["localhost", "127.0.0.1"]:
            physical_dir = self.system_settings.field("伺服器物理備份路徑")
            if physical_dir not in ["", None]:
                if os.path.isdir(physical_dir):
                    targets.append(("第二磁碟", physical_dir))
                else:
                    self._show_error(
                        "備份路徑錯誤",
                        "找不到第二磁碟備份路徑, 該路徑本次略過.",
                        "請重新檢查備份路徑是否存在.",
                    )

        backup_dir = nhi_utils.get_dir(self.system_settings, "備份路徑")
        if backup_dir not in ["", None]:
            targets.append(("本機備份", backup_dir))

        external_dir = self.system_settings.field("異地備份路徑")
        if external_dir not in ["", None]:
            targets.append(("異地備份", external_dir))

        # 去除重複目錄
        seen, unique_targets = set(), []
        for label, data_dir in targets:
            key = os.path.normcase(os.path.abspath(data_dir))
            if key in seen:
                continue
            seen.add(key)
            unique_targets.append((label, data_dir))

        return unique_targets

    # -------------------------------------------------------------------
    # 主要目標：實際 dump
    # -------------------------------------------------------------------
    def _backup_primary(self, label, data_dir, table_names, view_names, target_count):
        result = TargetResult(label, data_dir)
        result.tables_total = len(table_names)
        result.backup_path = os.path.join(data_dir, self._backup_date)
        started = time.time()

        # 這個階段的步驟數：每張表 1 步，加上物件備份與病歷 JSON 各 1 步
        self._begin_stage(1, target_count, label, len(table_names) + 2)

        try:
            os.makedirs(result.backup_path, exist_ok=True)
        except OSError as error:
            result.error = f"無法建立備份目錄: {error}"
            result.seconds = time.time() - started
            return result

        table_results = []
        object_results = []

        # 純 InnoDB 靠 MVCC：mysqldump 一張表就是一句 SELECT，
        # 該句開始時就固定 read view，單表本身仍然是一致快照。
        # 犧牲的只有跨表一致性（換取備份期間其他站台不被凍住）。
        # MyISAM／混合沒有 MVCC，仍然只能靠全域讀鎖。
        locked = False
        if self._engine_mode != ENGINE_INNODB:
            locked = self._acquire_global_lock(result)
        else:
            logger.info("純 InnoDB，本次不取全域讀鎖（無跨表一致性）")

        try:
            for table_name in table_names:
                self._set_label(f"正在備份 {table_name} ...")
                table_results.append(self._dump_table(result.backup_path, table_name))
                self._advance()

            self._set_label("正在備份資料庫物件 ...")
            object_results = self._dump_objects(result.backup_path, view_names)
            self._advance()
        except BackupCancelled:
            result.cancelled = True
            result.error = "使用者取消備份"
        finally:
            self._release_global_lock(locked, result)

        if not result.cancelled:
            object_results.append(self._backup_json(result.backup_path))
        self._advance()
        self._end_stage()

        result.failed = [t for t in table_results if not t.ok]
        result.warnings = [t for t in object_results if not t.ok]
        self._write_manifest(result.backup_path, label, table_results + object_results)

        # 物件檔（檢視表、routines）與病歷 JSON 失敗不算致命：資料表本身完整，
        # 異地備份仍應照常複製，舊備份也可以照常輪替。
        result.ok = not result.failed and not result.cancelled and not result.error
        result.seconds = time.time() - started
        return result

    def _copy_to_others(self, primary, others, target_count):
        """把主要目標的備份資料夾複製到其他目標，逐檔顯示進度.

        先複製到 <日期>.tmp，全部成功才換掉該目標當日的舊備份。
        直接對正式目錄 rmtree 再複製的話，網路磁碟中途斷線或
        使用者按取消，該目標當天就一份都不剩。
        """
        results = []

        try:
            filenames = sorted(os.listdir(primary.backup_path))
        except OSError as error:
            logger.error("無法列出備份目錄: %s", error)
            filenames = []

        for offset, (label, data_dir) in enumerate(others):
            result = TargetResult(label, data_dir)
            result.tables_total = primary.tables_total
            result.backup_path = os.path.join(data_dir, self._backup_date)
            started = time.time()

            self._begin_stage(offset + 2, target_count, label, len(filenames))

            staging_path = f"{result.backup_path}.tmp"
            try:
                if os.path.isdir(staging_path):
                    shutil.rmtree(staging_path)
                os.makedirs(staging_path, exist_ok=True)

                for filename in filenames:
                    self._check_cancelled()
                    self._set_label(f"正在複製 {filename} ...")

                    source = os.path.join(primary.backup_path, filename)
                    destination = os.path.join(staging_path, filename)
                    if os.path.isdir(source):
                        shutil.copytree(source, destination)
                    else:
                        shutil.copy2(source, destination)
                    self._advance()

                if os.path.isdir(result.backup_path):
                    shutil.rmtree(result.backup_path)
                os.rename(staging_path, result.backup_path)
                result.ok = True
            except BackupCancelled:
                result.cancelled = True
                result.error = "使用者取消備份"
            except Exception as error:  # noqa: BLE001
                result.error = f"複製備份失敗: {error}"
                logger.error("複製備份到 %s 失敗: %s", label, error)
            finally:
                if not result.ok and os.path.isdir(staging_path):
                    try:
                        shutil.rmtree(staging_path)
                    except OSError:
                        pass

            self._end_stage()
            result.seconds = time.time() - started
            results.append(result)

            if result.cancelled:
                break

        return results

    # -------------------------------------------------------------------
    # mysqldump
    # -------------------------------------------------------------------
    def _run_mysqldump(self, extra_args, out_filename):
        """執行 mysqldump 並把輸出寫進 out_filename，途中可取消.

        失敗時丟 subprocess.CalledProcessError（stderr 帶回真正原因），
        使用者取消時丟 BackupCancelled。呼叫端負責清理 out_filename。
        """
        # InnoDB：靠 MVCC，完全不鎖。
        # MyISAM／混合：外層已取得全域讀鎖時子行程不必再鎖；
        #               沒取到鎖就退回 mysqldump 預設的單表鎖，
        #               至少保住單表一致性（--skip-lock-tables 會連這個都沒有）。
        if self._engine_mode == ENGINE_INNODB or self._global_locked:
            lock_args = ["--skip-lock-tables"]
        else:
            lock_args = ["--lock-tables"]

        common_args = [
            f"--host={self._host}",
            f"--user={self._user}",
            *CHARSET_ARGS,
            *lock_args,
            *extra_args,
        ]

        if self.use_docker:
            # 不可加 -t：GUI 程式沒有 TTY，且會在輸出中混入 \r
            args = [
                "docker",
                "exec",
                "-e",
                "MYSQL_PWD",
                "mariadb-db-service",
                "mariadb-dump",
                *common_args,
            ]
        else:
            args = [system_utils.get_mariadb_dump(self._version), *common_args]

        # 密碼走環境變數，不出現在命令列（工作管理員／ps 看不到）
        env = os.environ.copy()
        env["MYSQL_PWD"] = self._password

        kwargs = {"env": env}
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo

        # stderr 導到暫存檔而不是 PIPE：不必邊跑邊讀，也不會因為
        # 管線塞滿而卡死；跑完再一次讀回來。
        with open(out_filename, "wb") as out_file, tempfile.TemporaryFile() as err_file:
            process = subprocess.Popen(args, stdout=out_file, stderr=err_file, **kwargs)
            while True:
                try:
                    process.wait(timeout=DUMP_POLL_SECONDS)
                    break
                except subprocess.TimeoutExpired:
                    if self._is_cancel_requested():
                        # docker 模式下只殺得掉本機的 docker exec，
                        # 容器裡的 mariadb-dump 會自己跑完才結束
                        process.kill()
                        process.wait()
                        raise BackupCancelled()
                    if self._progress is not None:
                        QApplication.processEvents()
            err_file.seek(0)
            stderr = err_file.read()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, args, output=None, stderr=stderr
            )

    @staticmethod
    def _remove_file(full_filename):
        try:
            if os.path.isfile(full_filename):
                os.remove(full_filename)
        except OSError:
            pass

    def _dump_and_verify(self, name, full_filename, extra_args):
        """dump 到暫存檔，驗證通過才覆蓋正式檔.

        直接寫正式檔的話，同一天重跑而這次失敗，會先把上一份好的
        備份截斷成 0 bytes——舊的沒了、新的也沒生出來。
        """
        tmp_filename = f"{full_filename}.tmp"

        try:
            self._run_mysqldump(extra_args, tmp_filename)
        except BackupCancelled:
            self._remove_file(tmp_filename)
            raise
        except subprocess.CalledProcessError as error:
            self._remove_file(tmp_filename)
            # 關鍵：mysqldump 真正的原因在 stderr，不在例外的字串裡
            stderr = (error.stderr or b"").decode("utf-8", errors="ignore").strip()
            return TableResult(
                name, False, 0, stderr or f"exit status {error.returncode}"
            )
        except OSError as error:
            self._remove_file(tmp_filename)
            return TableResult(name, False, 0, f"無法執行 mysqldump: {error}")

        verified = self._verify_dump_file(name, tmp_filename)
        if not verified.ok:
            self._remove_file(tmp_filename)
            return verified

        try:
            os.replace(tmp_filename, full_filename)
        except OSError as error:
            self._remove_file(tmp_filename)
            return TableResult(name, False, verified.size, f"無法覆寫備份檔: {error}")

        return verified

    def _dump_table(self, backup_path, table_name):
        self._check_cancelled()

        filename = f"{table_name}.sql"
        return self._dump_and_verify(
            filename,
            os.path.join(backup_path, filename),
            [self._database_name, table_name],
        )

    def _dump_object_file(self, name, backup_path, arg_variants):
        """依序嘗試多組參數，第一組成功就採用。

        舊版 mysqldump 對 --events / --routines 的支援程度不一，
        失敗時降級重試比直接放棄好。全部失敗時正式檔不會被動到
        （暫存檔已在 _dump_and_verify 裡清掉）。
        """
        full_filename = os.path.join(backup_path, name)
        last_error = ""

        for args in arg_variants:
            result = self._dump_and_verify(name, full_filename, args)
            if result.ok:
                return result
            last_error = result.error
            logger.warning("%s 匯出失敗（%s），嘗試下一組參數", name, last_error)

        return TableResult(name, False, 0, last_error)

    def _count_routines_and_events(self):
        """回傳 (routine 數, event 數)；查不到時回傳 -1 代表無法判斷."""
        try:
            rows = self.database.select_record(
                "SELECT COUNT(*) AS c FROM information_schema.ROUTINES "
                "WHERE ROUTINE_SCHEMA = %s",
                (self._database_name,),
            )
            routines = int(rows[0]["c"]) if rows else 0
        except Exception:  # noqa: BLE001
            routines = -1  # 查不到就當作可能有，照樣嘗試匯出

        try:
            rows = self.database.select_record(
                "SELECT COUNT(*) AS c FROM information_schema.EVENTS "
                "WHERE EVENT_SCHEMA = %s",
                (self._database_name,),
            )
            events = int(rows[0]["c"]) if rows else 0
        except Exception:  # noqa: BLE001
            events = 0  # 舊版伺服器沒有 EVENTS 檢視表

        return routines, events

    def _dump_objects(self, backup_path, view_names):
        """匯出逐表 dump 抓不到的東西：資料庫字元集、檢視表、routines、權限.

        這些都不是病歷資料本身，失敗只當警告處理。
        """
        results = []

        # 1. CREATE DATABASE（保住資料庫層級的字元集與 collation）
        try:
            self._dump_schema(backup_path)
            results.append(
                self._verify_text_file(
                    SCHEMA_FILENAME, os.path.join(backup_path, SCHEMA_FILENAME)
                )
            )
        except Exception as error:  # noqa: BLE001
            results.append(TableResult(SCHEMA_FILENAME, False, 0, str(error)))

        # 2. 檢視表（逐表 dump 的 BASE TABLE 過濾會漏掉）
        #    檢視表沒有資料，不需要任何鎖；放在後面會蓋掉 common_args 的鎖參數
        if view_names:
            results.append(
                self._dump_object_file(
                    VIEWS_FILENAME,
                    backup_path,
                    [["--skip-lock-tables", self._database_name, *view_names]],
                )
            )

        # 3. stored procedure / function / event
        #
        # 沒有任何 routine 與 event 時直接略過——大多數診所的資料庫
        # 都是這種情況，何必為了一個空檔案去踩舊版 mysqldump 的雷。
        routines, events = self._count_routines_and_events()
        if routines == 0 and events == 0:
            logger.info("資料庫沒有 routine 與 event，略過 %s", ROUTINES_FILENAME)
        else:
            base_args = [
                "--routines",
                "--no-create-info",
                "--no-data",
                "--no-create-db",
                "--skip-triggers",  # triggers 已隨各資料表匯出
                self._database_name,
            ]
            # 舊版 mysqldump（例如 mysqldump50）對新版伺服器的
            # mysql.event / mysql.proc 可能讀不動，逐步降級重試
            variants = []
            if events != 0:
                variants.append(["--events", *base_args])
            variants.append(base_args)
            results.append(
                self._dump_object_file(ROUTINES_FILENAME, backup_path, variants)
            )

        # 4. 使用者權限（權限不足時略過，不算失敗）
        try:
            self._dump_grants(backup_path)
        except Exception as error:  # noqa: BLE001
            logger.warning("略過使用者權限備份: %s", error)

        return results

    def _dump_schema(self, backup_path):
        """mysqldump 不加 --databases 時不會產生 CREATE DATABASE，要自己補."""
        rows = self.database.select_record(
            f"SHOW CREATE DATABASE `{self._database_name}`"
        )
        if not rows:
            raise RuntimeError("SHOW CREATE DATABASE 沒有回傳結果")

        create_sql = rows[0].get("Create Database") or rows[0].get("create database")
        if not create_sql:
            raise RuntimeError("無法解析 SHOW CREATE DATABASE 的結果")

        create_sql = create_sql.replace(
            "CREATE DATABASE ", "CREATE DATABASE IF NOT EXISTS ", 1
        )

        content = "\n".join(
            [
                "-- pymedical 資料庫層級設定備份",
                f"-- database: {self._database_name}",
                "",
                f"{create_sql};",
                "",
                f"USE `{self._database_name}`;",
                "",
                "-- Dump completed",
                "",
            ]
        )
        self._write_text_atomic(os.path.join(backup_path, SCHEMA_FILENAME), content)

    def _dump_grants(self, backup_path):
        rows = self.database.select_record(
            "SELECT User, Host FROM mysql.user ORDER BY User, Host"
        )

        lines = ["-- 使用者權限備份（僅供參考，還原時請人工確認）", ""]
        for row in rows:
            user_name, host_name = row["User"], row["Host"]
            lines.append(f"-- {user_name}@{host_name}")
            try:
                # 帳號／主機名含單引號時先跳脫，避免整句 SQL 壞掉
                safe_user = str(user_name).replace("'", "''")
                if user_name == "PUBLIC":
                    # MariaDB 10.11+ 內建的 PUBLIC 角色：語法不帶引號、不帶 host
                    sql = "SHOW GRANTS FOR PUBLIC"
                elif host_name in ("", None):
                    # 角色（role）的 host 是空字串，不能寫成 'name'@''
                    sql = f"SHOW GRANTS FOR '{safe_user}'"
                else:
                    safe_host = str(host_name).replace("'", "''")
                    sql = f"SHOW GRANTS FOR '{safe_user}'@'{safe_host}'"
                grant_rows = self.database.select_record(sql)
                for grant_row in grant_rows:
                    lines.append(f"-- {list(grant_row.values())[0]};")
            except Exception as error:  # noqa: BLE001
                lines.append(f"--   無法取得: {error}")
            lines.append("")

        lines.append("-- Dump completed")
        lines.append("")
        self._write_text_atomic(
            os.path.join(backup_path, GRANTS_FILENAME), "\n".join(lines)
        )

    @staticmethod
    def _write_text_atomic(full_filename, content):
        """寫暫存檔再換名，不讓半截檔案蓋掉上一份."""
        tmp_filename = f"{full_filename}.tmp"
        try:
            with open(tmp_filename, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_filename, full_filename)
        except Exception:
            Backup._remove_file(tmp_filename)
            raise

    # -------------------------------------------------------------------
    # 驗證
    # -------------------------------------------------------------------
    def _verify_dump_file(self, name, full_filename):
        """檢查 dump 檔是否完整：存在、非空、檔尾有 mysqldump 的結束標記."""
        if not os.path.isfile(full_filename):
            return TableResult(name, False, 0, "檔案不存在")

        try:
            size = os.path.getsize(full_filename)
        except OSError as error:
            return TableResult(name, False, 0, f"無法取得檔案大小: {error}")

        if size == 0:
            return TableResult(name, False, 0, "檔案為空（磁碟已滿或 dump 失敗）")

        try:
            with open(full_filename, "rb") as f:
                f.seek(max(0, size - 2048))
                tail = f.read().decode("utf-8", errors="ignore")
        except OSError as error:
            return TableResult(name, False, size, f"無法讀取檔案: {error}")

        if DUMP_COMPLETE_MARKER not in tail:
            return TableResult(name, False, size, "檔案不完整（缺少 dump 結束標記）")

        return TableResult(name, True, size, "")

    def _verify_text_file(self, name, full_filename):
        if not os.path.isfile(full_filename) or os.path.getsize(full_filename) == 0:
            return TableResult(name, False, 0, "檔案不存在或為空")
        return TableResult(name, True, os.path.getsize(full_filename), "")

    def _write_manifest(self, backup_path, label, table_results):
        ok_count = sum(1 for t in table_results if t.ok)
        total_size = sum(t.size for t in table_results)

        lines = [
            f"# 備份目標   : {label}",
            f"# 備份日期   : {self._backup_date}",
            f"# 完成時間   : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
            f"# 資料庫     : {self._database_name}",
            f"# 引擎       : {self._engine_mode}",
            f"# 全域讀鎖   : {'是' if self._engine_mode != ENGINE_INNODB else '否（InnoDB 靠 MVCC）'}",
            f"# MariaDB    : {self._version}",
            f"# 項目       : {ok_count} / {len(table_results)} 成功",
            f"# 總計大小   : {total_size:,} bytes",
            "#",
            "# file\tbytes\tstatus\tmessage",
        ]
        for item in table_results:
            status = "OK" if item.ok else "FAIL"
            lines.append(f"{item.name}\t{item.size}\t{status}\t{item.error}")

        try:
            self._write_text_atomic(
                os.path.join(backup_path, MANIFEST_FILENAME), "\n".join(lines) + "\n"
            )
        except Exception as error:  # noqa: BLE001
            logger.warning("寫入 manifest 失敗: %s", error)

    # -------------------------------------------------------------------
    # 全域讀鎖（保證跨表一致性）
    # -------------------------------------------------------------------
    def _acquire_global_lock(self, result):
        """取不到鎖時回傳 False 並記入 result.error；
        逐表 dump 會自動退回單表鎖，備份仍會做完，但整份標記為失敗以引起注意。"""
        try:
            self.database.exec_sql(
                f"SET SESSION lock_wait_timeout = {LOCK_WAIT_TIMEOUT}"
            )
        except Exception:  # noqa: BLE001
            pass  # 舊版沒有這個變數就算了

        try:
            self.database.exec_sql("FLUSH TABLES WITH READ LOCK")
            self._global_locked = True
            logger.info("已取得全域讀鎖")
            return True
        except Exception as error:  # noqa: BLE001
            self._global_locked = False
            logger.error("無法取得全域讀鎖，本次備份沒有跨表一致性: %s", error)
            result.error = f"無法取得全域讀鎖: {error}"
            return False

    def _release_global_lock(self, locked, result):
        """關鍵：取消或任何例外都必須解鎖，否則整個資料庫停在唯讀."""
        if not locked:
            return
        try:
            self.database.exec_sql("UNLOCK TABLES")
            self._global_locked = False
            logger.info("已釋放全域讀鎖")
        except Exception as error:  # noqa: BLE001
            logger.critical("UNLOCK TABLES 失敗，資料庫可能仍為唯讀: %s", error)
            result.error = f"解鎖失敗，資料庫可能仍為唯讀: {error}"

    # -------------------------------------------------------------------
    # 當日病歷 JSON
    # -------------------------------------------------------------------
    def _backup_json(self, backup_path):
        """匯出當日病歷 JSON；失敗只算警告，但必須讓人看得到.

        資料庫整個救不回來時這是最後一道保險，不能靜靜地失敗。
        今天沒有病歷是正常情況，不算失敗。
        """
        self._set_label("正在匯出當日病歷 JSON ...")
        filename = f"backup_{datetime.datetime.now():%Y%m%d}.json"
        full_filename = os.path.join(backup_path, filename)

        try:
            case_key_list = self._get_case_key_list()
        except Exception as error:  # noqa: BLE001
            logger.error("查詢當日病歷失敗: %s", error)
            return TableResult(filename, False, 0, f"查詢當日病歷失敗: {error}")

        if not case_key_list:
            logger.info("今日沒有病歷，略過 %s", filename)
            return TableResult(filename, True, 0, "今日無病歷，略過")

        try:
            db_utils.export_medical_record_to_json(
                self, self.database, full_filename, case_key_list
            )
        except Exception as error:  # noqa: BLE001
            logger.error("當日病歷 JSON 匯出失敗: %s", error)
            return TableResult(filename, False, 0, str(error))

        return self._verify_text_file(filename, full_filename)

    def _get_case_key_list(self):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        sql = """
            SELECT CaseKey FROM cases
            WHERE DATE(CaseDate) = %s
            ORDER BY CaseKey
        """
        rows = self.database.select_record(sql, (today,))
        return [row["CaseKey"] for row in rows]

    # -------------------------------------------------------------------
    # 舊備份清理：一般保留 KEEP_DAYS 天，每月 1 號的多留 MONTHLY_KEEP_DAYS 天
    # -------------------------------------------------------------------
    def _purge_old_backups(self, data_dir):
        try:
            entries = os.listdir(data_dir)
        except OSError:
            return

        today = datetime.date.today()
        keep, remove = [], []

        for entry in entries:
            if not BACKUP_DIR_PATTERN.match(entry):
                continue
            full_path = os.path.join(data_dir, entry)
            if not os.path.isdir(full_path):
                continue

            try:
                folder_date = datetime.datetime.strptime(entry, "%Y-%m-%d").date()
            except ValueError:
                continue

            age = (today - folder_date).days
            if age <= KEEP_DAYS or (folder_date.day == 1 and age <= MONTHLY_KEEP_DAYS):
                keep.append(full_path)
            else:
                remove.append(full_path)

        if not keep:  # 保險：絕不刪到一份都不剩
            return

        for full_path in remove:
            try:
                shutil.rmtree(full_path)
                logger.info("刪除舊備份: %s", full_path)
            except Exception as error:  # noqa: BLE001
                logger.warning("刪除舊備份 %s 失敗: %s", full_path, error)

    # -------------------------------------------------------------------
    # 進度與訊息
    # -------------------------------------------------------------------
    def _start_progress(self):
        self._step = 0
        self._stage_prefix = ""

        if self._unattended:  # 排程觸發：沒人在場，不能開 modal 視窗
            self._progress = None
            return

        # parent 用真正的主視窗；self 這個 QDialog 從來不顯示，
        # 座標永遠停在 (0, 0)，用它當 parent 會讓進度視窗跑到螢幕左上角
        owner = self._parent if self._parent is not None else self

        dialog = QtWidgets.QProgressDialog("", "取消", 0, 1, owner)
        dialog.setWindowTitle("資料備份")
        dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)  # 進度到頂時不要自己關掉
        dialog.setAutoReset(False)  # 也不要自己歸零
        dialog.setSizeGripEnabled(False)

        # 換上固定寬度、可折行的標籤：setLabelText 就不會再撐大視窗
        label = QtWidgets.QLabel()
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setFixedWidth(PROGRESS_WIDTH - 40)
        label.setMinimumHeight(70)
        dialog.setLabel(label)  # QProgressDialog 接管 label 的所有權

        dialog.setFixedSize(PROGRESS_WIDTH, PROGRESS_HEIGHT)

        self._progress = dialog
        self._center_window(dialog)  # 先定位再顯示，避免出現位移閃爍

        dialog.setValue(0)
        self._set_label("系統正在備份資料，請耐心等候...")
        dialog.show()
        QApplication.processEvents()

    def _begin_stage(self, index, count, label, total_steps):
        """每個備份目標各自從 0 跑到 100%，不要把所有目標擠在同一條進度條."""
        self._stage_prefix = f"({index}/{count}) {label}"
        self._step = 0
        if self._progress is not None:
            self._progress.setRange(0, max(1, total_steps))
            self._progress.setValue(0)
            QApplication.processEvents()

    def _end_stage(self):
        if self._progress is not None:
            self._progress.setValue(self._progress.maximum())
            QApplication.processEvents()

    def _finish_progress(self):
        if self._progress is None:
            return
        self._progress.close()
        self._progress.deleteLater()
        self._progress = None
        self._stage_prefix = ""

    def _advance(self, steps=1):
        self._step += steps
        if self._progress is not None:
            self._progress.setValue(min(self._step, self._progress.maximum()))
            QApplication.processEvents()

    def _set_label(self, text):
        if self._progress is not None:
            if self._stage_prefix:
                self._progress.setLabelText(f"{self._stage_prefix}\n{text}")
            else:
                self._progress.setLabelText(text)
            QApplication.processEvents()

    def _is_cancel_requested(self):
        """只回報狀態、不丟例外，給 dump 等待迴圈輪詢用."""
        # 用自己的旗標記住取消狀態：setRange/setValue 之後
        # QProgressDialog.wasCanceled() 的結果不一定保留
        if self._cancelled:
            return True
        if self._progress is not None and self._progress.wasCanceled():
            self._cancelled = True
            return True
        return False

    def _check_cancelled(self):
        if self._is_cancel_requested():
            raise BackupCancelled()

    def _center_window(self, widget):
        """把視窗置中到主視窗；主視窗不可用時退回螢幕置中."""
        geometry = None

        parent = widget.parentWidget()
        if parent is not None and parent.isVisible():
            geometry = parent.frameGeometry()

        if geometry is None:
            screen = QApplication.primaryScreen()
            if screen is not None:
                geometry = screen.availableGeometry()

        if geometry is None:
            return

        center = geometry.center()
        widget.move(
            center.x() - PROGRESS_WIDTH // 2,
            center.y() - PROGRESS_HEIGHT // 2,
        )

    def _show_error(self, title, message, hint):
        if self._unattended:
            logger.error("%s: %s %s", title, message, hint.replace("\n", " / "))
            return

        system_utils.show_message_box(
            QMessageBox.Critical,
            title,
            f'<font size="5" color="red"><b>{message}</b></font>',
            hint,
        )

    def _report(self, results, target_count):
        """成功時安靜結束；資料表失敗跳紅字，物件檔失敗只提醒.

        unattended 模式一律只寫 log，通知交給隔天啟動時的 check_backup_health()。
        """
        if self._unattended:
            for result in results:
                logger.info(
                    "備份結果 %s: ok=%s 失敗表=%d 警告=%d %s",
                    result.label,
                    result.ok,
                    len(result.failed),
                    len(result.warnings),
                    result.error,
                )
            if len(results) < target_count:
                logger.error("主要目標失敗，其餘備份路徑本次未複製")
            return

        problems = [r for r in results if not r.ok]
        warned = [r for r in results if r.ok and r.warnings]

        # 全部順利：安靜結束，不打擾櫃檯
        if not problems and not warned and len(results) == target_count:
            return

        # 資料表都完整，只是物件檔／病歷 JSON 有問題 → 提醒即可，備份仍然有效
        if not problems and len(results) == target_count:
            lines = []
            for result in warned:
                for item in result.warnings:
                    lines.append(f"　- {item.name}：{item.error}")
            system_utils.show_message_box(
                QMessageBox.Warning,
                "備份完成（部分項目未備份）",
                '<font size="5"><b>病歷資料表已完整備份，'
                "但部分項目備份失敗。</b></font>",
                "以下項目未納入本次備份，不影響資料表的還原：\n"
                + "\n".join(lines)
                + "\n\n請在方便時通知系統維護人員檢查。",
            )
            return

        lines = []
        for result in problems:
            if result.cancelled:
                lines.append(f"● {result.label}：使用者取消，本次備份不完整。")
            if result.error:
                lines.append(f"● {result.label}：{result.error}")
            if result.failed:
                lines.append(
                    f"● {result.label}：{len(result.failed)} / {result.tables_total} 個資料表失敗"
                )
                for item in result.failed[:10]:
                    lines.append(f"　　- {item.name}：{item.error}")
                if len(result.failed) > 10:
                    lines.append(f"　　- 其餘 {len(result.failed) - 10} 項請見備份日誌")

        for result in results:
            for item in result.warnings:
                lines.append(f"● {result.label}：{item.name} 未備份（{item.error}）")

        if len(results) < target_count:
            lines.append("● 主要目標失敗，其餘備份路徑本次未複製。")

        self._show_error(
            "備份未完成",
            "本次備份沒有全部完成，舊備份已保留未刪除。",
            "\n".join(lines) + "\n\n請立即通知系統維護人員處理。",
        )
