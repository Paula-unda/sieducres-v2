"""
screens/docente_contenido_editar.py
Reemplaza docente/editar_contenido.php.
Ademas de editar los datos principales, permite ver los materiales
adicionales ya guardados, corregir su titulo/URL, quitarlos, o agregar
nuevos (los cambios de materiales se aplican de inmediato al servidor,
ya que el contenido ya existe).
"""

import flet as ft

import api_client

COLOR_PRIMARIO = "#4BC4E7"
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"
COLOR_EXITO = "#58BC67"

TIPOS_MATERIAL = ["video", "audio", "documento", "enlace"]


def vista_docente_contenido_editar(page: ft.Page, contenido_id: int) -> ft.View:
    campo_titulo = ft.TextField(label="Titulo")
    campo_descripcion = ft.TextField(label="Descripcion", multiline=True, min_lines=3, max_lines=6)
    campo_asignatura = ft.TextField(label="Asignatura")
    campo_enlace = ft.TextField(label="Enlace (opcional)")
    texto_mensaje = ft.Text(value="", size=14, visible=False)
    indicador_carga = ft.ProgressRing(width=20, height=20, visible=False)
    boton_guardar = ft.ElevatedButton(text="Guardar cambios", bgcolor=COLOR_PRIMARIO, color="white")
    cargando = ft.ProgressRing(width=24, height=24)
    columna_formulario = ft.Column(visible=False, controls=[])

    # ---- Materiales existentes ----
    lista_materiales = ft.Column(spacing=8)
    texto_mensaje_material = ft.Text(value="", size=13, visible=False)

    dialogo_confirmar = ft.AlertDialog(modal=True, title=ft.Text(""), content=ft.Text(""), actions=[])
    page.overlay.append(dialogo_confirmar)

    def cerrar_dialogo():
        dialogo_confirmar.open = False
        page.update()

    def confirmar_quitar_material(material_id: int, titulo: str):
        def si_quitar(e):
            try:
                api_client.eliminar_material(material_id)
                cerrar_dialogo()
                cargar_materiales()
            except api_client.ApiError as err:
                cerrar_dialogo()
                texto_mensaje_material.value = err.mensaje
                texto_mensaje_material.color = COLOR_ERROR
                texto_mensaje_material.visible = True
                page.update()

        dialogo_confirmar.title = ft.Text("¿Quitar este material?")
        dialogo_confirmar.content = ft.Text(f'"{titulo}" se quitara de este contenido.')
        dialogo_confirmar.actions = [
            ft.TextButton(text="Cancelar", on_click=lambda e: cerrar_dialogo()),
            ft.TextButton(text="Si, quitar", style=ft.ButtonStyle(color=COLOR_ERROR), on_click=si_quitar),
        ]
        dialogo_confirmar.open = True
        page.update()

    def fila_material(m: dict) -> ft.Control:
        campo_titulo_edit = ft.TextField(value=m["titulo"], label="Titulo", dense=True)
        campo_url_edit = ft.TextField(value=m.get("url") or "", label="URL", dense=True, visible=bool(m.get("url")))

        def guardar_material(e):
            campos = {"titulo": campo_titulo_edit.value}
            if m.get("url"):
                campos["url"] = campo_url_edit.value
            try:
                api_client.editar_material(m["id"], campos)
                texto_mensaje_material.value = "Material actualizado."
                texto_mensaje_material.color = COLOR_EXITO
                texto_mensaje_material.visible = True
            except api_client.ApiError as err:
                texto_mensaje_material.value = err.mensaje
                texto_mensaje_material.color = COLOR_ERROR
                texto_mensaje_material.visible = True
            page.update()

        controles_fila = [
            ft.Row(
                controls=[
                    ft.Text(f"({m['tipo']})", size=12, color=COLOR_PLACEHOLDER),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_size=16,
                        tooltip="Quitar material",
                        icon_color=COLOR_ERROR,
                        on_click=lambda e, mid=m["id"], t=m["titulo"]: confirmar_quitar_material(mid, t),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            campo_titulo_edit,
        ]
        if m.get("url"):
            controles_fila.append(campo_url_edit)
        if m.get("archivo"):
            controles_fila.append(
                ft.Text(f"\U0001F4CE Archivo: {m['archivo']} (para cambiarlo, quita este y agrega uno nuevo)", size=11, color=COLOR_PLACEHOLDER)
            )
        controles_fila.append(
            ft.Row([ft.OutlinedButton(text="Guardar cambios de este material", on_click=guardar_material)])
        )

        return ft.Container(
            bgcolor="white",
            border_radius=8,
            padding=12,
            content=ft.Column(spacing=6, controls=controles_fila),
        )

    def cargar_materiales():
        try:
            materiales = api_client.listar_materiales(contenido_id)
        except api_client.ApiError as err:
            texto_mensaje_material.value = err.mensaje
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
            page.update()
            return

        if not materiales:
            lista_materiales.controls = [
                ft.Text("Este contenido no tiene materiales adicionales.", size=13, color=COLOR_PLACEHOLDER)
            ]
        else:
            lista_materiales.controls = [fila_material(m) for m in materiales]
        page.update()

    # ---- Agregar material nuevo (se sube de inmediato, el contenido ya existe) ----
    campo_tipo_nuevo = ft.Dropdown(
        label="Tipo de material",
        options=[ft.dropdown.Option(t) for t in TIPOS_MATERIAL],
        border_radius=0,
        border=ft.InputBorder.OUTLINE,
        color="#000000",
        alignment=ft.alignment.center_left,
    )
    campo_titulo_nuevo = ft.TextField(label="Titulo del material nuevo")
    campo_url_nuevo = ft.TextField(label="URL (para video, audio o enlace)", visible=False)
    texto_archivo_nuevo = ft.Text("Ningun archivo seleccionado", size=12, color=COLOR_PLACEHOLDER, visible=False)
    archivo_nuevo_elegido = {"path": None}

    def manejar_archivo_nuevo(e: ft.FilePickerResultEvent):
        if e.files:
            archivo_nuevo_elegido["path"] = e.files[0].path
            texto_archivo_nuevo.value = f"\U0001F4CE {e.files[0].name}"
            texto_archivo_nuevo.color = COLOR_TEXTO
        page.update()

    selector_archivo_nuevo = ft.FilePicker(on_result=manejar_archivo_nuevo)
    page.overlay.append(selector_archivo_nuevo)

    boton_adjuntar_nuevo = ft.OutlinedButton(
        text="Elegir archivo",
        icon=ft.icons.ATTACH_FILE,
        visible=False,
        on_click=lambda e: selector_archivo_nuevo.pick_files(allow_multiple=False),
    )

    def cambiar_tipo_nuevo(e):
        tipo = campo_tipo_nuevo.value
        mostrar_url = tipo in ("enlace", "video", "audio")
        mostrar_archivo = tipo in ("documento", "video", "audio")
        campo_url_nuevo.visible = mostrar_url
        texto_archivo_nuevo.visible = mostrar_archivo
        boton_adjuntar_nuevo.visible = mostrar_archivo
        page.update()

    campo_tipo_nuevo.on_change = cambiar_tipo_nuevo

    def agregar_material_nuevo(e):
        titulo_mat = (campo_titulo_nuevo.value or "").strip()
        tipo_mat = campo_tipo_nuevo.value
        url_mat = (campo_url_nuevo.value or "").strip() or None
        archivo_mat = archivo_nuevo_elegido["path"]

        if not titulo_mat or not tipo_mat:
            texto_mensaje_material.value = "Indica el tipo y el titulo del material."
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
            page.update()
            return

        try:
            api_client.agregar_material(contenido_id, titulo_mat, tipo_mat, url_mat, archivo_mat, 0)
            campo_titulo_nuevo.value = ""
            campo_url_nuevo.value = ""
            campo_tipo_nuevo.value = None
            archivo_nuevo_elegido["path"] = None
            texto_archivo_nuevo.value = "Ningun archivo seleccionado"
            texto_archivo_nuevo.color = COLOR_PLACEHOLDER
            campo_url_nuevo.visible = False
            texto_archivo_nuevo.visible = False
            boton_adjuntar_nuevo.visible = False
            texto_mensaje_material.value = "Material agregado."
            texto_mensaje_material.color = COLOR_EXITO
            texto_mensaje_material.visible = True
            cargar_materiales()
        except api_client.ApiError as err:
            texto_mensaje_material.value = err.mensaje
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
        page.update()

    def cargar_datos_actuales():
        try:
            c = api_client.obtener_contenido(contenido_id)
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            cargando.visible = False
            page.update()
            return

        campo_titulo.value = c.get("titulo", "")
        campo_descripcion.value = c.get("descripcion", "")
        campo_asignatura.value = c.get("asignatura", "")
        campo_enlace.value = c.get("enlace") or ""
        cargando.visible = False
        columna_formulario.visible = True
        page.update()
        cargar_materiales()

    def guardar(e):
        titulo = (campo_titulo.value or "").strip()
        descripcion = (campo_descripcion.value or "").strip()
        asignatura = (campo_asignatura.value or "").strip()
        enlace = (campo_enlace.value or "").strip() or None

        if not titulo or not descripcion or not asignatura:
            texto_mensaje.value = "Completa titulo, descripcion y asignatura."
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        boton_guardar.disabled = True
        indicador_carga.visible = True
        page.update()
        try:
            api_client.editar_contenido(
                contenido_id,
                {"titulo": titulo, "descripcion": descripcion, "asignatura": asignatura, "enlace": enlace},
            )
            page.go("/docente/contenidos")
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        finally:
            boton_guardar.disabled = False
            indicador_carga.visible = False
            page.update()

    boton_guardar.on_click = guardar

    columna_formulario.controls = [
        campo_titulo,
        campo_descripcion,
        campo_asignatura,
        campo_enlace,
        ft.Divider(),
        ft.Text("Materiales adicionales de este contenido", size=16, weight=ft.FontWeight.W_600),
        texto_mensaje_material,
        lista_materiales,
        ft.Container(height=10),
        ft.Text("Agregar un material nuevo:", size=14, weight=ft.FontWeight.W_600),
        campo_tipo_nuevo,
        campo_titulo_nuevo,
        campo_url_nuevo,
        boton_adjuntar_nuevo,
        texto_archivo_nuevo,
        ft.OutlinedButton(text="+ Agregar material", on_click=agregar_material_nuevo),
        ft.Divider(),
        ft.Text(
            "Nota: los materiales se guardan de inmediato al agregarlos/editarlos. "
            "Este boton solo guarda los cambios de titulo, descripcion, asignatura y enlace.",
            size=11,
            color=COLOR_PLACEHOLDER,
        ),
        ft.Row([boton_guardar, indicador_carga]),
    ]

    def volver(e):
        page.go("/docente/contenidos")

    cargar_datos_actuales()

    return ft.View(
        route=f"/docente/contenido-editar/{contenido_id}",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Editar contenido"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(controls=[texto_mensaje, cargando, columna_formulario]),
            ),
        ],
    )