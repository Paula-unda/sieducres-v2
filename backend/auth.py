"""
auth.py
Reemplaza la logica de auth/login.php + auth/procesar_login.php + auth/funciones.php

Cambios clave respecto a la version PHP (segun el documento de referencia):
  - PHP guardaba el rol en $_SESSION['rol'].
    Aqui el rol viaja DENTRO del token JWT, firmado, y se verifica en
    cada peticion sin depender de sesiones de servidor.
  - La consulta SQL "SELECT * FROM usuarios WHERE correo = %s" se mantiene
    identica a la que ya tenian en PHP (mismo nombre de tabla y columnas).
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from dotenv import load_dotenv

from database import get_connection

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

if not SECRET_KEY:
    raise RuntimeError(
        "Falta SECRET_KEY en el archivo .env. "
        "Genera una con: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

# passlib entiende hashes bcrypt con prefijo $2a$, $2b$ o $2y$,
# por lo que las contrasenas ya guardadas en V1.0 (formato $2a$06$...)
# funcionan sin necesidad de migrarlas.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Le dice a FastAPI donde esta el endpoint de login,
# para que /docs sepa donde pedir el token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["Autenticacion"])

# ----------------------------------------------------------------------
# Limite de intentos de login (proteccion basica anti fuerza bruta)
# ----------------------------------------------------------------------
# Se guarda en memoria del proceso (no en BD ni Redis): suficiente para
# el alcance de este proyecto (un solo servidor backend), pero se pierde
# si el servidor se reinicia, y no se comparte si en el futuro se corren
# varias instancias del backend al mismo tiempo (limitacion conocida).
MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15
intentos_login: dict = {}  # correo -> {"conteo": int, "bloqueado_hasta": datetime|None}


def _verificar_bloqueo(correo: str):
    """Lanza 429 si el correo esta temporalmente bloqueado por demasiados intentos fallidos."""
    registro_intentos = intentos_login.get(correo)
    if not registro_intentos:
        return
    bloqueado_hasta = registro_intentos.get("bloqueado_hasta")
    if bloqueado_hasta and datetime.now(timezone.utc) < bloqueado_hasta:
        minutos_restantes = int((bloqueado_hasta - datetime.now(timezone.utc)).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Demasiados intentos fallidos. Intenta de nuevo en {minutos_restantes} minuto(s), "
                "o contacta al administrador si no fuiste tu."
            ),
        )


def _registrar_intento_fallido(correo: str):
    registro_intentos = intentos_login.setdefault(correo, {"conteo": 0, "bloqueado_hasta": None})
    registro_intentos["conteo"] += 1
    if registro_intentos["conteo"] >= MAX_INTENTOS_FALLIDOS:
        registro_intentos["bloqueado_hasta"] = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_BLOQUEO)


def _limpiar_intentos(correo: str):
    intentos_login.pop(correo, None)


# ----------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------

def verificar_contrasena(contrasena_plana: str, contrasena_hash: str) -> bool:
    """Compara la contrasena escrita por el usuario contra el hash guardado en BD."""
    return pwd_context.verify(contrasena_plana, contrasena_hash)


def buscar_usuario_por_correo(correo: str):
    """
    Equivale a: SELECT * FROM usuarios WHERE correo = ? (auth/funciones.php)
    Devuelve None si no existe.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, correo, contrasena, rol, activo, escuela_id
                FROM usuarios
                WHERE correo = %s
                """,
                (correo,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def crear_token_acceso(datos: dict) -> str:
    """Genera un JWT firmado que incluye el rol y expira segun ACCESS_TOKEN_EXPIRE_MINUTES."""
    datos_token = datos.copy()
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    datos_token.update({"exp": expira})
    return jwt.encode(datos_token, SECRET_KEY, algorithm=ALGORITHM)


# ----------------------------------------------------------------------
# Dependencias para proteger endpoints (usadas por los routers de cada rol)
# ----------------------------------------------------------------------

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Reemplaza la verificacion de $_SESSION en cada pagina protegida de PHP.
    Se usa como Depends(get_current_user) en cualquier endpoint que
    requiera que el usuario este autenticado.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        if usuario_id is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    return {
        "id": int(usuario_id),
        "nombre": payload.get("nombre"),
        "correo": payload.get("correo"),
        "rol": payload.get("rol"),
        "escuela_id": payload.get("escuela_id"),
    }


def requerir_rol(*roles_permitidos: str):
    """
    Fabrica de dependencias para restringir un endpoint a ciertos roles.
    Equivale a: if ($_SESSION['rol'] !== 'Docente') { ... } en PHP.

    Uso en un router, por ejemplo backend/routers/docente.py:
        @router.get("/mis-contenidos")
        def mis_contenidos(usuario: dict = Depends(requerir_rol("Docente"))):
            ...
    """
    def verificador(usuario: dict = Depends(get_current_user)) -> dict:
        if usuario["rol"] not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Este recurso requiere rol: {', '.join(roles_permitidos)}",
            )
        return usuario
    return verificador


# ----------------------------------------------------------------------
# Endpoint de login
# ----------------------------------------------------------------------

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Reemplaza auth/login.php + auth/procesar_login.php

    form_data.username = correo del usuario (OAuth2 llama "username" al campo,
    aunque en SIEDUCRES el login es por correo, no por nombre de usuario).
    form_data.password = contrasena en texto plano escrita en el formulario.
    """
    _verificar_bloqueo(form_data.username)

    usuario = buscar_usuario_por_correo(form_data.username)

    if usuario is None:
        _registrar_intento_fallido(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos",
        )

    if not usuario["activo"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este usuario esta desactivado. Contacta al administrador.",
        )

    if not verificar_contrasena(form_data.password, usuario["contrasena"]):
        _registrar_intento_fallido(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos",
        )

    _limpiar_intentos(form_data.username)

    token = crear_token_acceso({
        "sub": str(usuario["id"]),
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "rol": usuario["rol"],
        "escuela_id": usuario["escuela_id"],
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "correo": usuario["correo"],
            "rol": usuario["rol"],
            "escuela_id": usuario["escuela_id"],
        },
    }


