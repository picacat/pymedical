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
-- Table structure for table `pregnant`
--

DROP TABLE IF EXISTS `pregnant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pregnant` (
  `PregnantKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) DEFAULT NULL,
  `PatientKey` int(11) DEFAULT NULL,
  `LowTemperature` varchar(10) DEFAULT NULL,
  `HighTemperature` varchar(10) DEFAULT NULL,
  `FollTemperature` decimal(10,2) DEFAULT NULL,
  `FollDays` int(11) DEFAULT NULL,
  `OvulateDate` date DEFAULT NULL,
  `OvulateTemperature` decimal(10,2) DEFAULT NULL,
  `LuteumTemperature` decimal(10,2) DEFAULT NULL,
  `LuteumDays` int(11) DEFAULT NULL,
  `Sperm` int(11) DEFAULT NULL,
  `Yield` varchar(10) DEFAULT NULL,
  `Liquefaction` varchar(10) DEFAULT NULL,
  `Impurity` varchar(10) DEFAULT NULL,
  `Activity` varchar(10) DEFAULT NULL,
  `Spouse` varchar(10) DEFAULT NULL,
  `HeartBeat` int(11) DEFAULT NULL,
  `BPLow` int(11) DEFAULT NULL,
  `BPHigh` int(11) DEFAULT NULL,
  `Vomit` int(11) DEFAULT NULL,
  `Bleed` int(11) DEFAULT NULL,
  `SymptomLine` varchar(20) DEFAULT NULL,
  `PhysiqueLine` varchar(20) DEFAULT NULL,
  `AnxietyGrade` int(11) DEFAULT NULL,
  `AnxietyLine` varchar(20) DEFAULT NULL,
  `Fertilization` varchar(4) DEFAULT NULL,
  `WesternCure` varchar(4) DEFAULT NULL,
  `InitDATE` date DEFAULT NULL,
  `DiseaseName` varchar(40) DEFAULT NULL,
  `BirthFoetus` int(11) DEFAULT NULL,
  `StillFoetus` int(11) DEFAULT NULL,
  `Foetus` int(11) DEFAULT NULL,
  `Remark` mediumtext DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`PregnantKey`),
  KEY `CaseKey` (`CaseKey`,`PatientKey`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pregnant`
--

LOCK TABLES `pregnant` WRITE;
/*!40000 ALTER TABLE `pregnant` DISABLE KEYS */;
/*!40000 ALTER TABLE `pregnant` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-06  7:00:32
