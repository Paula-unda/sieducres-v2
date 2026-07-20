"""
screens/docente_contenido_preview.py
Reemplaza docente/previsualizar_contenido.php.
Muestra el contenido EXACTAMENTE con el mismo diseno que ve el
estudiante (banner celeste, tarjeta de instrucciones, colores de
marca), solo que sin el boton "Ya lo vi!" (el docente solo esta
revisando, no debe alterar su propio progreso).
"""

import flet as ft

import api_client
from contenido_visor import bloque_recurso_principal, bloque_material

MARCA_CIAN = "#4BC4E7"
MARCA_ROSA = "#EF5E8E"

COLOR_PRIMARIO = MARCA_CIAN
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"


def vista_docente_contenido_preview(page: ft.Page, contenido_id: int) -> ft.View:
    contenedor = ft.Column(spacing=8)
    texto_mensaje = ft.Text(value="", size=14, visible=False)

    def cargar():
        try:
            c = api_client.obtener_contenido(contenido_id)
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        aviso_preview = ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            bgcolor="#FFF3CD",
            border_radius=6,
            content=ft.Text(
                "\U0001F441\uFE0F Vista previa \u2014 as\u00ed lo ve el estudiante",
                size=12,
                color="#856404",
                weight=ft.FontWeight.W_600,
            ),
        )

        # Mismo banner que la pantalla del estudiante: un solo color solido
        # de marca (celeste), texto oscuro para buen contraste.
        banner = ft.Container(
            border_radius=16,
            padding=20,
            bgcolor=MARCA_CIAN,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text("\U0001F4DA", size=36),
                    ft.Text(c["titulo"], size=19, weight=ft.FontWeight.W_700, color=COLOR_TEXTO),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                bgcolor="#FFFFFF66",
                                border_radius=20,
                                content=ft.Text(
                                    f"\U0001F4D6 {c.get('asignatura') or 'General'}", size=12, color=COLOR_TEXTO
                                ),
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                bgcolor="#FFFFFF66",
                                border_radius=20,
                                content=ft.Text(
                                    f"\U0001F393 {c.get('grado') or '-'} {c.get('seccion') or ''}",
                                    size=12,
                                    color=COLOR_TEXTO,
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

        tarjeta_instrucciones = ft.Container(
            bgcolor="white",
            border_radius=16,
            padding=16,
            shadow=ft.BoxShadow(blur_radius=8, color="#00000015", offset=ft.Offset(0, 3)),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("\U0001F4DD", size=18),
                            ft.Text("Instrucciones del docente", size=15, weight=ft.FontWeight.W_600, color=MARCA_ROSA),
                        ]
                    ),
                    ft.Text(c.get("descripcion") or "", size=14, color=COLOR_TEXTO),
                ],
            ),
        )

        controles = [
            aviso_preview,
            ft.Container(height=14),
            banner,
            ft.Container(height=14),
            tarjeta_instrucciones,
            ft.Container(height=14),
        ]

        recursos = bloque_recurso_principal(page, c)
        if recursos:
            controles.append(
                ft.Row(controls=[ft.Text("\U0001F3AC", size=18), ft.Text("Recursos de la clase", size=15, weight=ft.FontWeight.W_600, color=MARCA_ROSA)])
            )
            controles.append(ft.Container(height=6))
            controles.extend(recursos)
            controles.append(ft.Container(height=14))

        materiales = c.get("materiales") or []
        if materiales:
            controles.append(
                ft.Row(controls=[ft.Text("\U0001F4E6", size=18), ft.Text("Materiales adicionales", size=15, weight=ft.FontWeight.W_600, color=MARCA_ROSA)])
            )
            controles.append(ft.Container(height=6))
            for m in materiales:
                controles.append(bloque_material(page, m))
                controles.append(ft.Container(height=8))

        contenedor.controls = controles
        page.update()

    def volver(e):
        page.go("/docente/contenidos")

    cargar()

    return ft.View(
        route=f"/docente/contenido-preview/{contenido_id}",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Previsualizar"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(controls=[texto_mensaje, contenedor]),
            ),
        ],
    )