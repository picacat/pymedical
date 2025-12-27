
# 03-1. 病歷擴充檔 	100.07.01

CREATE TABLE IF NOT EXISTS CaseExtend
(
    CaseExtendKey INT AUTO_INCREMENT NOT NULL,  # 病歷序號

    CaseKey       INT,	        # 病歷序號
    ExtendType    VARCHAR(10),  # 類別:
                                #   收費收據 (含收費證明) 105.01.18 育源堂

                                #   精準脈點左, 精準脈點右: 27 = 1 * 3 cols *9 rows (Y/N)
                                #   精準脈名左, 精準脈名右: 90 = 10* 9 rows
                                #   精準脈象左, 精準脈象右: 90 = 30* 3 rows
                                #   精準備註

                                #   99.09.29 陳立德 華陽
                                #   藥品未領: Content 存 CaseDate + 包 * 天
                                #   藥負未清: Content 存 CaseDate + 金額

                                #   巡迴地區 100.01.03
                                #   IC診療時間: 診療資料寫入IC卡時間 100.01.14 歧伯齋
                                #               格式: YYYMMDDHHMMSS 民國年
                                #   EMRDate (電子病歷匯出日期) 16.04.25
                                #
                                # 給藥上限 Control.DrugLimit      新竹 16.12.12
                                #   處方比例總量 Prescript.Ratio

    Content	      VARCHAR(100),	# 內容
                                # 收費收據: 日期 yyyymmdd   105.01.18 育源堂
    PRIMARY KEY(CaseExtendKey),
    INDEX(CaseKey, ExtendType)
) CHARACTER SET utf8;

#*******************************************************************************

