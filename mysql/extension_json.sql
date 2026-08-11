-- ------------------------------------------------------------
-- 資料表 extension_json
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:28
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `extension_json` (
  `ExtensionJSONKey` int(11) NOT NULL AUTO_INCREMENT,
  `TableName` varchar(50) DEFAULT NULL,
  `KeyField` varchar(50) DEFAULT NULL,
  `KeyValue` varchar(50) DEFAULT NULL,
  `JSON` mediumtext DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ExtensionJSONKey`),
  KEY `TableName` (`TableName`,`KeyField`,`KeyValue`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
