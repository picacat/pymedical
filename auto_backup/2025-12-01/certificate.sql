/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.14-MariaDB, for debian-linux-gnu (x86_64)
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
-- Table structure for table `certificate`
--

DROP TABLE IF EXISTS `certificate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `certificate` (
  `CertificateKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseKey` int(11) NOT NULL,
  `PatientKey` int(11) NOT NULL,
  `Name` varchar(100) DEFAULT NULL,
  `Doctor` varchar(20) DEFAULT NULL,
  `CertificateDate` date DEFAULT NULL,
  `CertificateType` varchar(10) DEFAULT NULL,
  `InsType` varchar(10) DEFAULT NULL,
  `TreatType` varchar(20) DEFAULT NULL,
  `StartDate` date DEFAULT NULL,
  `EndDate` date DEFAULT NULL,
  `Diagnosis` text DEFAULT NULL,
  `DoctorComment` text DEFAULT NULL,
  `CertificateFee` int(11) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`CertificateKey`),
  KEY `CaseKey` (`CaseKey`,`PatientKey`,`CertificateDate`)
) ENGINE=MyISAM AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `certificate`
--

LOCK TABLES `certificate` WRITE;
/*!40000 ALTER TABLE `certificate` DISABLE KEYS */;
INSERT INTO `certificate` VALUES (2,0,1034,'林宜昉','林胤谷','2025-06-03','診斷證明','全部','全部','2025-06-03','2025-06-03','J069 急性上呼吸道感染 Acute upper respiratory infection, unspecified\n(以下空白)','患者因上述情形，宜在家休養，並持續回診治療(以下空白)',NULL,'2025-06-03 03:13:00');
INSERT INTO `certificate` VALUES (5,0,96,'李檠綸','林胤谷','2025-06-10','診斷證明','全部','全部','2025-06-10','2025-06-10','L239 過敏性接觸性皮膚炎，未明示原因 Allergic contact dermatitis, unspecified cause\n(以下空白)','患者因上述情形，宜門診持續追蹤治療(以下空白)',NULL,'2025-06-10 01:48:36');
INSERT INTO `certificate` VALUES (4,0,1041,'游逸菁','林胤谷','2025-06-06','診斷證明','全部','全部','2025-06-06','2025-06-06','L400 尋常性乾癬 Psoriasis vulgaris\n(以下空白)','患者因上述情形，宜門診持續追蹤治療(以下空白)',NULL,'2025-06-06 03:19:10');
INSERT INTO `certificate` VALUES (6,0,1021,'王睿翔','林胤谷','2025-06-11','診斷證明','全部','全部','2025-06-11','2025-06-11','L239 過敏性接觸性皮膚炎，未明示原因 Allergic contact dermatitis, unspecified cause\n(以下空白)','患者因上述情形，宜門診持續追蹤治療(以下空白)',NULL,'2025-06-11 00:25:26');
INSERT INTO `certificate` VALUES (9,0,1206,'尤漢丕','林胤谷','2025-06-25','收費證明','全部',NULL,'2025-06-15','2025-06-25',NULL,NULL,NULL,'2025-06-25 06:54:46');
INSERT INTO `certificate` VALUES (10,0,1157,'呂軒睿*','林胤谷','2025-06-26','診斷證明','全部','全部','2025-06-14','2025-06-14','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白)','患者因上述情形，宜門診持續追蹤治療(以下空白)',NULL,'2025-06-26 08:31:41');
INSERT INTO `certificate` VALUES (13,0,924,'黃安也','林胤谷','2025-06-30','診斷證明','全部','全部','2025-06-30','2025-06-30','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白)','患者護照號碼H22517723黃安也，因上述情形，宜門診持續追蹤治療(以下空白)',NULL,'2025-06-30 12:11:38');
INSERT INTO `certificate` VALUES (16,0,152,'^林宥廷','林胤谷','2025-06-26','診斷證明','全部','全部','2025-07-21','2025-07-21','L209 異位性皮膚炎 Atopic dermatitis, unspecified, 中重度\n(以下空白)','患者因全身異膚嚴重需全身用藥必需使用中藥自費藥物藥膏，並持續回診治療(以下空白)',NULL,'2025-07-21 11:11:25');
INSERT INTO `certificate` VALUES (14,0,424,'郭承稷','林胤谷','2025-06-13','診斷證明','全部','全部','2025-07-14','2025-07-14','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白)','患者因上述情形，宜門診持續追蹤治療(以下空白)',NULL,'2025-07-14 08:54:57');
INSERT INTO `certificate` VALUES (17,0,152,'^林宥廷','林胤谷','2025-07-21','診斷證明','全部','全部','2025-07-21','2025-07-21','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白 This space intentionally left blank)','患者因全身異位性皮膚炎嚴重，全身必需使用自費中藥藥膏治療,  並門診持續追蹤治療(以下空白 This space intentionally left blank)',NULL,'2025-07-21 11:16:11');
INSERT INTO `certificate` VALUES (18,0,1209,'林漢昱','林胤谷','2025-07-29','診斷證明','全部','全部','2025-07-29','2025-07-29','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白 This space intentionally left blank)','The herbal medicine (異膚靈軟膏 止癢洗方 袪濕癢方) be used in treating atopic dermatitis',NULL,'2025-07-29 03:39:02');
INSERT INTO `certificate` VALUES (19,0,1313,'洪郁雯','林胤谷','2025-08-18','診斷證明','全部','全部','2025-08-18','2025-08-18','異位性皮膚炎 ，急性發作(以下空白 )','患者因上述情形，全身皮膚發炎, 病灶暗沈乾燥, 宜在家休養並門診持續追蹤治療(以下空白)',NULL,'2025-08-18 07:46:04');
INSERT INTO `certificate` VALUES (20,0,1868,'張雅筑','林胤谷','2025-09-06','診斷證明','全部','全部','2025-09-06','2025-09-06','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白 This space intentionally left blank)','患者因上述情形，身體皮膚搔抓傷多, 不宜下水游泳，避免病情惡化, 並持續回診治療(以下空白 This space intentionally left blank)',NULL,'2025-09-06 01:56:24');
INSERT INTO `certificate` VALUES (21,0,1034,'林宜昉','林胤谷','2025-09-18','診斷證明','全部','全部','2025-09-18','2025-09-18','J069 急性上呼吸道感染 Acute upper respiratory infection, unspecified\n(以下空白 This space intentionally left blank)','患者因上述情形，宜在家休養，並持續回診治療(以下空白 This space intentionally left blank)',NULL,'2025-09-18 00:38:38');
INSERT INTO `certificate` VALUES (22,0,2074,'周昀蓁','林胤谷','2025-09-20','診斷證明','全部','全部','2025-09-20','2025-09-20','L209 異位性皮膚炎 Atopic dermatitis, unspecified\n(以下空白 This space intentionally left blank)','患者因全身性異位性皮膚炎, 症狀嚴重，日晒流汗, 碰水(游泳)，皆會造成病情惡化，應碰免, 並持續回診治療(以下空白 This space intentionally left blank)',NULL,'2025-09-20 05:46:26');
/*!40000 ALTER TABLE `certificate` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-01  6:36:38
