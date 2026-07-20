# Cómo probar el backend de SIEDUCRES en tu PC

## 1. Abrir la carpeta en VS Code
Abre VS Code → "File" → "Open Folder..." → selecciona la carpeta `backend`.

## 2. Crear un entorno virtual
Abre una terminal dentro de VS Code (menú "Terminal" → "New Terminal") y escribe:

```
python -m venv venv
venv\Scripts\activate
```

Si funcionó bien, vas a ver `(venv)` al inicio de la línea de la terminal.

## 3. Instalar las dependencias
Con el entorno virtual activado:

```
pip install -r requirements.txt
```

## 4. Configurar tu archivo .env
1. Copia `.env.example` y renombra la copia a `.env`
2. Ábrelo y coloca:
   - `DB_PASSWORD`: la contraseña que pusiste al instalar PostgreSQL 17
   - `SECRET_KEY`: genera una corriendo esto en la terminal:
     ```
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
     Copia lo que te imprima y pégalo como valor de `SECRET_KEY`

## 5. Levantar el servidor
```
uvicorn main:app --reload
```

Si todo salió bien, la terminal debe decir algo como:
`Uvicorn running on http://127.0.0.1:8000`

## 6. Probar en el navegador
Abre: **http://127.0.0.1:8000/docs**

Ahí vas a ver la documentación interactiva de la API (esto lo genera FastAPI solo).
Vas a ver 3 endpoints bajo "Autenticacion":
- `POST /auth/registro` — crear un usuario nuevo
- `POST /auth/login` — iniciar sesión y obtener el token
- `GET /auth/perfil` — ver los datos del usuario autenticado (requiere token)

### Prueba rápida:
1. Click en `POST /auth/login` → "Try it out"
2. En `username` escribe: `admin@sieducres.edu.ve`
3. En `password` escribe: `A2026siudecres+`
4. Click "Execute"
5. Deberías recibir un `access_token` largo en la respuesta — eso confirma que el login funciona con tu base de datos real.

### Probar el autorregistro:
1. Click en `POST /auth/registro` → "Try it out"
2. Rellena un usuario de prueba, por ejemplo:
   ```json
   {
     "nombre": "Docente de Prueba",
     "correo": "docente.prueba@sieducres.edu.ve",
     "contrasena": "clave123",
     "rol": "Docente",
     "escuela_id": 1
   }
   ```
3. Execute → deberías ver "Usuario registrado exitosamente"
4. Verifica en pgAdmin con `SELECT * FROM usuarios;` que el nuevo usuario aparece con su contraseña ya encriptada (no en texto plano).

## Si algo falla
Copia el mensaje de error exacto de la terminal (no solo lo que sale en el navegador) y compártelo para poder ayudarte a diagnosticarlo.
