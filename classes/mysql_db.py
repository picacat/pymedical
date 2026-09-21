"""MySQL/MariaDB 資料庫存取層。

本版目標：同一份程式碼在 MyISAM 與 InnoDB 客戶端都能安全運作，且在
「轉換到一半」的混合引擎資料庫上也不會比轉換前更脆弱。

設計原則
--------
客戶端會有一段長期的混合期（部分診所已轉 InnoDB、部分仍是 MyISAM，
而且同一個資料庫裡可能兩種都有），因此所有 InnoDB 導向的新行為都必須
在 MyISAM 上退化成無害的 no-op：

  * autocommit 明確設為 True
      InnoDB 預設 REPEATABLE READ，連線第一次 SELECT 就建立快照，在
      commit 之前所有後續 SELECT 都看同一份快照。候診名單、看診清單、
      Kiosk 這類「只讀不寫」的連線可能開著數小時從不 commit，於是永遠
      看不到別台存進去的資料。MyISAM 沒有 MVCC，本來就沒有這個問題，
      所以這項改動對 MyISAM 客戶完全無影響。

  * 資料引擎一律自動判定（_detect_engine）
      引擎不從設定檔讀取，而是依目前資料表判定。設定檔會說謊——conf
      寫著 InnoDB 而資料表其實還是 MyISAM（或反過來）時，新資料表會被
      建成另一種引擎，形成難以察覺的混合引擎資料庫。資料庫現況不會
      說謊，客戶跑完引擎轉換後也不需要再去改任何設定檔。
      判定必須在連上目標資料庫之後執行。

  * 交易深度計數（_tx_depth）與中止旗標（_tx_aborted）
      insert/update/delete/exec_sql 只有「不在明確交易中」時才自動提交。
      巢狀交易中內層回滾後，外層會被標記為中止：後續任何語句與最後的
      commit() 都會拋出 TransactionAborted，而不是讓外層在交易早已結束
      的連線上繼續寫入、最後留下半套資料。

  * 交易中禁止自動重連
      重連會靜默回滾未提交的變更，讓後續語句在新交易裡繼續跑，結果是
      半套資料且沒有任何錯誤。改為拋出 TransactionInterrupted。MyISAM
      客戶只要沒用交易就永遠不會觸發。

  * 死結重試（run_transaction）
      MyISAM 是表級鎖不會死結，InnoDB 是行級鎖會。重試必須以「整個交易」
      為單位，單句重試在交易中會產生不一致。MyISAM 上這段是死碼。

  * kill_sleep_connections 排除持有交易的連線
      MyISAM 的 Sleep 連線什麼都沒抓著，殺掉無害；InnoDB 的 Sleep 連線
      可能正持有未提交的交易與一批 row lock。改為排除 INNODB_TRX 中的
      執行緒，並只處理本使用者、本資料庫的連線。

  * 隔離等級 READ COMMITTED（條件式）
      對「讀出來→使用者編輯→寫回去」的桌面應用比 REPEATABLE READ 合理，
      也與 PostgreSQL 的預設一致。MyISAM 完全忽略隔離等級。
      注意：binlog_format=STATEMENT 搭配 READ COMMITTED 會讓 InnoDB 寫入
      直接報錯，因此套用前會先檢查 binlog 狀態，不符合就維持預設。

前一次修訂（2026-09）
---------------------
  1. 連線層級例外的判定範圍放寬（_is_connection_error）。
  2. 各方法 finally 區塊不再呼叫 is_connected()。
  3. DDL 不再預防性地擊殺閒置連線（_exec_ddl_with_lock_retry），改為先把
     session 的 lock_wait_timeout 壓到 10 秒，真的等不到才清理並重試。
  4. kill_sleep_connections 每次擊殺都寫明 Id / User / Host / Time。

本次修訂（2026-09-21）——全部針對錯誤 1205 的穩定性
---------------------------------------------------
背景：客戶端陸續回報 `1205 Lock wait timeout exceeded`，發生在
insert_correct_ic_card、update_diagnosis_data 這類一般寫入上，而且多半
出現在被 _detect_engine() 判定為 MyISAM 的客戶。1205 有兩個來源，必須
分清楚，因為它們的成因與對策完全不同：

  (a) metadata lock 逾時（lock_wait_timeout，MariaDB 預設 86400 秒）
      與儲存引擎無關。MyISAM 的 INSERT/UPDATE 一樣要先取得 MDL，別台在
      跑 ALTER TABLE 時就會卡住。MyISAM 沒有 online DDL，ALTER 是整表
      複製，大表要好幾分鐘，卡住的時間遠比 InnoDB 長。

  (b) InnoDB 行鎖逾時（innodb_lock_wait_timeout，預設 50 秒）
      只有 InnoDB 會發生。被判定為 MyISAM 的資料庫照樣可能出現——
      _detect_engine() 的規則是「只要還有一張 MyISAM 就算 MyISAM」，
      所以「MyISAM 客戶」很可能其實是轉換到一半的混合引擎資料庫，
      cases 這種大表早就已經是 InnoDB 了。

改動內容：

  1. lock_wait_timeout 不再洩漏到整條連線（_ddl_lock_timeout）。
     這是上一版留下的 bug，也是 (a) 類 1205 變成常態的直接原因。
     舊的 _set_ddl_lock_timeout() 設了 session 變數就再也不還原，還用
     旗標確保只設一次，等於這條連線後續「每一句」INSERT/UPDATE 都只等
     10 秒。看診站一開機做完結構檢查，接下來一整天只要撞上別台的 ALTER
     就會在 10 秒後拋 1205；改動之前同樣的情境只會慢一下然後成功。
     改為 context manager：進入 DDL 前壓低、離開時還原成原值。

  2. 交易外的 1205 / 1213 自動重試（_run_with_lock_retry）。
     過去刻意不做語句層級重試，理由是「execute 到一半斷線時語句可能已
     送達，重送會重複套用」——那個顧慮對「斷線」成立，對 1205 / 1213
     不成立：伺服器明確回報「等不到鎖，我沒有執行」，autocommit 連線上
     該句是完整回滾的，累加型的 UPDATE（診察費加成、初診加計 A90）重送
     也不會重複。因此 select/insert/update/delete/exec_sql 在「不在明確
     交易中」時都會退避重試，把偶發的鎖競爭從「存檔失敗」降級成「慢了
     幾百毫秒」。交易中一律不重試，仍由 run_transaction 以整批為單位處理。

  3. 1205 / 1213 用盡重試後抓現場（capture_lock_diagnostics）。
     錯誤已經發生，成本不重要。會記下兩個 timeout 的實際值、INNODB_TRX
     中的交易、本資料庫超過 5 秒的連線，以及 SHOW ENGINE INNODB STATUS
     的 TRANSACTIONS 區段，寫進 log/lock_timeout.log，同時併進例外訊息
     讓 crash report 的「異常值」直接帶出來。
     判讀重點：INNODB_TRX 裡 trx_started 很早、trx_state=RUNNING 而
     trx_query 是空的那一筆，就是「開著交易卻停在使用者互動或健保署
     回應上」的兇手，據此回頭修那個 transaction() 區塊。

  4. select_record 遇到鎖逾時改為拋出例外，不再回傳空 list。
     【行為變更，請留意】原本重試失敗只印訊息並回傳 []，呼叫端會把
     「查不到」與「鎖住了」混為一談——在病歷系統裡，這會讓程式以為沒有
     資料而繼續往下走，比直接報錯危險得多。連線層級失敗維持回傳 []
     （沿用舊行為，不在本次一起改）。

  5. 新增 table_engine()：查單張表的實際引擎。
     混合引擎資料庫中 db_engine() 只能告訴你「還沒轉完」，真正決定鎖
     行為的是出事那張表自己的引擎。crash report 請一併記錄。

  6. DDL 被擋住時的清理門檻從 60 秒提高到 300 秒
     （DDL_KILL_SLEEP_THRESHOLD）。看診站等健保署回應最長 30 秒，期間
     連線是 Sleep 狀態且沒有開任何 InnoDB 交易，不在保護名單內；門檻
     60 秒對它而言太近，抬到 300 秒可以完全避開誤傷，同時仍能清掉真正
     放著不管的連線。

刻意不改的項目
--------------
連線 collation 維持 {charset}_general_ci。改成 unicode_ci 會改變字串比較
與排序語意，且 MyISAM 與 InnoDB 客戶一律受影響，必須搭配所有資料表一起
ALTER，屬於獨立的一次性任務，不混在本次改動中。

innodb_lock_wait_timeout 維持伺服器預設（50 秒），不由程式調整。調低會
讓失敗變多，調高會讓使用者乾等，兩邊都不比「重試 + 抓現場」好；真正該
修的是那個長時間持有鎖的交易，而不是這個數字。

斷線（非鎖）情況下的 exec_sql 仍然不重試。get_cursor() 已經會在「建立
cursor」這一步自動重連；若是 execute() 執行到一半斷線，語句可能已經送達
伺服器只是回應沒收到，重送會變成重複套用。維持丟出例外由呼叫端處理。

（已知現況：restore_gui.py 以 utf8mb4_unicode_ci 建表，與此處的
general_ci 不一致。兩邊應擇一統一，但那是另一項獨立作業。）
"""

import configparser
import os
import re
import struct
import time
from contextlib import contextmanager
from datetime import datetime

import mysql.connector as mysql
import mysql.connector.errors as mysql_errors

from classes.database_interface import DatabaseInterface
from libs import db_utils, string_utils

BASE_DIR = os.path.abspath(os.getcwd())
DB_PATH = "mysql"

# 連線 collation 的後綴。維持 general_ci 以符合現有客戶的資料表定義，
# 詳見模組說明「刻意不改的項目」。
COLLATION_SUFFIX = "general_ci"

# 值得重試的鎖相關錯誤：
#   1213 ER_LOCK_DEADLOCK      死結，交易已被伺服器回滾（僅 InnoDB）
#   1205 ER_LOCK_WAIT_TIMEOUT  等鎖逾時。兩個來源：
#                                - InnoDB 行鎖（innodb_lock_wait_timeout）
#                                - metadata lock（lock_wait_timeout），
#                                  與引擎無關，MyISAM 也會遇到
RETRYABLE_LOCK_ERRORS = (1213, 1205)

# 交易外單句遇到鎖錯誤時的重試次數與退避基數（秒）。
# 退避為 base * 2**attempt：0.2 / 0.4 / 0.8...
LOCK_RETRY_ATTEMPTS = 3
LOCK_RETRY_BASE_DELAY = 0.2

