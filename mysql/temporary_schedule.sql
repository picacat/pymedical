-- ------------------------------------------------------------
-- 資料表 temporary_schedule
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:39
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `temporary_schedule` (
  `TemporaryScheduleKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseDate` date NOT NULL DEFAULT '0000-00-00',
  `ScheduleType` varchar(10) DEFAULT NULL,
  `Room` int(11) DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Position` varchar(10) DEFAULT NULL,
  `Name` varchar(10) DEFAULT NULL,
  `Agent` varchar(10) DEFAULT NULL,
  `Remark` varchar(200) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`TemporaryScheduleKey`),
  KEY `Room` (`Room`,`Period`,`Position`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
