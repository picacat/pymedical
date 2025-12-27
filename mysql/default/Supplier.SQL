
# 55. 廠商資料檔 	100.07.01

CREATE TABLE IF NOT EXISTS Supplier
(
    SupplierKey	INT AUTO_INCREMENT NOT NULL,  # 廠商序號
    Name		VARCHAR(20),	# 廠商名稱
    Code		VARCHAR(05),	# 代碼

    Telephone	VARCHAR(15),	# 聯絡電話
    Cellphone	VARCHAR(15),	# 行動電話
    Address	    VARCHAR(50),	# 地址
    Remark	    BLOB,           # 備註

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(SupplierKey),
    INDEX(Code)
) CHARACTER SET utf8;


