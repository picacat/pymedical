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
-- Table structure for table `extension_json`
--

DROP TABLE IF EXISTS `extension_json`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `extension_json` (
  `ExtensionJSONKey` int(11) NOT NULL AUTO_INCREMENT,
  `TableName` varchar(50) DEFAULT NULL,
  `KeyField` varchar(50) DEFAULT NULL,
  `KeyValue` varchar(50) DEFAULT NULL,
  `JSON` text DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`ExtensionJSONKey`),
  KEY `TableName` (`TableName`,`KeyField`,`KeyValue`)
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `extension_json`
--

LOCK TABLES `extension_json` WRITE;
/*!40000 ALTER TABLE `extension_json` DISABLE KEYS */;
INSERT INTO `extension_json` VALUES (1,'reference_medical_record','disease_code','L409','{\"diagnostic\": {\"symptom\": \"\", \"tongue\": \"\", \"pulse\": \"\", \"remark\": \"\", \"disease_code1\": \"L409\", \"disease_code2\": \"\", \"disease_code3\": \"\", \"disease_code4\": \"\", \"distinguish\": \"\", \"cure\": \"\", \"treatment\": \"\"}, \"prescript\": [{\"medicine_set\": 1, \"medicine_key\": \"10385\", \"medicine_type\": \"\\u8907\\u65b9\", \"medicine_name\": \"\\u6eab\\u6e05\\u98f2\", \"ins_code\": \"A036295\", \"dosage\": \"3.00\", \"dosage_mode\": \"\\u6b21\\u5291\\u91cf\", \"unit\": \"\\u514b\"}], \"dosage\": [{\"medicine_set\": 1, \"package\": \"3\", \"presdays\": \"14\", \"instruction\": \"\\u4e09\\u9910\\u98ef\\u5f8c\"}, {\"medicine_set\": 2, \"package\": \"\", \"presdays\": \"\", \"instruction\": \"\"}]}','2025-04-21 03:47:53');
INSERT INTO `extension_json` VALUES (2,'reference_medical_record','disease_code','L409','{\"diagnostic\": {\"symptom\": \"\\u4e7e\\u766c, \\u6414\\u7662, \\u9c57\\u5c51\", \"tongue\": \"\\u820c\\u6de1\\u7d05, \\u82d4\\u8584\\u767d\", \"pulse\": \"\\u5de6\\u8108:\\u5f26, \\u53f3\\u8108:\\u5f26\", \"remark\": \"\", \"disease_code1\": \"L409\", \"disease_code2\": \"\", \"disease_code3\": \"\", \"disease_code4\": \"\", \"distinguish\": \"\", \"cure\": \"\", \"treatment\": \"\"}, \"prescript\": [{\"medicine_set\": 1, \"medicine_key\": \"10385\", \"medicine_type\": \"\\u8907\\u65b9\", \"medicine_name\": \"\\u6eab\\u6e05\\u98f2\", \"ins_code\": \"A036295\", \"dosage\": \"3.00\", \"dosage_mode\": \"\\u6b21\\u5291\\u91cf\", \"unit\": \"\\u514b\"}], \"dosage\": [{\"medicine_set\": 1, \"package\": \"3\", \"presdays\": \"14\", \"instruction\": \"\\u4e09\\u9910\\u98ef\\u5f8c\"}, {\"medicine_set\": 2, \"package\": \"\", \"presdays\": \"\", \"instruction\": \"\"}]}','2025-04-21 03:50:05');
INSERT INTO `extension_json` VALUES (3,'reference_medical_record','disease_code',NULL,'{\"diagnostic\": {\"symptom\": \"\\u4e3b\\u8a34:\\n\\u73fe\\u75c5\\u53f2:\\n\\n\\u98df\\u617e\\u5c1a\\u53ef; \\u98f2\\u6c34\\u6b63\\u5e38; \\u7761\\u7720\\u826f\\u597d; \\u4e8c\\u4fbf\\u53ef\\n\\n\\u671b\\u8a3a:\\n\\u9762\\u8272:\\u7d05\\u9ec3\\u96b1\\u96b1\\n\\u9ad4\\u683c:\\u4e2d\\u7b49 \\u504f\\u7626 \\u80d6\\n\\u76ae\\u819a:\\u4e7e\\u71e5, \\u7d05\\u75b9, \\u82d4\\u861a\\u5316,\\u7d05\\u8272\\u6591\\u584a\\n\\u6307\\u7532:\\u7121\\u7570\\u5e38\\n\\u6bdb\\u9aee:\\u7121\\u7570\\u5e38\\n\\u53e3\\u5507:\\u7121\\u7570\\u5e38\\n\\u805e\\u8a3a:\\n\\u6c23\\u5473:\\u7121\\u7570\\u5e38\\n\\u8072\\u97f3:\\u7121\\u7570\\u5e38\", \"tongue\": \"\\u820c\\u6de1\\u7d05, \\u82d4\\u8584\\u767d\", \"pulse\": \"\\u5de6\\u8108:\\u5f26, \\u53f3\\u8108:\\u5f26\", \"remark\": \"\", \"disease_code1\": \"\", \"disease_code2\": \"\", \"disease_code3\": \"\", \"disease_code4\": \"\", \"distinguish\": \"\", \"cure\": \"\", \"treatment\": \"\"}, \"prescript\": [], \"dosage\": [{\"medicine_set\": 1, \"package\": \"\", \"presdays\": \"\", \"instruction\": \"\"}, {\"medicine_set\": 2, \"package\": \"\", \"presdays\": \"\", \"instruction\": \"\"}]}','2025-06-11 00:48:14');
INSERT INTO `extension_json` VALUES (4,'reference_medical_record','disease_code',NULL,'{\"diagnostic\": {\"symptom\": \"\\u4e3b\\u8a34:\\n\\u73fe\\u75c5\\u53f2:\\n\\n\\u98df\\u617e\\u5c1a\\u53ef; \\u98f2\\u6c34\\u6b63\\u5e38; \\u7761\\u7720\\u826f\\u597d; \\u4e8c\\u4fbf\\u53ef\\n\", \"tongue\": \"\\u820c\\u6de1\\u7d05, \\u82d4\\u8584\\u767d\", \"pulse\": \"\\u5de6\\u8108:\\u5f26, \\u53f3\\u8108:\\u5f26\", \"remark\": \"\", \"disease_code1\": \"\", \"disease_code2\": \"\", \"disease_code3\": \"\", \"disease_code4\": \"\", \"distinguish\": \"\", \"cure\": \"\", \"treatment\": \"\"}, \"prescript\": [], \"dosage\": [{\"medicine_set\": 1, \"package\": \"\", \"presdays\": \"\", \"instruction\": \"\"}, {\"medicine_set\": 2, \"package\": \"\", \"presdays\": \"\", \"instruction\": \"\"}]}','2025-06-11 00:54:28');
/*!40000 ALTER TABLE `extension_json` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-13 12:59:56
