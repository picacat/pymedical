
# 56. 詞庫地址檔    100.07.01

CREATE TABLE IF NOT EXISTS Address
(
    AddressKey	INT AUTO_INCREMENT NOT NULL,  # 地址序號
    Code		VARCHAR(05),	  # 代碼
    Name		VARCHAR(50),	  # 地址名稱

    TimeStamp	TIMESTAMP,	  # 上次異動日期

    PRIMARY KEY(AddressKey),
    INDEX(Code)
) CHARACTER SET utf8;


