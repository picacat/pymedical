# waiting room sequence list for web
CREATE TABLE IF NOT EXISTS ClinicList
(
    ClinicListKey  INT AUTO_INCREMENT NOT NULL,  # 
    Region	  VARCHAR(20),	# 
    ClinicName	VARCHAR(50),	# 
    Telephone    VARCHAR(50),  # 
    Address    VARCHAR(100),  # 
    HostName    VARCHAR(20),  # 
    DBName    VARCHAR(50),  # 
    UserName    VARCHAR(20),  # 
    Password    VARCHAR(20),  # 
    GoogleMap    Blob,  # 

    TimeStamp	TIMESTAMP,	    # 上次異動日期

    PRIMARY KEY(ClinicListKey),
    INDEX(Region, ClinicName)
) CHARACTER SET utf8;


