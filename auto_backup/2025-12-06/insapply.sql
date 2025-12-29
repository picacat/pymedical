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
-- Table structure for table `insapply`
--

DROP TABLE IF EXISTS `insapply`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `insapply` (
  `InsApplyKey` int(11) NOT NULL AUTO_INCREMENT,
  `ClinicID` varchar(10) DEFAULT NULL,
  `ApplyDate` varchar(5) DEFAULT NULL,
  `ApplyPeriod` varchar(6) DEFAULT NULL,
  `ApplyType` char(1) DEFAULT NULL,
  `CaseType` char(2) DEFAULT NULL,
  `Sequence` int(11) DEFAULT NULL,
  `SpecialCode1` char(2) DEFAULT NULL,
  `SpecialCode2` char(2) DEFAULT NULL,
  `SpecialCode3` char(2) DEFAULT NULL,
  `SpecialCode4` char(2) DEFAULT NULL,
  `Class` char(2) DEFAULT NULL,
  `CaseDate` date DEFAULT NULL,
  `StopDate` date DEFAULT NULL,
  `Era` char(1) DEFAULT NULL,
  `Birthday` date DEFAULT NULL,
  `ID` varchar(10) DEFAULT NULL,
  `Card` varchar(5) DEFAULT NULL,
  `Injury` char(1) DEFAULT NULL,
  `ShareCode` char(3) DEFAULT NULL,
  `Visit` varchar(10) DEFAULT NULL,
  `TransferFrom` varchar(10) DEFAULT NULL,
  `TransferOut` char(1) DEFAULT NULL,
  `DiseaseCode1` varchar(10) DEFAULT NULL,
  `DiseaseCode2` varchar(10) DEFAULT NULL,
  `DiseaseCode3` varchar(10) DEFAULT NULL,
  `DiseaseCode4` varchar(10) DEFAULT NULL,
  `DiseaseCode5` varchar(10) DEFAULT NULL,
  `SurgeryCode` varchar(4) DEFAULT NULL,
  `PresDays` int(11) DEFAULT NULL,
  `PresType` char(1) DEFAULT NULL,
  `ChronicNo` varchar(10) DEFAULT NULL,
  `DoctorName` varchar(10) DEFAULT NULL,
  `DoctorID` varchar(10) DEFAULT NULL,
  `PharmacistID` varchar(10) DEFAULT NULL,
  `DrugFee` int(11) DEFAULT NULL,
  `TreatFee` int(11) DEFAULT NULL,
  `DiagCode` varchar(12) DEFAULT NULL,
  `DiagFee` int(11) DEFAULT NULL,
  `PharmacyCode` varchar(12) DEFAULT NULL,
  `PharmacyFee` int(11) DEFAULT NULL,
  `InsTotalFee` int(11) DEFAULT NULL,
  `ShareFee` int(11) DEFAULT NULL,
  `DiagShareFee` int(11) DEFAULT NULL,
  `DrugShareFee` int(11) DEFAULT NULL,
  `ExamShareFee` int(11) DEFAULT NULL,
  `InsApplyFee` int(11) DEFAULT NULL,
  `AgentCode` varchar(12) DEFAULT NULL,
  `AgentFee` int(11) DEFAULT NULL,
  `ChronicPresDays` int(11) DEFAULT NULL,
  `PatientKey` int(11) DEFAULT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Identifier` varchar(20) DEFAULT NULL,
  `ActualIdentifier` varchar(20) DEFAULT NULL,
  `OriginalIdentifier` varchar(20) DEFAULT NULL,
  `CaseKey1` int(11) DEFAULT NULL,
  `TreatCode1` varchar(12) DEFAULT NULL,
  `TreatFee1` int(11) DEFAULT NULL,
  `Percent1` int(11) DEFAULT NULL,
  `CaseKey2` int(11) DEFAULT NULL,
  `TreatCode2` varchar(12) DEFAULT NULL,
  `TreatFee2` int(11) DEFAULT NULL,
  `Percent2` int(11) DEFAULT NULL,
  `CaseKey3` int(11) DEFAULT NULL,
  `TreatCode3` varchar(12) DEFAULT NULL,
  `TreatFee3` int(11) DEFAULT NULL,
  `Percent3` int(11) DEFAULT NULL,
  `CaseKey4` int(11) DEFAULT NULL,
  `TreatCode4` varchar(12) DEFAULT NULL,
  `TreatFee4` int(11) DEFAULT NULL,
  `Percent4` int(11) DEFAULT NULL,
  `CaseKey5` int(11) DEFAULT NULL,
  `TreatCode5` varchar(12) DEFAULT NULL,
  `TreatFee5` int(11) DEFAULT NULL,
  `Percent5` int(11) DEFAULT NULL,
  `CaseKey6` int(11) DEFAULT NULL,
  `TreatCode6` varchar(12) DEFAULT NULL,
  `TreatFee6` int(11) DEFAULT NULL,
  `Percent6` int(11) DEFAULT NULL,
  `CaseKey7` int(11) DEFAULT NULL,
  `TreatCode7` varchar(12) DEFAULT NULL,
  `TreatFee7` int(11) DEFAULT NULL,
  `Percent7` int(11) DEFAULT NULL,
  `CaseKey8` int(11) DEFAULT NULL,
  `TreatCode8` varchar(12) DEFAULT NULL,
  `TreatFee8` int(11) DEFAULT NULL,
  `Percent8` int(11) DEFAULT NULL,
  `CaseKey9` int(11) DEFAULT NULL,
  `TreatCode9` varchar(12) DEFAULT NULL,
  `TreatFee9` int(11) DEFAULT NULL,
  `Percent9` int(11) DEFAULT NULL,
  `CaseKey10` int(11) DEFAULT NULL,
  `TreatCode10` varchar(12) DEFAULT NULL,
  `TreatFee10` int(11) DEFAULT NULL,
  `Percent10` int(11) DEFAULT NULL,
  `CaseKey11` int(11) DEFAULT NULL,
  `TreatCode11` varchar(12) DEFAULT NULL,
  `TreatFee11` int(11) DEFAULT NULL,
  `Percent11` int(11) DEFAULT NULL,
  `CaseKey12` int(11) DEFAULT NULL,
  `TreatCode12` varchar(12) DEFAULT NULL,
  `TreatFee12` int(11) DEFAULT NULL,
  `Percent12` int(11) DEFAULT NULL,
  `CaseKey13` int(11) DEFAULT NULL,
  `TreatCode13` varchar(12) DEFAULT NULL,
  `TreatFee13` int(11) DEFAULT NULL,
  `Percent13` int(11) DEFAULT NULL,
  `CaseKey14` int(11) DEFAULT NULL,
  `TreatCode14` varchar(12) DEFAULT NULL,
  `TreatFee14` int(11) DEFAULT NULL,
  `Percent14` int(11) DEFAULT NULL,
  `CaseKey15` int(11) DEFAULT NULL,
  `TreatCode15` varchar(12) DEFAULT NULL,
  `TreatFee15` int(11) DEFAULT NULL,
  `Percent15` int(11) DEFAULT NULL,
  `Note` char(1) DEFAULT NULL,
  `Message` varchar(40) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`InsApplyKey`),
  KEY `ApplyDate` (`ApplyDate`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `insapply`
--

LOCK TABLES `insapply` WRITE;
/*!40000 ALTER TABLE `insapply` DISABLE KEYS */;
/*!40000 ALTER TABLE `insapply` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-06  7:00:29
