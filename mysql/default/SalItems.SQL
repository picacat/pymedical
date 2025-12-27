
# 42-1. 每月薪資檔  100.07.01
CREATE TABLE IF NOT EXISTS SalItems
(
    SalItemsKey  INT AUTO_INCREMENT NOT NULL,  #薪資序號

    SalaryKey   INT,            #薪資序號
    ItemNo      INT,            #項次
    ItemCode    VARCHAR(5),     #科目代號
    Item        VARCHAR(20),    #項目
    Amount	    INT,	        #金額
    Remark	    VARCHAR(100),   #備註

    TimeStamp	TIMESTAMP,      #上次異動日期

    PRIMARY KEY(SalItemsKey),
    INDEX(SalaryKey, ItemNo)
) CHARACTER SET utf8;

