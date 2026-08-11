-- ------------------------------------------------------------
-- 資料表 icd10
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:29
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `icd10` (
  `ICD10Key` int(11) NOT NULL AUTO_INCREMENT,
  `ICDCode` varchar(10) NOT NULL DEFAULT '',
  `InputCode` varchar(5) DEFAULT NULL,
  `ChineseName` varchar(100) DEFAULT NULL,
  `EnglishName` varchar(100) DEFAULT NULL,
  `SpecialCode` varchar(2) DEFAULT NULL,
  `Groups` varchar(100) DEFAULT NULL,
  `HitRate` int(11) DEFAULT 0,
  `Position1` varchar(2) DEFAULT NULL,
  `Position2` varchar(2) DEFAULT NULL,
  `Remark` varchar(50) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ICD10Key`) USING BTREE,
  KEY `ICD10Code` (`ICDCode`),
  KEY `InputCode` (`InputCode`),
  KEY `ChineseName` (`ChineseName`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
