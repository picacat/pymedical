-- MariaDB dump 10.19  Distrib 10.6.4-MariaDB, for Win64 (AMD64)
--
-- Host: 192.168.0.168    Database: lin
-- ------------------------------------------------------
-- Server version	10.11.11-MariaDB-0+deb12u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `massage_cases`
--

DROP TABLE IF EXISTS `massage_cases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `massage_cases` (
  `MassageCaseKey` int(11) NOT NULL AUTO_INCREMENT,
  `MassageCustomerKey` int(11) DEFAULT NULL,
  `PatientKey` int(11) DEFAULT NULL,
  `ClinicName` varchar(50) DEFAULT NULL,
  `Name` varchar(20) DEFAULT NULL,
  `CaseDate` datetime NOT NULL,
  `FinishDate` datetime NOT NULL,
  `TreatType` varchar(10) DEFAULT NULL,
  `InsType` varchar(4) DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Massager` varchar(10) DEFAULT NULL,
  `Registrar` varchar(10) DEFAULT NULL,
  `Cashier` varchar(10) DEFAULT NULL,
  `Remark` blob DEFAULT NULL,
  `DesignatedMassager` enum('False','True') NOT NULL,
  `SelfTotalFee` int(11) DEFAULT NULL,
  `DiscountFee` int(11) DEFAULT NULL,
  `TotalFee` int(11) DEFAULT NULL,
  `ReceiptFee` int(11) DEFAULT NULL,
  `DebtFee` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`MassageCaseKey`),
  KEY `MassageCustomerKey` (`MassageCustomerKey`,`CaseDate`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `massage_cases`
--

LOCK TABLES `massage_cases` WRITE;
/*!40000 ALTER TABLE `massage_cases` DISABLE KEYS */;
/*!40000 ALTER TABLE `massage_cases` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-13 12:59:58
