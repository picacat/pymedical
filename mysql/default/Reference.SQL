
# 36. 參考處方檔 (病名) 100.07.01  主檔

CREATE TABLE IF NOT EXISTS Reference
(
    ReferenceKey    INT AUTO_INCREMENT NOT NULL,	# 參考處方序號
    ICDCode	        VARCHAR(10) NOT NULL,	# 病名碼 ICD9 / ICD10 5->10 103.09.10
    ICD10Code	      VARCHAR(10),	# 病名碼 ICD 104.10.19

    RefSet	        INT,		      # 參考處方組別
    RefSetName	    VARCHAR(40),	# 參考處方組別名稱
    RefSetDoctor    VARCHAR(10),  # 參考處方醫師  姓名, 公用處方

    RefSymptom	    BLOB,	        # 主訴
    RefTongue	      BLOB,	        # 舌診
    RefPulse 	      BLOB,	        # 脈象

    TimeStamp	      IMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ReferenceKey),
    INDEX(ICDCode)
) CHARACTER SET utf8;





