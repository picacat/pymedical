
# 11-詞庫病名檔 	104.01.01   for ICD10       void 104.10.24 use ICD10

CREATE TABLE IF NOT EXISTS Disease10
(
    DiseaseKey	INT AUTO_INCREMENT NOT NULL,  # 病名序號

    ICDCode	    VARCHAR(10),	# 病名碼 ICD10
    ICD9Code    VARCHAR(10),	# 病名碼 ICD9  
    InputCode 	VARCHAR(05),	# 輸入碼 (注音碼)

    ChineseName	VARCHAR(100),	# 中文病名
    EnglishName	VARCHAR(100),	# 英文病名

    Position	  VARCHAR(40),  # 部位
    Symptom	    VARCHAR(40),	# 症狀 (分類)
    SpecialCode	VARCHAR(02),	# 專案代碼

    Description BLOB,         # XML format: <針傷部位1>4A</針傷部位1><針傷部位2>4B</針傷部位2>

    TimeStamp	  TIMESTAMP,	  # 上次異動日期

    PRIMARY KEY(DiseaseKey),
    INDEX(ICDCode, InputCode)
);

