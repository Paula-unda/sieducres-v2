"""
screens/docente_contenido_estadisticas.py
Reemplaza docente/estadisticas_contenido.php.
"""

import flet as ft

import api_client

COLOR_PRIMARIO = "#4BC4E7"
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"
COLOR_EXITO = "#58BC67"


def vista_docente_contenido_estadisticas(page: ft.Page, contenido_id: int) -> ft.View:
    contenedor = ft.Column(spacing=10)
    texto_mensaje = ft.Text(value="", size=14, visible=False)

    def fila_estudiante(est: dict) -> ft.Row:
        completado = bool(est.get("completado"))
        icono = ft.icons.CHECK_CIRCLE if completado else ft.icons.RADIO_BUTTON_UNCHECKED
        color = COLOR_EXITO if completado else COLOR_PLACEHOLDER
        detalle = f"{round(est.get('porcentaje_visto') or 0)}%" if completado else "Sin ver"
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icono, color=color, size=18),
                        ft.Text(est["nombre"], size=14, color=COLOR_TEXTO),
                    ]
                ),
                ft.Text(detalle, size=13, color=color),
            ],
        )

    def cargar():
        try:
            datos = api_client.obtener_estadisticas_contenido(contenido_id)
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        total = datos.get("total_estudiantes_clase", 0)
        vieron = datos.get("estudiantes_vieron", 0)
        porcentaje = datos.get("porcentaje", 0)

        controles = [
            ft.Container(
                bgcolor="white",
                border_radius=8,
                padding=16,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Text(f"{vieron} de {total} estudiantes han visto este contenido", size=15, weight=ft.FontWeight.W_600),
                        ft.ProgressBar(value=(porcentaje / 100), color=COLOR_EXITO, bgcolor="#E0E0E0", height=8),
                        ft.Text(f"{porcentaje}% de la clase", size=13, color=COLOR_PLACEHOLDER),
                    ],
                ),
            ),
            ft.Container(height=16),
            ft.Text("Detalle por estudiante:", size=14, weight=ft.FontWeight.W_600),
        ]

        estudiantes = datos.get("estudiantes", [])
        if not estudiantes:
            controles.append(ft.Text("No hay estudiantes registrados en este grado/seccion.", color=COLOR_PLACEHOLDER, size=13))
        else:
            controles.extend([fila_estudiante(est) for est in estudiantes])

        contenedor.controls = controles
        page.update()

    def volver(e):
        page.go("/docente/contenidos")

    cargar()

    return ft.View(
        route=f"/docente/contenido-estadisticas/{contenido_id}",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Estadisticas del contenido"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(controls=[texto_mensaje, contenedor]),
            ),
        ],
    )