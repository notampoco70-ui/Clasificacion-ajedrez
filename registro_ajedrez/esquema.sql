DROP DATABASE IF EXISTS ajedrez_db;

CREATE DATABASE ajedrez_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ajedrez_db;

CREATE TABLE jugadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    pais VARCHAR(150) NOT NULL,
    titulo VARCHAR(20) DEFAULT 'Ninguno',
    elo INT NOT NULL DEFAULT 1200,
    partidas_jugadas INT DEFAULT 0,
    victorias INT DEFAULT 0,
    derrotas INT DEFAULT 0,
    empates INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;