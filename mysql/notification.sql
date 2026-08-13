CREATE TABLE IF NOT EXISTS notification (
    NotificationKey BIGINT       NOT NULL AUTO_INCREMENT,
    Channel         VARCHAR(32)  NOT NULL DEFAULT '',   -- registration / waiting_list /call_number / system
    Source          VARCHAR(64)  NOT NULL DEFAULT '',   -- 發送站台，用來過濾自己
    Message         TEXT,
    CreatedAt       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (NotificationKey),
    INDEX idx_created (CreatedAt)                       -- 只給 purge 用
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;