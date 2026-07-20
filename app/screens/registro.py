"""
screens/registro.py
Pantalla nueva en V2.0 (no existia en V1.0, ya que el autorregistro
es una funcionalidad nueva definida en el Documento Vision, C01).

Llama a api_client.registro(), que a su vez llama a POST /auth/registro.
"""

import flet as ft

import api_client

COLOR_PRIMARIO = "#4BC4E7"
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"
COLOR_EXITO = "#58BC67"

# Roles que pueden autorregistrarse (el Administrador queda excluido
# a proposito, igual que en backend/auth.py -> ROLES_AUTORREGISTRO)
ROLES_DISPONIBLES = ["Docente", "Estudiante", "Representante"]

GRADOS_DISPONIBLES = ["1ro", "2do", "3ro", "4to", "5to"]
SECCIONES_DISPONIBLES = ["A", "B", "C", "D", "E", "F", "U"]  # U = Unica


def _opcion_escuela(esc: dict, ancho_campo: int) -> ft.dropdown.Option:
    """
    Crea una opcion de escuela para el Dropdown. En vez de recortar el
    nombre con '...', el texto se envuelve a una segunda linea DENTRO
    del mismo campo si no cabe en una sola (sin perder ninguna palabra
    ni informacion). El Dropdown crece de alto solo cuando hace falta.
    """
    return ft.dropdown.Option(
        key=str(esc["id"]),
        content=ft.Container(
            width=ancho_campo - 64,
            alignment=ft.alignment.center_left,
            content=ft.Text(esc["nombre"], size=14, color="#000000", text_align=ft.TextAlign.LEFT),
        ),
    )