# select_record 的總嘗試次數（連線層級錯誤與鎖錯誤共用這個上限）。
SELECT_RETRY_ATTEMPTS = 3

# DDL 等待 metadata lock 的上限（秒）。
# MariaDB 的 lock_wait_timeout 預設是 86400 秒，ALTER TABLE 只要遇到任何
# 一條還開著這張表的連線就會實質上永遠卡住。把上限壓低之後，卡住會變成
# 一個可以接住的錯誤（1205），就不必預防性地擊殺閒置連線了。
#
# 【重要】這是 session 變數，只在 DDL 期間套用，離開時必須還原——
# 否則整條連線的每一句 DML 都只等 10 秒，見模組說明本次修訂第 1 項。
DDL_LOCK_WAIT_TIMEOUT = 10

# DDL 真的被 metadata lock 擋住時，才清理閒置超過這個秒數的連線。
# 看診站等健保署回應最長 30 秒，期間連線是 Sleep 且沒有開 InnoDB 交易，
# 不在保護名單內；門檻抬高到 300 秒以完全避開誤傷。
DDL_KILL_SLEEP_THRESHOLD = 300

# 鎖診斷的輸出上限
LOCK_DIAG_MAX_ROWS = 20
LOCK_DIAG_STATUS_CHARS = 3000
LOCK_DIAG_MAX_CHARS = 6000
LOCK_LOG_DIR = os.path.join(BASE_DIR, "log")
LOCK_LOG_FILE = os.path.join(LOCK_LOG_DIR, "lock_timeout.log")

# 無法從資料庫現況判定引擎時採用的值。三種情況會用到：
#   1. 全新資料庫，還沒有任何資料表（正常情形）
#   2. 尚未連線（異常，會另外警告）
#   3. 連線未選定資料庫，DATABASE() 為 NULL（異常，會另外警告）
# 只有第 1 種是預期會發生的；另外兩種都會印出明確警告，不會靜默通過。
FALLBACK_ENGINE = "InnoDB"


def _is_connection_error(exc):
    """判斷例外是否屬於連線層級（可以重連再試），而非 SQL 本身有問題。

    connector 在連線半死或協定流不同步時，不一定會丟出 InterfaceError：

      * cmd_ping() 讀到不足 5 bytes 的封包
        -> _handle_ok() 的 `packet[4]` 丟出 IndexError
      * 封包表頭殘缺 -> struct.error
      * socket 已被對端關閉 -> OSError / ConnectionResetError

    這些都必須當成「連線壞了，重連再試」，而不是「SQL 寫錯了」——
    後者會讓呼叫端收到一個完全指錯方向的錯誤訊息。
    """
    if isinstance(exc, (mysql_errors.OperationalError, mysql_errors.InterfaceError)):
        return True

    return isinstance(exc, (IndexError, struct.error, OSError))


def _is_lock_error(exc):
    """是否為可重試的鎖錯誤（1205 等鎖逾時 / 1213 死結）。"""
    return getattr(exc, "errno", None) in RETRYABLE_LOCK_ERRORS


class TransactionInterrupted(mysql_errors.InterfaceError):
    """交易進行中連線中斷。

    未提交的變更已被伺服器回滾，整個操作必須從頭重做。這個例外刻意獨立
    出來，讓 select_record 等重試邏輯能區分「可以重連再試」與「交易已毀，
    重試沒有意義」兩種情況。
    """


class TransactionAborted(RuntimeError):
    """外層交易已被內層回滾，不可再繼續。

    典型情境：外層 transaction() 區塊裡呼叫了另一個包 transaction() 的
    函式，內層出錯回滾，但外層程式碼把例外吞掉繼續往下跑。此時伺服器端
    的交易早就結束，連線回到 autocommit，外層接下來的每一句都會立刻落地
    ——這正是「半套資料且沒有任何錯誤」的來源。

    因此內層回滾後，外層的任何語句與最後的 commit() 都會拋出這個例外。
    正確的做法是讓例外一路傳出最外層的 transaction() 區塊，重做整個操作。
    """


