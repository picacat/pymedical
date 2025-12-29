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
) ENGINE=MyISAM AUTO_INCREMENT=3726 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `wait`
--

LOCK TABLES `wait` WRITE;
/*!40000 ALTER TABLE `wait` DISABLE KEYS */;
INSERT INTO `wait` VALUES (3725,3752,'2025-12-05 22:50:16',1,NULL,'黃從輝?',NULL,NULL,NULL,'複診',NULL,'一般門診','內科','基層醫療','自費','免卡',NULL,'晚班',1,NULL,20,NULL,'林胤谷',NULL,NULL,'True','False','False','False','False',NULL,NULL,'2025-12-05 14:51:08');
INSERT INTO `wait` VALUES (3720,3747,'2025-12-05 10:56:19',2501,NULL,'許琪雯',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,15,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 04:19:35');
INSERT INTO `wait` VALUES (3721,3748,'2025-12-05 11:06:51',2013,NULL,'王文總',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,16,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 03:52:03');
INSERT INTO `wait` VALUES (3722,3749,'2025-12-05 11:32:20',2370,NULL,'金沛蓁.',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,17,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 09:39:09');
INSERT INTO `wait` VALUES (3723,3750,'2025-12-05 11:32:49',2492,NULL,'陳昭瑋',NULL,NULL,NULL,'初診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,18,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 03:55:10');
INSERT INTO `wait` VALUES (3724,3751,'2025-12-05 11:51:25',1189,NULL,'楊舒安',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,19,NULL,'林胤谷',NULL,NULL,'True','False','False','True','False',NULL,NULL,'2025-12-05 06:58:16');
INSERT INTO `wait` VALUES (3719,3746,'2025-12-05 10:51:54',1018,NULL,'吳悠',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,14,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 04:19:36');
INSERT INTO `wait` VALUES (3717,3744,'2025-12-05 10:42:45',1578,NULL,'許庭恩',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,12,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 04:19:41');
INSERT INTO `wait` VALUES (3718,3745,'2025-12-05 10:51:25',2500,NULL,'林宜蓉',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,13,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 04:19:36');
INSERT INTO `wait` VALUES (3716,3743,'2025-12-05 10:37:25',433,NULL,'陳邤媃',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,11,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 03:20:52');
INSERT INTO `wait` VALUES (3713,3740,'2025-12-05 10:18:08',2250,NULL,'林冬龍',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,9,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 03:15:49');
INSERT INTO `wait` VALUES (3714,3741,'2025-12-05 10:19:18',2424,NULL,'黎尚華?',NULL,NULL,NULL,'初診',NULL,'預約門診','內科','三歲兒童','自費','免卡',NULL,'早班',1,NULL,9,NULL,'林胤谷',NULL,NULL,'True','False','True','True','True',NULL,NULL,'2025-12-05 09:45:35');
INSERT INTO `wait` VALUES (3715,3742,'2025-12-05 10:24:58',2497,NULL,'連亭竹',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,10,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 03:20:18');
INSERT INTO `wait` VALUES (3712,3739,'2025-12-05 10:09:56',32,NULL,'吳采芸',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,8,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 02:39:08');
INSERT INTO `wait` VALUES (3711,3738,'2025-12-05 09:51:52',2440,NULL,'楊妍晞',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,7,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 02:36:29');
INSERT INTO `wait` VALUES (3710,3737,'2025-12-05 09:29:18',2458,NULL,'劉秉儉',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,6,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 02:35:27');
INSERT INTO `wait` VALUES (3709,3736,'2025-12-05 09:20:26',2481,NULL,'白連頤',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,5,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 01:49:07');
INSERT INTO `wait` VALUES (3708,3735,'2025-12-05 09:17:41',2338,NULL,'蕭大誠',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,4,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 01:47:24');
INSERT INTO `wait` VALUES (3707,3734,'2025-12-05 09:04:37',2403,NULL,'徐暐智',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,3,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 01:47:23');
INSERT INTO `wait` VALUES (3706,3733,'2025-12-05 08:54:41',2243,NULL,'沈吳碧雲',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,2,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 01:47:23');
INSERT INTO `wait` VALUES (3705,3732,'2025-12-05 08:52:44',1013,NULL,'吳峻次',NULL,NULL,NULL,'複診',NULL,'預約門診','內科','基層醫療','自費','免卡',NULL,'早班',1,NULL,1,NULL,'林胤谷',NULL,NULL,'True','False','False','True','True',NULL,NULL,'2025-12-05 01:06:41');
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

-- Dump completed on 2025-12-05 23:02:08
