
# 38. 處方集 (組)   100.07.01  主檔
#     陳士源  Master

CREATE TABLE IF NOT EXISTS Collection
(
    CollectionKey   INT AUTO_INCREMENT NOT NULL,	# 處方集序號

    CollectionType1 VARCHAR(100),
    CollectionType2 VARCHAR(100),
    CollectionName  VARCHAR(100),
    CollectionCode  VARCHAR(10),

    ICDCode1	      VARCHAR(10),	# 病名碼 ICD9 / ICD10 5->10 103.09.10
    ICDCode2	      VARCHAR(10),	# 病名碼 ICD9 / ICD10 5->10 103.09.10
    ICDCode3	      VARCHAR(10),	# 病名碼 ICD9 / ICD10 5->10 103.09.10

    Symptom         VARCHAR(250),
    Tongue          VARCHAR(100),
    Pulse           VARCHAR(100),
    Distincts       VARCHAR(100),
    Cure            VARCHAR(100),

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(CollectionKey),
    INDEX(CollectionType1, CollectionType2, CollectionName)
) CHARACTER SET utf8;
