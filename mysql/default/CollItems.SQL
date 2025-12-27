
# 38-1. 處方集副檔 - 藥品內容   100.07.01 CollMedicine; Collection Detail 陳士源

CREATE TABLE IF NOT EXISTS CollItems                  # 原  CollectionSet
(
    CollectionSetKey  INT AUTO_INCREMENT NOT NULL,	# 處方集序號
    CollectionKey     INT,

    MedicineType	    VARCHAR(04),	  # 類別(詞庫為準): 單方,複方,水藥,外用
    MedicineKey	      INT,		        # 詞庫處方序號
    InsCode	          VARCHAR(12),	  # 健保碼                        //自購:購藥者
    MedicineName	    VARCHAR(40),    # 處方名稱

    Dosage	          Decimal(10, 2),	# 藥品用量; 健保:日劑量; 自費:一帖(包)劑量
    Unit		          VARCHAR(10),	  # 單位

    TimeStamp	        TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(CollectionSetKey),
    INDEX(CollectionKey)
) CHARACTER SET utf8;





