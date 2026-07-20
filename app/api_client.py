"""
api_client.py
Todas las llamadas HTTP hacia el backend van aqui, tal como establece
la estructura de carpetas del documento de referencia.

Reemplaza lo que en V1.0 era una conexion directa a PostgreSQL desde
las paginas PHP (getConexion() en funciones.php). En V2.0, la app NUNCA
habla directo con la base de datos: siempre pasa por esta capa, que
llama al backend FastAPI por HTTP.
"""

import os
import requests
from typing import Optional

from session import sesion_activa

BASE_URL = "http://127.0.0.1:8000"


def _headers_autenticados() -> dict:
    if sesion_activa.token:
        return {"Authorization": f"Bearer {sesion_activa.token}"}
    return {}


class ApiError(Exception):
    """Se lanza cuando el backend responde con un error, o cuando falla la conexion/tiempo de espera."""
    def __init__(self, mensaje: str, status_code: int = 0):
        self.mensaje = mensaje
        self.status_code = status_code
        super().__init__(mensaje)


def _manejar_respuesta(respuesta: requests.Response) -> dict:
    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json().get("detail", "Ocurrio un error inesperado")
        except ValueError:
            detalle = "Ocurrio un error inesperado"

        if isinstance(detalle, list):
            mensajes = [item.get("msg", str(item)) for item in detalle]
            detalle = " / ".join(mensajes)

        raise ApiError(detalle, respuesta.status_code)
    return respuesta.json()


def _peticion(metodo, url, **kwargs) -> requests.Response:
    """
    Envoltorio comun para todas las peticiones HTTP. Atrapa CUALQUIER
    error de red (no solo 'no hay conexion', sino tambien 'se tardo
    demasiado' u otros), y siempre lo convierte en un ApiError legible.
    Antes, solo se atrapaba ConnectionError: si ocurria un Timeout (por
    ejemplo al subir un archivo grande), el error se escapaba sin
    convertirse en ApiError y rompia el codigo que llamaba a esta funcion.
    """
    try:
        return metodo(url, **kwargs)
    except requests.exceptions.Timeout:
        raise ApiError("El servidor tardo demasiado en responder. Intenta de nuevo.")
    except requests.exceptions.ConnectionError:
        raise ApiError("No se pudo conectar con el servidor. Verifica tu conexion a internet.")
    except requests.exceptions.RequestException as err:
        raise ApiError(f"Ocurrio un problema de red inesperado: {err}")


def obtener_escuelas() -> list:
    respuesta = _peticion(requests.get, f"{BASE_URL}/auth/escuelas", timeout=10)
    return _manejar_respuesta(respuesta)


