-- MariaDB dump 10.19  Distrib 10.11.6-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: pymedical
-- ------------------------------------------------------
-- Server version	10.11.6-MariaDB-0+deb12u1
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dosage`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dosage` (
  `DosageKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL,
  `MedicineSet` int(11) DEFAULT NULL,
  `Packages` int(11) DEFAULT NULL,
  `Days` int(11) DEFAULT NULL,
  `TotalDosage` double(6,2) DEFAULT NULL,
  `Instruction` varchar(100) DEFAULT NULL,
  `SelfTotalFee` int(11) DEFAULT NULL,
  `DiscountRate` int(11) DEFAULT 100,
  `DiscountFee` int(11) DEFAULT NULL,
  `TotalFee` int(11) DEFAULT NULL,
  `Amount` int(11) DEFAULT NULL,
  `FreeInsMedicine` varchar(4) DEFAULT NULL,
  `NoPharmacy` varchar(4) DEFAULT NULL,
  `Remark` varchar(200) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`DosageKey`),
  KEY `CaseKey` (`CaseKey`,`MedicineSet`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-02-04  9:14:27
