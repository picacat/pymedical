CREATE TABLE `stockdispense` (
  `StockDispenseKey` int(11) NOT NULL AUTO_INCREMENT,
  `CaseDate` date DEFAULT NULL,
  `ArchivedDate` date DEFAULT NULL,
  `User` varchar(100) DEFAULT NULL,
  `Remark` varchar(100) DEFAULT NULL,
  `TimeStamp` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`StockDispenseKey`),
  KEY `CaseDate` (`ArchivedDate`)
) ENGINE=MyISAM CHARACTER SET utf8;
