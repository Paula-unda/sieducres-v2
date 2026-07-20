# Cómo probar la app Flet (SIEDUCRES móvil) en tu PC

## Requisito previo
El backend (`uvicorn main:app --reload`) debe estar corriendo en la otra
terminal, tal como lo dejaste antes. La app Flet necesita que el backend
esté encendido para poder iniciar sesión o registrarse.

## 1. Abrir una terminal nueva (deja la del backend corriendo aparte)
En VS Code: ícono "+" en el panel de terminal, o `Ctrl+Shift+ñ` (según tu teclado).

## 2. Ir a la carpeta de la app y activar el mismo entorno virtual
Como `app/` está al mismo nivel que `backend/` dentro de `sieducres-v2/`,
puedes reutilizar el mismo `venv` que ya creaste:

```
cd sieducres-v2\app
..\venv\Scripts\activate
```

## 3. Instalar las dependencias de la app
```
pip install -r requirements.txt
```

## 4. Levantar la app
```
flet run main.py
```

Esto debe abrir una ventana de escritorio (Flet simula la app móvil en
una ventana mientras se prueba en la PC) mostrando la pantalla de login
de SIEDUCRES.

## Prueba completa de extremo a extremo
1. En la pantalla de login, click en "Crear una cuenta nueva"
2. Registra un usuario de prueba (por ejemplo rol "Docente", cualquier escuela)
3. Debería devolverte al login automáticamente
4. Inicia sesión con ese usuario nuevo
5. Deberías ver la pantalla "Bienvenido/a, [tu nombre]" con tu rol y correo

También puedes iniciar sesión directo con el Admin:
- Correo: `admin@sieducres.edu.ve`
- Contraseña: `A2026siudecres+`

## Si algo falla
- Si dice que no se puede conectar al servidor: confirma que la terminal
  del backend siga corriendo y mostrando `Uvicorn running on http://127.0.0.1:8000`
- Copia el error exacto de la terminal de la app (no solo lo que se ve en pantalla)
