"""
app/main.py
Punto de entrada de la aplicacion movil. Equivale al index.php + el
enrutamiento que antes hacian redirigirPorRol() y los header('Location: ...')
de PHP, pero usando el sistema de rutas nativo de Flet (page.go).
"""

import flet as ft

from screens.login import vista_login
from screens.registro import vista_registro
from screens.recuperar import vista_recuperar
from screens.docente_contenidos import vista_docente_contenidos, vista_docente_contenido_nuevo
from screens.docente_contenido_editar import vista_docente_contenido_editar
from screens.docente_contenido_estadisticas import vista_docente_contenido_estadisticas
from screens.docente_contenido_preview import vista_docente_contenido_preview
from screens.estudiante_contenidos import vista_estudiante_contenidos, vista_estudiante_contenido_detalle
from session import sesion_activa


def vista_inicio(page: ft.Page) -> ft.View:
    """
    Pantalla principal: cada rol ve sus propios accesos, equivalente a
    protegido/docente/index.php, protegido/estudiante/index.php, etc.
    """
    def cerrar_sesion(e):
        sesion_activa.cerrar()
        page.go("/login")

    botones_por_rol = []
    if sesion_activa.rol == "Docente":
        botones_por_rol.append(
            ft.ElevatedButton(
                text="Mis contenidos academicos",
                bgcolor="#4BC4E7",
                color="white",
                on_click=lambda e: page.go("/docente/contenidos"),
            )
        )
    elif sesion_activa.rol == "Estudiante":
        botones_por_rol.append(
            ft.ElevatedButton(
                text="Ver contenidos",
                bgcolor="#4BC4E7",
                color="white",
                on_click=lambda e: page.go("/estudiante/contenidos"),
            )
        )
    # Representante y Administrador: sus modulos se agregan en sprints siguientes.

    return ft.View(
        route="/inicio",
        controls=[
            ft.AppBar(title=ft.Text("SIEDUCRES"), bgcolor="#4BC4E7"),
            ft.Container(
                padding=24,
                content=ft.Column(
                    controls=[
                        ft.Text(f"Bienvenido/a, {sesion_activa.nombre}", size=20, weight=ft.FontWeight.W_600),
                        ft.Text(f"Rol: {sesion_activa.rol}"),
                        ft.Text(f"Correo: {sesion_activa.correo}"),
                        ft.Container(height=20),
                        *botones_por_rol,
                        ft.Container(height=20),
                        ft.OutlinedButton(text="Cerrar sesion", on_click=cerrar_sesion),
                    ]
                ),
            ),
        ],
    )


def main(page: ft.Page):
    page.title = "SIEDUCRES"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.icon = "icon.png"  # Icono que se ve en la barra de titulo/tarea, junto al nombre y la X de cerrar

    # Tamano de ventana tipo celular, solo para que las pruebas en PC
    # se vean parecidas a como se vera en un telefono real. Esto NO
    # afecta el APK final en Android (ahi la app usa el 100% de la
    # pantalla del dispositivo automaticamente).
    page.window.width = 400
    page.window.height = 800
    page.window.resizable = True  # se puede seguir agrandando si se necesita

    def enrutar(route):
        page.views.clear()

        ruta_actual = page.route or "/login"

        # Rutas que requieren sesion activa (equivalen a la verificacion
        # de $_SESSION['usuario_id'] en las paginas protegidas de PHP).
        rutas_protegidas = (
            "/inicio",
            "/docente/contenidos",
            "/docente/contenido-nuevo",
            "/estudiante/contenidos",
        )
        requiere_sesion = (
            ruta_actual in rutas_protegidas
            or ruta_actual.startswith("/estudiante/contenido/")
            or ruta_actual.startswith("/docente/contenido-editar/")
            or ruta_actual.startswith("/docente/contenido-estadisticas/")
            or ruta_actual.startswith("/docente/contenido-preview/")
        )

        if requiere_sesion and not sesion_activa.esta_activa():
            page.go("/login")
            return

        if ruta_actual == "/registro":
            page.views.append(vista_registro(page))
        elif ruta_actual == "/recuperar":
            page.views.append(vista_recuperar(page))
        elif ruta_actual == "/inicio":
            page.views.append(vista_inicio(page))
        elif ruta_actual == "/docente/contenidos":
            page.views.append(vista_docente_contenidos(page))
        elif ruta_actual == "/docente/contenido-nuevo":
            page.views.append(vista_docente_contenido_nuevo(page))
        elif ruta_actual.startswith("/docente/contenido-editar/"):
            contenido_id = int(ruta_actual.rsplit("/", 1)[-1])
            page.views.append(vista_docente_contenido_editar(page, contenido_id))
        elif ruta_actual.startswith("/docente/contenido-estadisticas/"):
            contenido_id = int(ruta_actual.rsplit("/", 1)[-1])
            page.views.append(vista_docente_contenido_estadisticas(page, contenido_id))
        elif ruta_actual.startswith("/docente/contenido-preview/"):
            contenido_id = int(ruta_actual.rsplit("/", 1)[-1])
            page.views.append(vista_docente_contenido_preview(page, contenido_id))
        elif ruta_actual == "/estudiante/contenidos":
            page.views.append(vista_estudiante_contenidos(page))
        elif ruta_actual.startswith("/estudiante/contenido/"):
            contenido_id = int(ruta_actual.rsplit("/", 1)[-1])
            page.views.append(vista_estudiante_contenido_detalle(page, contenido_id))
        else:
            page.views.append(vista_login(page))

        page.update()

    def manejar_resize(e):
        # Al cambiar el tamano de la ventana (o rotar el celular),
        # se reconstruye la vista actual para recalcular anchos
        # segun el nuevo page.width (ver logica en cada pantalla).
        enrutar(page.route)

    page.on_route_change = enrutar
    page.on_resized = manejar_resize
    page.go(page.route or "/login")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")