# ----------------------------------------------------------------------
# Autorregistro (C01 - Must Have del Documento Vision)
# ----------------------------------------------------------------------

ROLES_AUTORREGISTRO = ("Docente", "Estudiante", "Representante")
# Nota: "Administrador" queda excluido a proposito. Ese rol solo lo puede
# asignar otro administrador ya existente, nunca por autorregistro abierto.


class RegistroUsuario(BaseModel):
    nombre: str
    correo: EmailStr
    contrasena: str
    rol: str
    escuela_id: Optional[int] = None
    grado: Optional[str] = None    # obligatorio si rol es Docente o Estudiante
    seccion: Optional[str] = None  # obligatorio si rol es Docente o Estudiante
    estudiantes_ids: Optional[List[int]] = None  # obligatorio si rol es Representante (IDs obtenidos de /auth/estudiantes/buscar)

    @field_validator("contrasena")
    @classmethod
    def validar_fortaleza_contrasena(cls, valor: str) -> str:
        """
        Politica de contrasena: minimo 8 caracteres, con al menos una
        letra y un numero. Se balancea con la usabilidad del proyecto
        (usuarios incluyen estudiantes de escuela rural) sin bajar a
        exigir mayusculas/simbolos, que suele generar mas contrasenas
        anotadas en papel que contrasenas realmente mas seguras.
        """
        if len(valor) < 8:
            raise ValueError("La contrasena debe tener al menos 8 caracteres")
        if not any(c.isalpha() for c in valor):
            raise ValueError("La contrasena debe incluir al menos una letra")
        if not any(c.isdigit() for c in valor):
            raise ValueError("La contrasena debe incluir al menos un numero")
        return valor


