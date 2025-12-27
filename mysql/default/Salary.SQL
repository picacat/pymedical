
# 42. 每月薪資檔 	100.07.01
CREATE TABLE IF NOT EXISTS Salary
(
    SalaryKey   INT AUTO_INCREMENT NOT NULL,  #薪資序號

    PayDate     VARCHAR(08),    # 薪資月份 YYYYMMxx(西元) 20051200 DD-期別 00-全月/不分

    PersonKey   INT,	        # 員工編號
    Name        VARCHAR(20),	# 員工
    Amount      INT,	        # 實領薪資
    Remark	    VARCHAR(100),   # 備註

    TimeStamp   TIMESTAMP,      # 上次異動日期

    PRIMARY KEY(SalaryKey),
    INDEX(PayDate, PersonKey)
) CHARACTER SET utf8;







