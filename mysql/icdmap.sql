-- ------------------------------------------------------------
-- 資料表 icdmap
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:29
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `icdmap` (
  `ICDMAPKey` int(11) NOT NULL AUTO_INCREMENT,
  `ICD9Code` varchar(10) DEFAULT NULL,
  `ICD9ChineseName` varchar(100) DEFAULT NULL,
  `ICD9EnglishName` varchar(100) DEFAULT NULL,
  `ICD10Code` varchar(10) DEFAULT NULL,
  `ICD10ChineseName` varchar(100) DEFAULT NULL,
  `ICD10EnglishName` varchar(100) DEFAULT NULL,
  `Remark` varchar(50) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ICDMAPKey`),
  KEY `ICD9Code` (`ICD9Code`,`ICD10Code`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
