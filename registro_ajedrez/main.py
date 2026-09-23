from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector

app = FastAPI(title="API Sistema de Clasificación de Ajedrez")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def obtener_conexion():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="ajedrez_db"
    )

@app.get("/api/jugadores")
def get_jugadores():
    cnx = obtener_conexion()
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jugadores ORDER BY elo DESC")
    jugadores = cursor.fetchall()
    cursor.close()
    cnx.close()
    return jugadores

@app.post("/api/jugadores")
def create_jugador(data: dict):
    cnx = obtener_conexion()
    cursor = cnx.cursor()
    sql = """
    INSERT INTO jugadores (nombre, pais, titulo, elo, partidas_jugadas, victorias, derrotas, empates)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    valores = (
        data.get("nombre"),
        data.get("pais"),
        data.get("titulo", "Ninguno"),
        data.get("elo", 1200),
        data.get("partidas_jugadas", 0),
        data.get("victorias", 0),
        data.get("derrotas", 0),
        data.get("empates", 0)
    )
    cursor.execute(sql, valores)
    cnx.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    cnx.close()
    return {"mensaje": "Jugador creado correctamente", "id": nuevo_id}

@app.put("/api/jugadores/{jugador_id}")
def update_jugador(jugador_id: int, data: dict):
    cnx = obtener_conexion()
    cursor = cnx.cursor()
    sql = """
    UPDATE jugadores 
    SET nombre=%s, pais=%s, titulo=%s, elo=%s, partidas_jugadas=%s, victorias=%s, derrotas=%s, empates=%s
    WHERE id=%s
    """
    valores = (
        data.get("nombre"),
        data.get("pais"),
        data.get("titulo"),
        data.get("elo"),
        data.get("partidas_jugadas"),
        data.get("victorias"),
        data.get("derrotas"),
        data.get("empates"),
        jugador_id
    )
    cursor.execute(sql, valores)
    cnx.commit()
    cursor.close()
    cnx.close()
    return {"mensaje": "Jugador actualizado correctamente"}

@app.delete("/api/jugadores/{jugador_id}")
def delete_jugador(jugador_id: int):
    cnx = obtener_conexion()
    cursor = cnx.cursor()
    cursor.execute("DELETE FROM jugadores WHERE id = %s", (jugador_id,))
    cnx.commit()
    cursor.close()
    cnx.close()
    return {"mensaje": "Jugador eliminado correctamente"}

@app.get("/api/estadisticas")
def get_estadisticas():
    cnx = obtener_conexion()
    cursor = cnx.cursor(dictionary=True)
    
    cursor.execute("SELECT nombre, elo FROM jugadores ORDER BY elo DESC LIMIT 10")
    top_10 = cursor.fetchall()
    
    cursor.execute("SELECT titulo, COUNT(*) as cantidad FROM jugadores GROUP BY titulo")
    titulos = cursor.fetchall()
    
    sql_rangos = """
    SELECT 
        CASE 
            WHEN elo < 1400 THEN 'Principiante (<1400)'
            WHEN elo BETWEEN 1400 AND 1799 THEN 'Intermedio (1400-1799)'
            WHEN elo BETWEEN 1800 AND 2199 THEN 'Avanzado (1800-2199)'
            WHEN elo BETWEEN 2200 AND 2499 THEN 'Maestro (2200-2499)'
            ELSE 'Gran Maestro (2500+)'
        END AS rango,
        COUNT(*) AS cantidad
    FROM jugadores
    GROUP BY rango
    """
    cursor.execute(sql_rangos)
    rangos_elo = cursor.fetchall()
    
    cursor.execute("SELECT pais, COUNT(*) as cantidad FROM jugadores GROUP BY pais ORDER BY cantidad DESC LIMIT 10")
    paises = cursor.fetchall()
    
    cursor.close()
    cnx.close()
    
    return {
        "top_10": top_10,
        "titulos": titulos,
        "rangos_elo": rangos_elo,
        "paises": paises
    }