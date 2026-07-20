"""
screens/login.py
Reemplaza login.php + procesar_login.php

Mismos campos y misma paleta de colores que la version PHP:
  --primary: #4BC4E7 (botones, acentos)
  --text-dark: #333333
  --text-placeholder: #AAAAAA
La diferencia es que aqui, al enviar el formulario, se llama a
api_client.login() en vez de hacer un POST directo a un .php.
"""

import flet as ft

import api_client
from session import sesion_activa

# Paleta de SIEDUCRES (identica a la definida en login.php / documento de diseno)
COLOR_PRIMARIO = "#4BC4E7"
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"


def vista_login(page: ft.Page) -> ft.View:
    ancho_disponible = page.width or 380
    ancho_tarjeta = min(380, max(280, ancho_disponible - 48))
    ancho_campo = ancho_tarjeta - 64  # descuenta el padding=32 de cada lado

    campo_correo = ft.TextField(
        label="Correo electronico",
        autofocus=True,
        border_color=COLOR_PLACEHOLDER,
        keyboard_type=ft.KeyboardType.EMAIL,
        width=ancho_campo,
    )
    campo_contrasena = ft.TextField(
        label="Contrasena",
        password=True,
        can_reveal_password=True,
        border_color=COLOR_PLACEHOLDER,
        width=ancho_campo,
    )
    texto_error = ft.Text(value="", color=COLOR_ERROR, size=14, visible=False)
    boton_login = ft.ElevatedButton(
        text="Iniciar sesion",
        width=ancho_campo,
        bgcolor=COLOR_PRIMARIO,
        color="white",
    )
    indicador_carga = ft.ProgressRing(width=20, height=20, visible=False)

    def manejar_login(e):
        # Reinicia el mensaje de error de un intento anterior
        texto_error.visible = False
        page.update()

        correo = campo_correo.value.strip() if campo_correo.value else ""
        contrasena = campo_contrasena.value or ""

        # Validacion simple antes de llamar al backend (evita una peticion
        # innecesaria si el usuario dejo campos vacios).
        if not correo or not contrasena:
            texto_error.value = "Por favor ingrese correo y contraseña."
            texto_error.visible = True
            page.update()
            return

        boton_login.disabled = True
        indicador_carga.visible = True
        page.update()

        try:
            respuesta = api_client.login(correo, contrasena)
            sesion_activa.iniciar(respuesta)
            # Reemplaza redirigirPorRol() de funciones.php:
            # cada rol tiene su propia pantalla principal.
            page.go(f"/inicio")
        except api_client.ApiError as err:
            texto_error.value = err.mensaje
            texto_error.visible = True
        finally:
            boton_login.disabled = False
            indicador_carga.visible = False
            page.update()

    boton_login.on_click = manejar_login

    # Ancho responsivo: en pantallas angostas (celulares) ocupa casi todo
    # el ancho disponible; en pantallas anchas (PC) se limita a 380px
    # para no verse estirado. Se recalcula cada vez que la ventana
    # cambia de tamano (ver page.on_resized en main.py).
    return ft.View(
        route="/login",
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
                                    width=90,
                                    height=90,
                                    fit=ft.ImageFit.CONTAIN,
                                ),
                                ft.Container(height=8),
                                ft.Text(
                                    "SIEDUCRES",
                                    size=24,
                                    weight=ft.FontWeight.W_600,
                                    color=COLOR_TEXTO,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=16),
                                texto_error,
                                campo_correo,
                                campo_contrasena,
                                ft.Row(
                                    [boton_login, indicador_carga],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.Container(height=8),
                                ft.TextButton(
                                    text="Olvidaste tu contraseña?",
                                    on_click=lambda e: page.go("/recuperar"),
                                ),
                                ft.TextButton(
                                    text="Crear una cuenta nueva",
                                    on_click=lambda e: page.go("/registro"),
                                ),
                            ]
                        ),
                    )
                ],
            )
        ],
    )