-- ------------------------------------------------------------
-- 資料表 special_schedule
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:37
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `special_schedule` (
  `SpecialScheduleKey` int(11) NOT NULL AUTO_INCREMENT,
  `Period` varchar(4) DEFAULT NULL,
  `Monday` varchar(10) DEFAULT NULL,
  `Tuesday` varchar(10) DEFAULT NULL,
  `Wednesday` varchar(10) DEFAULT NULL,
  `Thursday` varchar(10) DEFAULT NULL,
  `Friday` varchar(10) DEFAULT NULL,
  `Saturday` varchar(10) DEFAULT NULL,
  `Sunday` varchar(10) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`SpecialScheduleKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
