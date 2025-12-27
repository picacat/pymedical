
CREATE TABLE ICD10
(
    ICD10Key	  INT AUTO_INCREMENT NOT NULL,  #

    ICDCode	    VARCHAR(10),	#
    InputCode	  VARCHAR(05),	#

    ChineseName	VARCHAR(100),	#
    EnglishName	VARCHAR(100),	#

    SpecialCode	VARCHAR(02),    #
    Position1	  VARCHAR(02),	#
    Position2	  VARCHAR(02),	#

    Remark    	VARCHAR(50),	#
                                #
    TimeStamp	TIMESTAMP,	    #

    PRIMARY KEY(ICD10Key),
    INDEX(ICD10Code, InputCode, ChineseName)
);
