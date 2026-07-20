"""
routers/contenidos.py
Reemplaza:
  - docente/gestion_contenidos.php  -> crear_contenido, mis_contenidos
  - docente/editar_contenido.php    -> editar_contenido
  - docente/eliminar_contenido.php  -> eliminar_contenido
  - estudiante/contenidos.php       -> listar_contenidos_estudiante
  - estudiante/contenido_detalle.php-> obtener_contenido
  - estudiante/actualizar_progreso.php -> actualizar_progreso

Reglas de conversion aplicadas (segun el documento de referencia):
  - Las consultas SQL se mantienen iguales a las de PHP (mismos JOIN, mismos
    filtros de grado/seccion "TRIM(...) = ..."), solo cambia la sintaxis
    de parametros (%s en vez de :nombre o $1).
  - El filtrado por escuela (escuela_id) se agrega ademas del filtro por
    grado/seccion que ya tenia V1.0, para separar las 12 instituciones.
"""

import os
import io
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from auth import get_current_user, requerir_rol
from database import get_connection

router = APIRouter(prefix="/contenidos", tags=["Contenidos Academicos"])

CARPETA_ADJUNTOS = "uploads/contenidos"
CARPETA_MATERIALES = "uploads/materiales"


# ----------------------------------------------------------------------
# Helpers internos
# ----------------------------------------------------------------------

def _obtener_grado_seccion_docente(docente_id: int):
    """Equivale a la consulta 'SELECT grado, seccion FROM docentes WHERE usuario_id = ?'."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT grado, seccion FROM docentes WHERE usuario_id = %s", (docente_id,))
            return cur.fetchone()
    finally:
        conn.close()


def _obtener_grado_seccion_estudiante(estudiante_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT TRIM(grado) as grado, TRIM(seccion) as seccion FROM estudiantes WHERE usuario_id = %s",
                (estudiante_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def _guardar_archivo(archivo: UploadFile, carpeta: str) -> str:
    """Guarda un archivo subido con un nombre unico (timestamp + nombre original), igual que en PHP."""
    os.makedirs(carpeta, exist_ok=True)
    nombre_unico = f"{int(datetime.now().timestamp())}_{archivo.filename}"
    ruta_destino = os.path.join(carpeta, nombre_unico)
    with open(ruta_destino, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
    return nombre_unico


# ----------------------------------------------------------------------
# DOCENTE: crear y gestionar contenidos
# ----------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
def crear_contenido(
    titulo: str = Form(...),
    descripcion: str = Form(...),
    asignatura: str = Form(...),
    enlace: Optional[str] = Form(None),
    archivo: Optional[UploadFile] = File(None),
    usuario: dict = Depends(requerir_rol("Docente")),
):
    """
    Reemplaza la parte de creacion de docente/gestion_contenidos.php.
    El grado y seccion NO los escribe el docente: se toman automaticamente
    de la tabla 'docentes', igual que en la version PHP.
    """
    datos_docente = _obtener_grado_seccion_docente(usuario["id"])
    if not datos_docente or not datos_docente.get("grado"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tienes un grado y seccion asignados. No puedes publicar contenido.",
        )

    nombre_archivo = None
    if archivo is not None:
        nombre_archivo = _guardar_archivo(archivo, CARPETA_ADJUNTOS)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contenidos
                    (titulo, descripcion, asignatura, grado, seccion, docente_id,
                     enlace, archivo_adjunto, escuela_id, fecha_publicacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE)
                RETURNING id, titulo, descripcion, asignatura, grado, seccion,
                          enlace, archivo_adjunto, fecha_publicacion
                """,
                (
                    titulo, descripcion, asignatura,
                    datos_docente["grado"], datos_docente["seccion"],
                    usuario["id"], enlace, nombre_archivo, usuario["escuela_id"],
                ),
            )
            nuevo_contenido = cur.fetchone()
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Contenido publicado exitosamente.", "contenido": nuevo_contenido}


