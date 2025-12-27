
# 09-2. 圖形檔 - 副檔 105.01.12   Picture.PicImage 一對一

CREATE TABLE IF NOT EXISTS PicImage
(
    PictureKey  INT NOT NULL, # 圖形(主檔) 序號
    Image  	    LONGBLOB,   	# 圖片
    PRIMARY KEY(PictureKey)
) CHARACTER SET utf8;