def login(correo: str, contrasena: str) -> dict:
    respuesta = _peticion(
        requests.post,
        f"{BASE_URL}/auth/login",
        data={"username": correo, "password": contrasena},
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def listar_estudiantes_por_escuela(escuela_id: int) -> list:
    respuesta = _peticion(
        requests.get,
        f"{BASE_URL}/auth/estudiantes/por-escuela",
        params={"escuela_id": escuela_id},
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def registro(
    nombre: str,
    correo: str,
    contrasena: str,
    rol: str,
    escuela_id: Optional[int],
    grado: Optional[str] = None,
    seccion: Optional[str] = None,
    estudiantes_ids: Optional[list] = None,
) -> dict:
    respuesta = _peticion(
        requests.post,
        f"{BASE_URL}/auth/registro",
        json={
            "nombre": nombre,
            "correo": correo,
            "contrasena": contrasena,
            "rol": rol,
            "escuela_id": escuela_id,
            "grado": grado,
            "seccion": seccion,
            "estudiantes_ids": estudiantes_ids,
        },
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def recuperar_contrasena(correo: str) -> dict:
    respuesta = _peticion(
        requests.post, f"{BASE_URL}/auth/recuperar", json={"correo": correo}, timeout=10
    )
    return _manejar_respuesta(respuesta)


# ----------------------------------------------------------------------
# Modulo academico (Sprint 2) - contenidos
# ----------------------------------------------------------------------

def crear_contenido(
    titulo: str,
    descripcion: str,
    asignatura: str,
    enlace: Optional[str] = None,
    archivo_path: Optional[str] = None,
) -> dict:
    datos_formulario = {"titulo": titulo, "descripcion": descripcion, "asignatura": asignatura, "enlace": enlace or ""}
    archivos = None
    manejador_archivo = None
    try:
        if archivo_path:
            manejador_archivo = open(archivo_path, "rb")
            archivos = {"archivo": (os.path.basename(archivo_path), manejador_archivo)}

        respuesta = _peticion(
            requests.post,
            f"{BASE_URL}/contenidos",
            data=datos_formulario,
            files=archivos,
            headers=_headers_autenticados(),
            timeout=60,  # mas tiempo, puede incluir un archivo grande
        )
    finally:
        if manejador_archivo:
            manejador_archivo.close()

    return _manejar_respuesta(respuesta)


def mis_contenidos_docente() -> list:
    respuesta = _peticion(
        requests.get, f"{BASE_URL}/contenidos/mis-contenidos", headers=_headers_autenticados(), timeout=10
    )
    return _manejar_respuesta(respuesta)


def eliminar_contenido(contenido_id: int) -> dict:
    respuesta = _peticion(
        requests.delete,
        f"{BASE_URL}/contenidos/{contenido_id}",
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def mis_contenidos_estudiante() -> list:
    respuesta = _peticion(
        requests.get,
        f"{BASE_URL}/contenidos/mis-contenidos-estudiante",
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def obtener_contenido(contenido_id: int) -> dict:
    respuesta = _peticion(
        requests.get,
        f"{BASE_URL}/contenidos/{contenido_id}",
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def actualizar_progreso(contenido_id: int, porcentaje_visto: float, material_id: Optional[int] = None) -> dict:
    respuesta = _peticion(
        requests.post,
        f"{BASE_URL}/contenidos/{contenido_id}/progreso",
        json={"porcentaje_visto": porcentaje_visto, "material_id": material_id},
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def descargar_reporte_pdf() -> str:
    respuesta = _peticion(
        requests.get,
        f"{BASE_URL}/contenidos/reporte-pdf",
        headers=_headers_autenticados(),
        timeout=30,
    )

    if respuesta.status_code >= 400:
        raise ApiError("No se pudo generar el reporte PDF.", respuesta.status_code)

    carpeta_descargas = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(carpeta_descargas, exist_ok=True)
    ruta_archivo = os.path.join(carpeta_descargas, "reporte_contenidos_sieducres.pdf")
    with open(ruta_archivo, "wb") as f:
        f.write(respuesta.content)

    return ruta_archivo


def editar_contenido(contenido_id: int, campos: dict) -> dict:
    respuesta = _peticion(
        requests.put,
        f"{BASE_URL}/contenidos/{contenido_id}",
        json=campos,
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def obtener_estadisticas_contenido(contenido_id: int) -> dict:
    respuesta = _peticion(
        requests.get,
        f"{BASE_URL}/contenidos/{contenido_id}/estadisticas",
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def agregar_material(
    contenido_id: int,
    titulo: str,
    tipo: str,
    url: Optional[str] = None,
    archivo_path: Optional[str] = None,
    orden: int = 0,
) -> dict:
    datos_formulario = {"titulo": titulo, "tipo": tipo, "url": url or "", "orden": orden}
    archivos = None
    manejador_archivo = None
    try:
        if archivo_path:
            manejador_archivo = open(archivo_path, "rb")
            archivos = {"archivo": (os.path.basename(archivo_path), manejador_archivo)}

        respuesta = _peticion(
            requests.post,
            f"{BASE_URL}/contenidos/{contenido_id}/materiales",
            data=datos_formulario,
            files=archivos,
            headers=_headers_autenticados(),
            timeout=60,  # mas tiempo, puede incluir un archivo grande (video/audio)
        )
    finally:
        if manejador_archivo:
            manejador_archivo.close()

    return _manejar_respuesta(respuesta)


def listar_materiales(contenido_id: int) -> list:
    respuesta = _peticion(
        requests.get,
        f"{BASE_URL}/contenidos/{contenido_id}/materiales",
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def editar_material(material_id: int, campos: dict) -> dict:
    respuesta = _peticion(
        requests.put,
        f"{BASE_URL}/contenidos/materiales/{material_id}",
        json=campos,
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)


def eliminar_material(material_id: int) -> dict:
    respuesta = _peticion(
        requests.delete,
        f"{BASE_URL}/contenidos/materiales/{material_id}",
        headers=_headers_autenticados(),
        timeout=10,
    )
    return _manejar_respuesta(respuesta)