@router.get("/escuelas")
def listar_escuelas():
    """
    Devuelve las 12 instituciones del NER 319, para que la pantalla de
    autorregistro pueda mostrar un selector de escuela. Es publico
    (no requiere token) porque se usa antes de que el usuario tenga cuenta.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, parroquia FROM escuelas WHERE activo = true ORDER BY id"
            )
            return cur.fetchall()
    finally:
        conn.close()


@router.get("/estudiantes/por-escuela")
def listar_estudiantes_por_escuela(escuela_id: int):
    """
    Lista los estudiantes de una escuela especifica, para que un
    Representante pueda elegir a su hijo/a de una lista en vez de
    escribir su nombre o correo (que muchos representantes no
    memorizan). Se filtra primero por escuela porque los hijos de un
    mismo representante pueden estar en instituciones distintas del
    NER 319.

    Es publico (no requiere token) porque se usa durante el registro
    del representante, antes de que tenga cuenta. Por privacidad, el
    correo se devuelve parcialmente oculto.

    Decision de diseno: un estudiante que YA tiene un representante
    vinculado deja de aparecer en esta lista, para evitar que dos
    personas distintas reclamen al mismo estudiante por error. Si en el
    futuro se necesita permitir varios representantes por estudiante
    (ej: madre y padre), quitar el filtro 're.estudiante_id IS NULL'.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.nombre, u.correo, e.grado, e.seccion
                FROM usuarios u
                INNER JOIN estudiantes e ON e.usuario_id = u.id
                LEFT JOIN representantes_estudiantes re ON re.estudiante_id = u.id
                WHERE u.rol = 'Estudiante' AND u.activo = true AND u.escuela_id = %s
                    AND re.estudiante_id IS NULL
                ORDER BY e.grado, e.seccion, u.nombre
                """,
                (escuela_id,),
            )
            resultados = cur.fetchall()
    finally:
        conn.close()

    def enmascarar_correo(correo: str) -> str:
        usuario_parte, _, dominio = correo.partition("@")
        visible = usuario_parte[:2] if len(usuario_parte) > 2 else usuario_parte[:1]
        return f"{visible}***@{dominio}"

    return [
        {
            "id": r["id"],
            "nombre": r["nombre"],
            "correo_enmascarado": enmascarar_correo(r["correo"]),
            "grado": r["grado"],
            "seccion": r["seccion"],
        }
        for r in resultados
    ]


@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(datos: RegistroUsuario):
    """
    Reemplaza el modulo de autorregistro (nuevo en V2.0, no existia en V1.0).
    Cualquier docente, estudiante o representante puede crear su cuenta
    sin aprobacion previa del administrador (segun alcance del Documento
    Vision, seccion 5.1). El administrador conserva la capacidad de
    gestionar o revocar accesos despues, pero no bloquea el registro inicial.
    """
    if datos.rol not in ROLES_AUTORREGISTRO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol debe ser uno de: {', '.join(ROLES_AUTORREGISTRO)}",
        )

    # Docente y Estudiante SI necesitan grado/seccion para poder usar el
    # modulo academico (publicar o ver contenidos). Representante no.
    if datos.rol in ("Docente", "Estudiante") and not (datos.grado and datos.seccion):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los usuarios con rol Docente o Estudiante deben indicar grado y seccion",
        )

    # Representante debe vincularse a al menos un estudiante YA registrado
    # (no se permite crear el estudiante desde el formulario del representante,
    # por decision de diseno: mantiene el registro simple y evita cuentas
    # de estudiante creadas "a nombre de otro" sin su propia contrasena).
    if datos.rol == "Representante" and not datos.estudiantes_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar al menos un estudiante para vincularte como representante",
        )

    if buscar_usuario_por_correo(datos.correo) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese correo",
        )

    contrasena_hash = pwd_context.hash(datos.contrasena)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (nombre, correo, contrasena, rol, activo, escuela_id)
                VALUES (%s, %s, %s, %s, true, %s)
                RETURNING id, nombre, correo, rol, escuela_id
                """,
                (datos.nombre, datos.correo, contrasena_hash, datos.rol, datos.escuela_id),
            )
            nuevo_usuario = cur.fetchone()

            # Segun el rol, se crea ademas la fila en docentes o estudiantes
            # con su grado/seccion, para que el modulo academico (Sprint 2)
            # pueda filtrar contenidos automaticamente sin pasos manuales.
            if datos.rol == "Docente":
                cur.execute(
                    "INSERT INTO docentes (usuario_id, grado, seccion) VALUES (%s, %s, %s)",
                    (nuevo_usuario["id"], datos.grado, datos.seccion),
                )
            elif datos.rol == "Estudiante":
                cur.execute(
                    "INSERT INTO estudiantes (usuario_id, grado, seccion) VALUES (%s, %s, %s)",
                    (nuevo_usuario["id"], datos.grado, datos.seccion),
                )
            elif datos.rol == "Representante":
                # Ya se validaron por nombre en /auth/estudiantes/buscar antes
                # del registro; aqui solo se confirma que el ID sigue existiendo
                # con rol 'Estudiante' (por si fue eliminado justo antes de enviar).
                ids_no_encontrados = []
                ids_validos = []
                for estudiante_id in datos.estudiantes_ids:
                    cur.execute(
                        "SELECT id FROM usuarios WHERE id = %s AND rol = 'Estudiante'",
                        (estudiante_id,),
                    )
                    if cur.fetchone() is None:
                        ids_no_encontrados.append(estudiante_id)
                    else:
                        ids_validos.append(estudiante_id)

                if ids_no_encontrados:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Uno o mas estudiantes seleccionados ya no estan disponibles. "
                            "Vuelve a buscarlos e intenta de nuevo."
                        ),
                    )

                for estudiante_id in ids_validos:
                    cur.execute(
                        "INSERT INTO representantes_estudiantes (representante_id, estudiante_id) "
                        "VALUES (%s, %s)",
                        (nuevo_usuario["id"], estudiante_id),
                    )

            conn.commit()
    finally:
        conn.close()

    return {
        "mensaje": "Usuario registrado exitosamente",
        "usuario": nuevo_usuario,
    }


