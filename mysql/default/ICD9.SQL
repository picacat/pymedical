
# 33-1. 國際病名檔 	100.07.01

CREATE TABLE IF NOT EXISTS ICD9
(
    ICD9Key	    INT AUTO_INCREMENT NOT NULL,  # 病名序號

    ICD9Code	VARCHAR(10),	  # 病名碼 ICD
    ChineseName	VARCHAR(100),	# 中文病名
    EnglishName	VARCHAR(100),	# 英文病名
  
    Remark    	VARCHAR(50),	# 備註

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ICD9Key),
    INDEX(ICD9Code)
) CHARACTER SET utf8;
