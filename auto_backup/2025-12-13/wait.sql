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
-- Table structure for table `wait`
--

DROP TABLE IF EXISTS `wait`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wait` (
  `WaitKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL DEFAULT 0,
  `CaseDate` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `PatientKey` int(11) NOT NULL DEFAULT 0,
  `RegistrationNo` varchar(10) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Era` char(1) DEFAULT NULL,
  `Birthday` date DEFAULT NULL,
  `Sex` varchar(4) DEFAULT NULL,
  `Visit` varchar(4) DEFAULT NULL,
  `RegistTypex` varchar(10) DEFAULT NULL,
  `RegistType` varchar(10) DEFAULT NULL,
  `TreatType` varchar(100) DEFAULT NULL,
  `Share` varchar(50) DEFAULT NULL,
  `InsType` varchar(4) DEFAULT NULL,
  `Card` varchar(6) DEFAULT NULL,
  `Continuance` int(11) DEFAULT NULL,
  `Period` varchar(4) DEFAULT NULL,
  `Room` int(11) NOT NULL DEFAULT 1,
  `MassageRoom` int(11) DEFAULT NULL,
  `RegistNo` int(11) DEFAULT NULL,
  `MassageNo` int(11) DEFAULT NULL,
  `Doctor` varchar(10) DEFAULT NULL,
  `InProgress` varchar(10) DEFAULT NULL,
  `Massager` varchar(10) DEFAULT NULL,
  `DoctorDone` enum('False','True') NOT NULL DEFAULT 'False',
  `MassagerDone` enum('False','True') NOT NULL DEFAULT 'False',
  `ChargeDone` enum('False','True') NOT NULL DEFAULT 'False',
  `DrugDone` enum('False','True') NOT NULL DEFAULT 'False',
  `DrugPickupDone` enum('False','True') NOT NULL DEFAULT 'False',
  `Remark` varchar(100) DEFAULT NULL,
  `VHCReqCode` varchar(256) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`WaitKey`),
  KEY `CaseKey` (`CaseKey`,`CaseDate`,`PatientKey`)
) ENGINE=MyISAM AUTO_INCREMENT=3736 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wait`
--

LOCK TABLES `wait` WRITE;
/*!40000 ALTER TABLE `wait` DISABLE KEYS */;
INSERT INTO `wait` VALUES (3735,3762,'2025-12-13 12:53:31',2506,NULL,'黃登貴',NULL,NULL,NULL,'複診',NULL,'一般門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,1,NULL,'林胤谷',NULL,NULL,'True','False','False','False','False',NULL,NULL,'2025-12-13 04:53:49');
/*!40000 ALTER TABLE `wait` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-13 13:00:03
