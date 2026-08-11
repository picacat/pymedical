-- ------------------------------------------------------------
-- 資料表 backup_records
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:23
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `backup_records` (
  `BackupRecordsKey` int(11) NOT NULL AUTO_INCREMENT,
  `TableName` varchar(50) DEFAULT NULL,
  `KeyField` varchar(50) DEFAULT NULL,
  `KeyValue` int(11) DEFAULT NULL,
  `JSON` mediumtext DEFAULT NULL,
  `Deleter` varchar(50) DEFAULT NULL,
  `Editor` varchar(50) DEFAULT NULL,
  `DeleteDateTime` datetime DEFAULT NULL,
  `RecordRestored` varchar(10) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`BackupRecordsKey`),
  KEY `TableName` (`TableName`,`KeyField`,`KeyValue`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
