-- ------------------------------------------------------------
-- 資料表 basic_schedule
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:23
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `basic_schedule` (
  `BasicScheduleKey` int(11) NOT NULL AUTO_INCREMENT,
  `Period` varchar(20) DEFAULT NULL,
  `Monday` varchar(20) DEFAULT NULL,
  `Tuesday` varchar(20) DEFAULT NULL,
  `Wednesday` varchar(20) DEFAULT NULL,
  `Thursday` varchar(20) DEFAULT NULL,
  `Friday` varchar(20) DEFAULT NULL,
  `Saturday` varchar(20) DEFAULT NULL,
  `Sunday` varchar(20) DEFAULT NULL,
  `TimeStamp` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`BasicScheduleKey`),
  KEY `Period` (`Period`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
