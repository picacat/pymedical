-- ------------------------------------------------------------
-- 資料表 reservation_table_hide
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:36
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `reservation_table_hide` (
  `ReservationTableHideKey` int(11) NOT NULL AUTO_INCREMENT,
  `Weekday` varchar(10) DEFAULT NULL,
  `Period` varchar(10) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `ReserveNo` int(11) DEFAULT NULL,
  PRIMARY KEY (`ReservationTableHideKey`),
  KEY `Weekday` (`Weekday`,`Period`,`ReserveNo`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
