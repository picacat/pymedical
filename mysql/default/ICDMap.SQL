
CREATE TABLE ICDMap
(
    ICDMapKey	INT AUTO_INCREMENT NOT NULL,  #

    ICD9Code	        VARCHAR(10),	#
    ICD9ChineseName	    VARCHAR(100),	#
    ICD9EnglishName	    VARCHAR(100),	#

    ICD10Code	        VARCHAR(10),	#
    ICD10ChineseName	VARCHAR(100),	#
    ICD10EnglishName	VARCHAR(100),	#

    Remark    	VARCHAR(50),	#

    TimeStamp	TIMESTAMP,	    #

    PRIMARY KEY(ICDMapKey),
    INDEX(ICD9Code, ICD10Code)
);