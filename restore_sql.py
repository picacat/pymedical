import os
import subprocess
import json
import mysql.connector

DEFAULT_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "620210",
    "database": "tongde",
    "sql_folder": "~/_temp/20250922"
}

CONFIG_FILE = "config.json"

def create_default_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=4)
    print(f"⚠️ 找不到 {CONFIG_FILE}，已建立預設設定檔。")
    print("請編輯 config.json 後重新執行本程式。")
    exit(0)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def ensure_database_exists(config):
    try:
        connection = mysql.connector.connect(
            host=config.get('host', 'localhost'),
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        if config['database'] not in databases:
            print(f"📦 資料庫 `{config['database']}` 不存在，正在建立...")
            cursor.execute(f"CREATE DATABASE `{config['database']}`")
            print("✅ 資料庫已建立。")
        else:
            print(f"🔍 資料庫 `{config['database']}` 已存在。")
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"❌ 無法連線資料庫或建立資料庫：{err}")
        exit(1)

def restore_all_sql_in_folder(folder, config):
    db_user = config['user']
    db_pass = config['password']
    db_name = config['database']

    sql_files = [f for f in os.listdir(folder) if f.endswith('.sql')]
    total = len(sql_files)
    if total == 0:
        print("⚠️ 沒有找到任何 .sql 檔案！請確認備份資料夾內容正確。")
        exit(1)

    print(f"\n💾 開始匯入 SQL 檔案，共 {total} 個...\n")
    for idx, sql_file in enumerate(sql_files, 1):
        full_path = os.path.join(folder, sql_file)
        percent = idx / total
        bar_length = 30
        filled = int(percent * bar_length)
        bar = '#' * filled + '.' * (bar_length - filled)
        text = f"[{bar}] {idx}/{total} 匯入 {sql_file}"
        print(text.ljust(80), end='\r')

        cmd = f'mysql -u {db_user} -p{db_pass} {db_name} < "{full_path}"'

        subprocess.run(cmd, shell=True)

    print("\n✅ 所有資料表已還原完成！")

if __name__ == '__main__':
    config = load_config()

    sql_folder = config.get('sql_folder')
    if not sql_folder or not os.path.exists(sql_folder):
        print("⚠️ sql_folder 設定錯誤或資料夾不存在，請修改 config.json 中的 sql_folder 路徑。")
        exit(1)

    ensure_database_exists(config)
    restore_all_sql_in_folder(folder=sql_folder, config=config)
