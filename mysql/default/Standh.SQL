
# 91-處方集 	    100.07.01
# 鄭和耀 only   for 處方集主檔,  used by Case5

CREATE TABLE IF NOT EXISTS Standh
(
    StandhKey	INT AUTO_INCREMENT NOT NULL,  # 藥品序號
    serial	    VARCHAR(17),    # 藥品序號
    no		    VARCHAR(10),	#
    name		VARCHAR(20),	#
    s_no		VARCHAR(6),	    #
    s_no1		VARCHAR(6),	    #
    s_name	    VARCHAR(20),	#
    s_name1	    VARCHAR(20),	#
    d_way		VARCHAR(100),	#
    eat_f		VARCHAR(12),	#
    packs		INT,
    days		INT,
    descript	VARCHAR(180),	#

    PRIMARY KEY(StandhKey),
    INDEX(serial)
) CHARACTER SET utf8;

