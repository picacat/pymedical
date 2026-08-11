-- ------------------------------------------------------------
-- 資料表 physiotherapy_schedule
-- 來源: localhost:3306 / pymedical_innodb
-- 產生: 資料表結構匯出工具 v1.3  2026-08-11 16:01:34
-- ------------------------------------------------------------

-- 本檔不含 DROP 陳述式。目標資料庫若已有同名物件，
-- 匯入會停在錯誤 1050 (Table already exists)。

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;

CREATE TABLE `physiotherapy_schedule` (
  `PhysiotherapyDate` date NOT NULL,
  `PhysiotherapyTime` varchar(5) NOT NULL,
  `Physiotherapy` varchar(10) NOT NULL,
  `PatientKey` int(11) DEFAULT NULL,
  `ArrivalTime` varchar(5) DEFAULT NULL,
  `TreatFee` int(11) DEFAULT NULL,
  `ReceiptFee` int(11) DEFAULT NULL,
  `Remark` varchar(200) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PhysiotherapyDate`,`PhysiotherapyTime`,`Physiotherapy`),
  KEY `PatientKey` (`PatientKey`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
