"""
session.py
Guarda el token JWT y los datos del usuario mientras la app esta abierta.

Reemplaza a $_SESSION de PHP (iniciarSesion() / sesionActiva() en
funciones.php). La diferencia clave: PHP guardaba la sesion en el
SERVIDOR y el navegador solo mandaba una cookie. Aqui el token se
guarda en el propio DISPOSITIVO (celular), y es la app la que lo envia
en cada peticion al backend.

NOTA: esto guarda la sesion solo mientras la app esta abierta en memoria.
Mas adelante, para que la sesion sobreviva si el usuario cierra la app,
se puede usar page.client_storage (almacenamiento persistente de Flet)
en vez de estas variables simples. Se deja asi por ahora para mantener
el Sprint 1 simple.
"""


class Sesion:
    def __init__(self):
        self.token: str | None = None
        self.usuario_id: int | None = None
        self.nombre: str | None = None
        self.correo: str | None = None
        self.rol: str | None = None
        self.escuela_id: int | None = None

    def iniciar(self, respuesta_login: dict):
        """Equivale a iniciarSesion() en funciones.php."""
        self.token = respuesta_login["access_token"]
        datos_usuario = respuesta_login["usuario"]
        self.usuario_id = datos_usuario["id"]
        self.nombre = datos_usuario["nombre"]
        self.correo = datos_usuario["correo"]
        self.rol = datos_usuario["rol"]
        self.escuela_id = datos_usuario["escuela_id"]

    def esta_activa(self) -> bool:
        """Equivale a sesionActiva() en funciones.php."""
        return self.token is not None

    def cerrar(self):
        """
        Reemplaza logout.php.
        En JWT no existe 'cerrar sesion en el servidor': el token es
        valido hasta que expira por si solo. 'Cerrar sesion' aqui
        simplemente significa: borrar el token guardado en el celular,
        para que la app deje de enviarlo.
        """
        self.token = None
        self.usuario_id = None
        self.nombre = None
        self.correo = None
        self.rol = None
        self.escuela_id = None


# Una sola instancia compartida por toda la app (patron simple tipo singleton)
sesion_activa = Sesion()
