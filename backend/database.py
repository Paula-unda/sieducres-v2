"""
database.py
Maneja la conexion a PostgreSQL usando psycopg2 (consultas directas),
tal como se definio en el documento de referencia de conversion V1 -> V2.

Equivale a los datos de conexion que antes estaban en un archivo de
configuracion PHP (por ejemplo conexion.php).
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sieducres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_connection():
    """
    Abre y devuelve una nueva conexion a la base de datos.
    Cada funcion que necesite hablar con la BD debe abrir su propia
    conexion y cerrarla despues (o usar 'with', ver ejemplo en auth.py).
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
        # RealDictCursor hace que cada fila se devuelva como diccionario
        # (ej: fila["correo"]) en lugar de tupla posicional (fila[1]),
        # que es mucho mas facil de convertir a JSON despues.
    )
