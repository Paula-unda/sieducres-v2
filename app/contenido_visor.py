"""
contenido_visor.py
Modulo compartido (usado por estudiante_contenidos.py y
docente_contenido_preview.py) para mostrar los recursos de un contenido,
replicando el comportamiento de previsualizar_contenido.php:

  - Videos subidos como archivo -> se reproducen DENTRO de la app (ft.Video)
  - Enlaces de YouTube -> se incrustan DENTRO de la app con ft.WebView
    (igual que el <iframe src="youtube.com/embed/...">) del PHP original),
    pero SOLO en Android/iOS: ft.WebView de Flet no funciona en Windows/
    macOS/Linux de escritorio. En esos casos (como al probar con
    'flet run' en esta PC) se usa un boton que abre el video externamente,
    y esto es una limitacion de la libreria, no un error del codigo.
  - Documentos (PDF, Word, imagenes, etc.) -> boton de descarga
  - Otros enlaces (no YouTube) -> boton que abre fuera de la app
"""

from urllib.parse import urlparse, parse_qs
from typing import Optional

import flet as ft

from api_client import BASE_URL

COLOR_TEXTO = "#333333"
COLOR_PLACEHOLDER = "#AAAAAA"
COLOR_PRIMARIO = "#4BC4E7"

EXTENSIONES_VIDEO = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
EXTENSIONES_AUDIO = {".mp3", ".wav", ".ogg", ".m4a"}


def _es_video_por_extension(nombre_archivo: str) -> bool:
    nombre_archivo = (nombre_archivo or "").lower()
    return any(nombre_archivo.endswith(ext) for ext in EXTENSIONES_VIDEO)


def _es_audio_por_extension(nombre_archivo: str) -> bool:
    nombre_archivo = (nombre_archivo or "").lower()
    return any(nombre_archivo.endswith(ext) for ext in EXTENSIONES_AUDIO)


def _es_reproducible_por_extension(nombre_archivo: str) -> bool:
    """Video o audio: ambos se reproducen con el mismo control ft.Video."""
    return _es_video_por_extension(nombre_archivo) or _es_audio_por_extension(nombre_archivo)


def _url_archivo(carpeta: str, nombre_archivo: str) -> str:
    return f"{BASE_URL}/uploads/{carpeta}/{nombre_archivo}"


def _url_embed_youtube(url: str) -> Optional[str]:
    """
    Misma logica que previsualizar_contenido.php: convierte una URL de
    YouTube (watch?v=... o youtu.be/...) a su version /embed/VIDEO_ID,
    necesaria para poder incrustarla en un WebView.
    """
    url_limpia = (url or "").strip()
    if "youtube.com" not in url_limpia and "youtu.be" not in url_limpia:
        return None

    if "watch?v=" in url_limpia:
        query = urlparse(url_limpia).query
        video_id = parse_qs(query).get("v", [None])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
    elif "youtu.be/" in url_limpia:
        video_id = url_limpia.rstrip("/").split("/")[-1]
        return f"https://www.youtube.com/embed/{video_id}"

    return None


def _es_plataforma_movil(page: ft.Page) -> bool:
    """ft.WebView solo esta soportado en Android/iOS segun la documentacion de Flet."""
    try:
        return page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
    except Exception:
        return False


def _control_video_youtube(page: ft.Page, url: str, titulo_boton: str) -> ft.Control:
    """
    Incrusta el video de YouTube con WebView si es Android/iOS.
    En escritorio (donde se prueba con 'flet run' en esta PC), cae
    automaticamente al boton externo, porque WebView no funciona ahi.
    """
    url_embed = _url_embed_youtube(url)

    if url_embed and _es_plataforma_movil(page):
        return ft.Container(
            height=200,
            border_radius=8,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.WebView(url=url_embed, expand=True),
        )

    # Escritorio, o enlace que no es de YouTube: boton externo.
    return ft.TextButton(text=titulo_boton, icon=ft.icons.OPEN_IN_NEW, url=url)


def bloque_recurso_principal(page: ft.Page, contenido: dict) -> list:
    """
    Construye los controles para el 'documento principal' (archivo_adjunto)
    y el 'video/enlace principal' (enlace) del contenido, tal como se
    subieron en gestion_contenidos.php.
    """
    controles = []

    archivo_adjunto = contenido.get("archivo_adjunto")
    if archivo_adjunto:
        if _es_video_por_extension(archivo_adjunto):
            controles.append(ft.Text("Video principal:", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXTO))
            controles.append(
                ft.Container(
                    height=200,
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Video(
                        playlist=[ft.VideoMedia(resource=_url_archivo("contenidos", archivo_adjunto))],
                        show_controls=True,
                        aspect_ratio=16 / 9,
                    ),
                )
            )
        else:
            controles.append(
                ft.OutlinedButton(
                    text="Descargar documento principal",
                    icon=ft.icons.DOWNLOAD,
                    url=_url_archivo("contenidos", archivo_adjunto),
                )
            )

    enlace = contenido.get("enlace")
    if enlace:
        controles.append(ft.Text("Video principal:", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXTO))
        controles.append(_control_video_youtube(page, enlace, "Ver video (se abre fuera de la app)"))

    return controles


def bloque_material(page: ft.Page, material: dict) -> ft.Control:
    """Construye el control adecuado para un material adicional, segun su tipo."""
    titulo = material.get("titulo", "Material")
    tipo = material.get("tipo")
    archivo = material.get("archivo")
    url = material.get("url")

    if archivo and _es_reproducible_por_extension(archivo):
        etiqueta_altura = 100 if _es_audio_por_extension(archivo) else 180
        return ft.Column(
            spacing=4,
            controls=[
                ft.Text(titulo, size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
                ft.Container(
                    height=etiqueta_altura,
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Video(
                        playlist=[ft.VideoMedia(resource=_url_archivo("materiales", archivo))],
                        show_controls=True,
                        aspect_ratio=16 / 9,
                    ),
                ),
            ],
        )

    if archivo:  # documento subido (pdf, word, imagen, etc.)
        return ft.OutlinedButton(
            text=f"Descargar: {titulo}",
            icon=ft.icons.DOWNLOAD,
            url=_url_archivo("materiales", archivo),
        )

    if url and tipo in ("video", "audio"):
        return ft.Column(
            spacing=4,
            controls=[
                ft.Text(titulo, size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
                _control_video_youtube(page, url, "Ver/escuchar (se abre fuera de la app)"),
            ],
        )

    if url:  # enlace web (no video)
        return ft.TextButton(text=f"Abrir enlace: {titulo}", icon=ft.icons.OPEN_IN_NEW, url=url)

    return ft.Text(f"{titulo} (sin archivo ni enlace)", size=13, color=COLOR_PLACEHOLDER)