@router.get("/mis-contenidos")
def mis_contenidos(usuario: dict = Depends(requerir_rol("Docente"))):
    """
    Reemplaza la consulta principal de docente/gestion_contenidos.php:
    lista los contenidos del docente con el conteo de estudiantes que
    ya lo vieron, respecto al total de estudiantes de su grado/seccion.
    """
    datos_docente = _obtener_grado_seccion_docente(usuario["id"])
    grado = datos_docente["grado"] if datos_docente else None
    seccion = datos_docente["seccion"] if datos_docente else None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as total
                FROM estudiantes e
                INNER JOIN usuarios u ON e.usuario_id = u.id
                WHERE u.rol = 'Estudiante' AND e.grado = %s AND e.seccion = %s
                """,
                (grado, seccion),
            )
            total_estudiantes_clase = cur.fetchone()["total"]

            cur.execute(
                """
                SELECT
                    c.id, c.titulo, c.asignatura, c.grado, c.seccion,
                    c.fecha_publicacion, c.docente_id, c.enlace, c.archivo_adjunto,
                    c.activo, c.creado_en,
                    %s as total_estudiantes_clase,
                    COUNT(DISTINCT CASE WHEN p.completado = true AND p.material_id IS NULL
                                        THEN p.estudiante_id END) as estudiantes_vieron
                FROM contenidos c
                LEFT JOIN progreso_contenido p ON c.id = p.contenido_id AND p.material_id IS NULL
                WHERE c.docente_id = %s AND c.activo = true
                GROUP BY c.id, c.titulo, c.asignatura, c.grado, c.seccion,
                         c.fecha_publicacion, c.docente_id, c.enlace, c.archivo_adjunto,
                         c.activo, c.creado_en
                ORDER BY c.fecha_publicacion DESC, c.id DESC
                """,
                (total_estudiantes_clase, usuario["id"]),
            )
            return cur.fetchall()
    finally:
        conn.close()


@router.get("/reporte-pdf")
def reporte_pdf(usuario: dict = Depends(requerir_rol("Docente"))):
    """
    Genera un PDF con el reporte general de estadisticas de todos los
    contenidos publicados por el docente autenticado (titulo, asignatura,
    fecha, cuantos estudiantes lo vieron y el porcentaje de la clase).
    Usa ReportLab, tal como se establecio en el stack tecnologico del
    Documento Vision (reemplaza a dompdf de la version PHP).
    """
    datos_docente = _obtener_grado_seccion_docente(usuario["id"])
    grado = datos_docente["grado"] if datos_docente else None
    seccion = datos_docente["seccion"] if datos_docente else None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as total
                FROM estudiantes e
                INNER JOIN usuarios u ON e.usuario_id = u.id
                WHERE u.rol = 'Estudiante' AND e.grado = %s AND e.seccion = %s
                """,
                (grado, seccion),
            )
            total_estudiantes_clase = cur.fetchone()["total"]

            cur.execute(
                """
                SELECT
                    c.titulo, c.asignatura, c.grado, c.seccion, c.fecha_publicacion,
                    COUNT(DISTINCT CASE WHEN p.completado = true AND p.material_id IS NULL
                                        THEN p.estudiante_id END) as estudiantes_vieron
                FROM contenidos c
                LEFT JOIN progreso_contenido p ON c.id = p.contenido_id AND p.material_id IS NULL
                WHERE c.docente_id = %s AND c.activo = true
                GROUP BY c.id, c.titulo, c.asignatura, c.grado, c.seccion, c.fecha_publicacion
                ORDER BY c.fecha_publicacion DESC, c.id DESC
                """,
                (usuario["id"],),
            )
            contenidos = cur.fetchall()
    finally:
        conn.close()

    # ---- Construccion del PDF en memoria ----
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph("SIEDUCRES - Reporte General de Contenidos", estilos["Title"]),
        Paragraph(f"Docente: {usuario['nombre']}", estilos["Normal"]),
        Paragraph(f"Grado/Seccion: {grado or '-'} {seccion or ''}", estilos["Normal"]),
        Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos["Normal"]),
        Spacer(1, 0.6 * cm),
    ]

    datos_tabla = [["Titulo", "Asignatura", "Fecha", "Vistos", "% de la clase"]]
    for c in contenidos:
        vistos = c["estudiantes_vieron"] or 0
        porcentaje = round((vistos / total_estudiantes_clase) * 100) if total_estudiantes_clase > 0 else 0
        fecha_str = c["fecha_publicacion"].strftime("%d/%m/%Y") if c["fecha_publicacion"] else "-"
        datos_tabla.append([
            c["titulo"], c["asignatura"] or "-", fecha_str,
            f"{vistos} / {total_estudiantes_clase}", f"{porcentaje}%",
        ])

    if len(datos_tabla) == 1:
        elementos.append(Paragraph("No hay contenidos publicados todavia.", estilos["Normal"]))
    else:
        tabla = Table(datos_tabla, colWidths=[6.5 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4BC4E7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabla)

    documento.build(elementos)
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_contenidos_sieducres.pdf"},
    )


