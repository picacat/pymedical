-- ------------------------------------------------------------
-- 資料表 prescript
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:34
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `prescript` (
  `PrescriptKey` int(11) NOT NULL AUTO_INCREMENT,
  `PrescriptNo` int(11) DEFAULT NULL,
  `CaseKey` int(11) NOT NULL DEFAULT 0,
  `CaseDate` datetime DEFAULT NULL,
  `MedicineSet` int(11) DEFAULT NULL,
  `MedicineType` varchar(10) DEFAULT NULL,
  `MedicineKey` int(11) DEFAULT NULL,
  `InsCode` varchar(12) DEFAULT NULL,
  `MedicineName` varchar(40) DEFAULT NULL,
  `DosageMode` varchar(10) DEFAULT NULL,
  `Dosage` decimal(10,2) DEFAULT NULL,
  `Unit` varchar(10) DEFAULT NULL,
  `Instruction` varchar(40) DEFAULT NULL,
  `Price` decimal(10,2) DEFAULT NULL,
  `DiscountFee` decimal(10,2) DEFAULT NULL,
  `Debt` decimal(10,2) DEFAULT NULL,
  `Amount` decimal(10,2) DEFAULT NULL,
  `Dealer` varchar(10) DEFAULT NULL,
  `Promotion` varchar(10) DEFAULT NULL,
  `Remark` varchar(200) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PrescriptKey`),
  KEY `CaseKey` (`CaseKey`,`CaseDate`),
  KEY `idx_update_optimization` (`MedicineSet`,`CaseDate`,`MedicineKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
