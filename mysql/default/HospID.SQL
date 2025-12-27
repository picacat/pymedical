
# 54. 醫療院所檔	100.07.01

CREATE TABLE IF NOT EXISTS HospID
(
    HospKey	  INT AUTO_INCREMENT NOT NULL,  # 密碼序號

    HospID	  VARCHAR(10),	# 院所代號
    HospName	VARCHAR(50),# 院所名稱

    Telephone VARCHAR(15),  #
    Address   VARCHAR(50),  # 聯絡地址

    TimeStamp	TIMESTAMP,	# 上次易動日期

    PRIMARY KEY(HospKey),
    INDEX(HospID)
) CHARACTER SET utf8;


