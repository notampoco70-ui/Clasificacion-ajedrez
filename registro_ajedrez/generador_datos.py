import random
from faker import Faker
import mysql.connector

fake = Faker()

TITULOS = ['Ninguno', 'CM', 'FM', 'IM', 'GM']
PESOS_TITULOS = [0.85, 0.07, 0.05, 0.02, 0.01]

def conectar_bd():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="ajedrez_db"
    )

def generar_jugadores(cantidad=1000):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    print(f"Generando {cantidad} jugadores aleatorios...")
    
    sql = """
    INSERT INTO jugadores 
    (nombre, pais, titulo, elo, partidas_jugadas, victorias, derrotas, empates)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    jugadores = []
    for _ in range(cantidad):
        nombre = fake.name()
        pais = fake.country()
        titulo = random.choices(TITULOS, weights=PESOS_TITULOS)[0]
      
        if titulo == 'GM':
            elo = random.randint(2500, 2850)
        elif titulo == 'IM':
            elo = random.randint(2400, 2550)
        elif titulo == 'FM':
            elo = random.randint(2300, 2450)
        elif titulo == 'CM':
            elo = random.randint(2200, 2350)
        else:
            elo = random.randint(1000, 2199)
            
        partidas = random.randint(10, 500)
        victorias = random.randint(0, partidas)
        derrotas = random.randint(0, partidas - victorias)
        empates = partidas - victorias - derrotas
        
        jugadores.append((nombre, pais, titulo, elo, partidas, victorias, derrotas, empates))
    
    cursor.executemany(sql, jugadores)
    conexion.commit()
    
    print(f"¡Éxito! Se insertaron {cursor.rowcount} registros correctamente.")
    cursor.close()
    conexion.close()

if __name__ == "__main__":
    generar_jugadores(1000)