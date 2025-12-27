
# 36-2. 參考醫令檔 	(參考處方檔 Reference 副檔)   100.07.01

CREATE TABLE IF NOT EXISTS RefPrescript
(
    RefPrescriptKey INT AUTO_INCREMENT NOT NULL,	# 參考醫令序號
    ReferenceKey    INT,		    # 參考處方序號

    MedicineKey	    INT,		    # 詞庫醫令序號, 處方詞庫檔內之各藥品
    Quantity	    Decimal(10, 2), # 藥品用量
    Unit		    VARCHAR(10),    # 單位. 若處方是處置, 無用量與單位

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(RefPrescriptKey),
    INDEX(ReferenceKey)
) CHARACTER SET utf8;





