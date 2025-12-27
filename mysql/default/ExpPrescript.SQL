
# 39-1 驗方副檔 (處方)

CREATE TABLE IF NOT EXISTS ExpPrescript
(
    ExpPrescriptKey INT AUTO_INCREMENT NOT NULL,	# 驗方處方序號
    ExperienceKey	INT,   		    # 驗方序號

    MedicineType	VARCHAR(04),	# 類別(詞庫為準): 單方,複方,水藥,外用
				                    #                 高貴,藥丸,穴道,處置,器材,檢驗,檢自
    InsCode	        VARCHAR(12),	# 健保碼                        //自購:購藥者
    MedicineName	VARCHAR(40),	# 處方名稱

    Dosage	        Decimal(10, 2),	# 藥品用量; 健保:日劑量; 自費:一帖(包)劑量
    Unit		    VARCHAR(10),	# 單位
    Instruction     VARCHAR(10),	# 用藥指示
    Price 	        Decimal(10, 2), # 單價

    TimeStamp	      TIMESTAMP,	# 上次異動日期

    PRIMARY KEY(ExpPrescriptKey),
    INDEX(ExperienceKey)
) CHARACTER SET utf8;





