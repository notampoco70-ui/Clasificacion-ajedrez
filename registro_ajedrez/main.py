from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import os
import random
from faker import Faker

app = FastAPI(title="API Sistema de Clasificación de Ajedrez")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CARPETA_FICHAS = "fichas_jugadores"
os.makedirs(CARPETA_FICHAS, exist_ok=True)

def obtener_conexion():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="root123",  # Cambia por tu contraseña de MySQL si aplica
            database="ajedrez_db"
        )
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en la BD MySQL: {err}")

# ==========================================================
# REGISTRO DE NUEVOS USUARIOS
# ==========================================================

@app.post("/api/register")
def register(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña requeridos.")

    try:
        cnx = obtener_conexion()
        cursor = cnx.cursor()
        
        # Verificar si el usuario ya existe
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            cnx.close()
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado.")

        # Insertar nuevo usuario con rol predeterminado 'usuario'
        cursor.execute(
            "INSERT INTO usuarios (username, password, rol) VALUES (%s, %s, %s)",
            (username, password, "usuario")
        )
        cnx.commit()
        cursor.close()
        cnx.close()

        return {"mensaje": "Usuario registrado exitosamente", "username": username, "rol": "usuario"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# AUTHENTICATION / AUTENTICACIÓN
# ==========================================================

@app.post("/api/login")
def login(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña requeridos.")

    try:
        cnx = obtener_conexion()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT id, username, rol FROM usuarios WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        cnx.close()

        if not user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

        return {
            "mensaje": "Inicio de sesión exitoso",
            "username": user["username"],
            "rol": user["rol"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# 1. ENDPOINTS MYSQL (TABLA, ADMINISTRACIÓN Y GRÁFICAS)
# ==========================================================

@app.get("/api/jugadores")
def get_jugadores():
    try:
        cnx = obtener_conexion()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT * FROM jugadores ORDER BY elo DESC")
        jugadores = cursor.fetchall()
        cursor.close()
        cnx.close()
        return jugadores
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jugadores")
def create_jugador(data: dict):
    try:
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
            int(data.get("elo", 1200)),
            int(data.get("partidas_jugadas", 0)),
            0, 0, 0
        )
        cursor.execute(sql, valores)
        cnx.commit()
        nuevo_id = cursor.lastrowid
        cursor.close()
        cnx.close()
        return {"mensaje": "Jugador creado", "id": nuevo_id}
    except ValueError:
        raise HTTPException(status_code=400, detail="El ELO y las partidas deben ser números enteros.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/jugadores/{jugador_id}")
def update_jugador(jugador_id: int, data: dict):
    try:
        cnx = obtener_conexion()
        cursor = cnx.cursor()
        sql = """
        UPDATE jugadores 
        SET nombre=%s, pais=%s, titulo=%s, elo=%s, partidas_jugadas=%s
        WHERE id=%s
        """
        valores = (
            data.get("nombre"),
            data.get("pais"),
            data.get("titulo"),
            int(data.get("elo")),
            int(data.get("partidas_jugadas")),
            jugador_id
        )
        cursor.execute(sql, valores)
        cnx.commit()
        cursor.close()
        cnx.close()
        return {"mensaje": "Jugador actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/jugadores/todos")
def vaciar_base_de_datos(x_user_role: str = Header(None, alias="X-User-Role")):
    """Borra todos los registros de la tabla jugadores (Solo Administrador)."""
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado: solo los administradores pueden vaciar la base de datos.")

    try:
        cnx = obtener_conexion()
        cursor = cnx.cursor()
        cursor.execute("TRUNCATE TABLE jugadores")
        cnx.commit()
        cursor.close()
        cnx.close()
        return {"mensaje": "La base de datos ha sido vaciada completamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al vaciar BD: {str(e)}")

@app.delete("/api/jugadores/{jugador_id}")
def delete_jugador(jugador_id: int):
    """Permitido tanto para admin como para usuario normal."""
    try:
        cnx = obtener_conexion()
        cursor = cnx.cursor()
        cursor.execute("DELETE FROM jugadores WHERE id = %s", (jugador_id,))
        cnx.commit()
        cursor.close()
        cnx.close()
        return {"mensaje": "Jugador eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jugadores/generar")
def generar_registros_aleatorios(cantidad: int = 1000, x_user_role: str = Header(None, alias="X-User-Role")):
    """Genera N registros aleatorios e inserta en lote en MySQL (Solo Administrador)."""
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado: solo los administradores pueden generar registros en masa.")

    try:
        fake = Faker()
        TITULOS = ['Ninguno', 'CM', 'FM', 'IM', 'GM']
        PESOS_TITULOS = [0.85, 0.07, 0.05, 0.02, 0.01]

        cnx = obtener_conexion()
        cursor = cnx.cursor()

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
        cnx.commit()
        insertados = cursor.rowcount
        cursor.close()
        cnx.close()

        return {"mensaje": f"Se generaron e insertaron {insertados} registros correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar datos: {str(e)}")

@app.get("/api/estadisticas")
def get_estadisticas():
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# 2. VALIDACIÓN DE FECHA Y TUPLAS CON TRY-EXCEPT
# ==========================================================

def validar_y_obtener_tupla_fecha(fecha_str: str) -> tuple:
    try:
        partes = fecha_str.strip().split('/')
        if len(partes) != 3:
            raise ValueError("Formato de fecha incorrecto. Debe ser dd/mm/aa (ej: 23/09/26).")
        
        dia, mes, anio = int(partes[0]), int(partes[1]), int(partes[2])
        
        if not (1 <= dia <= 31 and 1 <= mes <= 12 and 0 <= anio <= 99):
            raise ValueError("Día (1-31), Mes (1-12) o Año (00-99) fuera de rango válido.")
            
        tupla_fecha = (f"{dia:02d}", f"{mes:02d}", f"{anio:02d}")
        return tupla_fecha

    except ValueError as ve:
        raise ValueError(f"Excepción en Validación de Fecha: {ve}")
    except Exception as e:
        raise ValueError(f"Error procesando la fecha: {e}")

# ==========================================================
# 3. MENÚ INTERACTIVO Y DICCIONARIO DE ARCHIVOS
# ==========================================================

OPCIONES_MENU = [
    {"id": 1, "titulo": "Crear Ficha (.txt)", "descripcion": "Valida fecha dd/mm/aa, genera tupla y guarda el archivo"},
    {"id": 2, "titulo": "Listar y Abrir Fichas", "descripcion": "Muestra diccionario de archivos y permite abrir uno"},
    {"id": 3, "titulo": "Escribir/Anexar Datos", "descripcion": "Anexa observaciones al archivo seleccionando su clave"},
    {"id": 4, "titulo": "Cerrar Sesión", "descripcion": "Reinicia la sesión del usuario actual"}
]

@app.get("/api/menu")
def obtener_menu():
    return {"opciones": OPCIONES_MENU}

@app.post("/api/menu/ejecutar")
def ejecutar_menu(payload: dict):
    opcion = payload.get("opcion")
    usuario_actual = payload.get("usuario_actual", "Anónimo")
    lineas_salida = []

    archivos_lista = os.listdir(CARPETA_FICHAS)
    dict_archivos = {str(i + 1): arch for i, arch in enumerate(archivos_lista)}

    try:
        if opcion == 1:
            nombre = payload.get("nombre", "").strip()
            pais = payload.get("pais", "Desconocido").strip()
            titulo = payload.get("titulo", "Ninguno").strip()
            fecha_str = payload.get("fecha", "").strip()
            enfrentamientos = payload.get("enfrentamientos", "Sin registro").strip()

            try:
                elo = int(payload.get("elo", 1200))
            except (ValueError, TypeError):
                raise ValueError("El ELO debe ser un valor entero numérico válido.")

            if not nombre:
                raise ValueError("El nombre del jugador es requerido para la ficha.")

            tupla_fecha = validar_y_obtener_tupla_fecha(fecha_str)
            nombre_archivo = f"{nombre.lower().replace(' ', '_')}_ficha.txt"
            ruta_completa = os.path.join(CARPETA_FICHAS, nombre_archivo)

            contenido = (
                f"=========================================\n"
                f"         FICHA TÉCNICA DE AJEDREZ        \n"
                f"=========================================\n"
                f"Registrado por: {usuario_actual}\n"
                f"Fecha Registro (Tupla): {tupla_fecha} -> {tupla_fecha[0]}/{tupla_fecha[1]}/{tupla_fecha[2]}\n"
                f"Nombre: {nombre}\n"
                f"País: {pais}\n"
                f"Título: {titulo}\n"
                f"ELO: {elo}\n"
                f"Enfrentamientos: {enfrentamientos}\n"
                f"=========================================\n"
            )

            try:
                with open(ruta_completa, "w", encoding="utf-8") as f:
                    f.write(contenido)
            except IOError as io_err:
                raise IOError(f"Error de E/S al escribir en el disco: {io_err}")

            archivos_lista = os.listdir(CARPETA_FICHAS)
            dict_archivos = {str(i + 1): arch for i, arch in enumerate(archivos_lista)}

            lineas_salida = [
                f">>> [ÉXITO] Archivo '{nombre_archivo}' guardado correctamente.",
                f"  • Tupla de Fecha generada: ({tupla_fecha[0]}, {tupla_fecha[1]}, {tupla_fecha[2]})",
                f"  • Archivo guardado en: {ruta_completa}",
                "\n--- VISTA PREVIA DEL CONTENIDO ---",
                contenido
            ]

        elif opcion == 2:
            clave_o_nombre = payload.get("archivo_solicitado", "").strip()

            lineas_salida.append(">>> [ESTRUCTURA DE DICCIONARIO DE ARCHIVOS (.TXT)]")
            
            if not dict_archivos:
                lineas_salida.append("  ⚠️ El diccionario está vacío. Usa la Opción 1 para crear un archivo.")
            else:
                lineas_salida.append(f"  dict_archivos = {dict_archivos}\n")
                lineas_salida.append("  Opciones disponibles:")
                for k, v in dict_archivos.items():
                    lineas_salida.append(f"    • Clave [{k}] => Archivo: '{v}'")

                if clave_o_nombre:
                    archivo_a_abrir = dict_archivos.get(clave_o_nombre, clave_o_nombre)
                    ruta = os.path.join(CARPETA_FICHAS, archivo_a_abrir)

                    try:
                        with open(ruta, "r", encoding="utf-8") as f:
                            contenido_leido = f.read()
                        lineas_salida.append(f"\n--- CONTENIDO LEÍDO DE: '{archivo_a_abrir}' ---")
                        lineas_salida.append(contenido_leido)
                    except FileNotFoundError:
                        raise FileNotFoundError(f"El archivo '{archivo_a_abrir}' no existe en el directorio.")
                    except IOError as io_err:
                        raise IOError(f"Error al leer archivo: {io_err}")

        elif opcion == 3:
            clave_o_nombre = payload.get("archivo_solicitado", "").strip()
            nota = payload.get("nota_adicional", "").strip()
            fecha_str = payload.get("fecha", "").strip()

            if not dict_archivos:
                raise ValueError("No hay archivos en el diccionario para modificar.")

            if not nota:
                raise ValueError("Debes ingresar una nota u observación a anexar.")

            tupla_fecha = validar_y_obtener_tupla_fecha(fecha_str)
            archivo_target = dict_archivos.get(clave_o_nombre, clave_o_nombre) if clave_o_nombre else list(dict_archivos.values())[0]
            ruta = os.path.join(CARPETA_FICHAS, archivo_target)

            try:
                with open(ruta, "a", encoding="utf-8") as f:
                    f.write(f"  [Anexo {tupla_fecha[0]}/{tupla_fecha[1]}/{tupla_fecha[2]} | Tupla {tupla_fecha} por {usuario_actual}]: {nota}\n")

                lineas_salida = [
                    f">>> [ÉXITO] Anexo añadido a '{archivo_target}' con tupla de fecha {tupla_fecha}.",
                    "\n--- CONTENIDO ACTUALIZADO DEL ARCHIVO ---"
                ]

                with open(ruta, "r", encoding="utf-8") as f:
                    lineas_salida.append(f.read())
            except FileNotFoundError:
                raise FileNotFoundError(f"No se encontró el archivo '{archivo_target}'.")
            except IOError as io_err:
                raise IOError(f"Error de escritura en archivo: {io_err}")

        elif opcion == 4:
            lineas_salida = [
                ">>> [SISTEMA] Cerrando sesión...",
                f"  • Usuario '{usuario_actual}' desconectado.",
                "  • Volviendo al menú de bienvenida..."
            ]

        else:
            raise ValueError(f"Opción {opcion} no válida.")

    except (ValueError, FileNotFoundError, IOError) as ex_conocida:
        lineas_salida = [f"⚠️ EXCEPCIÓN CAPTURADA EN PYTHON ({type(ex_conocida).__name__}):\n  -> {ex_conocida}"]
    except Exception as ex_general:
        lineas_salida = [f"❌ ERROR INESPERADO ({type(ex_general).__name__}):\n  -> {ex_general}"]

    return {
        "lineas_consola": lineas_salida,
        "dict_archivos": dict_archivos,
        "archivos": list(dict_archivos.values())
    }