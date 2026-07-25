import configparser
import os
import sys

import mysql.connector
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# convert_gui.py（含進度條 / 分批寫入 / 動態字元集 / 單表錯誤處理）
class MyISAMToInnoDBConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyISAM 轉換為 InnoDB 工具")
        self.resize(480, 420)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout()

        self.host_input = self._add_row(layout, "主機:", "")
        self.port_input = self._add_row(layout, "埠號:", "")
        self.user_input = self._add_row(layout, "使用者:", "")
        self.password_input = self._add_row(layout, "密碼:", "", is_password=True)
        self.source_input = self._add_row(layout, "來源資料庫:", "")
        self.target_input = self._add_row(layout, "目標資料庫:", "")

        # 批次大小設定
        batch_layout = QHBoxLayout()
        batch_label = QLabel("每批筆數:")
        self.batch_size_input = QSpinBox()
        self.batch_size_input.setRange(100, 100000)
        self.batch_size_input.setValue(5000)
        self.batch_size_input.setSingleStep(500)
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.batch_size_input)
        layout.addLayout(batch_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton("開始轉換")
        self.start_button.clicked.connect(self.convert)
        layout.addWidget(self.start_button)

        # 顯示處理過程與錯誤清單
        log_label = QLabel("處理紀錄:")
        layout.addWidget(log_label)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

    def _add_row(self, parent_layout, label_text, default_text="", is_password=False):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        input_field = QLineEdit()
        input_field.setText(default_text)
        if is_password:
            input_field.setEchoMode(QLineEdit.Password)
        layout.addWidget(label)
        layout.addWidget(input_field)
        parent_layout.addLayout(layout)
        return input_field

    def _load_config(self):
        config_file = os.path.join(os.path.dirname(__file__), "pymedical.conf")
        if not os.path.exists(config_file):
            QMessageBox.critical(self, "錯誤", f"找不到設定檔: {config_file}")
            return

        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")

        self.host_input.setText(config["db"].get("host", "localhost"))
        self.port_input.setText(config["db"].get("port", "3306"))
        self.user_input.setText(config["db"].get("user", "root"))
        self.password_input.setText(config["db"].get("password", ""))
        self.source_input.setText(config["db"].get("database", "pymedical"))
        self.target_input.setText(config["db"].get("inno_database", "pymedical_innodb"))

    def _log(self, msg):
        self.log_box.append(msg)
        QApplication.processEvents()

    def convert(self):
        conn = None
        try:
            host = self.host_input.text()
            port = int(self.port_input.text())
            user = self.user_input.text()
            password = self.password_input.text()
            source_db = self.source_input.text()
            target_db = self.target_input.text()
            batch_size = self.batch_size_input.value()

            if not source_db or not target_db:
                QMessageBox.warning(self, "提示", "請確認來源與目標資料庫名稱已填寫。")
                return

            if source_db == target_db:
                QMessageBox.warning(
                    self, "提示", "來源與目標資料庫不可相同，避免覆蓋原始資料。"
                )
                return

            self.log_box.clear()
            self.start_button.setEnabled(False)

            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                connection_timeout=10,
            )
            cursor = conn.cursor()

            # 動態抓取來源資料庫的字元集與校對規則，避免中文資料寫入時亂碼
            cursor.execute(
                "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (source_db,),
            )
            row = cursor.fetchone()
            if not row:
                QMessageBox.critical(self, "錯誤", f"找不到來源資料庫: {source_db}")
                return
            charset, collation = row
            self._log(f"來源資料庫字元集: {charset} / {collation}")

            # 建立目標資料庫，沿用來源字元集而非寫死 utf8mb4
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{target_db}` "
                f"DEFAULT CHARACTER SET {charset} COLLATE {collation}"
            )

            # 找出 MyISAM 表格，順便取得各表筆數，用於後續分批與比對
            cursor.execute(
                """
                SELECT TABLE_NAME, TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND ENGINE = 'MyISAM'
            """,
                (source_db,),
            )
            tables = cursor.fetchall()
            total = len(tables)

            if not tables:
                QMessageBox.information(self, "完成", "來源資料庫中沒有 MyISAM 表格。")
                return

            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)

            failed_tables = []
            success_tables = []

            for i, (table, _approx_rows) in enumerate(tables):
                self._log(f"\n[{i + 1}/{total}] 處理表格: {table}")
                try:
                    # 每張表獨立 cursor + 交易，避免單表失敗影響整體狀態
                    work_cursor = conn.cursor()

                    work_cursor.execute(f"SHOW CREATE TABLE `{source_db}`.`{table}`")
                    create_sql = work_cursor.fetchone()[1]
                    create_sql = create_sql.replace(
                        f"CREATE TABLE `{table}`",
                        f"CREATE TABLE `{target_db}`.`{table}`",
                    )
                    create_sql = create_sql.replace("ENGINE=MyISAM", "ENGINE=InnoDB")

                    # 若目標表已存在（例如重跑），先記錄但不直接覆蓋，避免誤刪資料
                    work_cursor.execute(
                        "SELECT COUNT(*) FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                        (target_db, table),
                    )
                    exists = work_cursor.fetchone()[0] > 0
                    if exists:
                        self._log("  目標表已存在，略過建表，僅檢查資料。")
                    else:
                        work_cursor.execute(create_sql)
                        self._log("  已建立 InnoDB 表格結構。")

                    # 取得來源實際筆數（TABLE_ROWS 對 MyISAM 通常準確，但仍以 COUNT(*) 確認）
                    work_cursor.execute(f"SELECT COUNT(*) FROM `{source_db}`.`{table}`")
                    source_count = work_cursor.fetchone()[0]

                    work_cursor.execute(f"SELECT COUNT(*) FROM `{target_db}`.`{table}`")
                    target_count = work_cursor.fetchone()[0]

                    if target_count >= source_count > 0:
                        self._log(
                            f"  資料筆數已一致（{target_count}/{source_count}），略過複製。"
                        )
                    else:
                        # 分批複製，避免大表一次性 INSERT 造成長交易、鎖表或記憶體問題
                        copied = target_count
                        while copied < source_count:
                            work_cursor.execute(
                                f"INSERT INTO `{target_db}`.`{table}` "
                                f"SELECT * FROM `{source_db}`.`{table}` "
                                f"LIMIT {batch_size} OFFSET {copied}"
                            )
                            conn.commit()
                            copied += batch_size
                            self._log(
                                f"  已複製約 {min(copied, source_count)}/{source_count} 筆..."
                            )

                    # 最終比對筆數，確認轉換完整
                    work_cursor.execute(f"SELECT COUNT(*) FROM `{target_db}`.`{table}`")
                    final_count = work_cursor.fetchone()[0]
                    if final_count != source_count:
                        raise RuntimeError(
                            f"筆數不一致：來源 {source_count} 筆，目標 {final_count} 筆"
                        )

                    self._log(f"  完成，筆數核對相符（{final_count} 筆）。")
                    success_tables.append(table)
                    work_cursor.close()

                except Exception as table_err:
                    conn.rollback()
                    self._log(f"  ⚠ 失敗: {table_err}")
                    failed_tables.append((table, str(table_err)))

                self.progress_bar.setValue(i + 1)

            cursor.close()

            summary = f"成功: {len(success_tables)} 張，失敗: {len(failed_tables)} 張。"
            self._log(f"\n=== 轉換結束 === {summary}")

            if failed_tables:
                detail = "\n".join(f"- {t}: {e}" for t, e in failed_tables)
                self._log(f"失敗清單:\n{detail}")
                QMessageBox.warning(
                    self,
                    "部分完成",
                    f"{summary}\n\n失敗的表格請查看下方紀錄，修正問題後可重新執行（已成功的表格會自動略過）。",
                )
            else:
                QMessageBox.information(self, "轉換完成", summary)

        except Exception as e:
            self._log(f"⚠ 發生錯誤: {e}")
            QMessageBox.critical(self, "錯誤", f"轉換失敗：\n{e!s}")
        finally:
            self.start_button.setEnabled(True)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyISAMToInnoDBConverter()
    window.show()
    sys.exit(app.exec_())
