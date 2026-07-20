"""
screens/docente_contenidos.py
Reemplaza docente/gestion_contenidos.php (listado + creacion + materiales
adicionales) y docente/eliminar_contenido.php.
"""

import os

import flet as ft

import api_client

COLOR_PRIMARIO = "#4BC4E7"
COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_FONDO = "#F5F5F5"
COLOR_ERROR = "#E05555"
COLOR_EXITO = "#58BC67"

TIPOS_MATERIAL = ["video", "audio", "documento", "enlace"]


def vista_docente_contenidos(page: ft.Page) -> ft.View:
    lista_contenidos = ft.Column(spacing=10)
    texto_mensaje = ft.Text(value="", size=14, visible=False)

    dialogo_confirmar = ft.AlertDialog(modal=True, title=ft.Text(""), content=ft.Text(""), actions=[])
    page.overlay.append(dialogo_confirmar)

    def cerrar_dialogo():
        dialogo_confirmar.open = False
        page.update()

    def confirmar_eliminar(contenido_id: int, titulo: str):
        def si_eliminar(e):
            try:
                api_client.eliminar_contenido(contenido_id)
                cerrar_dialogo()
                cargar_contenidos()
            except api_client.ApiError as err:
                cerrar_dialogo()
                texto_mensaje.value = err.mensaje
                texto_mensaje.color = COLOR_ERROR
                texto_mensaje.visible = True
                page.update()

        dialogo_confirmar.title = ft.Text("¿Eliminar contenido?")
        dialogo_confirmar.content = ft.Text(
            f'¿Seguro que deseas eliminar "{titulo}"? Esta accion no se puede deshacer.'
        )
        dialogo_confirmar.actions = [
            ft.TextButton(text="Cancelar", on_click=lambda e: cerrar_dialogo()),
            ft.TextButton(text="Si, eliminar", style=ft.ButtonStyle(color=COLOR_ERROR), on_click=si_eliminar),
        ]
        dialogo_confirmar.open = True
        page.update()

    def tarjeta_contenido(c: dict) -> ft.Container:
        vistos = c.get("estudiantes_vieron", 0) or 0
        total = c.get("total_estudiantes_clase", 0) or 0
        porcentaje = (vistos / total) if total > 0 else 0

        return ft.Container(
            bgcolor="white",
            border_radius=8,
            padding=14,
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(c["titulo"], size=16, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
                    ft.Text(f"Asignatura: {c.get('asignatura') or '-'}", size=13, color=COLOR_PLACEHOLDER),
                    ft.Text(
                        f"Grado/Seccion: {c.get('grado') or '-'} {c.get('seccion') or ''}",
                        size=13,
                        color=COLOR_PLACEHOLDER,
                    ),
                    ft.Text(f"Vistos: {vistos} / {total} estudiantes ({round(porcentaje * 100)}%)", size=13, color=COLOR_EXITO),
                    ft.ProgressBar(value=porcentaje, color=COLOR_EXITO, bgcolor="#E0E0E0", height=6),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.IconButton(
                                icon=ft.icons.VISIBILITY_OUTLINED,
                                tooltip="Previsualizar",
                                icon_color=COLOR_PRIMARIO,
                                on_click=lambda e, cid=c["id"]: page.go(f"/docente/contenido-preview/{cid}"),
                            ),
                            ft.IconButton(
                                icon=ft.icons.BAR_CHART_OUTLINED,
                                tooltip="Estadisticas",
                                icon_color=COLOR_PRIMARIO,
                                on_click=lambda e, cid=c["id"]: page.go(f"/docente/contenido-estadisticas/{cid}"),
                            ),
                            ft.IconButton(
                                icon=ft.icons.EDIT_OUTLINED,
                                tooltip="Editar",
                                icon_color=COLOR_PRIMARIO,
                                on_click=lambda e, cid=c["id"]: page.go(f"/docente/contenido-editar/{cid}"),
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                tooltip="Eliminar",
                                icon_color=COLOR_ERROR,
                                on_click=lambda e, cid=c["id"], t=c["titulo"]: confirmar_eliminar(cid, t),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def cargar_contenidos():
        try:
            contenidos = api_client.mis_contenidos_docente()
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        if not contenidos:
            lista_contenidos.controls = [
                ft.Text("Aun no has publicado ningun contenido.", color=COLOR_PLACEHOLDER, size=14)
            ]
        else:
            lista_contenidos.controls = [tarjeta_contenido(c) for c in contenidos]
        page.update()

    def ir_a_nuevo(e):
        page.go("/docente/contenido-nuevo")

    def descargar_reporte(e):
        boton_reporte.disabled = True
        indicador_reporte.visible = True
        page.update()
        try:
            ruta_pdf = api_client.descargar_reporte_pdf()
            try:
                os.startfile(ruta_pdf)
            except AttributeError:
                page.launch_url(f"file:///{ruta_pdf}")
            texto_mensaje.value = f"Reporte descargado en: {ruta_pdf}"
            texto_mensaje.color = COLOR_EXITO
            texto_mensaje.visible = True
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        finally:
            boton_reporte.disabled = False
            indicador_reporte.visible = False
            page.update()

    boton_reporte = ft.OutlinedButton(
        text="\U0001F4C4 Descargar reporte general (PDF)",
        on_click=descargar_reporte,
    )
    indicador_reporte = ft.ProgressRing(width=18, height=18, visible=False)

    def volver_inicio(e):
        page.go("/inicio")

    cargar_contenidos()

    return ft.View(
        route="/docente/contenidos",
        bgcolor=COLOR_FONDO,
        controls=[
            ft.AppBar(
                title=ft.Text("Mis contenidos"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver_inicio),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        texto_mensaje,
                        ft.ElevatedButton(
                            text="+ Publicar contenido nuevo",
                            bgcolor=COLOR_PRIMARIO,
                            color="white",
                            on_click=ir_a_nuevo,
                        ),
                        ft.Row([boton_reporte, indicador_reporte]),
                        ft.Container(height=10),
                        lista_contenidos,
                    ]
                ),
            ),
        ],
    )


def vista_docente_contenido_nuevo(page: ft.Page) -> ft.View:
    materiales_pendientes = []

    campo_titulo = ft.TextField(label="Titulo")
    campo_descripcion = ft.TextField(label="Descripcion", multiline=True, min_lines=3, max_lines=6)
    campo_asignatura = ft.TextField(label="Asignatura")
    campo_enlace = ft.TextField(label="Enlace / video principal (opcional)")
    texto_mensaje = ft.Text(value="", size=14, visible=False)
    indicador_carga = ft.ProgressRing(width=20, height=20, visible=False)
    boton_publicar = ft.ElevatedButton(text="Publicar", bgcolor=COLOR_PRIMARIO, color="white")

    archivo_elegido = {"path": None}
    texto_archivo = ft.Text("Ningun archivo seleccionado", size=12, color=COLOR_PLACEHOLDER)

    def manejar_archivo_elegido(e: ft.FilePickerResultEvent):
        if e.files:
            archivo_elegido["path"] = e.files[0].path
            texto_archivo.value = f"\U0001F4CE {e.files[0].name}"
            texto_archivo.color = COLOR_TEXTO
        else:
            archivo_elegido["path"] = None
            texto_archivo.value = "Ningun archivo seleccionado"
            texto_archivo.color = COLOR_PLACEHOLDER
        page.update()

    selector_archivo = ft.FilePicker(on_result=manejar_archivo_elegido)
    page.overlay.append(selector_archivo)

    boton_adjuntar = ft.OutlinedButton(
        text="Documento principal (opcional)",
        icon=ft.icons.ATTACH_FILE,
        on_click=lambda e: selector_archivo.pick_files(
            allow_multiple=False,
            allowed_extensions=["pdf", "doc", "docx", "ppt", "pptx", "jpg", "jpeg", "png", "mp4", "mp3"],
        ),
    )

    lista_materiales_visual = ft.Column(spacing=6)

    campo_tipo_material = ft.Dropdown(
        label="Tipo de material",
        options=[ft.dropdown.Option(t) for t in TIPOS_MATERIAL],
        border_radius=0,
        border=ft.InputBorder.OUTLINE,
        color="#000000",
        alignment=ft.alignment.center_left,
    )
    campo_titulo_material = ft.TextField(label="Titulo del material")
    campo_url_material = ft.TextField(label="URL (para video, audio o enlace)", visible=False)
    texto_archivo_material = ft.Text("Ningun archivo seleccionado", size=12, color=COLOR_PLACEHOLDER, visible=False)
    archivo_material_elegido = {"path": None, "nombre": None}

    def manejar_archivo_material(e: ft.FilePickerResultEvent):
        if e.files:
            archivo_material_elegido["path"] = e.files[0].path
            archivo_material_elegido["nombre"] = e.files[0].name
            texto_archivo_material.value = f"\U0001F4CE {e.files[0].name}"
            texto_archivo_material.color = COLOR_TEXTO
        page.update()

    selector_archivo_material = ft.FilePicker(on_result=manejar_archivo_material)
    page.overlay.append(selector_archivo_material)

    boton_adjuntar_material = ft.OutlinedButton(
        text="Elegir archivo",
        icon=ft.icons.ATTACH_FILE,
        visible=False,
        on_click=lambda e: selector_archivo_material.pick_files(allow_multiple=False),
    )

    def cambiar_tipo_material(e):
        tipo = campo_tipo_material.value
        mostrar_url = tipo in ("enlace", "video", "audio")
        mostrar_archivo = tipo in ("documento", "video", "audio")

        campo_url_material.visible = mostrar_url
        texto_archivo_material.visible = mostrar_archivo
        boton_adjuntar_material.visible = mostrar_archivo
        page.update()

    campo_tipo_material.on_change = cambiar_tipo_material

    texto_mensaje_material = ft.Text(value="", size=13, visible=False)

    def redibujar_lista_materiales():
        filas = []
        for indice, mat in enumerate(materiales_pendientes):

            def hacer_actualizador_titulo(i):
                def actualizar(e):
                    materiales_pendientes[i]["titulo"] = e.control.value
                return actualizar

            def hacer_actualizador_url(i):
                def actualizar(e):
                    materiales_pendientes[i]["url"] = e.control.value or None
                return actualizar

            campo_titulo_editable = ft.TextField(
                value=mat["titulo"],
                dense=True,
                label="Titulo",
                on_change=hacer_actualizador_titulo(indice),
            )

            controles_material = [
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"{mat['tipo'].capitalize()}", size=12, color=COLOR_PLACEHOLDER),
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_size=16,
                            tooltip="Quitar este material",
                            icon_color=COLOR_ERROR,
                            on_click=lambda e, i=indice: quitar_material(i),
                        ),
                    ],
                ),
                campo_titulo_editable,
            ]

            if mat.get("url") is not None:
                controles_material.append(
                    ft.TextField(
                        value=mat["url"],
                        dense=True,
                        label="URL",
                        on_change=hacer_actualizador_url(indice),
                    )
                )
            elif mat.get("archivo_path"):
                nombre_archivo = mat["archivo_path"].split("\\")[-1].split("/")[-1]
                controles_material.append(
                    ft.Text(f"\U0001F4CE {nombre_archivo}", size=12, color=COLOR_PLACEHOLDER)
                )

            filas.append(
                ft.Container(
                    bgcolor="white",
                    border_radius=8,
                    padding=10,
                    content=ft.Column(spacing=4, controls=controles_material),
                )
            )
        lista_materiales_visual.controls = filas
        page.update()

    def quitar_material(indice: int):
        materiales_pendientes.pop(indice)
        redibujar_lista_materiales()

    def agregar_material_click(e):
        titulo_mat = (campo_titulo_material.value or "").strip()
        tipo_mat = campo_tipo_material.value
        url_mat = (campo_url_material.value or "").strip() or None
        archivo_mat = archivo_material_elegido["path"]

        if not titulo_mat or not tipo_mat:
            texto_mensaje_material.value = "Indica el tipo y el titulo del material."
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
            page.update()
            return
        if tipo_mat == "documento" and not archivo_mat:
            texto_mensaje_material.value = "Para tipo documento, elige un archivo."
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
            page.update()
            return
        if tipo_mat == "enlace" and not url_mat:
            texto_mensaje_material.value = "Para tipo enlace, escribe la URL."
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
            page.update()
            return
        if tipo_mat in ("video", "audio") and not (url_mat or archivo_mat):
            texto_mensaje_material.value = "Para video o audio, elige un archivo o escribe una URL."
            texto_mensaje_material.color = COLOR_ERROR
            texto_mensaje_material.visible = True
            page.update()
            return

        materiales_pendientes.append(
            {"titulo": titulo_mat, "tipo": tipo_mat, "url": url_mat, "archivo_path": archivo_mat}
        )
        redibujar_lista_materiales()

        campo_titulo_material.value = ""
        campo_url_material.value = ""
        campo_tipo_material.value = None
        archivo_material_elegido["path"] = None
        texto_archivo_material.value = "Ningun archivo seleccionado"
        texto_archivo_material.color = COLOR_PLACEHOLDER
        campo_url_material.visible = False
        texto_archivo_material.visible = False
        boton_adjuntar_material.visible = False
        texto_mensaje_material.visible = False
        page.update()

    def publicar(e):
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

        # Aviso de seguridad: si el docente lleno los campos de un material
        # (titulo, tipo, url o archivo) pero se le olvido tocar el boton
        # "+ Agregar material", ese material se perderia en silencio al
        # publicar. Se detiene aqui y se le avisa, en vez de continuar.
        hay_material_sin_agregar = bool(
            (campo_titulo_material.value or "").strip()
            or campo_tipo_material.value
            or (campo_url_material.value or "").strip()
            or archivo_material_elegido["path"]
        )
        if hay_material_sin_agregar:
            texto_mensaje.value = (
                "Tienes un material sin agregar a la lista (revisa la seccion "
                "'Materiales adicionales'). Toca '+ Agregar material' para incluirlo, "
                "o borra esos campos si no lo quieres, antes de publicar."
            )
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
            page.update()
            return

        boton_publicar.disabled = True
        indicador_carga.visible = True
        page.update()
        try:
            resultado = api_client.crear_contenido(titulo, descripcion, asignatura, enlace, archivo_elegido["path"])
            contenido_id = resultado["contenido"]["id"]

            # 2) Se suben, uno por uno, los materiales que quedaron en la lista.
            #    IMPORTANTE: se atrapa CUALQUIER excepcion (no solo ApiError),
            #    para que si UN material falla (ej: timeout subiendo un video
            #    grande), el ciclo continue intentando con los siguientes en
            #    vez de detenerse ahi. Antes esto causaba que, si el material
            #    2 de 3 fallaba con un error no controlado, el material 3
            #    nunca se llegaba a intentar.
            materiales_fallidos = []
            for indice, mat in enumerate(materiales_pendientes):
                try:
                    api_client.agregar_material(
                        contenido_id, mat["titulo"], mat["tipo"], mat["url"], mat["archivo_path"], indice
                    )
                except api_client.ApiError as err_material:
                    materiales_fallidos.append(f"{mat['titulo']} ({err_material.mensaje})")
                except Exception as err_material:
                    materiales_fallidos.append(f"{mat['titulo']} (error inesperado: {err_material})")

            if materiales_fallidos:
                texto_mensaje.value = (
                    "Contenido publicado, pero fallaron estos materiales: " + "; ".join(materiales_fallidos)
                )
                texto_mensaje.color = COLOR_ERROR
                texto_mensaje.visible = True
                page.update()
            else:
                page.go("/docente/contenidos")
        except api_client.ApiError as err:
            texto_mensaje.value = err.mensaje
            texto_mensaje.color = COLOR_ERROR
            texto_mensaje.visible = True
        finally:
            boton_publicar.disabled = False
            indicador_carga.visible = False
            page.update()

    boton_publicar.on_click = publicar

    def volver(e):
        page.go("/docente/contenidos")

    return ft.View(
        route="/docente/contenido-nuevo",
        bgcolor=COLOR_FONDO,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Publicar contenido"),
                bgcolor=COLOR_PRIMARIO,
                leading=ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=volver),
            ),
            ft.Container(
                padding=16,
                content=ft.Column(
                    controls=[
                        texto_mensaje,
                        campo_titulo,
                        campo_descripcion,
                        campo_asignatura,
                        campo_enlace,
                        boton_adjuntar,
                        texto_archivo,
                        ft.Divider(),
                        ft.Text("Materiales adicionales (opcional)", size=16, weight=ft.FontWeight.W_600),
                        ft.Text(
                            "Agrega los que quieras: videos, audios, documentos o enlaces. "
                            "Puedes quitar cualquiera con la 'x' antes de publicar.",
                            size=12,
                            color=COLOR_PLACEHOLDER,
                        ),
                        lista_materiales_visual,
                        texto_mensaje_material,
                        campo_tipo_material,
                        campo_titulo_material,
                        campo_url_material,
                        boton_adjuntar_material,
                        texto_archivo_material,
                        ft.OutlinedButton(text="+ Agregar material", on_click=agregar_material_click),
                        ft.Divider(),
                        ft.Row([boton_publicar, indicador_carga]),
                    ]
                ),
            ),
        ],
    )