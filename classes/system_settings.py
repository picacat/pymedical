# -*- coding: UTF-8 -*-

import configparser

from PyQt5.QtWidgets import QMessageBox

from libs import system_utils


# 系統設定
class SystemSettings:
    # 初始化
    def __init__(self, database, config_file, station_no=None):
        self.database = database
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

        if station_no is None:
            self.station_no = self.config["settings"]["station_no"]
            if not self.station_no.isdigit():
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "設定檔內容有誤",
                    '<font color="red"><h3>系統設定conf檔工作站編號錯誤, 請重新設定!</h3></font>',
                    "請修正系統設定Conf檔.",
                )
                self.station_no = 1
        else:
            self.station_no = station_no

    # 解構
    def __del__(self):
        pass

    # 讀取設定檔
    def field(self, field_name):
        station_no = self.get_station_no(field_name)
        if field_name == "工作站編號":
            return station_no

        sql = f'''
            SELECT Value FROM system_settings
            WHERE
                StationNo = {station_no} AND
                Field = "{field_name}"
        '''
        try:
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return None
            else:
                return rows[0]["Value"]
        except Exception:
            return None

    # 寫入設定檔
    def post(self, field_name, value):
        if field_name == "工作站編號":
            self.config.set("settings", "station_no", value)
            with open(self.config_file, "w") as configfile:
                self.config.write(configfile)

            return

        station_no = self.get_station_no(field_name)

        script = f'''
            SELECT * FROM system_settings
            WHERE
                StationNo = {station_no} AND
                Field = "{field_name}"
            LIMIT 1
        '''
        try:
            setting_row = self.database.select_record(script)[0]
            if value == setting_row["Value"]:
                return

            self.database.update_record(
                "system_settings",
                ["Value"],
                "SystemSettingsKey",
                setting_row["SystemSettingsKey"],
                [value],
            )
        except IndexError:
            fields = ["StationNo", "Field", "Value"]
            data = [station_no, field_name, value]
            self.database.insert_record("system_settings", fields, data)

    def remove(self, field_name):
        station_no = self.get_station_no(field_name)

        script = f'''
            DELETE  FROM system_settings
            WHERE
                StationNo = {station_no} AND
                Field = "{field_name}"
        '''
        try:
            self.database.exec_sql(script)
        except Exception:
            pass

    # 取得工作站編號
    def get_station_no(self, field_name):
        if field_name in [
            "院所名稱",
            "院所代號",
            "統一編號",
            "健保業務",
            "負責醫師",
            "醫師證號",
            "開業證號",
            "院所電話",
            "院所地址",
            "資源類別",
            "巡迴區域",
            "掛號類別",
            "矯正機關",
            "劑量上限",
            "最低劑量",
            "6歲以下最低劑量",
            "預設空白自費頁",
            "健保用藥成本上限",
            "無折扣批價計算",
            "自費折扣方式",
            "自費折扣進位",
            "自費折扣尾數",
            "手動批價",
            "視訊診療須經過批價作業",
            "同自費只算一筆",
            "櫃台結帳列出未完診名單",
            "櫃台結帳班別",
            "療程不同病名不能存檔",
            "內科同病名超過3次",
            "開藥連續三次相同不能存檔",
            "用藥重複二日不能存檔",
            "行動電話必填",
            "隔日過卡不能存檔",
            "療程同病名超過兩個",
            "部份負擔連動",
            "病歷查詢日期排序",
            "預設中度複雜性針灸治療時間",
            "預設高度複雜性針灸治療時間",
            "預設中度複雜性傷科治療時間",
            "預設高度複雜性傷科治療時間",
            "民俗調理單地址",
            "民俗調理單電話",
            "民俗調理單備註",
            "alleypin",
            "appID",
            "secret",
            "webhook",
            "hainachuan",
            "webservice",
            "虛擬健保卡授權憑證",
            "電子郵件",
            "早班時間",
            "午班時間",
            "晚班時間",
            "護士人數",
            "藥師人數",
            "申報藥事服務費",
            "申報初診照護",
            "新特約期間",
            "針灸認證合格",
            "針灸認證合格日期",
            "電子化抽審初診日期",
            "新診所初診日期",
            "當日用藥重複檢查次日起算",
            "檢查損傷診斷碼",
            "相同診斷碼用藥天數",
            "分班",
            "分診",
            "早班起始號",
            "午班起始號",
            "晚班起始號",
            "領藥起始號",
            "現場掛號給號模式",
            "指定診別起始號",
            "預約選擇當診醫師",
            "預約班表不顯示時間",
            "預約報到給號模式",
            "掛號收費批價進行",
            "拷貝處方藥價更新",
            "預設門診類別",
            "首次警告次數",
            "針傷警告次數",
            "自購藥銷售人員",
            "欠卡日期檢查範圍",
            "掛號選擇當診醫師",
            "掛號療程14日未完成提醒",
            "療程中斷不續療程",
            "掛號過去病歷顯示主訴",
            "掛號過去病歷顯示民俗調理",
            "自動帶出民俗調理費",
            "療程首次民俗調理費",
            "候診名單顯示自費民俗調理",
            "掛號診號不可重複",
            "掛號作業顯示初診統計",
            "掛號新療程自動帶出上次就醫類別",
            "診斷資料必填",
            "欠款未還不能掛號",
            "顯示次診斷3",
            "掛號名單顯示民俗調理費",
            "過去病歷顯示推拿師父",
            "外觀主題",
            "老人優待",
            "老人優待年齡",
            "兒童優待",
            "兒童優待年齡",
            "釋出預約號",
            "同日預約兩次",
            "預約次數限制",
            "爽約天數",
            "爽約期間",
            "爽約次數",
            "檢驗所伺服器",
            "檢驗所用戶代碼",
            "檢驗所密碼",
            "檢查療程開藥超過1次",
            "療程開藥超過1次存檔",
            "健保自費分開",
            "自費水藥批價原則",
            "列印院所名稱",
            "列印推拿師父",
            "列印預約號碼",
            "醫療費用證明書抬頭",
            "收費收據列印劑量",
            "自費收據列印日量",
            "處方箋列印總量",
            "列印藥品存放位置",
            "列印藥品存放位置在處方名稱前面",
            "列印病歷備註",
            "列印主訴字數限制",
            "列印主訴字數",
            "列印處方字數限制",
            "列印處方字數",
            "列印處方別名",
            "列印民俗調理",
            "掛號收據無金額不列印",
            "列印穴道處置",
            "列印針傷處置名稱",
            "列印診斷證明日期明細",
            "自費同意書自費1金額",
            "民俗調理項目名稱",
            "病歷存檔列印順序",
            "列印所有收費收據費用明細",
            "自訂適應症",
            "醫療費用證明自費藥費欄位名稱",
            "醫療費用證明自費處置欄位名稱",
            "醫療費用證明其他費用欄位名稱",
            "醫療費用證明自費金額欄位名稱",
            "醫療費用自付明細自費金額欄位名稱",
            "列印報表雙色印刷",
            "醫療費用證明預設金額",
            "列印預設字體",
            "媒體播放來源",
            "媒體播放位址",
            "媒體播放音量",
            "叫號不包含診療室",
            "叫號包含病患姓名",
            "封存資料庫名稱",
            "候診系統顯示器編號",
            "門診表圖檔名",
            "固定圖檔名",
            "調整庫存量",
            "處方列印方向",
            "電子處方箋格式",
            "列印所有收費收據各自金額",
            "掛號已就診名單顯示自購藥病歷",
            "診察費抽成率",
            "診療費抽成率",
            "自費藥品抽成率",
            "自費針傷抽成率",
            "自訂叫號格式",
            "醫師候診名單欄位固定寬度",
            "處方詞庫僅列出水藥",
            "慢性病開藥檢查",
            "醫師候診名單只顯示當班預約資料",
            "預約網站後台帳號",
            "預約網站後台密碼",
            "診察費抽成類別",
            "診療費抽成類別",
            "自費藥品抽成類別",
            "自費針傷抽成類別",
            "顯示備忘錄",
            "病歷查詢預設健保",
            "病名詞庫預設類別",
            "預設就醫類別",
            "病歷查詢一頁筆數",
            "病歷查詢顯示合計",
            "還卡期限",
            "自費處方預設計價方式",
            "開放當日網路預約",
            "網路預約開放週數",
            "當日可以取消網路預約",
            "望聞問切輸入碼預設英數",
            "診斷碼輸入法預設中文",
            "掛號候診名單排序方式",
            "醫療費用總表合併處置費至藥費",
            "處方輸入編輯模式",
            "自動產生病歷號",
            "民俗調理收據抬頭",
            "日期格式",
            "詞庫視窗顯示方式",
            "健保處方給藥劑量上限檢查時機",
            "健保用藥成本上限檢查時機",
            "輪播圖片間隔秒數",
            "預約次數不同醫師分別計算",
            "健保IC卡資料上傳格式",
            "病歷存檔檢查醫師姓名",
            "舌診1",
            "舌診2",
            "舌診3",
            "舌診4",
            "舌診5",
            "脈象1",
            "脈象2",
            "脈象3",
            "脈象4",
            "脈象5",
            "脈象6",
            "脈象7",
            "脈象8",
            "脈象9",
            "脈象10",
            "病歷查詢檢視方式",
            "輸入進貨資料同步更新藥品進價",
            "健保開藥劑量必須大於0",
            "自費開藥劑量必須大於0",
            "自訂院所名稱",
            "匯出電子病歷包含自費病歷",
            "預約遲到寫入掛號備註",
            "預約名單顯示上次病歷備註",
            "不印報稅提示",
            "不印折扣",
            "網路預約不顯示看診進度",
            "列印條碼",
            "列印處方依照存放位置排序",
            "療程開藥兩次以上提醒",
            "刪除處方啟用彈出式選單",
            "在掛號機批價繳費",
            "使用測試環境",
            "診號累加器最大號",
            "電子秤測重時間",
            "候診名單只顯示名字",
            "不開放初診網路預約",
            "統計醫師看診人數",
            "叫號同時啟動叫號燈",
            "病歷存檔檢查補退掛號費用",
            "處方無存放位置淡色顯示",
            "健保處方詞庫只顯示單方複方",
            "備忘錄以病患鍵為主",
            "日期查詢預設為昨日",
            "自費處方次劑量",
            "線上看診號同步",
            "列印印花稅總繳",
            "自動登入",
            "伺服器資料來源",
            "欠卡申報點數檢查",
            "檢查門診負擔多退少補",
            "SAMID",
            "費用收據不印處方",
            "處方箋不印費用明細",
            "醫療費用收據自訂報稅備註",
            "單一處方服法不可取代用藥天數",
            "輸入病名後不要彈出複雜性針傷提示視窗",
            "開立費用證明不要列出民俗調理",
            "民俗調理欄位名稱",
            "預約過號寫入掛號備註",
            "廣播叫號同步所有線上看診號",
            "預約過號顯示過號序號",
            "掛號診別更改不要連動醫師姓名",
            "單日計價輸入藥品不要歸零",
            "叫號包含下一位請準備",
            "所有資料都已批價才能結帳",
            "優先遞補現場號",
            "不要轉換一般針灸",
            "不申報高度複雜性傷科",
            "庫存量不足不要提醒",
            "使用docker",
            "不申報傷科治療",
            "最少針灸穴道數",
            "不要顯示停用的藥品",
            "預約班表顯示剩餘次數",
            "列印科中處方依照存放位置排序",
            "掛號醫師不在醫師班表",
        ]:
            station_no = 0
        else:
            station_no = self.station_no

        if "指定診別起始號" in field_name:
            station_no = 0
        if "跑馬燈訊息" in field_name:
            station_no = 0
        if "輪播圖片檔" in field_name:
            station_no = 0
        if "輪播影片檔" in field_name:
            station_no = 0

        return station_no