class ContenidoEditar(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    asignatura: Optional[str] = None
    enlace: Optional[str] = None


@router.put("/{contenido_id}")
def editar_contenido(
    contenido_id: int,
    datos: ContenidoEditar,
    usuario: dict = Depends(requerir_rol("Docente")),
):
    """Reemplaza docente/editar_contenido.php. Solo el docente dueño puede editar."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT docente_id FROM contenidos WHERE id = %s", (contenido_id,))
            existente = cur.fetchone()
            if existente is None:
                raise HTTPException(status_code=404, detail="Contenido no encontrado")
            if existente["docente_id"] != usuario["id"]:
                raise HTTPException(status_code=403, detail="No puedes editar contenido de otro docente")

            campos = {k: v for k, v in datos.dict().items() if v is not None}
            if not campos:
                raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

            set_clause = ", ".join(f"{campo} = %s" for campo in campos)
            valores = list(campos.values()) + [contenido_id]
            cur.execute(f"UPDATE contenidos SET {set_clause} WHERE id = %s", valores)
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Contenido actualizado exitosamente."}


@router.delete("/{contenido_id}")
def eliminar_contenido(contenido_id: int, usuario: dict = Depends(requerir_rol("Docente"))):
    """Reemplaza docente/eliminar_contenido.php (borrado logico, activo = false)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT docente_id FROM contenidos WHERE id = %s", (contenido_id,))
            existente = cur.fetchone()
            if existente is None:
                raise HTTPException(status_code=404, detail="Contenido no encontrado")
            if existente["docente_id"] != usuario["id"]:
                raise HTTPException(status_code=403, detail="No puedes eliminar contenido de otro docente")

            cur.execute("UPDATE contenidos SET activo = false WHERE id = %s", (contenido_id,))
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Contenido eliminado exitosamente."}


# ----------------------------------------------------------------------
# MATERIALES adicionales de un contenido
# ----------------------------------------------------------------------

@router.get("/{contenido_id}/estadisticas")
def estadisticas_contenido(contenido_id: int, usuario: dict = Depends(requerir_rol("Docente"))):
    """
    Reemplaza docente/estadisticas_contenido.php.
    Devuelve el detalle de que estudiantes de la clase ya vieron el
    contenido y cuales no, ademas del porcentaje general.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT docente_id, grado, seccion FROM contenidos WHERE id = %s", (contenido_id,))
            contenido = cur.fetchone()
            if contenido is None:
                raise HTTPException(status_code=404, detail="Contenido no encontrado")
            if contenido["docente_id"] != usuario["id"]:
                raise HTTPException(status_code=403, detail="No puedes ver estadisticas de contenido de otro docente")

            cur.execute(
                """
                SELECT
                    u.id, u.nombre,
                    COALESCE(p.completado, false) as completado,
                    COALESCE(p.porcentaje_visto, 0) as porcentaje_visto,
                    p.ultima_visualizacion
                FROM usuarios u
                INNER JOIN estudiantes e ON e.usuario_id = u.id
                LEFT JOIN progreso_contenido p
                    ON p.estudiante_id = u.id AND p.contenido_id = %s AND p.material_id IS NULL
                WHERE u.rol = 'Estudiante' AND u.activo = true
                    AND e.grado = %s AND e.seccion = %s
                ORDER BY completado DESC, u.nombre
                """,
                (contenido_id, contenido["grado"], contenido["seccion"]),
            )
            estudiantes = cur.fetchall()

            total = len(estudiantes)
            vieron = sum(1 for e in estudiantes if e["completado"])
            porcentaje = round((vieron / total) * 100) if total > 0 else 0

            return {
                "total_estudiantes_clase": total,
                "estudiantes_vieron": vieron,
                "porcentaje": porcentaje,
                "estudiantes": estudiantes,
            }
    finally:
        conn.close()


@router.post("/{contenido_id}/materiales", status_code=status.HTTP_201_CREATED)
def agregar_material(
    contenido_id: int,
    titulo: str = Form(...),
    tipo: str = Form(...),  # video | audio | documento | enlace
    url: Optional[str] = Form(None),
    archivo: Optional[UploadFile] = File(None),
    orden: int = Form(0),
    usuario: dict = Depends(requerir_rol("Docente")),
):
    """Reemplaza el bloque de 'materiales adicionales' de docente/gestion_contenidos.php."""
    nombre_archivo = None
    if archivo is not None:
        nombre_archivo = _guardar_archivo(archivo, CARPETA_MATERIALES)

    if not url and not nombre_archivo:
        raise HTTPException(status_code=400, detail="Debes proporcionar una URL o un archivo para el material")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO materiales (contenido_id, titulo, tipo, url, archivo, orden)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, titulo, tipo, url, archivo, orden
                """,
                (contenido_id, titulo, tipo, url, nombre_archivo, orden),
            )
            nuevo_material = cur.fetchone()
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Material agregado exitosamente.", "material": nuevo_material}


