# Cómo probar SIEDUCRES V2.0 — Guía completa

Esta guía cubre todo lo necesario para instalar y probar el proyecto
desde cero: base de datos, backend (API) y aplicación móvil (Flet).

> Nota de seguridad: las credenciales de prueba que aparecen en esta
> guía son de un usuario **Administrador de demostración**, sobre una
> base de datos sin información real de estudiantes. Son válidas solo
> para fines de evaluación académica de este proyecto.

---

## Requisitos previos (instalar antes de empezar)

| Programa | Versión recomendada | Descarga |
|---|---|---|
| **Python** | 3.10 o superior (evita 3.8, sin soporte) | [python.org/downloads](https://www.python.org/downloads/) |
| **PostgreSQL** | 17 (usa el instalador `.exe`, no el paquete "binaries") | [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) |
| **Git** | Cualquier versión reciente | [git-scm.com/downloads](https://git-scm.com/downloads) |

**Al instalar Python:** marca la casilla **"Add python.exe to PATH"** en
la primera pantalla del instalador — si no la marcas, Windows no
reconocerá el comando `python` en la terminal.

**Al instalar PostgreSQL:** anota la contraseña que le pongas al usuario
`postgres`, la vas a necesitar más adelante. pgAdmin 4 viene incluido.

---

## Paso 1: Descargar el proyecto

```
git clone https://github.com/Paula-unda/sieducres-v2.git
cd sieducres-v2
```

## Paso 2: Crear la base de datos

1. Abre **pgAdmin 4**
2. Click derecho en "Databases" → "Create" → "Database..." → nómbrala `sieducres`
3. Click derecho sobre `sieducres` → "Query Tool"
4. Abre el archivo `docs/sieducres_completo.sql`, copia todo el
   contenido, pégalo en el Query Tool, y presiona **F5**
5. Debe terminar sin errores. Verifica con:
   ```sql
   SELECT * FROM usuarios;
   SELECT * FROM escuelas;
   ```
   Deberías ver 1 usuario (el Administrador) y 12 escuelas.

## Paso 3: Instalar y levantar el backend

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Si PowerShell bloquea la activación del entorno virtual:
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Configurar variables de entorno:**
1. Copia `.env.example` y renómbralo a `.env`
2. Completa `DB_PASSWORD` con la contraseña de tu usuario `postgres`
3. Genera una clave secreta:
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   y pégala en `SECRET_KEY`

**Crear las carpetas de archivos subidos:**
```
mkdir uploads\contenidos
mkdir uploads\materiales
```

**Levantar el servidor:**
```
uvicorn main:app --reload
```
Debe mostrar `Uvicorn running on http://127.0.0.1:8000` sin errores.
**Deja esta terminal abierta y corriendo.**

## Paso 4: Revisar la documentación interactiva de la API (`/docs`)

Con el backend corriendo, abre en el navegador:

**http://127.0.0.1:8000/docs**

Ahí verás dos grupos de endpoints, cada uno con su descripción:

- **Autenticacion**: login, registro por rol, recuperación de
  contraseña, listado de escuelas, búsqueda de estudiantes por escuela
- **Contenidos Academicos**: crear/editar/eliminar contenido,
  materiales adicionales (video/audio/documento/enlace), progreso de
  estudiantes, estadísticas, reporte general en PDF

**Para probar un endpoint directamente ahí (sin la app):**
1. Click en `POST /auth/login` → "Try it out"
2. `username`: `admin@sieducres.edu.ve`
3. `password`: `A2026siudecres+`
4. "Execute" — debe devolver un `access_token`
5. Para probar endpoints protegidos (los de "Contenidos Academicos"),
   click en el botón **"Authorize"** 🔓 arriba a la derecha, pega el
   `access_token` que obtuviste, y ya puedes probar cualquiera de esos
   endpoints directamente desde ahí

## Paso 5: Instalar y levantar la app móvil (Flet)

En una **terminal nueva** (deja la del backend corriendo aparte):

```
cd app
..\venv\Scripts\activate
pip install -r requirements.txt
flet run main.py
```

Debe abrir una ventana de escritorio con la pantalla de login de
SIEDUCRES (Flet simula así la app móvil mientras se prueba en la PC).

---

## Credenciales de prueba

**Usuario Administrador** (ya viene creado en la base de datos):
- Correo: `admin@sieducres.edu.ve`
- Contraseña: `A2026siudecres+`

También puedes registrar usuarios nuevos de cualquier rol (Docente,
Estudiante, Representante) directamente desde la pantalla de registro
de la app.

---

## Flujo de prueba — Sprint 1: Autenticación y Autorregistro

1. En el login, click en "Crear una cuenta nueva"
2. Registra un **Docente** o **Estudiante** (elige grado y sección), y
   si quieres, un **Representante** (busca y vincula un estudiante
   existente por escuela)
3. Inicia sesión con el usuario creado — debe llevarte a la pantalla
   "Bienvenido/a" con su nombre, rol y correo
4. Prueba también "¿Olvidaste tu contraseña?" con un correo registrado

## Flujo de prueba — Sprint 2: Módulo Académico Multi-Institución

**Como Docente:**
1. Desde "Bienvenido/a", entra a **"Mis contenidos académicos"**
2. **"+ Publicar contenido nuevo"** — completa título, descripción,
   asignatura, y opcionalmente un enlace o documento principal
3. Agrega uno o más **materiales adicionales** (video, audio,
   documento o enlace), tocando **"+ Agregar material"** por cada uno
4. Toca **"Publicar"**
5. En "Mis contenidos", prueba los íconos de cada tarjeta:
   - 👁️ **Previsualizar** (como lo ve un estudiante)
   - 📊 **Estadísticas** (quién lo ha visto)
   - ✏️ **Editar** (datos principales + gestionar materiales)
   - 🗑️ **Eliminar** (con confirmación)
6. Prueba **"📄 Descargar reporte general (PDF)"**

**Como Estudiante** (mismo grado/sección que el docente de prueba):
1. Entra a **"Ver contenidos"** — tarjetas de color con insignia de
   estado (Sin ver / Recién visto / Visto)
2. Toca una tarjeta para ver el detalle: descripción, recursos y
   materiales adicionales
3. Los **videos/audios subidos como archivo** se reproducen dentro de
   la app; los **enlaces de YouTube** se abren externamente en esta PC
   (ver nota de limitación abajo)
4. Prueba la **descarga** de documentos adjuntos
5. Toca **"¡Ya lo vi!"** y confirma que la tarjeta cambia a "Visto"

### ⚠️ Limitación conocida: video de YouTube incrustado

El reproductor incrustado de YouTube (`ft.WebView` de Flet) solo
funciona en Android/iOS, no en la ventana de escritorio de Windows
usada en estas pruebas. En el APK final se verá incrustado dentro de
la app; en escritorio se abre externamente con un botón — esto es una
limitación documentada de la librería, no un error del proyecto.

---

## Problemas comunes al instalar

| Problema | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'reportlab'` | Falta la dependencia del reporte PDF | `pip install reportlab` |
| `psycopg2-binary` falla al compilar (`Microsoft Visual C++ 14.0 required`) | Versión sin instalador precompilado para tu Python | `pip install psycopg2-binary` sin fijar versión |
| Error de bcrypt al hacer login | Incompatibilidad `passlib` 1.7.4 con `bcrypt` 5.x | `pip install bcrypt==4.0.1` (ya fijado en `requirements.txt`) |
| `Could not find a suitable TLS CA certificate bundle` | Variable `CURL_CA_BUNDLE` de una instalación vieja de PostgreSQL | `$env:CURL_CA_BUNDLE = $null` en la terminal actual |
| `email-validator is not installed` | Dependencia faltante | `pip install email-validator` |
| PowerShell no deja activar el entorno virtual | Política de ejecución restringida | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Un error de importación persiste tras reemplazar un archivo | El archivo no se guardó completo | Verificar con `Select-String -Path <archivo> -Pattern "<texto esperado>"` |
