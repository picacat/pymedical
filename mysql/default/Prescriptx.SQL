
# 04. 病歷處方檔    刪除備份用

CREATE TABLE IF NOT EXISTS Prescriptx
(
    PrescriptKey	INT AUTO_INCREMENT NOT NULL,  # 處方序號
    PrescriptNo     Int,            # 處方編號, 每次讀取排序專用

    CaseKey	        INT NOT NULL,	# 病歷序號
    CaseDate	    DATETIME,	    # 門診日期
    MedicineSet	    INT DEFAULT 0,  # 組別-健保:1; 自費1-5:2,3,4,5,6; 處置:1,2; 自購:99

    MedicineType    VARCHAR(04),	# 類別(詞庫為準): 單方, 複方, 水藥, 外用
				                    #   高貴, 藥丸, 穴道, 處置, 器材, 檢驗, 檢自
                                    #   複成(成方名稱, 翰林專用)
    MedicineKey	    INT,	        # 詞庫處方序號
    InsCode	        VARCHAR(12),	# 健保碼    自購:購藥者
    MedicineName    VARCHAR(40),    # 處方名稱

    DosageMode      VARCHAR(04),	# 劑量模式: 日量(一般用, Default)/次量/總量
    Dosage	        Decimal(10, 2)  DEFAULT 0,   # 藥品用量     申報時依劑量模式 => 次量
    Unit		    VARCHAR(10),	# 單位
    Instruction     VARCHAR(40),	# 用藥指示

    Price 	        Decimal(10, 2) DEFAULT 0,   # 單價
    Amount        	Decimal(10, 2) DEFAULT 0,   # 金額

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(PrescriptKey),
    INDEX(CaseKey, CaseDate)
) CHARACTER SET utf8;