class MySQLDatabase(DatabaseInterface):
    """MySQL 資料庫操作類別，提供連線、查詢、插入、更新、刪除與資料表管理功能。"""

    CONFIG_FILE = os.path.join(BASE_DIR, "pymedical.conf")

    def __init__(self, config_file=None, **kwargs):
        """初始化 MySQLDatabase 類別。

        Args:
            config_file (str, optional): 設定檔路徑。
            **kwargs: 資料庫連線參數。
        """
        self.cnx = None
        self.host = "localhost"
        self.user = ""
        self.password = ""
        self.database = ""
        self.charset = "utf8mb4"
        self.port = 3306

        # 連線建立前的佔位值。真正的引擎在 _connect_to_db() 中由
        # _detect_engine() 依資料庫現況判定——不可提前到這裡執行，此時
        # self.cnx 還是 None，偵測必定失敗並靜默落回 FALLBACK_ENGINE。
        self.engine = None

        # 連線是否為 autocommit 模式。_create_connection() 一律以
        # autocommit=True 建立連線，這個旗標讓 _auto_commit() 知道不必再
        # 多送一句 COMMIT。刻意不讀 cnx.autocommit：C 版 connector 的
        # getter 會真的跑一句 SELECT @@session.autocommit。
        self._autocommit = True

        # 明確交易的巢狀深度（呼叫端的認知）。0 表示不在交易中。
        self._tx_depth = 0
        # 內層已回滾、外層尚未收工。詳見 TransactionAborted。
        self._tx_aborted = False
        # MyISAM 客戶端使用交易時只提醒一次，避免洗畫面
        self._warned_myisam_tx = False
        # 正在抓鎖診斷，避免診斷查詢本身又觸發診斷造成遞迴
        self._capturing_diagnostics = False

        # 舊欄位。本檔案內沒有任何地方使用，但其他模組可能會讀，暫時保留。
        self.timeout = 0

        if config_file:
            self.CONFIG_FILE = config_file

        self._connect_to_db(**kwargs)

    # ------------------------------------------------------------------
    # 連線管理
    # ------------------------------------------------------------------

    def connected(self):
        """檢查是否與資料庫成功連線。

        注意：connector 的 is_connected() 會真的送一個 PING 到伺服器，
        不是免費的。熱路徑（get_cursor 的正常路徑、各方法的 finally）
        一律不使用它，只留給啟動、重連、維護工具這類低頻場合。

        Returns:
            bool: 如果資料庫連線成功，回傳 True，否則回傳 False。
        """
        try:
            return self.cnx is not None and self.cnx.is_connected()
        except Exception:
            # is_connected() 內部的 cmd_ping() 在連線半死時可能丟出
            # IndexError 之類的非 connector 例外，一律當成沒連上
            return False

    @property
    def in_transaction(self):
        """目前是否處於由本類別管理的明確交易中。"""
        return self._tx_depth > 0

    def close_database(self):
        """關閉目前的資料庫連線，並將連線設為 None。"""
        if self.cnx:
            try:
                self.cnx.close()
            except Exception:
                pass
            finally:
                self.cnx = None
        self._tx_depth = 0
        self._tx_aborted = False

    def _get_database_name(self):
        """取得目前使用的資料庫名稱。

        Returns:
            str: 資料庫名稱。
        """
        sql = "SELECT DATABASE()"
        rows = self.select_record(sql)

        return rows[0]["DATABASE()"] if rows else None

    def _connect_to_db(self, **kwargs):
        """建立資料庫連線，並初始化資料庫。

        Args:
            **kwargs: 包含 host、user、password、database 等參數。
        """
        try:
            if not kwargs:
                config = configparser.ConfigParser()
                config.read(self.CONFIG_FILE)
                if "db" in config:
                    self.host = config["db"].get("host", self.host)
                    self.user = config["db"]["user"]
                    self.password = config["db"]["password"]
                    self.database = config["db"]["database"]
                    self.charset = config["db"]["charset"]
                    self.port = config["db"].getint("port", 3306)
                    # engine 不再從設定檔讀取，一律由 _detect_engine() 依
                    # 資料庫現況判定。舊設定檔若仍留著 engine= 會被忽略。
                else:
                    print(f"⚠️ 找不到 [db] 區段，設定檔位置：{self.CONFIG_FILE}")
                    self.cnx = None
                    return
            else:
                self.host = kwargs.get("host", self.host)
                self.user = kwargs["user"]
                self.password = kwargs["password"]
                self.database = kwargs["database"]
                self.charset = kwargs["charset"]
                self.port = kwargs.get("port", 3306)

            self._tx_depth = 0
            self._tx_aborted = False

            self._create_connection(use_db=False)
            self._initialize_database()

            # 引擎一律由資料庫現況判定。必須在連上目標資料庫之後才做得到，
            # 不可提前到 __init__——那時 self.cnx 還是 None，偵測會失敗並
            # 靜默落回 FALLBACK_ENGINE，把 MyISAM 客戶誤判成 InnoDB。
            #
            # 連線失敗時直接跳過：此時 _detect_engine() 會印出「請檢查呼叫
            # 順序」的訊息，但真正的原因是連不上（密碼錯、伺服器沒開、
            # 網路不通），那句話會把人引導到錯誤的方向。
            if self.connected():
                self.engine = self._detect_engine()

                # 啟動時就講清楚目前是哪種引擎，不要等業務邏輯跑到第一筆
                # 交易才發現環境不支援
                self._warn_if_non_transactional()
                self._report_lock_timeouts()
            else:
                print("⚠️ 資料庫連線失敗，略過引擎判定。")
        except mysql.Error as err:
            print(f"Error: {err}")
            self.cnx = None

    def _create_connection(self, use_db=True):
        """建立與資料庫的實際連線。

        這裡刻意不動 _tx_depth / _tx_aborted：_reconnect() 需要在重連
        前後保留呼叫端的交易認知，好讓外層的 rollback() 能正確收尾。

        Args:
            use_db (bool): 是否指定資料庫名稱連線。
        """
        try:
            self.cnx = mysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database if use_db else None,
                charset=self.charset,
                port=self.port,
                buffered=True,
                collation=f"{self.charset}_{COLLATION_SUFFIX}",
                # mysql.connector 預設 autocommit=False。搭配 InnoDB 的
                # REPEATABLE READ，只讀不寫的連線會永遠停留在第一次查詢
                # 建立的快照上，看不到其他站台寫入的資料。明確開啟。
                # 對 MyISAM 而言此設定無任何作用。
                autocommit=True,
            )
            self._autocommit = True
            # use_db=False 的連線只用來 CREATE DATABASE，馬上就會被關掉
            # 重連，不必浪費一趟去設隔離等級。
            if use_db:
                self._apply_session_settings()
        except mysql.Error as err:
            print(f"Error: {err}")
            self.cnx = None

    def _apply_session_settings(self):
        """套用連線層級的 session 設定。

        目前只設定隔離等級。這裡的效益主要不在「看得到最新資料」——那件事
        已經由 autocommit=True 解決了（沒開交易的連線每句都是獨立的微型
        交易，本來就讀得到最新已提交的資料）。READ COMMITTED 真正的價值在
        【明確交易內的鎖行為】，而那正是多站台環境會出事的地方：

          * REPEATABLE READ 掃描時會加 gap lock / next-key lock，
            READ COMMITTED 幾乎不加 → 大幅減少死結（錯誤 1213）
          * 不符合 WHERE 條件的資料列，REPEATABLE READ 會鎖到交易結束，
            READ COMMITTED 掃完就釋放
          * 交易內每一句都取新快照，SELECT ... FOR UPDATE 之後重讀才會
            拿到最新值；REPEATABLE READ 下會讀到交易開始時的舊快照，
            很容易寫出難以察覺的錯誤

        配號、批價這類會被包進交易的流程受益最明顯。
        另外這也與 PostgreSQL 的預設一致，將來遷移時少一項行為差異。

        重要：binlog_format=STATEMENT 搭配 READ COMMITTED 時，InnoDB 的寫入
        會直接以 ER_BINLOG_STMT_MODE_AND_ROW_ENGINE 失敗。因此先檢查 binlog
        狀態，不符合條件就維持伺服器預設，寧可不最佳化也不能弄壞寫入。

        這是 session 層級的設定，重連後必須重新套用——所以所有重連都必須
        走 _reconnect()，不可用 connector 內建的 ping(reconnect=True)。

        注意這裡【不】設定 lock_wait_timeout。那是 DDL 專用、且只在 DDL
        期間生效的設定，見 _ddl_lock_timeout()。
        """
        if self.cnx is None:
            return

        cursor = None
        try:
            cursor = self.cnx.cursor()
            cursor.execute("SELECT @@log_bin, @@binlog_format")
            row = cursor.fetchone()
            log_bin = str(row[0]).upper() in ("1", "ON", "TRUE")
            binlog_format = str(row[1]).upper()

            if log_bin and binlog_format == "STATEMENT":
                # 不可套用，否則 InnoDB 寫入會全數失敗
                return

            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        except Exception as e:
            # 權限不足或伺服器不支援時靜默跳過——這只是最佳化，不是必要條件
            print(f"（略過 session 設定：{e}）")
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    def _report_lock_timeouts(self):
        """啟動時印出兩個 timeout 的實際值。

        1205 有兩個來源，而這兩個數字就是判讀 crash report 的第一線索：
        錯誤發生前等了大約幾秒，直接對應到是哪一種鎖。
        """
        rows = self._select_raw(
            "SELECT @@session.lock_wait_timeout AS mdl,"
            " @@session.innodb_lock_wait_timeout AS row_lock"
        )
        if not rows:
            return

        row = rows[0]
        print(
            f"鎖等待上限：metadata lock {row.get('mdl')} 秒、"
            f"InnoDB 行鎖 {row.get('row_lock')} 秒"
        )

    def db_engine(self):
        """取得目前資料庫的儲存引擎（快取值）。

        連線建立時已由 _detect_engine() 判定，這裡直接回傳，不重新查詢、
        不印訊息，UI 狀態列可以放心頻繁呼叫。引擎轉換工具在轉換完成後
        要顯示最新狀態，請改呼叫 refresh_engine()。

        注意：這是「整個資料庫」的判定，規則是只要還有一張 MyISAM 就算
        MyISAM。要知道某張表真正的引擎（也就是真正決定鎖行為的東西），
        請用 table_engine()。
        """
        return self.engine or "未知"

    def refresh_engine(self):
        """重新依資料庫現況判定引擎並更新快取。

        給引擎轉換工具在轉換完成後呼叫。會重新查一次 information_schema
        並印出判定結果。

        Returns:
            str: 判定後的引擎名稱。
        """
        try:
            self.engine = self._detect_engine()
        except Exception as e:
            print(f"⚠️ 重新判定資料引擎失敗：{e}")
        return self.engine or "未知"

    def table_engine(self, table_name):
        """取得單一資料表的實際儲存引擎。

        混合引擎資料庫中，db_engine() 只能告訴你「還沒轉完」，真正決定
        鎖行為的是出事那張表自己的引擎：cases 可能早就是 InnoDB（會有
        行鎖、會有 1205），而資料庫仍因為某張小設定表被判定為 MyISAM。
        crash report 請一併記錄這個值。

        Args:
            table_name (str): 資料表名稱。

        Returns:
            str | None: 引擎名稱；查不到或查詢失敗時回傳 None。
        """
        sql = """
            SELECT ENGINE FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """
        try:
            rows = self.select_record(sql, (table_name,))
        except Exception as e:
            print(f"⚠️ 查詢資料表 {table_name} 的引擎失敗：{e}")
            return None

        return rows[0]["ENGINE"] if rows else None

    def _detect_engine(self):
        """依現有資料表判定本資料庫使用的儲存引擎。

        這是引擎的唯一判定來源，設定檔不再參與。理由是設定檔會說謊——
        conf 寫著 InnoDB 而資料表其實還是 MyISAM（或反過來）時，新資料表
        會被建成另一種引擎，形成難以察覺的混合引擎資料庫。資料庫現況不會
        說謊，而且客戶跑完引擎轉換後不需要再去改任何設定檔。

        判定規則：只要還有任何一張 MyISAM 資料表，整個資料庫就算 MyISAM；
        全部都不是 MyISAM 才算 InnoDB。不用多數決，因為多數決在轉換到一半
        時會回報 InnoDB，讓人誤以為已經升級完成——「還剩一張沒轉」和
        「已經轉完」必須是不同的答案。

        反過來也要記得：回報 MyISAM 不代表每張表都是 MyISAM。轉換到一半的
        資料庫會回報 MyISAM，但大表可能早就有 InnoDB 行鎖了。

        前置條件：必須已連上目標資料庫。未連線時直接回傳 FALLBACK_ENGINE
        並明確警告，而不是讓查詢一路失敗後靜默落回預設值——後者會把
        MyISAM 客戶誤判成 InnoDB。

        Returns:
            str: 引擎名稱。
        """
        if not self.connected():
            print(
                f"⚠️ 尚未連線，無法判定資料引擎，暫用 {FALLBACK_ENGINE}。"
                "若此訊息出現在正常啟動流程中，代表 _detect_engine() 被"
                "提前呼叫了，請檢查呼叫順序。"
            )
            return FALLBACK_ENGINE

        sql = """
            SELECT
                COUNT(*) AS total,
                SUM(UPPER(ENGINE) = 'MYISAM') AS myisam
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_TYPE = 'BASE TABLE'
            AND ENGINE IS NOT NULL
        """
        try:
            rows = self.select_record(sql)
        except Exception as e:
            print(f"⚠️ 查詢資料引擎失敗，暫用 {FALLBACK_ENGINE}：{e}")
            return FALLBACK_ENGINE

        row = (rows or [{}])[0]
        total = int(row.get("total") or 0)
        myisam = int(row.get("myisam") or 0)

        if total == 0:
            # 兩種截然不同的情況，訊息不能混為一談：
            #
            # (a) 連線根本沒選到資料庫。_initialize_database() 的
            #     CREATE DATABASE IF NOT EXISTS 在「資料庫已存在但使用者
            #     沒有 CREATE 權限」時仍會失敗（權限檢查先於存在檢查），
            #     它的 except 只印訊息，於是後面的 _create_connection
            #     (use_db=True) 不會執行，連線停留在未選定資料庫的狀態。
            #     此時 DATABASE() 是 NULL，查詢自然數不到任何表——若當成
            #     空資料庫處理，MyISAM 客戶就會被靜默誤判成 InnoDB。
            #
            # (b) 資料庫確實是空的（全新安裝），採用預設值才是對的。
            if not self._get_database_name():
                print(
                    f"⚠️ 連線未選定資料庫（`{self.database}` 可能不存在或"
                    f"權限不足），無法判定引擎，暫用 {FALLBACK_ENGINE}。"
                    "請確認資料庫名稱與使用者權限。"
                )
            else:
                print(
                    f"資料庫 `{self.database}` 尚無資料表，"
                    f"新資料表將採用 {FALLBACK_ENGINE}。"
                )
            return FALLBACK_ENGINE

        if myisam:
            if myisam == total:
                print(f"資料引擎：MyISAM（{total} 張資料表全部為 MyISAM）")
            else:
                print(
                    f"⚠️ 資料庫 `{self.database}` 共 {total} 張資料表，"
                    f"其中 {myisam} 張仍是 MyISAM，尚未轉換完成，"
                    "整個資料庫仍以 MyISAM 處理。"
                    "注意：已轉為 InnoDB 的資料表仍會產生行鎖與錯誤 1205，"
                    "請儘快完成轉換。"
                )
            return "MyISAM"

        print(f"資料引擎：InnoDB（{total} 張資料表均已非 MyISAM）")
        return "InnoDB"

    def myisam_tables(self):
        """列出還沒轉換的 MyISAM 資料表，供收尾與驗收。

        Returns:
            list[dict]: 每筆含 TABLE_NAME；空 list 代表已全部轉換完成。
                未連線或查詢失敗時回傳 None，以便和「確實沒有」區分。
        """
        if not self.connected():
            print("⚠️ 尚未連線，無法列出資料表引擎。")
            return None

        sql = """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_TYPE = 'BASE TABLE'
            AND UPPER(ENGINE) = 'MYISAM'
            ORDER BY TABLE_NAME
        """
        try:
            return list(self.select_record(sql) or [])
        except Exception as e:
            print(f"⚠️ 查詢 MyISAM 資料表失敗：{e}")
            return None

    def _initialize_database(self):
        """如果資料庫不存在則建立，並重新連線使用該資料庫。"""
        if self.cnx is None:
            print("Database connection not established.")
            return
        try:
            cursor = self.cnx.cursor()
            cursor.execute(f"""
                CREATE DATABASE IF NOT EXISTS `{self.database}`
                DEFAULT CHARACTER SET {self.charset}
                COLLATE {self.charset}_{COLLATION_SUFFIX}
            """)
            cursor.close()
            self.cnx.close()
            self._create_connection(use_db=True)
        except mysql.Error as err:
            print(f"Error: {err}")

    def get_cursor(self, dictionary=False, buffered=True):
        """取得 cursor。若連線已斷開，嘗試重連一次。

        這裡不再自己呼叫 connected()：connector 的 cursor() 在建立前會
        自行 ping 一次驗證連線，我們再 ping 一次只是每句 SQL 多一趟往返。
        改為直接建立 cursor，失敗（連線已死）時才走重連。

        注意 except 的範圍是 Exception 而非只有 OperationalError /
        InterfaceError。connector 在連線半死時會在 _handle_ok() 的
        `packet[4]` 丟出 IndexError（讀到空封包），那不是 connector 的
        錯誤類別，窄的 except 接不到，重連機制會形同虛設。
        這個 try 區塊裡只有「建立 cursor」一件事，不會夾帶業務邏輯的
        例外，所以放寬到 Exception 是安全的。

        Args:
            dictionary (bool): 是否回傳 dict 格式。
            buffered (bool): 是否啟用 buffer 模式。

        Returns:
            MySQLCursor: 資料庫 cursor。

        Raises:
            TransactionAborted: 外層交易已被內層回滾，不可再執行任何語句。
            TransactionInterrupted: 交易進行中連線中斷。
            mysql_errors.InterfaceError: 重連後仍無法取得有效連線。
        """
        if self._tx_aborted:
            raise TransactionAborted(
                "交易已在內層回滾，伺服器端的交易早已結束，不可再繼續執行"
                "語句。請讓例外傳出最外層的 transaction() 區塊並重做整個操作。"
            )

        if self.cnx is not None:
            try:
                return self.cnx.cursor(dictionary=dictionary, buffered=buffered)
            except Exception as e:
                # 連線已死（閒置過夜被伺服器砍掉、被別台 KILL、網路閃斷、
                # 協定流不同步…），往下重連
                print(f"⚠️ 建立 cursor 失敗，將重新連線：{type(e).__name__}: {e}")

        self._reconnect()  # 交易中會拋 TransactionInterrupted

        if not self.connected():
            raise mysql_errors.InterfaceError("資料庫連線已中斷，重新連線失敗。")

        return self.cnx.cursor(dictionary=dictionary, buffered=buffered)

    def _reconnect(self):
        """關閉並重新連線資料庫，強制指定使用資料庫。

        Raises:
            TransactionInterrupted: 若重連時正處於明確交易中。

        交易中斷線後重連是危險的靜默失敗：伺服器已回滾未提交的變更，但
        呼叫端毫不知情，後續語句會在一個全新的交易裡繼續執行，最後留下
        半套資料而且完全沒有錯誤訊息。因此這裡選擇重連完成後主動拋出
        例外，讓呼叫端知道整個操作必須重做。

        _tx_depth 刻意不歸零：那是呼叫端的認知，要由呼叫端的 rollback()
        逐層收尾。這裡只把交易標記為中止，讓收尾前的任何語句都會被擋下。
        """
        was_in_transaction = self.in_transaction
        if was_in_transaction:
            self._tx_aborted = True

        if self.cnx:
            try:
                self.cnx.close()
            except Exception:
                pass
            finally:
                self.cnx = None

        try:
            self._create_connection(use_db=True)
        except Exception as e:
            print(f"❌ 無法重新連線至資料庫：{e}")
            self.cnx = None

        # 啟動時連線失敗、引擎沒判定成功，這次重連成功了就補判定
        if self.engine is None and not was_in_transaction and self.connected():
            self.engine = self._detect_engine()

        if was_in_transaction:
            raise TransactionInterrupted(
                "交易進行中連線中斷，未提交的變更已回滾，請重試整個操作。"
            )

    @staticmethod
    def _close_cursor(cursor):
        """關閉 cursor。

        刻意不先檢查 is_connected()——那會真的送一個 PING，等於每個查詢
        多一趟往返。連線已死時 close() 本來就只會丟例外，接住即可。
        """
        if cursor is None:
            return

        try:
            cursor.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 鎖錯誤重試與診斷
    # ------------------------------------------------------------------

    def _run_with_lock_retry(self, operation, description, retries=LOCK_RETRY_ATTEMPTS):
        """執行 operation()，交易外遇到 1205 / 1213 時整句退避重試。

        為什麼「鎖錯誤」可以重試，而「斷線」不行：

          * 收到 1205 / 1213 表示伺服器明確回報「我沒有執行這句」。
            autocommit 連線上該句是完整回滾的，重送不會重複套用——
            累加型的 UPDATE（診察費加成、初診加計 A90）也安全。
          * 斷線則相反：語句可能已經送達伺服器並執行完畢，只是回應沒
            收到，重送就會變成套用兩次。所以那條路仍然不重試。

        交易中一律不重試：1205 在 InnoDB 預設只回滾「該句」，交易仍然
        開著，單句重試會讓資料進入不一致狀態。交易的重試必須以整批為
        單位，由 run_transaction() 負責。

        用盡重試後會抓一次鎖診斷（見 capture_lock_diagnostics），寫進
        log 並併入例外訊息，然後把原例外重新拋出。

        Args:
            operation (callable): 實際執行 SQL 的函式（自行處理 cursor）。
            description (str): 用於訊息與 log 的說明文字。
            retries (int): 最多嘗試次數。

        Returns:
            operation 的回傳值。
        """
        last_error = None

        for attempt in range(retries):
            try:
                return operation()
            except mysql_errors.Error as e:
                if not _is_lock_error(e) or self.in_transaction:
                    raise

                last_error = e
                if attempt >= retries - 1:
                    break

                wait = LOCK_RETRY_BASE_DELAY * (2**attempt)
                print(
                    f"⚠️ {description} 等鎖逾時（錯誤 {e.errno}），"
                    f"{wait:.1f} 秒後重試（第 {attempt + 1}/{retries} 次）"
                )
                time.sleep(wait)

        self._attach_lock_diagnostics(last_error, description)
        raise last_error

    def _select_raw(self, sql):
        """診斷專用的查詢：單次執行，不重試、不重連、不拋例外。

        鎖診斷是在錯誤已經發生之後跑的，絕不可以因為診斷本身失敗（權限
        不足、伺服器版本沒有該視圖、連線剛好也壞了）而蓋掉呼叫端原本要
        處理的例外。也刻意繞過 get_cursor()，這樣即使交易已被標記為中止
        也還抓得到現場。

        Returns:
            list[dict] | None: 查詢結果；任何失敗都回傳 None。
        """
        cursor = None
        try:
            cursor = self.cnx.cursor(dictionary=True, buffered=True)
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception:
            return None
        finally:
            self._close_cursor(cursor)

    def capture_lock_diagnostics(self):
        """在 1205 / 1213 發生當下抓現場。

        錯誤已經發生了，成本不重要；每一段都各自處理失敗，缺哪一段就
        記哪一段的失敗原因，不影響其他段。

        判讀重點：
          * [session] 兩個 timeout 的值。等了約 10 秒就失敗多半是
            metadata lock（與引擎無關，通常是別台在跑 ALTER）；等了約
            50 秒多半是 InnoDB 行鎖。
          * [INNODB_TRX] trx_started 很早、trx_state=RUNNING 而 trx_query
            是空的那一筆，就是「開著交易卻停在使用者互動或健保署回應上」
            ——那是真正要修的地方。
          * [PROCESSLIST] State 欄位若出現 "Waiting for table metadata
            lock"，就確定是 (a) 類；同時可以看到是誰在跑 ALTER。

        Returns:
            str: 可直接寫進 log 或例外訊息的多段文字。
        """
        parts = []

        def add(title, body):
            parts.append(f"----- {title} -----\n{body}")

        # --- session 設定與本連線狀態 ---
        rows = self._select_raw(
            "SELECT @@session.lock_wait_timeout AS mdl,"
            " @@session.innodb_lock_wait_timeout AS row_lock,"
            " CONNECTION_ID() AS me"
        )
        if rows:
            row = rows[0]
            add(
                "session",
                f"lock_wait_timeout(MDL)={row.get('mdl')}s  "
                f"innodb_lock_wait_timeout={row.get('row_lock')}s  "
                f"connection_id={row.get('me')}  "
                f"db_engine={self.db_engine()}  tx_depth={self._tx_depth}",
            )
        else:
            add("session", "查詢失敗（權限不足或連線已死）")

        # --- 目前有哪些 InnoDB 交易 ---
        rows = self._select_raw("""
            SELECT trx_mysql_thread_id AS id,
                   trx_state            AS state,
                   trx_started          AS started,
                   trx_rows_locked      AS locked,
                   trx_rows_modified    AS modified,
                   LEFT(IFNULL(trx_query, ''), 200) AS q
            FROM information_schema.INNODB_TRX
            ORDER BY trx_started
        """)
        if rows is None:
            add("INNODB_TRX", "查詢失敗（伺服器未啟用 InnoDB 或權限不足）")
        elif not rows:
            add("INNODB_TRX", "（無進行中的 InnoDB 交易）")
        else:
            add(
                "INNODB_TRX",
                "\n".join(
                    f"  thread={r.get('id')} state={r.get('state')} "
                    f"started={r.get('started')} "
                    f"rows_locked={r.get('locked')} "
                    f"rows_modified={r.get('modified')}\n"
                    f"    sql={r.get('q') or '（空——停在使用者互動或外部呼叫）'}"
                    for r in rows[:LOCK_DIAG_MAX_ROWS]
                ),
            )

        # --- 本資料庫中執行超過 5 秒的連線 ---
        rows = self._select_raw("SHOW FULL PROCESSLIST")
        if rows is None:
            add("PROCESSLIST", "查詢失敗（需要 PROCESS 權限）")
        else:
            busy = [
                r
                for r in rows
                if r.get("db") == self.database and int(r.get("Time") or 0) > 5
            ]
            add(
                "PROCESSLIST（本庫、超過 5 秒）",
                "\n".join(
                    f"  Id={r.get('Id')} User={r.get('User')} "
                    f"Host={r.get('Host')} Command={r.get('Command')} "
                    f"Time={r.get('Time')}s State={r.get('State')}\n"
                    f"    sql={str(r.get('Info') or '')[:200]}"
                    for r in busy[:LOCK_DIAG_MAX_ROWS]
                )
                or "  （無）",
            )

        # --- InnoDB 狀態的 TRANSACTIONS 區段 ---
        rows = self._select_raw("SHOW ENGINE INNODB STATUS")
        if not rows:
            add("INNODB STATUS", "查詢失敗（需要 PROCESS 權限）")
        else:
            status = str(rows[0].get("Status") or "")
            index = status.find("TRANSACTIONS")
            add(
                "INNODB STATUS / TRANSACTIONS",
                status[index : index + LOCK_DIAG_STATUS_CHARS]
                if index >= 0
                else "（找不到 TRANSACTIONS 區段）",
            )

        return "\n".join(parts)

    def _attach_lock_diagnostics(self, exc, description):
        """抓鎖診斷、寫 log，並把摘要併進例外訊息。

        併進例外訊息是為了讓 crash report 的「異常值」直接帶出現場——
        報告目前只回傳例外字串與追蹤，光看 `1205 Lock wait timeout
        exceeded` 完全無從判斷是 metadata lock 還是行鎖、誰擋住的。

        這個方法本身絕不可以拋出例外：它跑在例外處理路徑上，失敗的話
        呼叫端就再也收不到原本的錯誤了。
        """
        if exc is None:
            return

        if self._capturing_diagnostics:
            # 診斷查詢自己又撞上鎖錯誤時不要無限套娃
            return

        self._capturing_diagnostics = True
        try:
            diagnostics = self.capture_lock_diagnostics()
        except Exception as e:
            diagnostics = f"（抓取鎖診斷失敗：{e}）"
        finally:
            self._capturing_diagnostics = False

        report = (
            f"[鎖診斷] {datetime.now():%Y-%m-%d %H:%M:%S} "
            f"{description}\n{exc}\n{diagnostics}"
        )

        print(f"❌ {description} 重試後仍等不到鎖，已記錄現場：\n{report}")

        try:
            os.makedirs(LOCK_LOG_DIR, exist_ok=True)
            with open(LOCK_LOG_FILE, "a", encoding="utf-8") as log_file:
                log_file.write(report)
                log_file.write("\n\n" + "=" * 72 + "\n\n")
        except Exception as e:
            print(f"（寫入 {LOCK_LOG_FILE} 失敗：{e}）")

        # 併進例外訊息。connector 的 Error 把完整訊息放在 args[0]，
        # str(e) 取的就是它。截斷以免 crash report 過長。
        try:
            head = exc.args[0] if exc.args else str(exc)
            merged = f"{head}\n\n[鎖診斷] {description}\n{diagnostics}"
            exc.args = (merged[:LOCK_DIAG_MAX_CHARS],) + tuple(exc.args[1:])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 交易管理
    # ------------------------------------------------------------------

    def begin_transaction(self):
        """開始一個資料庫交易（transaction）。支援巢狀呼叫。

        巢狀時只有最外層真正開啟交易，內層僅增加深度計數，因此在交易中
        呼叫 insert_record 等方法不會提前把交易切斷。

        注意：MyISAM 資料表不支援交易，這裡不會報錯，但也不會有任何保護
        效果——出錯時不會回滾，仍會留下半套資料。

        【重要】區塊內不可開啟 QMessageBox 等 modal 對話框，也不可呼叫
        健保署（最長 30 秒）。交易會一直開著等對方回應，期間 row lock
        不放，其他診間就會收到 1205。這是目前 1205 最主要的來源。

        Raises:
            TransactionAborted: 外層交易已被內層回滾，不可再開新的巢狀層。
        """
        if self.cnx is None:
            raise mysql_errors.InterfaceError("資料庫未連線，無法開始交易。")

        if self._tx_aborted:
            raise TransactionAborted(
                "外層交易已在內層回滾，不可再開啟巢狀交易。"
                "請讓例外傳出最外層的 transaction() 區塊並重做整個操作。"
            )

        if self._tx_depth == 0:
            self._warn_if_non_transactional()
            # 不在交易中，斷線可以安全重連：先確認連線活著再 START
            cursor = self.get_cursor()
            self._close_cursor(cursor)
            self.cnx.start_transaction()

        self._tx_depth += 1

    def commit(self):
        """提交目前交易。巢狀時只有最外層真正提交。

        Raises:
            TransactionAborted: 交易已在內層回滾，沒有東西可以提交。
        """
        if self._tx_depth > 0:
            self._tx_depth -= 1
            if self._tx_depth > 0:
                return

        if self._tx_aborted:
            self._tx_aborted = False
            raise TransactionAborted(
                "交易已在內層回滾，無法提交。伺服器端沒有留下本交易的任何"
                "變更，請重做整個操作。"
            )

        if self.cnx:
            self.cnx.commit()

    def rollback(self):
        """回復目前交易。

        伺服器端一律回滾整個交易（含所有巢狀層）；呼叫端的深度計數則只
        退一層，讓外層的 with 區塊能自己收尾。若退完還有外層存在，就把
        交易標記為中止，外層接下來的語句與 commit() 都會拋出
        TransactionAborted。
        """
        if self.cnx:
            try:
                self.cnx.rollback()
            except Exception as e:
                # MyISAM 會回報 warning 1196（部分資料表無法回滾），這是
                # 預期行為，不應讓它蓋掉呼叫端原本要處理的例外
                print(f"（rollback 未完全生效：{e}）")

        if self._tx_depth > 1:
            self._tx_aborted = True

        if self._tx_depth > 0:
            self._tx_depth -= 1

        if self._tx_depth == 0:
            # 最外層已收尾，整個交易乾淨地結束了
            self._tx_aborted = False

    def _auto_commit(self):
        """寫入方法用的自動提交：只有不在明確交易中時才真的提交。

        連線是 autocommit 模式，不在交易中的語句在 execute 回來時就已由
        伺服器提交，再送 COMMIT 只是多一趟往返。只有將來有人把連線改成
        autocommit=False 時，這裡才需要真的動作。
        """
        if self._tx_depth == 0 and self.cnx and not self._autocommit:
            self.cnx.commit()

    def _auto_rollback(self):
        """寫入方法用的自動回滾：在明確交易中時不自行回滾。

        交易中的失敗應由外層決定要回滾整批還是另做處理，內層擅自回滾會
        把外層的變更一併清掉而外層毫不知情。
        autocommit 連線上失敗的語句本來就不會留下任何東西，不必多送。
        """
        if self._tx_depth == 0 and self.cnx and not self._autocommit:
            try:
                self.cnx.rollback()
            except Exception:
                pass

    def _warn_if_non_transactional(self):
        """資料表為非交易式引擎時提醒一次。

        在兩個時機呼叫：連線建立完成（讓維護者一啟動就知道環境）與第一次
        begin_transaction()（涵蓋引擎在執行期才確定的情況）。旗標確保整個
        程序生命週期內只印一次。
        """
        if self._warned_myisam_tx:
            return

        if not self.is_transactional():
            self._warned_myisam_tx = True
            print(
                f"⚠️ 目前資料庫 `{self.database}` 使用 "
                f"{self.engine or '未知'} 引擎，不支援交易。"
                "程式中的 transaction() 區塊可以正常執行，但出錯時不會回滾，"
                "仍可能留下不完整的資料；死結重試邏輯也不會生效。"
                "轉換為 InnoDB 後才會真正得到保護。"
            )

    @contextmanager
    def transaction(self):
        """以 with 區塊包住一組必須同生共死的寫入。

        用法：
            with db.transaction():
                case_key = db.insert_record('cases', fields, data)
                db.insert_record('dosage', fields2, data2)

        重要：區塊內【不可】開啟 QMessageBox 等 modal 對話框，也不可呼叫
        健保署或任何會等待外部回應的動作。交易會一直開著等對方，期間
        row lock 不放，其他診間會收到 1205。所有確認、選擇與健保署往返
        都要在進入區塊之前完成。

        區塊內也不可執行 DDL（ALTER/CREATE/DROP），MariaDB 會隱含提交，
        交易會在你不知情的狀況下被切斷。

        區塊內若呼叫了另一個也包 transaction() 的函式，而內層失敗了，
        請讓例外一路傳出來，不要在區塊內 except 掉——否則接下來的語句會
        拋出 TransactionAborted。
        """
        self.begin_transaction()
        try:
            yield self
        except BaseException:
            self.rollback()
            raise
        else:
            self.commit()

    def run_transaction(self, func, *args, retries=3, **kwargs):
        """在交易中執行 func，遇到死結／等鎖逾時時整批重試。

        重試必須以整個交易為單位——單獨重試交易中的某一句會讓資料進入
        不一致狀態，因為前面的語句早已被伺服器回滾。

        【重要】func 必須是冪等的，也就是「整個重跑一次」要能得到相同結果：

          * 不要在 func 內修改外部狀態（self.xxx、全域變數、UI 欄位、
            檔案、計數器）。資料庫的變更會被回滾，Python 端的不會——
            第二次執行時就是從一個被污染的起點開始。
          * 需要回傳新產生的 key（例如 insert 後的 CaseKey）時，用
            return 交出去，不要在 func 裡直接寫進 self。
          * 不要在 func 內開啟 QMessageBox 等 modal 對話框，也不要呼叫
            健保署：交易會一直開著等回應，期間 row lock 不放，其他診間
            會被卡住；而且重試時對話框會再跳一次。

        錯誤處理的行為依據：收到 1213（死結）時 InnoDB 已經把整個交易
        回滾掉了，連線立即可用；1205（等鎖逾時）預設只回滾該句、交易仍
        開著，由 transaction() 例外路徑的 rollback() 收尾。兩種情況重試
        前的狀態都是乾淨的。

        MyISAM 是表級鎖，不會產生死結，這段重試邏輯在 MyISAM 上等同死碼。

        Args:
            func (callable): 要在交易中執行的函式。
            *args: 傳給 func 的位置參數。
            retries (int): 最多嘗試次數。
            **kwargs: 傳給 func 的關鍵字參數。

        Returns:
            func 的回傳值。
        """
        last_error = None

        for attempt in range(retries):
            try:
                with self.transaction():
                    return func(*args, **kwargs)
            except mysql_errors.Error as e:
                errno = getattr(e, "errno", None)
                if errno not in RETRYABLE_LOCK_ERRORS or attempt >= retries - 1:
                    if errno in RETRYABLE_LOCK_ERRORS:
                        self._attach_lock_diagnostics(
                            e, f"run_transaction({getattr(func, '__name__', func)})"
                        )
                    raise
                last_error = e
                wait = 0.1 * (2**attempt)
                print(
                    f"⚠️ 交易衝突（錯誤 {errno}），"
                    f"{wait:.1f} 秒後重試（第 {attempt + 1}/{retries} 次）"
                )
                time.sleep(wait)

        if last_error:
            raise last_error

    def _assert_not_in_transaction(self, what):
        """DDL 類操作的防呆。

        MariaDB 執行 DDL 前會隱含提交，在交易中呼叫會讓交易被無聲切斷，
        後續的 rollback 也救不回已經提交的部分。
        """
        if self.in_transaction:
            raise RuntimeError(
                f"{what} 會執行 DDL（MariaDB 會隱含提交），不可在交易中呼叫。"
                f"請在進入 transaction() 區塊之前完成。"
            )

    # ------------------------------------------------------------------
    # DDL 執行
    # ------------------------------------------------------------------

    @contextmanager
    def _ddl_lock_timeout(self):
        """DDL 期間暫時壓低 lock_wait_timeout，離開時還原。

        MariaDB 的 lock_wait_timeout 預設是 86400 秒。ALTER TABLE 需要
        metadata lock，只要有任何一條連線還開著這張表的交易或未關閉的
        語句，DDL 就會實質上永遠卡住。把上限壓到 DDL_LOCK_WAIT_TIMEOUT
        秒之後，卡住會變成一個可以接住的錯誤（1205）。

        【還原是必要的，不是禮貌。】這是 session 變數，管的是 metadata
        lock，而 MDL 與儲存引擎無關——MyISAM 的 INSERT/UPDATE 一樣要先
        取得 MDL。上一版設定後不還原，等於這條連線後續「每一句」寫入都
        只等 10 秒：看診站一開機做完結構檢查，接下來一整天只要撞上別台
        的 ALTER（MyISAM 沒有 online DDL，大表要好幾分鐘）就會在 10 秒後
        拋 1205。改動之前同樣的情境只會慢一下然後成功。
        """
        previous = None

        rows = self._select_raw("SELECT @@session.lock_wait_timeout AS t")
        if rows:
            try:
                previous = int(rows[0]["t"])
            except (TypeError, ValueError, KeyError):
                previous = None

        try:
            self.exec_sql(f"SET SESSION lock_wait_timeout = {DDL_LOCK_WAIT_TIMEOUT}")
        except Exception as e:
            # 舊版伺服器或權限不足時就算了，行為退回原本的長時間等待
            print(f"（無法設定 lock_wait_timeout：{e}）")
            previous = None

        try:
            yield
        finally:
            if previous is not None:
                try:
                    self.exec_sql(f"SET SESSION lock_wait_timeout = {previous}")
                except Exception as e:
                    # 還原失敗代表這條連線可能還留著 10 秒的上限，必須讓
                    # 維護者看得到——這正是上一版 1205 大量出現的原因
                    print(
                        f"⚠️ 無法還原 lock_wait_timeout（目前仍為 "
                        f"{DDL_LOCK_WAIT_TIMEOUT} 秒）：{e}"
                    )

    def _exec_ddl_with_lock_retry(self, sql, description):
        """執行 DDL；等不到 metadata lock 時清理閒置連線再重試一次。

        與舊版的差別在「開槍的時機」：舊版每次 DDL 前都先跑一輪
        kill_sleep_connections(threshold=60)，不管有沒有人擋路。診所電腦
        整天開著，兩個病人之間閒置一分鐘是常態，而看診站在等健保署回應
        時（最長 30 秒）連線正是 Sleep 狀態且沒有開任何 InnoDB 交易，
        不在保護名單內——別台電腦一啟動做結構檢查，就可能把正在看診的
        那台連線殺掉，對方回來要寫資料時就會撞上「連線已死」。

        現在只有真的被擋住才清理，而且門檻拉到
        DDL_KILL_SLEEP_THRESHOLD 秒（遠高於健保署最長 30 秒的等待），
        以完全避開誤傷。

        lock_retries=1：這裡的重試節奏由本方法自己控制（先清理再重試），
        不要讓 exec_sql 內建的退避重試再多繞幾圈。

        Args:
            sql (str): 要執行的 DDL 語句。
            description (str): 用於訊息的說明文字。
        """
        with self._ddl_lock_timeout():
            try:
                self.exec_sql(sql, lock_retries=1)
                return
            except mysql_errors.Error as e:
                if not _is_lock_error(e):
                    raise

                print(
                    f"⚠️ {description} 等不到 metadata lock（{DDL_LOCK_WAIT_TIMEOUT}"
                    f" 秒），清理閒置超過 {DDL_KILL_SLEEP_THRESHOLD} 秒的連線後重試。"
                )

            try:
                self.kill_sleep_connections(threshold=DDL_KILL_SLEEP_THRESHOLD)
            except Exception as e:
                print(f"（清理閒置連線失敗：{e}）")

            self.exec_sql(sql, lock_retries=1)

    # ------------------------------------------------------------------
    # 資料表管理
    # ------------------------------------------------------------------

    def create_table(self, table_name):
        """
        根據指定資料表名稱，從對應的 .sql 檔案讀取建表語法並建立資料表。

        此方法會：
        - 讀取 BASE_DIR/mysql/{table_name}.sql 檔案內容
        - 清除 UTF-8 BOM（若存在）
        - 自動修正或補上 ENGINE 與 CHARSET 設定
        - 逐條執行 SQL 指令建立資料表

        ENGINE 採用 self.engine，由 _detect_engine() 在連線建立時依資料庫
        現況判定（設定檔不參與），因此不會在既有資料庫中混入另一種引擎的
        新資料表。

        Args:
            table_name (str): 要建立的資料表名稱，對應的 SQL 檔案應為 {table_name}.sql。

        Raises:
            顯示 QMessageBox 錯誤訊息，如果發生檔案不存在、編碼錯誤或 SQL 執行錯誤。
        """
        self._assert_not_in_transaction("create_table")

        engine = self.engine or FALLBACK_ENGINE
        table_file = os.path.join(BASE_DIR, DB_PATH, f"{table_name}.sql")
        cursor = None
        try:
            with open(table_file, "r", encoding="utf-8") as db_table:
                sql = db_table.read()

            # 移除 BOM
            sql = string_utils.remove_bom(sql)

            # 逐條處理 SQL 指令
            final_statements = []
            for statement in sql.split(";"):
                statement = statement.strip()
                if not statement:
                    continue

                # 強制設定 ENGINE 與 CHARSET
                upper_stmt = statement.upper()
                if upper_stmt.startswith("CREATE TABLE"):
                    # 使用正則式替換 ENGINE 設定
                    statement = re.sub(
                        r"ENGINE\s*=\s*\w+",
                        f"ENGINE={engine}",
                        statement,
                        flags=re.IGNORECASE,
                    )
                    # 若未指定 ENGINE，則補上 ENGINE 與 CHARSET 設定
                    if "ENGINE=" not in statement.upper():
                        statement += (
                            f" ENGINE={engine} DEFAULT CHARSET={self.charset} "
                            f"COLLATE {self.charset}_{COLLATION_SUFFIX}"
                        )

                final_statements.append(statement)

            # 執行所有 SQL 語句。建表也是 DDL，同樣需要 metadata lock
            # （CREATE TABLE IF NOT EXISTS 撞到既有的表時），因此一併
            # 套用縮短的等待上限，離開時還原。
            with self._ddl_lock_timeout():
                cursor = self.get_cursor()
                for stmt in final_statements:
                    cursor.execute(stmt)
                self._auto_commit()

        except FileNotFoundError:
            self._show_error_message(
                "資料表檔案不存在", f"找不到資料表定義檔：{table_file}"
            )
        except UnicodeDecodeError:
            self._show_error_message(
                "編碼錯誤", f"無法解析檔案：{table_file}，請確認是否為 UTF-8 編碼。"
            )
        except mysql.Error as err:
            # 模組是以 `import mysql.connector as mysql` 匯入的，mysql 已經
            # 是 mysql.connector 本身，不可寫成 mysql.connector.Error。
            self._show_error_message(
                "建表錯誤", f"建立資料表 {table_name} 時出現錯誤：\n{err!s}"
            )
        finally:
            self._close_cursor(cursor)

    # ------------------------------------------------------------------
    # 查詢與寫入
    # ------------------------------------------------------------------

    def select_record(self, sql, params=None, dictionary=True):
        """執行 SELECT 查詢並回傳結果。

        兩類可重試的失敗在同一個迴圈裡處理，但處置方式不同：

          * 鎖錯誤（1205 / 1213）：退避後重試同一句。交易中不重試——那要
            由 run_transaction() 以整批為單位處理。
          * 連線層級錯誤：重連後重試。交易中不重連——重連會靜默回滾整批
            未提交的變更。

        【行為變更】鎖錯誤用盡重試後會拋出例外，不再回傳空 list。原本
        把「鎖住了」與「查不到」混為一談，會讓呼叫端以為沒有資料而繼續
        往下走；在病歷系統裡這比直接報錯危險得多。
        連線層級失敗仍維持回傳 []（沿用舊行為）。

        Args:
            sql (str): 查詢語句，值的部分請用 %s 佔位符。
            params (tuple, optional): 對應 %s 佔位符的參數值。
            dictionary (bool): 是否以 dict 格式回傳每一列。

        Returns:
            list[dict]: 查詢結果列表；連線層級失敗時回傳空列表。

        Raises:
            mysql_errors.Error: SQL 本身有問題，或鎖錯誤重試後仍失敗。
            TransactionAborted / TransactionInterrupted: 交易已毀。
        """
        if not sql:
            return []

        lock_error = None
        connection_error = None

        for attempt in range(SELECT_RETRY_ATTEMPTS):
            cursor = None
            try:
                cursor = self.get_cursor(dictionary=dictionary)
                cursor.execute(sql, params or ())
                return cursor.fetchall()

            except (TransactionInterrupted, TransactionAborted):
                # 交易已毀，重試單句沒有意義，直接讓呼叫端知道
                raise

            except Exception as e:
                if _is_lock_error(e):
                    if self.in_transaction:
                        # 交易中的鎖錯誤要整批重做，不在這裡處理
                        print(f"❌ 交易中等鎖逾時，不重試：{e}")
                        raise

                    lock_error = e
                    if attempt >= SELECT_RETRY_ATTEMPTS - 1:
                        break

                    wait = LOCK_RETRY_BASE_DELAY * (2**attempt)
                    print(
                        f"⚠️ 查詢等鎖逾時（錯誤 {e.errno}），"
                        f"{wait:.1f} 秒後重試"
                        f"（第 {attempt + 1}/{SELECT_RETRY_ATTEMPTS} 次）"
                    )
                    time.sleep(wait)
                    continue

                # 連線層級的判定交給 _is_connection_error()：connector 在
                # 連線半死時不一定丟得出 InterfaceError（見該函式說明），
                # 只看例外類別會把「連線壞了」誤判成「SQL 寫錯了」。
                if not _is_connection_error(e):
                    print(f"❌ SQL 執行失敗，非連線問題，不重試：{sql}\n{e}")
                    raise

                if self.in_transaction:
                    # 交易中不可重連——重連會靜默回滾整批未提交的變更
                    print(f"❌ 交易中發生連線層級錯誤，不重試：{e}")
                    raise

                print(f"⚠️ 連線層級錯誤 (第 {attempt + 1} 次): {type(e).__name__}: {e}")
                connection_error = e
                self._reconnect()

            finally:
                self._close_cursor(cursor)

        if lock_error is not None:
            self._attach_lock_diagnostics(lock_error, f"select_record: {sql[:120]}")
            raise lock_error

        if connection_error is not None:
            print(f"❌ 重試 {SELECT_RETRY_ATTEMPTS} 次後仍失敗：{connection_error}")

        return []

    def delete_record(self, table_name, primary_key, key_value):
        """刪除資料表中指定主鍵的紀錄。

        交易外遇到鎖錯誤會自動退避重試，詳見 _run_with_lock_retry()。

        Args:
            table_name (str): 資料表名稱。
            primary_key (str): 主鍵欄位名稱。
            key_value (any): 要刪除的主鍵值。
        """
        sql = f"DELETE FROM {table_name} WHERE {primary_key} = %s"

        def _run():
            cursor = self.get_cursor(dictionary=True)
            try:
                cursor.execute(sql, (key_value,))
                self._auto_commit()
            except Exception:
                self._auto_rollback()
                raise
            finally:
                self._close_cursor(cursor)

        self._run_with_lock_retry(
            _run, f"delete_record({table_name}, {primary_key}={key_value})"
        )

    def insert_record(self, table_name, fields, data):
        """新增一筆紀錄至指定資料表。

        交易外遇到鎖錯誤會自動退避重試。這是安全的：收到 1205 / 1213 表示
        伺服器沒有執行該句，不會插入兩筆。

        Args:
            table_name (str): 資料表名稱。
            fields (list[str]): 欄位名稱列表。
            data (list): 欲新增的值。

        Returns:
            int: 自動遞增的主鍵 ID。
        """
        fields_list = ", ".join(fields)
        value_list = ", ".join(["%s"] * len(fields))
        sql = f"INSERT INTO {table_name} ({fields_list}) VALUES ({value_list})"

        # 只轉換一次。重試時沿用同一份資料，不要重複套用轉換。
        string_utils.str_to_none(data)

        def _run():
            cursor = self.get_cursor(dictionary=True)
            try:
                cursor.execute(sql, data)
                # 直接取 cursor.lastrowid，不要在關掉 cursor 之後再跑一次
                # SELECT LAST_INSERT_ID()：那會多一次來回，而且中間若發生
                # 重連就會取到錯誤的值（甚至是 None）。
                last_row_id = cursor.lastrowid
                self._auto_commit()
                return last_row_id
            except Exception:
                self._auto_rollback()
                raise
            finally:
                self._close_cursor(cursor)

        return self._run_with_lock_retry(_run, f"insert_record({table_name})")

    def update_record(self, table_name, fields, primary_key, key_value, data):
        """更新指定主鍵的紀錄。

        交易外遇到鎖錯誤會自動退避重試。這是安全的：收到 1205 / 1213 表示
        伺服器沒有執行該句，即使是累加型的 UPDATE（診察費加成、初診加計
        A90）也不會被套用兩次。

        Args:
            table_name (str): 資料表名稱。
            fields (list[str]): 欲更新的欄位名稱。
            primary_key (str): 主鍵欄位名稱。
            key_value (any): 主鍵值。
            data (list): 欲更新的欄位值。
        """
        assignment_list = ", ".join([f"{field} = %s" for field in fields])
        sql = f"UPDATE {table_name} SET {assignment_list} WHERE {primary_key} = %s"

        string_utils.str_to_none(data)
        values = list(data) + [key_value]

        def _run():
            cursor = self.get_cursor(dictionary=True)
            try:
                cursor.execute(sql, values)
                self._auto_commit()
            except Exception:
                self._auto_rollback()
                raise
            finally:
                self._close_cursor(cursor)

        self._run_with_lock_retry(
            _run, f"update_record({table_name}, {primary_key}={key_value})"
        )

    def exec_sql(
        self, sql, params=None, auto_commit=True, lock_retries=LOCK_RETRY_ATTEMPTS
    ):
        """執行任意 SQL 語句（非查詢類），例如 INSERT、UPDATE、DELETE。

        鎖錯誤（1205 / 1213）在交易外會自動退避重試——伺服器明確回報
        「沒有執行」，重送不會重複套用。

        斷線則【不】重試：若 execute() 執行到一半斷線，語句可能已經送達
        伺服器只是回應沒收到，重送會變成重複套用——累加型的 UPDATE
        （診察費加成、初診加計 A90）正是不能重複的那種。get_cursor() 已經
        會在「建立 cursor」這一步自動重連，涵蓋了大部分的斷線情境。

        Args:
            sql (str): 要執行的 SQL 語句，可包含 %s 佔位符。
            params (tuple): 對應佔位符的參數，None 表示不使用參數化查詢。
            auto_commit (bool): 只在 transaction() 區塊內有意義（且在那裡
                本來就由外層決定提交與否，此參數無作用）。在交易外傳
                False 會直接報錯：連線是 autocommit 模式，語句執行完就已
                提交，「先不提交、之後再一起 commit」在這裡做不到，靜默
                接受只會讓呼叫端誤以為自己有回滾的機會。
            lock_retries (int): 鎖錯誤的最多嘗試次數。DDL 路徑會傳 1，
                由 _exec_ddl_with_lock_retry() 自行控制重試節奏。

        Returns:
            int: INSERT 時為新資料的 auto_increment 值，其他語句為 0。

        Raises:
            RuntimeError: 交易外傳入 auto_commit=False。
        """
        if not auto_commit and self._tx_depth == 0:
            raise RuntimeError(
                "exec_sql(auto_commit=False) 只能在 transaction() 區塊內使用。"
                "交易外的連線是 autocommit，語句執行完即已提交，此參數沒有"
                "任何效果。需要一組語句同生共死請改用 with db.transaction():。"
            )

        def _run():
            cursor = self.get_cursor(dictionary=True)
            try:
                cursor.execute(sql, params)  # params=None 時等同 execute(sql)
                last_row_id = cursor.lastrowid
                self._auto_commit()
                return last_row_id
            except Exception as e:
                # 在明確交易中時 _auto_rollback() 不會動作，由外層決定。
                # 注意：若 sql 是 DDL（如 ALTER TABLE），MySQL 在執行前已
                # 隱性 commit，這裡的 rollback 多半是 no-op。
                self._auto_rollback()
                if not _is_lock_error(e):
                    # 鎖錯誤的訊息由重試邏輯統一輸出，這裡不重複洗畫面
                    print(f"❌ exec_sql 執行失敗：{sql}\n參數：{params}\n錯誤資訊：{e}")
                raise
            finally:
                self._close_cursor(cursor)

        return self._run_with_lock_retry(
            _run, f"exec_sql: {sql[:120]}", retries=max(1, lock_retries)
        )

    def get_last_insert_id(self):
        """取得最近一次插入的自動編號 ID。

        Note:
            insert_record 已改用 cursor.lastrowid，不再依賴此方法。保留是
            為了相容既有呼叫端，但要注意它是獨立的一次查詢，中間若發生
            重連就會取到錯誤的值。新程式碼請優先使用 insert_record 或
            exec_sql 的回傳值。

        Returns:
            int: 最後插入的 ID。
        """
        row = self.select_record("SELECT LAST_INSERT_ID()")
        return row[0]["LAST_INSERT_ID()"] if row else None

    def get_last_auto_increment_key(self, table_name):
        """取得指定資料表的下一個自動編號值。

        Args:
            table_name (str): 資料表名稱。

        Returns:
            int: 下一個自動編號值。
        """
        sql = """
            SELECT AUTO_INCREMENT FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """
        row = self.select_record(sql, (table_name,))
        return row[0]["AUTO_INCREMENT"] if row else None

    # ------------------------------------------------------------------
    # 資訊查詢
    # ------------------------------------------------------------------

    def host_name(self):
        """取得目前連線的主機名稱。"""
        return self.host

    def database_name(self):
        """取得目前使用的資料庫名稱。"""
        return self.database

    def engine_name(self):
        """取得目前資料庫使用的儲存引擎（快取值，未知時給 FALLBACK_ENGINE）。

        與 db_engine() 的差別只在未知時的回傳值：這裡給的是「建表時會用
        的引擎」，db_engine() 給的是「顯示給人看的狀態」。
        """
        return self.engine or FALLBACK_ENGINE

    def is_transactional(self):
        """目前資料庫的引擎是否支援交易。

        MyISAM 回傳 False。引擎尚未判定（連線失敗）時也回傳 False——
        「不知道」就當作沒有保護，比樂觀地假設有來得安全。可用於在 UI 上
        提示客戶尚未轉換，或在關鍵流程中決定是否要走額外的補償邏輯。

        注意混合引擎資料庫：只要還有一張 MyISAM 就回傳 False，但已經轉成
        InnoDB 的資料表仍然有真正的行鎖與 1205。要判斷「這張表會不會被
        鎖」請用 table_engine()，不要用這個方法。
        """
        if not self.engine:
            return False
        return str(self.engine).upper() not in ("MYISAM", "MEMORY", "CSV")

    def cursor(self):
        """取得預設 dictionary 格式的 cursor。"""
        return self.get_cursor(dictionary=True)

    def get_table_names(self):
        """取得目前資料庫內所有資料表名稱。

        Returns:
            list[str]: 資料表名稱列表。
        """
        rows = self.select_record("SHOW TABLES")
        return [list(row.values())[0] for row in rows]

    def get_tables_without_primary_key(self):
        """列出沒有 PRIMARY KEY 的資料表。

        InnoDB 缺少 PRIMARY KEY 時會自建隱藏的 6-byte rowid，效能較差，
        將來要遷移到 PostgreSQL 也會卡住。MyISAM 時代很容易漏掉，轉換
        前後值得盤點一次。

        Returns:
            list[str]: 資料表名稱列表。
        """
        sql = """
            SELECT t.TABLE_NAME
            FROM information_schema.TABLES t
            WHERE t.TABLE_SCHEMA = DATABASE()
              AND t.TABLE_TYPE = 'BASE TABLE'
              AND NOT EXISTS (
                    SELECT 1 FROM information_schema.STATISTICS s
                    WHERE s.TABLE_SCHEMA = t.TABLE_SCHEMA
                      AND s.TABLE_NAME  = t.TABLE_NAME
                      AND s.INDEX_NAME  = 'PRIMARY')
            ORDER BY t.TABLE_NAME
        """
        rows = self.select_record(sql)
        return [row["TABLE_NAME"] for row in rows]

    def ping(self):
        """測試資料庫連線是否仍有效，若中斷則自動重連。

        重連一律走本類別的 _reconnect()，不用 connector 內建的
        ping(reconnect=True)：後者只還原連線參數，不會重新套用
        _apply_session_settings() 下的隔離等級，連線會悄悄回到
        REPEATABLE READ，而且 self.engine 等狀態也不會同步。

        交易中不重連（會靜默回滾），斷線就直接回傳 False，讓下一句
        get_cursor() 拋出 TransactionInterrupted 由呼叫端處理。

        Returns:
            bool: 連線是否可用。
        """
        if self.cnx is None:
            return False

        try:
            self.cnx.ping(reconnect=False)
            return True
        except Exception:
            # connector 的 ping 在連線半死時也可能丟出 IndexError 之類的
            # 非 connector 例外，一律當成斷線
            pass

        if self.in_transaction:
            return False

        try:
            self._reconnect()
        except Exception as e:
            print(f"❌ ping 後重新連線失敗：{e}")
            return False

        return self.connected()

    # ------------------------------------------------------------------
    # 結構維護（皆為 DDL，不可在交易中呼叫）
    # ------------------------------------------------------------------

    def check_table_exists(self, table_name):
        """檢查資料表是否存在，不存在時自動建立並寫入預設資料。"""
        if "InsReply" in table_name:
            return

        self._assert_not_in_transaction("check_table_exists")

        if not self._is_table_exists(table_name):
            try:
                self.create_table(table_name)
            except Exception:
                pass

            db_utils.set_default_data(self, table_name)

    def _is_table_exists(self, table_name):
        sql = "SHOW TABLES LIKE %s"
        rows = self.select_record(sql, (table_name,))
        return bool(rows)

    def check_field_exists(self, table_name, alter_type, column, data_type):
        """檢查欄位是否存在，必要時自動建立或修改欄位型態。

        Note:
            table_name、column、data_type 會直接組進 ALTER TABLE 語句的識別字
            (identifier) 位置，MySQL 參數化查詢無法替換識別字，僅能替換值。
            因此這幾個參數務必只能來自程式內部可信任的呼叫（例如寫死的表結構
            定義），不可直接帶入外部輸入。

            不做預防性的閒置連線擊殺，改由 _exec_ddl_with_lock_retry() 在
            真的被 metadata lock 擋住時才處理，詳見該方法說明。

            【效能與干擾】這個方法在 MyISAM 大表上是整表複製，期間持有
            exclusive metadata lock，其他站台的寫入會全部卡住。每台客戶端
            每次啟動都跑一輪結構檢查，是目前 1205 的主要製造者之一。
            建議改為在資料庫中記錄結構版本號，版本相符就整段跳過。
        """
        self._assert_not_in_transaction("check_field_exists")

        if isinstance(column, list) and len(column) == 2:
            search_column, new_column = column
        else:
            search_column = new_column = column

        sql = f"SHOW COLUMNS FROM {table_name} LIKE %s"
        rows = self.select_record(sql, (search_column,))
        column_exists = bool(rows)
        field_match = (
            column_exists and string_utils.xstr(rows[0]["Field"]) == new_column
        )
        type_match = (
            column_exists
            and string_utils.xstr(rows[0]["Type"]).lower() == data_type.lower()
        )
        if alter_type == "add" and column_exists:
            return
        if (
            alter_type in ("change", "modify")
            and column_exists
            and field_match
            and type_match
        ):
            return
        if alter_type in ("change", "modify") and not column_exists:
            # 不再靜默跳過：舊欄位不存在時印出警告，並讓下面的 ALTER TABLE
            # 繼續執行，由 MySQL 拋出 Unknown column 之類的真正錯誤，問題
            # 才會在發生的當下就被看到，而不是被吞掉、之後在別處才爆炸。
            print(
                f"⚠️ 嘗試以 {alter_type} 修改資料表 {table_name} 的欄位 "
                f"`{search_column}`，但該欄位不存在，將繼續執行 ALTER TABLE"
                "（可能因找不到欄位而報錯）。"
            )

        if alter_type == "add":
            # 用拆解後的 new_column，不可用原始的 column——後者若是 list
            # 會被組成 ADD `['old', 'new']`
            sql = f"ALTER TABLE {table_name} ADD `{new_column}` {data_type}"
        elif alter_type == "change":
            sql = f"ALTER TABLE {table_name} CHANGE `{search_column}` `{new_column}` {data_type}"
        elif alter_type == "modify":
            sql = f"ALTER TABLE {table_name} MODIFY `{new_column}` {data_type}"
        else:
            raise ValueError(f"不支援的 alter_type：{alter_type!r}")

        self._exec_ddl_with_lock_retry(
            sql, f"修改資料表 {table_name} 的欄位 `{new_column}`"
        )

    def _get_transaction_thread_ids(self):
        """取得目前持有 InnoDB 交易的執行緒 ID 集合。

        MyISAM 客戶端這裡永遠是空集合（沒有任何 InnoDB 交易），因此下面
        kill_sleep_connections 的行為與先前完全相同。

        Returns:
            set[int] | None: 執行緒 ID；無法查詢時回傳 None 代表「無法判斷」。
        """
        rows = self._select_raw(
            "SELECT trx_mysql_thread_id FROM information_schema.INNODB_TRX"
        )
        if rows is None:
            # 伺服器停用 InnoDB 或無權限時，寧可保守一點：回傳 None 代表
            # 「無法判斷」，由呼叫端決定是否放棄擊殺
            return None

        return {
            int(row["trx_mysql_thread_id"])
            for row in rows
            if row.get("trx_mysql_thread_id") is not None
        }

    def kill_sleep_connections(self, threshold=60):
        """
        殺掉本使用者、本資料庫、且閒置時間超過 threshold 秒的 Sleep 連線。

        【這是破壞性操作，不要預防性地呼叫。】
        被殺掉的連線屬於別台正在使用的電腦，對方毫不知情，下一次要用
        資料庫時才會發現連線已死（症狀是 connector 在 cmd_ping() 讀到空
        封包，於 _handle_ok() 的 packet[4] 丟出 IndexError）。看診站在等
        健保署回應時連線正是 Sleep 狀態且沒有開任何 InnoDB 交易，不在
        保護名單內，最容易被誤傷——所以 DDL 路徑用的門檻是
        DDL_KILL_SLEEP_THRESHOLD（300 秒），遠高於健保署最長 30 秒的等待。
        只有在 DDL 真的被 metadata lock 擋住時才該呼叫——請走
        _exec_ddl_with_lock_retry()。

        InnoDB 注意事項：Sleep 狀態的連線可能正持有一個未提交的交易與一批
        row lock（idle in transaction）。殺掉它會讓對方的變更被回滾，而對方
        程式毫不知情。因此這裡會先查出 INNODB_TRX 中的執行緒並排除。

        只處理 User 與 db 都和自己相同的連線。db 為 NULL 的連線可能是別的
        應用剛連上還沒 USE、監控工具、備份腳本，不在本系統的管轄範圍。

        MyISAM 客戶端的排除清單永遠為空，行為與改動前完全相同。

        Args:
            threshold (int): 超過這個秒數的 Sleep 連線會被終止，預設為 60 秒。

        Returns:
            int: 實際終止的連線數。
        """
        protected = self._get_transaction_thread_ids()
        if protected is None:
            # 無法判斷哪些連線持有交易時，只在確定不會誤傷的情況下才動作。
            # 引擎未知也算無法確定。
            if self.engine is None or self.is_transactional():
                print("⚠️ 無法查詢 INNODB_TRX，為避免中斷他人交易，略過清理連線。")
                return 0
            protected = set()

        killed = 0
        cursor = self.get_cursor(dictionary=True, buffered=True)

        try:
            # 取得目前連線的 ID（避免自殺）
            cursor.execute("SELECT CONNECTION_ID()")
            my_id = cursor.fetchone()["CONNECTION_ID()"]

            # 取得所有連線狀態
            cursor.execute("SHOW PROCESSLIST")
            processlist = cursor.fetchall()

            for row in processlist:
                if (
                    row["Command"] == "Sleep"
                    and row["Time"] > threshold
                    and row["Id"] != my_id
                    and row.get("User") == self.user
                    and row.get("db") == self.database
                ):
                    process_id = row["Id"]

                    if int(process_id) in protected:
                        print(
                            f"⏭️ 跳過 ID {process_id}："
                            f"該連線持有未提交的交易，殺掉會讓對方的變更遺失。"
                        )
                        continue

                    # 這一行是日後與 crash report 對帳的關鍵：對方的
                    # 「連線已死」一定緊接在這個時間點之後
                    print(
                        f"🔪 終止閒置連線 Id={process_id} "
                        f"User={row.get('User')} Host={row.get('Host')} "
                        f"db={row.get('db')} Time={row.get('Time')}s"
                    )
                    try:
                        # 沿用外層 cursor。外層 cursor 是 buffered 且已
                        # fetchall()，沒有未讀結果，重用是安全的。
                        cursor.execute(f"KILL {process_id}")
                        killed += 1
                    except Exception as e:
                        print(f"❌ 無法刪除 ID {process_id}: {e}")
        finally:
            self._close_cursor(cursor)

        return killed

    def add_index_if_not_exists(self, table_name, index_name, fields):
        """
        動態檢查並建立索引

        注意：在 MyISAM 大表上建索引會重建整個索引檔，期間持有 exclusive
        metadata lock，其他站台的寫入會全部卡住。請安排在非看診時段執行。

        :param table_name: 資料表名稱
        :param index_name: 索引名稱
        :param fields: 欄位串列, 例如 ['MedicineSet', 'CaseDate']
        """
        self._assert_not_in_transaction("add_index_if_not_exists")

        # 1. 檢查索引是否存在
        check_sql = """
            SELECT COUNT(*) as total FROM information_schema.STATISTICS
            WHERE table_schema = DATABASE()
            AND table_name = %s
            AND index_name = %s
        """
        res = self.select_record(check_sql, (table_name, index_name))

        # 2. 如果不存在則執行建立
        if res and res[0].get("total", 0) == 0:
            # 使用 join 處理欄位，避免 tuple 單一元素時出現的末尾逗號問題
            field_str = ", ".join([f"`{f}`" for f in fields])
            create_sql = (
                f"ALTER TABLE `{table_name}` ADD INDEX `{index_name}` ({field_str})"
            )

            print(f"正在建立索引：{index_name} -> {table_name}({field_str})")
            self._exec_ddl_with_lock_retry(
                create_sql, f"建立索引 {index_name} -> {table_name}"
            )
