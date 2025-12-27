
# 91. 處方集 	100.07.01
# 鄭和耀 only   for 處方集副檔 -> standh

CREATE TABLE IF NOT EXISTS Standi
(
    StandiKey	INT AUTO_INCREMENT NOT NULL,  # 藥品序號
    serial	    VARCHAR(17),    # 藥品序號
    c_no		VARCHAR(10),	#
    num		    VARCHAR(2),	    #

    eat		    VARCHAR(20),	#
    count		INT,	        #
    unit		VARCHAR(2),	    #
    licno		VARCHAR(12),	#
    locate	    VARCHAR(10),	#
    sell		Float,	        #

    PRIMARY KEY(StandiKey),
    INDEX(serial)
) CHARACTER SET utf8;

