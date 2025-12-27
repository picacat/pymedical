
# 病理資料檔    102.07.01   Relative to Cases

CREATE TABLE IF NOT EXISTS Pathologic
(
    PathologicKey	  INT AUTO_INCREMENT NOT NULL,	# 病理序號

    CaseKey	    INT NOT NULL,		# 病歷序號

    Height	    Decimal(10, 2),	# 身高  cm
    Weight	    Decimal(10, 2),	# 體重  kg    show BMI
    Temperature Decimal(10, 2), # 體溫  Celsuis

    HeartBeat   INT,            # 心跳
    BPHigh	    INT,		        # 收縮壓
    BPLow 	    INT,		        # 舒張壓

    BloodSugarAC INT,		        # 飯前血糖 102.07.01
    BloodSugarPC INT,		        # 飯後血糖

    Fat   	    Decimal(10, 2),	# 體脂肪

    Remark	    BLOB,           # 備註

    TimeStamp	  TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(PathologicKey),
    INDEX(CaseKey)
) CHARACTER SET utf8;


