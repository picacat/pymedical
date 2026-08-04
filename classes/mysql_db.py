"""MySQL/MariaDB 資料庫存取層。

本版目標：同一份程式碼在 MyISAM 與 InnoDB 客戶端都能安全運作。

設計原則
--------
客戶端會有一段長期的混合期（部分診所已轉 InnoDB、部分仍是 MyISAM），
因此所有 InnoDB 導向的新行為都必須在 MyISAM 上退化成無害的 no-op：

  * autocommit 明確設為 True
      InnoDB 預設 REPEATABLE READ，連線第一次 SELECT 就建立快照，在
      commit 之前所有後續 SELECT 都看同一份快照。候診名單、看診清單、
      Kiosk 這類「只讀不寫」的連線可能開著數小時從不 commit，於是永遠
      看不到別台存進去的資料。MyISAM 沒有 MVCC，本來就沒有這個問題，
      所以這項改動對 MyISAM 客戶完全無影響。

  * 資料引擎一律自動判定（_detect_engine）
      引擎不從設定檔讀取，而是依目前資料表的多數引擎判定。設定檔會說謊
      ——conf 寫著 InnoDB 而資料表其實還是 MyISAM（或反過來）時，新資料
      表會被建成另一種引擎，形成難以察覺的混合引擎資料庫。資料庫現況不
      會說謊，客戶跑完引擎轉換後也不需要再去改任何設定檔。
      MyISAM 客戶判定出 MyISAM、已轉換的判定出 InnoDB、全新資料庫給
      InnoDB，三種情況都正確。判定必須在連上目標資料庫之後執行。

  * 交易深度計數（_tx_depth）
      insert/update/delete/exec_sql 原本無條件 commit，使得外層交易一
      開始就被截斷。改為只有「不在明確交易中」時才自動提交。對 MyISAM
      而言資料本來就即時寫入，跳過 commit 呼叫沒有任何差別。

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
      執行緒。MyISAM 客戶的排除清單為空，行為與先前完全相同。

  * 隔離等級 READ COMMITTED（條件式）
      對「讀出來→使用者編輯→寫回去」的桌面應用比 REPEATABLE READ 合理，
      也與 PostgreSQL 的預設一致。MyISAM 完全忽略隔離等級。
      注意：binlog_format=STATEMENT 搭配 READ COMMITTED 會讓 InnoDB 寫入
      直接報錯，因此套用前會先檢查 binlog 狀態，不符合就維持預設。

刻意不改的項目
--------------
連線 collation 維持 {charset}_general_ci。改成 unicode_ci 會改變字串比較
與排序語意，且 MyISAM 與 InnoDB 客戶一律受影響，必須搭配所有資料表一起
ALTER，屬於獨立的一次性任務，不混在本次改動中。

（已知現況：restore_gui.py 以 utf8mb4_unicode_ci 建表，與此處的
general_ci 不一致。兩邊應擇一統一，但那是另一項獨立作業。）
"""

import configparser
import os
import re
import time
from contextlib import contextmanager

import mysql.connector as mysql
import mysql.connector.errors as mysql_errors

from classes.database_interface import DatabaseInterface
from libs import db_utils, string_utils

BASE_DIR = os.path.abspath(os.getcwd())
DB_PATH = "mysql"

# 連線 collation 的後綴。維持 general_ci 以符合現有客戶的資料表定義，
# 詳見模組說明「刻意不改的項目」。
COLLATION_SUFFIX = "general_ci"

# 值得整批重試的 InnoDB 鎖相關錯誤：
#   1213 ER_LOCK_DEADLOCK      死結，交易已被伺服器回滾
#   1205 ER_LOCK_WAIT_TIMEOUT  等鎖逾時
# MyISAM 是表級鎖，不會產生 1213。
RETRYABLE_LOCK_ERRORS = (1213, 1205)

# 無法從資料庫現況判定引擎時採用的值。三種情況會用到：
#   1. 全新資料庫，還沒有任何資料表（正常情形）
#   2. 尚未連線（異常，會另外警告）
#   3. 連線未選定資料庫，DATABASE() 為 NULL（異常，會另外警告）
# 只有第 1 種是預期會發生的；另外兩種都會印出明確警告，不會靜默通過。
FALLBACK_ENGINE = "InnoDB"


