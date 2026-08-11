-- ------------------------------------------------------------
-- 資料表 insappeal_items
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:30
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `insappeal_items` (
  `InsAppealItemsKey` int(11) NOT NULL AUTO_INCREMENT,
  `InsAppealKey` int(11) NOT NULL,
  `ItemType` varchar(20) DEFAULT NULL,
  `OrderSeq` int(11) DEFAULT NULL,
  `InsCode` varchar(12) DEFAULT NULL,
  `RejectCode` varchar(10) DEFAULT NULL,
  `Percent` int(11) DEFAULT NULL,
  `Quantity` int(11) DEFAULT NULL,
  `Point` int(11) DEFAULT NULL,
  `FileLink` varchar(2) DEFAULT NULL,
  `Reason1` varchar(1000) DEFAULT NULL,
  `Reason2` varchar(1000) DEFAULT NULL,
  `Note` varchar(1) DEFAULT NULL,
  `Message` varchar(40) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`InsAppealItemsKey`),
  KEY `InsAppealKey` (`InsAppealKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
