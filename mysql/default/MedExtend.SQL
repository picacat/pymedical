
# 34-1. 藥品擴充檔 	100.07.01
#    列印專用

CREATE TABLE IF NOT EXISTS MedExtend
(
    MedExtendKey	INT AUTO_INCREMENT NOT NULL,  # 健保藥品序號

    MedicineKey     INT,	        # 藥品序號
    ExtendType   VARCHAR(10),     # 類別: 適應症, 警語, 副作用, 作用(功效,正面).
                                  #       抽成比例 (% 99.09.03 福丞堂)
                                  #       停用, 供應廠商, 劑量上限
                                  #       預設劑量 (103.12.12 九條城)
    Description	    VARCHAR(100),	# 一般說明
                                  #       開始停用日期 yyyy/mm/dd (西元年)

    TimeStamp	    TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(MedExtendKey),
    INDEX(MedicineKey, ExtendType)
) CHARACTER SET utf8;