@router.get("/{contenido_id}/materiales")
def listar_materiales(contenido_id: int, usuario: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, titulo, tipo, url, archivo, orden FROM materiales "
                "WHERE contenido_id = %s AND activo = true ORDER BY orden",
                (contenido_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def _verificar_material_pertenece_al_docente(material_id: int, docente_id: int, cur):
    """Confirma que el material exista y que su contenido le pertenezca al docente autenticado."""
    cur.execute(
        """
        SELECT m.id, c.docente_id
        FROM materiales m
        INNER JOIN contenidos c ON c.id = m.contenido_id
        WHERE m.id = %s
        """,
        (material_id,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    if fila["docente_id"] != docente_id:
        raise HTTPException(status_code=403, detail="No puedes modificar material de otro docente")


class MaterialEditar(BaseModel):
    titulo: Optional[str] = None
    url: Optional[str] = None


@router.put("/materiales/{material_id}")
def editar_material(material_id: int, datos: MaterialEditar, usuario: dict = Depends(requerir_rol("Docente"))):
    """
    Permite corregir el titulo o la URL de un material ya guardado
    (por ejemplo, si el docente escribio mal el enlace). Para cambiar
    el ARCHIVO adjunto de un material, se recomienda eliminarlo y
    agregar uno nuevo, en vez de reemplazar el archivo existente.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _verificar_material_pertenece_al_docente(material_id, usuario["id"], cur)

            campos = {k: v for k, v in datos.dict().items() if v is not None}
            if not campos:
                raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

            set_clause = ", ".join(f"{campo} = %s" for campo in campos)
            valores = list(campos.values()) + [material_id]
            cur.execute(f"UPDATE materiales SET {set_clause} WHERE id = %s", valores)
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Material actualizado exitosamente."}


@router.delete("/materiales/{material_id}")
def eliminar_material(material_id: int, usuario: dict = Depends(requerir_rol("Docente"))):
    """Elimina (borrado logico) un material adicional de un contenido propio."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _verificar_material_pertenece_al_docente(material_id, usuario["id"], cur)
            cur.execute("UPDATE materiales SET activo = false WHERE id = %s", (material_id,))
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Material eliminado exitosamente."}


# ----------------------------------------------------------------------
# ESTUDIANTE: ver contenidos y progreso
# ----------------------------------------------------------------------

@router.get("/mis-contenidos-estudiante")
def listar_contenidos_estudiante(usuario: dict = Depends(requerir_rol("Estudiante"))):
    """
    Reemplaza estudiante/contenidos.php + obtenerContenidosConProgreso() de funciones.php.
    Filtra por grado/seccion del estudiante y trae el progreso de cada contenido.
    """
    datos_estudiante = _obtener_grado_seccion_estudiante(usuario["id"])
    grado = datos_estudiante["grado"] if datos_estudiante else ""
    seccion = datos_estudiante["seccion"] if datos_estudiante else ""

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT
                    c.id, c.titulo, c.descripcion, c.fecha_publicacion,
                    c.archivo_adjunto, c.enlace, c.asignatura, c.grado, c.seccion,
                    u.nombre as docente_nombre,
                    COALESCE(p.porcentaje_visto, 0) as porcentaje_visto,
                    COALESCE(p.completado, false) as completado,
                    p.ultima_visualizacion
                FROM contenidos c
                LEFT JOIN usuarios u ON c.docente_id = u.id
                LEFT JOIN (
                    SELECT DISTINCT contenido_id, estudiante_id, porcentaje_visto, completado, ultima_visualizacion
                    FROM progreso_contenido
                    WHERE estudiante_id = %s AND material_id IS NULL
                ) p ON p.contenido_id = c.id
                WHERE c.activo = true
                    AND (
                        (c.grado IS NULL AND c.seccion IS NULL)
                        OR (TRIM(c.grado) = %s AND (c.seccion IS NULL OR TRIM(c.seccion) = %s))
                        OR (TRIM(c.grado) = %s AND TRIM(c.seccion) = %s)
                    )
                ORDER BY c.fecha_publicacion DESC, c.id DESC
                """,
                (usuario["id"], grado, seccion, grado, seccion),
            )
            return cur.fetchall()
    finally:
        conn.close()


@router.get("/{contenido_id}")
def obtener_contenido(contenido_id: int, usuario: dict = Depends(get_current_user)):
    """Reemplaza estudiante/contenido_detalle.php (detalle + materiales asociados)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT c.*, u.nombre as docente_nombre
                FROM contenidos c
                LEFT JOIN usuarios u ON c.docente_id = u.id
                WHERE c.id = %s AND c.activo = true
                """,
                (contenido_id,),
            )
            contenido = cur.fetchone()
            if contenido is None:
                raise HTTPException(status_code=404, detail="Contenido no encontrado")

            cur.execute(
                "SELECT id, titulo, tipo, url, archivo, orden FROM materiales "
                "WHERE contenido_id = %s AND activo = true ORDER BY orden",
                (contenido_id,),
            )
            contenido["materiales"] = cur.fetchall()
            return contenido
    finally:
        conn.close()


class ProgresoActualizar(BaseModel):
    porcentaje_visto: float
    material_id: Optional[int] = None


@router.post("/{contenido_id}/progreso")
def actualizar_progreso(
    contenido_id: int,
    datos: ProgresoActualizar,
    usuario: dict = Depends(requerir_rol("Estudiante")),
):
    """
    Reemplaza estudiante/actualizar_progreso.php y actualizar_progreso_material.php
    (unificados aqui: material_id es None para el contenido principal, o un id
    especifico si el progreso es de un material adicional).
    """
    completado = datos.porcentaje_visto >= 100

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM progreso_contenido
                WHERE estudiante_id = %s AND contenido_id = %s
                    AND (material_id = %s OR (material_id IS NULL AND %s IS NULL))
                """,
                (usuario["id"], contenido_id, datos.material_id, datos.material_id),
            )
            existente = cur.fetchone()

            if existente:
                cur.execute(
                    """
                    UPDATE progreso_contenido
                    SET porcentaje_visto = %s, completado = %s, ultima_visualizacion = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (datos.porcentaje_visto, completado, existente["id"]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO progreso_contenido
                        (estudiante_id, contenido_id, material_id, porcentaje_visto, completado, ultima_visualizacion)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (usuario["id"], contenido_id, datos.material_id, datos.porcentaje_visto, completado),
                )
            conn.commit()
    finally:
        conn.close()

    return {"mensaje": "Progreso actualizado.", "completado": completado}