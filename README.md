# Sistema ERP - Guía de Despliegue y Desarrollo

Este proyecto está dividido en un Backend (Django) y un Frontend (React + Vite).

## 🚀 Desarrollo Local

### Backend (Django)
1.  **Entorno Virtual**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
2.  **Dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configuración**:
    -   Copia `.env.example` a `.env` y ajusta las variables.
4.  **Ejecución**:
    ```bash
    python manage.py runserver --settings=config.settings.local
    ```

### Frontend (React + Vite)
1.  **Instalación**:
    ```bash
    npm install
    ```
2.  **Configuración**:
    -   Copia `.env.example` a `.env` y ajusta `VITE_API_URL`.
3.  **Ejecución**:
    ```bash
    npm run dev
    ```

---

## ☁️ Despliegue en Producción

### Backend (Render)
1.  **Tipo de Servicio**: Web Service.
2.  **Runtime**: Python 3.
3.  **Build Command**: `./build.sh` (Asegúrate de que tenga permisos: `chmod +x build.sh`).
4.  **Start Command**: `gunicorn config.wsgi:application`
5.  **Variables de Entorno**:
    -   `DEBUG`: `False`
    -   `SECRET_KEY`: Una clave aleatoria segura.
    -   `DJANGO_SETTINGS_MODULE`: `config.settings.production`
    -   `DATABASE_URL`: Tu URL de PostgreSQL.
    -   `ALLOWED_HOSTS`: `tu-app.onrender.com`
    -   `CORS_ALLOWED_ORIGINS`: `https://tu-frontend.vercel.app`

### Frontend (Vercel)
1.  **Build Command**: `npm run build`
2.  **Output Directory**: `dist`
3.  **Variables de Entorno**:
    -   `VITE_API_URL`: `https://tu-backend.onrender.com/api`

---

## 🛠️ Notas Tecnicas
-   **Static Files**: Se sirven mediante WhiteNoise en producción.
-   **Seguridad**: HSTS y Cookies Seguras habilitadas en `production.py`.
-   **CORS**: Configurado dinámicamente mediante `CORS_ALLOWED_ORIGINS`.
