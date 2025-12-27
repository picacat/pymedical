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
-- Table structure for table `debt`
--

DROP TABLE IF EXISTS `debt`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `debt` (
  `DebtKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL DEFAULT 0,
  `PrescriptKey` int(11) DEFAULT NULL,
  `PatientKey` int(11) NOT NULL DEFAULT 0,
  `DebtType` varchar(10) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `CaseDate` datetime DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `Fee` int(11) DEFAULT NULL,
  `PaymentType` varchar(20) DEFAULT '現金',
  `ReturnDate1` datetime DEFAULT NULL,
  `Period1` varchar(4) DEFAULT NULL,
  `Casher1` varchar(10) DEFAULT NULL,
  `Cashier1` varchar(10) DEFAULT NULL,
  `Fee1` int(11) DEFAULT NULL,
  `ReturnDate2` datetime DEFAULT NULL,
  `Period2` varchar(4) DEFAULT NULL,
  `Casher2` varchar(10) DEFAULT NULL,
  `Cashier2` varchar(10) DEFAULT NULL,
  `Fee2` int(11) DEFAULT NULL,
  `ReturnDate3` datetime DEFAULT NULL,
  `Period3` varchar(4) DEFAULT NULL,
  `Casher3` varchar(10) DEFAULT NULL,
  `Cashier3` varchar(10) DEFAULT NULL,
  `Fee3` int(11) DEFAULT NULL,
  `TotalReturn` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`DebtKey`),
  KEY `CaseKey` (`CaseKey`,`PatientKey`,`CaseDate`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `debt`
--

LOCK TABLES `debt` WRITE;
/*!40000 ALTER TABLE `debt` DISABLE KEYS */;
/*!40000 ALTER TABLE `debt` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-13 12:59:54
