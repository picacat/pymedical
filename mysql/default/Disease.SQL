
# 33. 詞庫病名檔    100.07.01

CREATE TABLE IF NOT EXISTS Disease
(
    DiseaseKey	INT AUTO_INCREMENT NOT NULL,  # 病名序號

    ICDCode	    VARCHAR(10),	# 病名碼 ICD9
    ICD10Code   VARCHAR(10),	# 病名碼 ICD10   104.01.01 新增
    InputCode	  VARCHAR(05),	# 輸入碼 (注音碼)

    ChineseName	VARCHAR(100),	# 中文病名
    EnglishName	VARCHAR(100),	# 英文病名

    Position	  VARCHAR(40),	# 部位
    Symptom	    VARCHAR(40),	# 症狀 (分類)
    SpecialCode	VARCHAR(02),	# 專案代碼

    Description BLOB,         # 說明

    TimeStamp	  TIMESTAMP,	  # 上次異動日期

    PRIMARY KEY(DiseaseKey),
    INDEX(ICDCode, InputCode)
) CHARACTER SET utf8;