def vista_registro(page: ft.Page) -> ft.View:
    ancho_disponible = page.width or 380
    ancho_tarjeta = min(380, max(280, ancho_disponible - 48))
    ancho_campo = ancho_tarjeta - 64

    campo_nombre = ft.TextField(label="Nombre completo", border_color=COLOR_PLACEHOLDER, width=ancho_campo)
    campo_correo = ft.TextField(
        label="Correo electronico",
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
    selector_rol = ft.Dropdown(
        label="Tu rol en el NER 319",
        options=[ft.dropdown.Option(rol) for rol in ROLES_DISPONIBLES],
        border_color=COLOR_PLACEHOLDER,
        width=ancho_campo,
        border=ft.InputBorder.OUTLINE,
        border_radius=0,
        color="#000000",
        alignment=ft.alignment.center_left,
    )
    campo_grado = ft.Dropdown(
        label="Grado",
        options=[ft.dropdown.Option(g) for g in GRADOS_DISPONIBLES],
        border_color=COLOR_PLACEHOLDER,
        width=ancho_campo,
        visible=False,  # solo se muestra para Docente/Estudiante (ver manejar_cambio_rol)
        border=ft.InputBorder.OUTLINE,
        border_radius=0,
        color="#000000",
        alignment=ft.alignment.center_left,
    )
    campo_seccion = ft.Dropdown(
        label="Seccion (U = Unica)",
        options=[ft.dropdown.Option(s) for s in SECCIONES_DISPONIBLES],
        border_color=COLOR_PLACEHOLDER,
        width=ancho_campo,
        visible=False,
        border=ft.InputBorder.OUTLINE,
        border_radius=0,
        color="#000000",
        alignment=ft.alignment.center_left,
    )
    selector_escuela = ft.Dropdown(
        label="Tu escuela",
        options=[],  # se llena en cuanto la pantalla carga (ver cargar_escuelas)
        border_color=COLOR_PLACEHOLDER,
        width=ancho_campo,
        border=ft.InputBorder.OUTLINE,
        border_radius=0,
        color="#000000",
        alignment=ft.alignment.center_left,
    )

    # ---- Campos exclusivos del rol Representante ----
    # El estudiante debe existir previamente. Como los hijos de un mismo
    # representante pueden estar en escuelas distintas del NER 319, primero
    # se elige la escuela del nino/a y luego se elige de la lista de
    # estudiantes de esa escuela (no se escribe nombre ni correo a mano).
    estudiantes_seleccionados = []  # lista de dicts: {id, nombre, grado, seccion, ...}

    selector_escuela_hijo = ft.Dropdown(
        label="Escuela del estudiante",
        options=[],  # se llena con las mismas 12 escuelas (ver cargar_escuelas)
        border_color=COLOR_PLACEHOLDER,
        width=ancho_campo,
        visible=False,
        border=ft.InputBorder.OUTLINE,
        border_radius=0,
        color="#000000",
        alignment=ft.alignment.center_left,
    )
    lista_estudiantes_escuela = ft.Column(controls=[], visible=False)
    lista_seleccionados = ft.Column(controls=[])

    def actualizar_lista_seleccionados():
        lista_seleccionados.controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        f"\u2713 {est['nombre']} ({est.get('grado') or '-'} {est.get('seccion') or ''})",
                        size=13,
                        color=COLOR_EXITO,
                    ),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_size=16,
                        tooltip="Quitar",
                        on_click=lambda e, eid=est["id"]: quitar_estudiante(eid),
                    ),
                ],
            )
            for est in estudiantes_seleccionados
        ]

    def quitar_estudiante(estudiante_id):
        estudiantes_seleccionados[:] = [e for e in estudiantes_seleccionados if e["id"] != estudiante_id]
        actualizar_lista_seleccionados()
        page.update()

    def seleccionar_estudiante(est):
        if any(e["id"] == est["id"] for e in estudiantes_seleccionados):
            return  # ya esta agregado
        estudiantes_seleccionados.append(est)
        actualizar_lista_seleccionados()
        page.update()

    def cambiar_escuela_hijo(e):
        """Al elegir la escuela del nino/a, carga la lista de estudiantes de esa escuela."""
        if not selector_escuela_hijo.value:
            lista_estudiantes_escuela.controls = []
            lista_estudiantes_escuela.visible = False
            page.update()
            return

        try:
            estudiantes = api_client.listar_estudiantes_por_escuela(int(selector_escuela_hijo.value))
        except api_client.ApiError as err:
            lista_estudiantes_escuela.controls = [ft.Text(err.mensaje, size=13, color=COLOR_ERROR)]
            lista_estudiantes_escuela.visible = True
            page.update()
            return

        if not estudiantes:
            lista_estudiantes_escuela.controls = [
                ft.Text("No hay estudiantes registrados en esa escuela todavia.", size=13, color=COLOR_PLACEHOLDER)
            ]
        else:
            lista_estudiantes_escuela.controls = [
                ft.TextButton(
                    text=(
                        f"{est['nombre']} — {est.get('grado') or 'sin grado'} {est.get('seccion') or ''} "
                        f"({est['correo_enmascarado']})"
                    ),
                    on_click=lambda e, est=est: seleccionar_estudiante(est),
                )
                for est in estudiantes
            ]
        lista_estudiantes_escuela.visible = True
        page.update()

    selector_escuela_hijo.on_change = cambiar_escuela_hijo

    contenedor_estudiantes = ft.Column(
        visible=False,
        controls=[
            selector_escuela_hijo,
            lista_estudiantes_escuela,
            lista_seleccionados,
        ],
    )

    texto_mensaje = ft.Text(value="", size=14, visible=False)
    boton_registro = ft.ElevatedButton(
        text="Crear cuenta",
        width=ancho_campo,
        bgcolor=COLOR_PRIMARIO,
        color="white",
    )
    indicador_carga = ft.ProgressRing(width=20, height=20, visible=False)

    def cargar_escuelas():
        """Trae las 12 escuelas del NER 319 desde el backend para los selectores."""
        try:
            escuelas = api_client.obtener_escuelas()
            if not escuelas:
                texto_mensaje.value = (
                    "No se encontraron escuelas registradas. "
                    "Puedes continuar el registro sin seleccionar una."
                )
                texto_mensaje.color = COLOR_ERROR
                texto_mensaje.visible = True
            opciones_escuela = [_opcion_escuela(esc, ancho_campo) for esc in escuelas]
            selector_escuela.options = opciones_escuela
            selector_escuela_hijo.options = opciones_escuela
        except api_client.ApiError as err:
            # Antes esto fallaba en silencio. Ahora se muestra el motivo
            # real para poder diagnosticarlo, por ejemplo si el backend
            # de esta PC no tiene el endpoint /auth/escuelas.
            texto_mensaje.value = f"No se pudo cargar la lista de escuelas: {err.mensaje}"
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        page.update()

    def manejar_cambio_rol(e):
        mostrar_academico = selector_rol.value in ("Docente", "Estudiante")
        campo_grado.visible = mostrar_academico
        campo_seccion.visible = mostrar_academico

        mostrar_representante = selector_rol.value == "Representante"
        selector_escuela_hijo.visible = mostrar_representante
        contenedor_estudiantes.visible = mostrar_representante

        if not mostrar_representante:
            # Si el usuario cambia de rol despues de haber seleccionado
            # estudiantes, se limpia todo para que no quede nada "pegado"
            # por si mas adelante vuelve a elegir Representante.
            estudiantes_seleccionados.clear()
            actualizar_lista_seleccionados()
            selector_escuela_hijo.value = None
            lista_estudiantes_escuela.controls = []
            lista_estudiantes_escuela.visible = False

        # El Representante no tiene una escuela propia fija: sus hijos
        # pueden estar en instituciones distintas del NER 319, asi que
        # ese campo no le aplica (se usa selector_escuela_hijo en su lugar).
        selector_escuela.visible = not mostrar_representante
        if mostrar_representante:
            selector_escuela.value = None

        page.update()

    selector_rol.on_change = manejar_cambio_rol

    def manejar_registro(e):
        texto_mensaje.visible = False
        page.update()

        nombre = (campo_nombre.value or "").strip()
        correo = (campo_correo.value or "").strip()
        contrasena = campo_contrasena.value or ""
        rol = selector_rol.value
        escuela_id = int(selector_escuela.value) if selector_escuela.value else None
        grado = campo_grado.value or None
        seccion = campo_seccion.value or None

        if not nombre or not correo or not contrasena or not rol:
            texto_mensaje.value = "Completa todos los campos obligatorios."
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        if rol in ("Docente", "Estudiante") and not (grado and seccion):
            texto_mensaje.value = "Como Docente o Estudiante, debes indicar tu grado y seccion."
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        estudiantes_ids = None
        if rol == "Representante":
            estudiantes_ids = [est["id"] for est in estudiantes_seleccionados]
            if not estudiantes_ids:
                texto_mensaje.value = "Busca y selecciona al menos un estudiante para vincularte."
                texto_mensaje.color = COLOR_ERROR
                texto_mensaje.visible = True
                page.update()
                return

        if len(contrasena) < 8 or not any(c.isalpha() for c in contrasena) or not any(c.isdigit() for c in contrasena):
            texto_mensaje.value = "La contrasena debe tener al menos 8 caracteres, con letras y numeros."
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        boton_registro.disabled = True
        indicador_carga.visible = True
        page.update()

        try:
            api_client.registro(nombre, correo, contrasena, rol, escuela_id, grado, seccion, estudiantes_ids)
            texto_mensaje.value = "Cuenta creada exitosamente. Ya puedes iniciar sesion."
            texto_mensaje.color = COLOR_EXITO
            texto_mensaje.visible = True
            page.update()
            # Pequena pausa visual antes de mandar al login (opcional):
            page.go("/login")
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        finally:
            boton_registro.disabled = False
            indicador_carga.visible = False
            page.update()

    boton_registro.on_click = manejar_registro

    vista = ft.View(
        route="/registro",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(height=40),
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
                                    "Crear cuenta en SIEDUCRES",
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                    color=COLOR_TEXTO,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=12),
                                texto_mensaje,
                                campo_nombre,
                                campo_correo,
                                campo_contrasena,
                                selector_rol,
                                campo_grado,
                                campo_seccion,
                                contenedor_estudiantes,
                                selector_escuela,
                                ft.Row(
                                    [boton_registro, indicador_carga],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.TextButton(
                                    text="Ya tengo cuenta, iniciar sesion",
                                    on_click=lambda e: page.go("/login"),
                                ),
                            ]
                        ),
                    ),
                ],
            )
        ],
    )

    cargar_escuelas()
    return vista