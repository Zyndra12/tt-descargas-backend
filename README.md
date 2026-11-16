# TT Descargas Backend - Microservicio en Python (FastAPI + yt-dlp)

Servidor de alta disponibilidad diseñado para extraer videos de TikTok sin marca de agua de forma gratuita y sin límites.

## 🚀 Despliegue Gratis en la Nube (Render, Railway, Fly.io)

### Opción A: Despliegue en Render.com (Gratis)
1. Crea un repositorio en GitHub y sube la carpeta `backend/`.
2. Entra a [Render.com](https://render.com) y crea un nuevo **Web Service**.
3. Conecta tu repositorio.
4. Render detectará automáticamente el `Dockerfile` o selecciona el entorno Python 3.
5. Comando de inicio: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. ¡Copia la URL pública generada (ej: `https://tt-backend.onrender.com`) y pégala en los ajustes de la App Android!

### Opción B: Ejecución Local en tu Computadora (Desarrollo)
```bash
cd backend
pip install -r requirements.txt
python main.py
```
El servidor estará corriendo en `http://localhost:8080` (o `http://10.0.2.2:8080` desde el emulador de Android).
