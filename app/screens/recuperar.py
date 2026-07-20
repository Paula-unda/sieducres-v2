"""
screens/recuperar.py
Reemplaza notificar_olvido.php

En V1.0 esto notificaba a un Administrador (no enviaba correo real).
Se mantiene exactamente la misma logica, llamando a POST /auth/recuperar.
"""

import flet as ft

import api_client

COLOR_PRIMARIO = "#4BC4E7"
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_EXITO = "#58BC67"
COLOR_ERROR = "#E05555"


def vista_recuperar(page: ft.Page) -> ft.View:
    ancho_disponible = page.width or 380
    ancho_tarjeta = min(380, max(280, ancho_disponible - 48))
    ancho_campo = ancho_tarjeta - 64

    campo_correo = ft.TextField(
        label="Correo registrado",
        border_color=COLOR_PLACEHOLDER,
        keyboard_type=ft.KeyboardType.EMAIL,
        width=ancho_campo,
    )
    texto_mensaje = ft.Text(value="", size=14, visible=False)
    boton_enviar = ft.ElevatedButton(
        text="Enviar solicitud",
        width=ancho_campo,
        bgcolor=COLOR_PRIMARIO,
        color="white",
    )

    def manejar_envio(e):
        correo = (campo_correo.value or "").strip()
        if not correo:
            texto_mensaje.value = "Ingresa tu correo registrado."
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        boton_enviar.disabled = True
        page.update()

        try:
            respuesta = api_client.recuperar_contrasena(correo)
            texto_mensaje.value = respuesta.get("mensaje", "Solicitud enviada.")
            texto_mensaje.color = COLOR_EXITO
            texto_mensaje.visible = True
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        finally:
            boton_enviar.disabled = False
            page.update()

    boton_enviar.on_click = manejar_envio

    return ft.View(
        route="/recuperar",
        bgcolor=COLOR_FONDO,
        controls=[
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
                controls=[
                    ft.Container(
                        bgcolor="white",
                        border_radius=8,
                        padding=32,
                        width=ancho_tarjeta,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Image(
                                    src="logo.png",
                                    width=70,
                                    height=70,
                                    fit=ft.ImageFit.CONTAIN,
                                ),
                                ft.Container(height=8),
                                ft.Text(
                                    "Olvidaste tu contraseña?",
                                    size=18,
                                    weight=ft.FontWeight.W_600,
                                    color=COLOR_TEXTO,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=8),
                                ft.Text(
                                    "Ingresa tu correo. El administrador sera notificado "
                                    "para ayudarte a restablecer tu contraseña.",
                                    size=13,
                                    color=COLOR_PLACEHOLDER,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=16),
                                texto_mensaje,
                                campo_correo,
                                boton_enviar,
                                ft.TextButton(
                                    text="Volver al inicio de sesión",
                                    on_click=lambda e: page.go("/login"),
                                ),
                            ]
                        ),
                    )
                ],
            )
        ],
    )