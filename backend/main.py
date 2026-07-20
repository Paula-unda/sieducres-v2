"""
main.py
Punto de entrada del backend. Equivale al index.php principal de V1.0,
pero en FastAPI cada "modulo" se registra como un router independiente.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from auth import router as auth_router
from routers.contenidos import router as contenidos_router
# A medida que se conviertan mas modulos (actividades, calificaciones, etc.)
# se importan y se registran aqui igual que contenidos_router:
# from routers.actividades import router as actividades_router

app = FastAPI(
    title="SIEDUCRES API",
    description="Backend del Sistema Educativo Resiliente - NER 319, Municipio Rojas, Barinas",
    version="2.0.0",
)

app.include_router(auth_router)
app.include_router(contenidos_router)
# app.include_router(actividades_router)

# Sirve los archivos subidos (adjuntos de contenidos, materiales)
# en http://.../uploads/contenidos/nombre.pdf , etc.
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def raiz():
    """Endpoint simple para confirmar que el servidor esta corriendo."""
    return {"mensaje": "SIEDUCRES API v2.0 - en linea"}