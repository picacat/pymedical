
# 31. 價目表: 特殊掛號費    掛號費優待 以 DiscountType of Patient.Sql
#     103.01.03 忠貞

CREATE TABLE IF NOT EXISTS ChargeRegist
(
    ChargeRegistKey	  INT AUTO_INCREMENT NOT NULL,  # 費用序號

    DiscountType      VARCHAR(20),	# 優待類別

    InitialFee        INT,	# 初診費
    InternalFee       INT,	# 內科

    AcupunctureFee1   INT,	# 針灸首次
    AcupunctureFee2   INT,	# 針灸療程
    EAcupunctureFee1  INT,	# 電針/複針首次
    EAcupunctureFee2  INT,	# 電針/複針療程

    MassageFee1       INT,  # 傷科首次
    MassageFee2       INT,  # 傷科療程
    CMassageFee1      INT,  # 複傷首次
    CMassageFee2      INT,  # 複傷療程

    TimeStamp	  TIMESTAMP,	# 上次異動日期

    PRIMARY KEY(ChargeRegistKey),
    INDEX(DiscountType)
) CHARACTER SET utf8;

#===================================================================

