-- ------------------------------------------------------------
-- 資料表 stockoutitems
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:38
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `stockoutitems` (
  `StockOutItemsKey` int(11) NOT NULL AUTO_INCREMENT,
  `StockOutKey` int(11) NOT NULL,
  `MedicineKey` int(11) NOT NULL,
  `MedicineName` varchar(40) DEFAULT NULL,
  `ProductNo` varchar(20) DEFAULT NULL,
  `ProductName` varchar(100) DEFAULT NULL,
  `Unit` varchar(20) DEFAULT NULL,
  `UnitQuantity` int(11) DEFAULT NULL,
  `Quantity` int(11) DEFAULT NULL,
  `UnitPrice` int(11) DEFAULT NULL,
  `Amount` int(11) DEFAULT NULL,
  `Remark` varchar(100) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`StockOutItemsKey`),
  KEY `StockOutKey` (`StockOutKey`,`MedicineKey`,`MedicineName`,`ProductNo`,`ProductName`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
