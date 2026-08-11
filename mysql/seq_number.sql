-- ------------------------------------------------------------
-- 資料表 seq_number
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:37
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `seq_number` (
  `SeqNumberKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseDate` date NOT NULL DEFAULT '0000-00-00',
  `Room` int(11) NOT NULL DEFAULT 1,
  `SeqNumber` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`SeqNumberKey`),
  KEY `Room` (`Room`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
