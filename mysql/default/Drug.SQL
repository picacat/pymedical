
# 35. 健保藥品檔 	100.07.01

CREATE TABLE IF NOT EXISTS Drug
(
    DrugKey	    INT AUTO_INCREMENT NOT NULL,  # 健保藥品序號

    InsCode	    VARCHAR(12),	# 健保碼
    DrugName	  VARCHAR(40),	# 藥品名稱

    Unit		    VARCHAR(10),	# 單位, 劑型
    InsPrice	  Decimal(10, 2), # 5.健保價
    Supplier	  VARCHAR(10),	# 廠商

    ValidDate   Date,         # 有效期限  轉檔後已合理化, 除非空白

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(DrugKey),
    INDEX(InsCode)
) CHARACTER SET utf8;


