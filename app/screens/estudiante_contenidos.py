"""
screens/estudiante_contenidos.py
Reemplaza estudiante/contenidos.php (listado con progreso) y
estudiante/contenido_detalle.php (detalle + materiales).

Diseno con los colores oficiales de marca, SIN degradados, usando
solo 2 colores para mantener la pantalla armoniosa (celeste como
principal, rosado como acento), con texto oscuro para buen contraste
sobre estos tonos claros/pastel.
"""

from datetime import datetime, timedelta

import flet as ft

import api_client
from contenido_visor import bloque_recurso_principal, bloque_material

# Colores OFICIALES de marca (los 4 definidos por Paula). Se usan solo
# 2 por pantalla para que se vea armonioso, no saturado de colores.
MARCA_CIAN = "#4BC4E7"
MARCA_ROSA = "#EF5E8E"
MARCA_LIMA = "#C3D54D"
MARCA_MORADO = "#9B8AFB"

COLOR_PRIMARIO = MARCA_CIAN
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"
COLOR_EXITO = "#58BC67"

# Para las tarjetas de contenido: se alterna SOLO entre estos 2 colores
# (sin degradado), ambos con texto oscuro porque son tonos claros/pastel.
COLORES_TARJETA = [MARCA_CIAN, MARCA_ROSA]


def _es_reciente(ultima_visualizacion) -> bool:
    """Replica la logica de contenidos.php: 'Recien visto' si fue en los ultimos 5 minutos."""
    if not ultima_visualizacion:
        return False
    try:
        fecha = datetime.fromisoformat(str(ultima_visualizacion))
    except ValueError:
        return False
    return fecha > (datetime.now() - timedelta(minutes=5))


def _formatear_fecha(fecha_str) -> str:
    if not fecha_str:
        return "-"
    try:
        fecha = datetime.fromisoformat(str(fecha_str))
        return fecha.strftime("%d/%m/%Y")
    except ValueError:
        return str(fecha_str)


def vista_estudiante_contenidos(page: ft.Page) -> ft.View:
    lista_contenidos = ft.Column(spacing=14)
    texto_mensaje = ft.Text(value="", size=14, visible=False)

    def tarjeta_contenido(c: dict, indice: int) -> ft.Container:
        completado = bool(c.get("completado"))
        reciente = completado and _es_reciente(c.get("ultima_visualizacion"))

        if reciente:
            badge_texto, badge_bg, badge_fg = "\U0001F195 Recien visto", "#FFF3CD", "#856404"
        elif completado:
            badge_texto, badge_bg, badge_fg = "\u2705 Visto", "#E8F5E9", "#28A745"
        else:
            badge_texto, badge_bg, badge_fg = "\U0001F4D6 Sin ver", "#F0F0F0", "#666666"

        color_tarjeta = COLORES_TARJETA[indice % len(COLORES_TARJETA)]
        descripcion = (c.get("descripcion") or "")
        descripcion_corta = descripcion[:120] + ("..." if len(descripcion) > 120 else "")

        return ft.Container(
            border_radius=16,
            padding=20,
            bgcolor=color_tarjeta,
            on_click=lambda e, cid=c["id"]: page.go(f"/estudiante/contenido/{cid}"),
            shadow=ft.BoxShadow(blur_radius=10, color="#00000022", offset=ft.Offset(0, 4)),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text(c["titulo"], size=17, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
                    ft.Text(descripcion_corta, size=14, color=COLOR_TEXTO, opacity=0.85),
                    ft.Container(height=4),
                    ft.Text(f"\U0001F4DA Asignatura: {c.get('asignatura') or 'General'}", size=14, color=COLOR_TEXTO),
                    ft.Text(f"\U0001F468\u200D\U0001F3EB Docente: {c.get('docente_nombre') or 'No especificado'}", size=14, color=COLOR_TEXTO),
                    ft.Text(f"\U0001F4C5 Fecha: {_formatear_fecha(c.get('fecha_publicacion'))}", size=14, color=COLOR_TEXTO),
                    ft.Container(height=6),
                    ft.Container(
                        alignment=ft.alignment.center,
                        padding=ft.padding.symmetric(horizontal=14, vertical=6),
                        bgcolor=badge_bg,
                        border_radius=20,
                        content=ft.Text(badge_texto, size=14, weight=ft.FontWeight.W_600, color=badge_fg),
                    ),
                    ft.Container(height=6),
                    ft.Container(
                        bgcolor="white",
                        border_radius=8,
                        padding=ft.padding.symmetric(vertical=8),
                        alignment=ft.alignment.center,
                        content=ft.Text("Ver contenido \u2192", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
                    ),
                ],
            ),
        )

    def cargar_contenidos():
        try:
            contenidos = api_client.mis_contenidos_estudiante()
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        if not contenidos:
            lista_contenidos.controls = [
                ft.Text(
                    "Aun no se han publicado contenidos para tu grado y seccion.",
                    color=COLOR_PLACEHOLDER,
                    size=14,
                )
            ]
        else:
            lista_contenidos.controls = [tarjeta_contenido(c, i) for i, c in enumerate(contenidos)]
        page.update()

    def volver_inicio(e):
        page.go("/inicio")

    cargar_contenidos()

    return ft.View(
        route="/estudiante/contenidos",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Contenidos Educativos"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver_inicio),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(controls=[texto_mensaje, lista_contenidos]),
            ),
        ],
    )


def vista_estudiante_contenido_detalle(page: ft.Page, contenido_id: int) -> ft.View:
    """Reemplaza estudiante/contenido_detalle.php."""
    contenedor_detalle = ft.Column(spacing=8)
    texto_mensaje = ft.Text(value="", size=14, visible=False)

    def marcar_visto(e):
        try:
            api_client.actualizar_progreso(contenido_id, 100)
            texto_mensaje.value = "Marcado como visto."
            texto_mensaje.color = COLOR_EXITO
            texto_mensaje.visible = True
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        page.update()

    def cargar():
        try:
            c = api_client.obtener_contenido(contenido_id)
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        # Banner superior: UN solo color solido de marca (celeste), sin
        # degradado, con texto oscuro porque el celeste es un tono claro.
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
                                    f"\U0001F468\u200D\U0001F3EB {c.get('docente_nombre') or '-'}",
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

        controles = [banner, ft.Container(height=14), tarjeta_instrucciones, ft.Container(height=14)]

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

        controles.append(ft.Container(height=10))
        controles.append(
            ft.ElevatedButton(
                text="¡Ya lo vi!",
                bgcolor=COLOR_EXITO,
                color="white",
                height=48,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=24)),
                on_click=marcar_visto,
            )
        )

        contenedor_detalle.controls = controles
        page.update()

    def volver(e):
        page.go("/estudiante/contenidos")

    cargar()

    return ft.View(
        route=f"/estudiante/contenido/{contenido_id}",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Detalle del contenido"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(controls=[texto_mensaje, contenedor_detalle]),
            ),
        ],
    )