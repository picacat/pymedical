
# 37. 成方檔-處方詞庫

CREATE TABLE IF NOT EXISTS RefCompound
(
    RefCompoundKey  INT AUTO_INCREMENT NOT NULL, # 參考成方序號

    CompoundKey	    INT NOT NULL,	  # 詞庫成方序號, 處方詞庫檔內之成方
    MedicineKey	    INT,		        # 詞庫處方序號, 處方詞庫檔內之各藥品

    Quantity	      Decimal(10, 2),	# 藥品用量
    Unit		        VARCHAR(10),	  # 單位. 若處方是處置, 無用量與單位

    TimeStamp	      TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(RefCompoundKey),
    INDEX(CompoundKey)
) CHARACTER SET utf8;
