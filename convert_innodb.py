# convert_gui.py（含進度條）

import sys
import configparser
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QHBoxLayout, QProgressBar
)
import mysql.connector
import os


class MyISAMToInnoDBConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyISAM 轉換為 InnoDB 工具")
        self.resize(400, 240)
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

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton("開始轉換")
        self.start_button.clicked.connect(self.convert)
        layout.addWidget(self.start_button)

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
        config.read(config_file, encoding='utf-8')

        self.host_input.setText(config['db'].get('host', 'localhost'))
        self.port_input.setText(config['db'].get('port', '3306'))
        self.user_input.setText(config['db'].get('user', 'root'))
        self.password_input.setText(config['db'].get('password', ''))
        self.source_input.setText(config['db'].get('database', 'pymedical'))
        self.target_input.setText(config['db'].get('inno_database', 'pymedical_innodb'))

    def convert(self):
        try:
            host = self.host_input.text()
            port = int(self.port_input.text())
            user = self.user_input.text()
            password = self.password_input.text()
            source_db = self.source_input.text()
            target_db = self.target_input.text()

            conn = mysql.connector.connect(
                host=host, port=port, user=user, password=password
            )
            cursor = conn.cursor()

            # 建立目標資料庫
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {target_db} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")

            # 找出 MyISAM 表格
            cursor.execute(f"""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND ENGINE = 'MyISAM'
            """, (source_db,))
            tables = [row[0] for row in cursor.fetchall()]
            total = len(tables)

            if not tables:
                QMessageBox.information(self, "完成", "來源資料庫中沒有 MyISAM 表格。")
                return

            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)

            for i, table in enumerate(tables):
                cursor.execute(f"SHOW CREATE TABLE {source_db}.{table}")
                create_sql = cursor.fetchone()[1]
                create_sql = create_sql.replace(f'CREATE TABLE `{table}`', f'CREATE TABLE `{target_db}`.`{table}`')
                create_sql = create_sql.replace('ENGINE=MyISAM', 'ENGINE=InnoDB')
                cursor.execute(create_sql)
                cursor.execute(f"INSERT INTO {target_db}.{table} SELECT * FROM {source_db}.{table}")
                self.progress_bar.setValue(i + 1)

            cursor.close()
            conn.close()

            QMessageBox.information(self, "轉換完成", f"{total} 張表格已成功轉為 InnoDB！")

        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"轉換失敗：\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyISAMToInnoDBConverter()
    window.show()
    sys.exit(app.exec_())
