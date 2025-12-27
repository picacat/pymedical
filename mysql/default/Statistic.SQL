
# 50. 統計資料  101.02.10

CREATE TABLE IF NOT EXISTS Statistic
(
    StatisticKey	INT AUTO_INCREMENT NOT NULL,  # 統計資料序號

    StatType        VARCHAR(10),    # 類別: 異常分析, ...
    StatDate        Date,           # 統計日期: 執行時間
    FieldName       VARCHAR(20),    # 統計欄位
    Value	          VARCHAR(20),	  # 統計值 (123.05%,  12345/12345, ...)

    PRIMARY KEY(StatisticKey),
    INDEX(StatType, StatDate)
) CHARACTER SET utf8;