@router.get("/perfil")
def perfil(usuario: dict = Depends(get_current_user)):
    """
    Endpoint de prueba: si el token es valido, devuelve los datos del usuario.
    Sirve para verificar en /docs que el login + token funcionan de punta a punta.
    """
    return usuario


# ----------------------------------------------------------------------
# Recuperacion de contrasena (reemplaza notificar_olvido.php)
# ----------------------------------------------------------------------

class SolicitudRecuperacion(BaseModel):
    correo: EmailStr


@router.post("/recuperar")
def recuperar_contrasena(datos: SolicitudRecuperacion):
    """
    Reemplaza auth/notificar_olvido.php

    En V1.0 esto no enviaba un correo real: creaba una notificacion interna
    dirigida al Administrador para que el reestablezca la contrasena
    manualmente. Se mantiene la misma logica aqui, insertando una fila
    en la tabla 'notificaciones' que ya existe en la base de datos.
    """
    usuario = buscar_usuario_por_correo(datos.correo)

    if usuario is None:
        # Se devuelve el mismo mensaje exista o no el correo,
        # para no revelar qué correos estan registrados en el sistema.
        return {"mensaje": "Si el correo esta registrado, el administrador sera notificado."}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM usuarios WHERE rol = 'Administrador' AND activo = true LIMIT 1"
            )
            admin = cur.fetchone()

            if admin is not None:
                cur.execute(
                    """
                    INSERT INTO notificaciones (usuario_id, titulo, mensaje, tipo, referencia_id, referencia_tipo)
                    VALUES (%s, %s, %s, 'sistema', %s, 'usuarios')
                    """,
                    (
                        admin["id"],
                        "Solicitud de recuperacion de contrasena",
                        f"El usuario {usuario['nombre']} ({usuario['correo']}) ha solicitado restablecer su contrasena.",
                        usuario["id"],
                    ),
                )
                conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Si el correo esta registrado, el administrador sera notificado."}