class TransactionInterrupted(mysql_errors.InterfaceError):
    """交易進行中連線中斷。

    未提交的變更已被伺服器回滾，整個操作必須從頭重做。這個例外刻意獨立
    出來，讓 select_record 等重試邏輯能區分「可以重連再試」與「交易已毀，
    重試沒有意義」兩種情況。
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

        # 明確交易的巢狀深度。0 表示不在交易中（自動提交模式）。
        self._tx_depth = 0
        # MyISAM 客戶端使用交易時只提醒一次，避免洗畫面
        self._warned_myisam_tx = False

        if config_file:
            self.CONFIG_FILE = config_file

        self.timeout = 0
        self._connect_to_db(**kwargs)

    # def __del__(self):
    #     """解構時關閉資料庫連線。"""
    #     self.close_database()

    # ------------------------------------------------------------------
    # 連線管理
    # ------------------------------------------------------------------

    def connected(self):
        """檢查是否與資料庫成功連線。

        Returns:
            bool: 如果資料庫連線成功，回傳 True，否則回傳 False。
        """
        try:
            return self.cnx is not None and self.cnx.is_connected()
        except Exception:
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
            else:
                print("⚠️ 資料庫連線失敗，略過引擎判定。")
        except mysql.Error as err:
            print(f"Error: {err}")
            self.cnx = None
        self.timeout = 0

    def _create_connection(self, use_db=True):
        """建立與資料庫的實際連線。

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
            self._tx_depth = 0
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

    def _detect_engine(self):
        """依現有資料表判定本資料庫使用的儲存引擎。

        這是引擎的唯一判定來源，設定檔不再參與。理由是設定檔會說謊——
        conf 寫著 InnoDB 而資料表其實還是 MyISAM（或反過來）時，新資料表
        會被建成另一種引擎，形成難以察覺的混合引擎資料庫。資料庫現況不會
        說謊，而且客戶跑完引擎轉換後不需要再去改任何設定檔。

        判定規則：取目前資料表中佔多數的引擎；數量相同時偏好 InnoDB，
        避免已經轉換一半的資料庫被判回 MyISAM 而倒退。

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
            SELECT ENGINE, COUNT(*) AS n
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_TYPE = 'BASE TABLE'
              AND ENGINE IS NOT NULL
            GROUP BY ENGINE
        """
        try:
            rows = self.select_record(sql)
        except Exception as e:
            print(f"⚠️ 查詢資料引擎失敗，暫用 {FALLBACK_ENGINE}：{e}")
            return FALLBACK_ENGINE

        counts = {}
        for row in rows or []:
            name = row.get("ENGINE")
            if name:
                counts[str(name)] = int(row.get("n") or 0)

        if not counts:
            # 兩種截然不同的情況，訊息不能混為一談：
            #
            # (a) 連線根本沒選到資料庫。_initialize_database() 的
            #     CREATE DATABASE IF NOT EXISTS 在「資料庫已存在但使用者
            #     沒有 CREATE 權限」時仍會失敗（權限檢查先於存在檢查），
            #     它的 except 只印訊息，於是後面的 _create_connection
            #     (use_db=True) 不會執行，連線停留在未選定資料庫的狀態。
            #     此時 DATABASE() 是 NULL，查詢自然沒有任何列——若當成
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

        # 數量相同時偏好交易式引擎，讓轉換到一半的資料庫不會被判回 MyISAM
        def _rank(item):
            name, n = item
            return (n, 1 if name.upper() == FALLBACK_ENGINE.upper() else 0)

        engine = max(counts.items(), key=_rank)[0]

        if len(counts) > 1:
            detail = "、".join(
                f"{k} {v} 張" for k, v in sorted(counts.items(), key=lambda x: -x[1])
            )
            print(
                f"⚠️ 資料庫 `{self.database}` 混合了多種儲存引擎（{detail}），"
                f"新資料表將採用 {engine}。"
                "這通常代表引擎轉換中斷或尚未完成，建議儘快統一。"
            )
        else:
            print(f"資料引擎：{engine}（依現有 {counts[engine]} 張資料表判定）")

        return engine

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

        Args:
            dictionary (bool): 是否回傳 dict 格式。
            buffered (bool): 是否啟用 buffer 模式。

        Returns:
            MySQLCursor: 資料庫 cursor。

        Raises:
            TransactionInterrupted: 交易進行中連線中斷。
            mysql_errors.InterfaceError: 重連後仍無法取得有效連線。
        """
        if not self.connected():
            self._reconnect()

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
        """
        was_in_transaction = self.in_transaction
        self._tx_depth = 0

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

        if was_in_transaction:
            raise TransactionInterrupted(
                "交易進行中連線中斷，未提交的變更已回滾，請重試整個操作。"
            )

    # ------------------------------------------------------------------
    # 交易管理
    # ------------------------------------------------------------------

    def begin_transaction(self):
        """開始一個資料庫交易（transaction）。支援巢狀呼叫。

        巢狀時只有最外層真正開啟交易，內層僅增加深度計數，因此在交易中
        呼叫 insert_record 等方法不會提前把交易切斷。

        注意：MyISAM 資料表不支援交易，這裡不會報錯，但也不會有任何保護
        效果——出錯時不會回滾，仍會留下半套資料。
        """
        if self.cnx is None:
            raise mysql_errors.InterfaceError("資料庫未連線，無法開始交易。")

        if self._tx_depth == 0:
            self._warn_if_non_transactional()
            self.cnx.start_transaction()

        self._tx_depth += 1

    def commit(self):
        """提交目前交易。巢狀時只有最外層真正提交。"""
        if self._tx_depth > 0:
            self._tx_depth -= 1
            if self._tx_depth > 0:
                return

        if self.cnx:
            self.cnx.commit()

    def rollback(self):
        """回復目前交易。

        回滾一律作用於整個交易（含所有巢狀層），因此深度直接歸零。
        """
        self._tx_depth = 0

        if self.cnx:
            try:
                self.cnx.rollback()
            except Exception as e:
                # MyISAM 會回報 warning 1196（部分資料表無法回滾），這是
                # 預期行為，不應讓它蓋掉呼叫端原本要處理的例外
                print(f"（rollback 未完全生效：{e}）")

    def _auto_commit(self):
        """寫入方法用的自動提交：只有不在明確交易中時才真的提交。"""
        if self._tx_depth == 0 and self.cnx:
            self.cnx.commit()

    def _auto_rollback(self):
        """寫入方法用的自動回滾：在明確交易中時不自行回滾。

        交易中的失敗應由外層決定要回滾整批還是另做處理，內層擅自回滾會
        把外層的變更一併清掉而外層毫不知情。
        """
        if self._tx_depth == 0 and self.cnx:
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

        重要：區塊內【不可】開啟 QMessageBox 等 modal 對話框。交易會一直
        開著等使用者按按鈕，期間 row lock 不放，其他診間會被卡住。所有
        確認與選擇都要在進入區塊之前完成。

        區塊內也不可執行 DDL（ALTER/CREATE/DROP），MariaDB 會隱含提交，
        交易會在你不知情的狀況下被切斷。
        """
        self.begin_transaction()
        try:
            yield self
        except Exception:
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
          * 不要在 func 內開啟 QMessageBox 等 modal 對話框：交易會一直
            開著等使用者按按鈕，期間 row lock 不放，其他診間會被卡住；
            而且重試時對話框會再跳一次。

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
                    # if "ENGINE=" not in statement.upper():
                    #     statement += f" ENGINE={engine} DEFAULT CHARSET={self.charset}"
                    if "ENGINE=" not in statement.upper():
                        statement += (
                            f" ENGINE={engine} DEFAULT CHARSET={self.charset} "
                            f"COLLATE {self.charset}_{COLLATION_SUFFIX}"
                        )

                final_statements.append(statement)

            # 執行所有 SQL 語句
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
            # 原本寫成 mysql.connector.Error。因為模組是以
            # `import mysql.connector as mysql` 匯入的，mysql 已經是
            # mysql.connector 本身，mysql.connector 這個屬性並不存在，
            # 真的進到這個 except 時會拋 AttributeError，把原始錯誤蓋掉。
            self._show_error_message(
                "建表錯誤", f"建立資料表 {table_name} 時出現錯誤：\n{err!s}"
            )
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # 查詢與寫入
    # ------------------------------------------------------------------

    def select_record(self, sql, params=None, dictionary=True):
        """執行 SELECT 查詢並回傳結果。

        Args:
            sql (str): 查詢語句，值的部分請用 %s 佔位符。
            params (tuple, optional): 對應 %s 佔位符的參數值。
            dictionary (bool): 是否以 dict 格式回傳每一列。

        Returns:
            list[dict]: 查詢結果列表，失敗時回傳空列表。
        """
        if not sql:
            return []

        retry_count = 2
        last_exception = None

        for attempt in range(retry_count):
            cursor = None
            try:
                cursor = self.get_cursor(dictionary=dictionary)
                cursor.execute(sql, params or ())
                return cursor.fetchall()

            except TransactionInterrupted:
                # 交易已毀，重試單句沒有意義，直接讓呼叫端知道
                raise

            except (mysql_errors.OperationalError, mysql_errors.InterfaceError) as e:
                if self.in_transaction:
                    # 交易中不可重連——重連會靜默回滾整批未提交的變更
                    print(f"❌ 交易中發生連線層級錯誤，不重試：{e}")
                    raise

                # 真正屬於連線層級的問題，才值得重連重試
                print(f"⚠️ 連線層級錯誤 (第 {attempt + 1} 次): {e}")
                last_exception = e
                self._reconnect()

            except Exception as e:
                # SQL 本身寫錯、欄位不存在等，重連沒有意義，直接往上丟
                print(f"❌ SQL 執行失敗，非連線問題，不重試：{sql}\n{e}")
                raise

            finally:
                if cursor is not None:
                    try:
                        if self.cnx and self.cnx.is_connected():
                            cursor.close()
                    except Exception:
                        pass

        if last_exception:
            print(f"❌ 重試 {retry_count} 次後仍失敗：{last_exception}")

        return []

    def delete_record(self, table_name, primary_key, key_value):
        """刪除資料表中指定主鍵的紀錄。

        Args:
            table_name (str): 資料表名稱。
            primary_key (str): 主鍵欄位名稱。
            key_value (any): 要刪除的主鍵值。
        """
        sql = f"DELETE FROM {table_name} WHERE {primary_key} = %s"
        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql, (key_value,))
            self._auto_commit()
        except Exception:
            self._auto_rollback()
            raise
        finally:
            if cursor is not None:
                try:
                    if self.cnx and self.cnx.is_connected():
                        cursor.close()
                except Exception:
                    pass

    def insert_record(self, table_name, fields, data):
        """新增一筆紀錄至指定資料表。

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
        string_utils.str_to_none(data)
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
            try:
                if cursor and self.cnx and self.cnx.is_connected():
                    cursor.close()
            except Exception:
                pass

    def update_record(self, table_name, fields, primary_key, key_value, data):
        """更新指定主鍵的紀錄。

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

        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql, list(data) + [key_value])
            self._auto_commit()
        except Exception:
            self._auto_rollback()
            raise
        finally:
            try:
                if cursor and self.cnx and self.cnx.is_connected():
                    cursor.close()
            except Exception:
                pass

    def exec_sql(self, sql, params=None, auto_commit=True):
        """執行任意 SQL 語句（非查詢類），例如 INSERT、UPDATE、DELETE。

        Args:
            sql (str): 要執行的 SQL 語句，可包含 %s 佔位符。
            params (tuple): 對應佔位符的參數，None 表示不使用參數化查詢。
            auto_commit (bool): 是否自動提交變更。在明確交易中時此參數
                無效——交易由外層的 commit()/rollback() 決定。

        Returns:
            int: INSERT 時為新資料的 auto_increment 值，其他語句為 0。
        """
        cursor = self.get_cursor(dictionary=True)
        try:
            cursor.execute(sql, params)  # params=None 時等同原本的 execute(sql)
            last_row_id = cursor.lastrowid
            if auto_commit:
                self._auto_commit()
            return last_row_id
        except Exception as e:
            # 失敗時主動清空交易狀態，避免連線殘留未提交/未回復的異動。
            # 注意：若 sql 是 DDL（如 ALTER TABLE），MySQL 在執行前已隱性
            # commit，這裡的 rollback 多半是 no-op。
            # 在明確交易中時 _auto_rollback() 不會動作，由外層決定。
            if auto_commit:
                self._auto_rollback()
            print(f"❌ exec_sql 執行失敗：{sql}\n參數：{params}\n錯誤資訊：{e}")
            raise
        finally:
            if cursor is not None:
                try:
                    if self.cnx and self.cnx.is_connected():
                        cursor.close()
                except Exception:
                    pass

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
        """取得目前資料庫使用的儲存引擎。"""
        return self.engine or FALLBACK_ENGINE

    def is_transactional(self):
        """目前資料庫的引擎是否支援交易。

        MyISAM 回傳 False。可用於在 UI 上提示客戶尚未轉換，或在關鍵流程
        中決定是否要走額外的補償邏輯。
        """
        return str(self.engine or "").upper() not in ("MYISAM", "MEMORY", "CSV")

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

        Returns:
            bool: 測試是否成功。
        """
        if self.cnx is None:
            return False

        # 交易中不可自動重連（會靜默回滾），只做不重連的檢查
        if self.in_transaction:
            try:
                self.cnx.ping(reconnect=False)
                return True
            except Exception:
                return False

        try:
            self.cnx.ping(reconnect=True, attempts=3, delay=2)
            return True
        except mysql.Error:
            return False

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

        try:
            self.kill_sleep_connections()
        except Exception:
            pass

        if alter_type == "add":
            sql = f"ALTER TABLE {table_name} ADD `{column}` {data_type}"
        elif alter_type == "change":
            sql = f"ALTER TABLE {table_name} CHANGE `{search_column}` `{new_column}` {data_type}"
        elif alter_type == "modify":
            sql = f"ALTER TABLE {table_name} MODIFY `{new_column}` {data_type}"
        self.exec_sql(sql)

    def _get_transaction_thread_ids(self):
        """取得目前持有 InnoDB 交易的執行緒 ID 集合。

        MyISAM 客戶端這裡永遠是空集合（沒有任何 InnoDB 交易），因此下面
        kill_sleep_connections 的行為與先前完全相同。

        Returns:
            set[int]: 執行緒 ID。
        """
        try:
            rows = self.select_record(
                "SELECT trx_mysql_thread_id FROM information_schema.INNODB_TRX"
            )
            return {
                int(row["trx_mysql_thread_id"])
                for row in rows
                if row.get("trx_mysql_thread_id") is not None
            }
        except Exception:
            # 伺服器停用 InnoDB 或無權限時，寧可保守一點：回傳 None 代表
            # 「無法判斷」，由呼叫端決定是否放棄擊殺
            return None

    def kill_sleep_connections(self, threshold=60):
        """
        殺掉所有與本資料庫有關、且閒置時間超過 threshold 秒的 Sleep 連線。

        InnoDB 注意事項：Sleep 狀態的連線可能正持有一個未提交的交易與一批
        row lock（idle in transaction）。殺掉它會讓對方的變更被回滾，而對方
        程式毫不知情。因此這裡會先查出 INNODB_TRX 中的執行緒並排除。

        MyISAM 客戶端的排除清單永遠為空，行為與改動前完全相同。

        Args:
            threshold (int): 超過這個秒數的 Sleep 連線會被終止，預設為 60 秒。
        """
        protected = self._get_transaction_thread_ids()
        if protected is None:
            # 無法判斷哪些連線持有交易時，只在確定不會誤傷的情況下才動作
            if self.is_transactional():
                print("⚠️ 無法查詢 INNODB_TRX，為避免中斷他人交易，略過清理連線。")
                return
            protected = set()

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
                    and row.get("db")
                    in (self.database, None)  # 確保是連到同一個資料庫或未指定的資料庫
                ):
                    process_id = row["Id"]

                    if int(process_id) in protected:
                        print(
                            f"⏭️ 跳過 ID {process_id}："
                            f"該連線持有未提交的交易，殺掉會讓對方的變更遺失。"
                        )
                        continue

                    print(
                        f"🔪 Killing sleep connection: ID {process_id}, User: {row['User']}, Host: {row['Host']}"
                    )
                    try:
                        # 沿用外層 cursor。原本在迴圈內另開 kill_cursor，
                        # execute 失敗時不會執行到 close()，每次失敗漏一個
                        # cursor。外層 cursor 是 buffered 且已 fetchall()，
                        # 沒有未讀結果，重用是安全的。
                        cursor.execute(f"KILL {process_id}")
                    except Exception as e:
                        print(f"❌ 無法刪除 ID {process_id}: {e}")
        finally:
            if cursor is not None:
                try:
                    if self.cnx and self.cnx.is_connected():
                        cursor.close()
                except Exception:
                    pass

    def add_index_if_not_exists(self, table_name, index_name, fields):
        """
        動態檢查並建立索引
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
            self.exec_sql(create_sql)
        else:
            # print(f"索引 {index_name} 已存在，跳過。")
            pass
