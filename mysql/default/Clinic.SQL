
# 32. 診察詞庫檔    100.07.01

CREATE TABLE IF NOT EXISTS Clinic
(
    ClinicKey	  INT AUTO_INCREMENT NOT NULL,  # 診察序號
    ClinicType  VARCHAR(04),	# 脈象, 舌診, 辨證, 備註, 指示(用藥), 醫囑(94.07.11診斷證明)
                        	    # 主訴(內科, 傷科, 婦科)
                              # 內辨, 傷辨 (辨證詞庫)
                              # 內治, 傷治 (治則詞庫, 點選用)

                              # 禁忌 (飲食) 97.03.13 福德
                              # 會計 (科目) 97.06.30 福安堂
                              # 新資 (科目) 97.06.30 福安堂
                              # 副作 (藥袋標示) 98.11.27 建宏
                              # 警語 (藥袋標示) 98.11.27 建宏

                              # 99.10.13 Used PatInitial.Dll 初診照護
                              # 初斷(診斷), 初照(自我照顧指導), 初飲(飲食宜忌指導)

    ClinicCode	VARCHAR(05),	# 診察碼
    InputCode	  VARCHAR(05),	# 輸入碼 (注音碼)
    ClinicName	VARCHAR(40),	# 診察名稱, 指示(用藥, 10 Bytes)
    Position	  VARCHAR(40),	# 診察部位, 辨證內治則
                              # 金額->新資 (科目)

    Groups	    VARCHAR(40),  # 分類 (診察名稱 belong to ??)

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ClinicKey),
    INDEX(ClinicCode, InputCode)
) CHARACTER SET utf8;


