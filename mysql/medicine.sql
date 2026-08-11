-- ------------------------------------------------------------
-- 資料表 medicine
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:32
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `medicine` (
  `MedicineKey` int(11) NOT NULL AUTO_INCREMENT,
  `MedicineType` varchar(10) DEFAULT NULL,
  `MedicineMode` varchar(20) DEFAULT NULL,
  `MedicineCode` varchar(15) DEFAULT NULL,
  `InputCode` varchar(5) DEFAULT NULL,
  `InsCode` varchar(12) DEFAULT NULL,
  `MedicineName` varchar(40) DEFAULT NULL,
  `DrugName` varchar(40) DEFAULT NULL,
  `AnimalDerived` tinyint(1) NOT NULL DEFAULT 0,
  `MedicineAlias` varchar(40) DEFAULT NULL,
  `Unit` varchar(10) DEFAULT NULL,
  `Dosage` decimal(10,2) DEFAULT NULL,
  `MinDosage` decimal(10,2) DEFAULT NULL,
  `MaxDosage` decimal(10,2) DEFAULT NULL,
  `Location` varchar(20) DEFAULT NULL,
  `SalePrice` decimal(10,2) DEFAULT NULL,
  `InPrice` decimal(10,2) DEFAULT NULL,
  `Commission` varchar(10) DEFAULT NULL,
  `Project` varchar(50) DEFAULT NULL,
  `DoctorProject` varchar(50) DEFAULT NULL,
  `Charged` varchar(4) DEFAULT NULL,
  `NoDosage` varchar(4) DEFAULT NULL,
  `NonNHI` varchar(4) DEFAULT NULL,
  `Quantity` decimal(10,2) DEFAULT NULL,
  `SafeQuantity` decimal(10,2) DEFAULT NULL,
  `Description` longtext DEFAULT NULL,
  `HitRate` int(11) DEFAULT 0,
  `Deactivate` varchar(50) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`MedicineKey`),
  KEY `InsCode` (`InsCode`,`InputCode`),
  KEY `idx_select_optimization` (`MedicineType`,`InputCode`,`InsCode`,`MedicineName`,`DrugName`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
