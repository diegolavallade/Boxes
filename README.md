# Documentación Técnica - Box's

## Descripción del Proyecto
**Box's** es una aplicación web que permite compartir archivos y chatear en tiempo real con un equipo. La aplicación utiliza un servidor Python basado en `http.server` y una interfaz de usuario desarrollada con TailwindCSS y FontAwesome.

## Características Principales
- **Gestor de archivos**: Subida y descarga de archivos con metadatos.
- **Chat en tiempo real**: Comunicación entre usuarios con almacenamiento de mensajes.
- **Notificaciones Push**: Sistema de suscripción basado en Web Push API.
- **Interfaz moderna**: Uso de TailwindCSS para una apariencia atractiva.
- **Configuraciones de usuario**: Cambio de nombre y preferencias de vista.

---

## Instalación y Configuración

### Requisitos
- Python 3.x
- Dependencias del servidor:
  ```sh
  pip install pywebpush
  ```

### Configuración de VAPID Keys
Para las notificaciones push, debes generar claves VAPID y configurarlas en `server.py`:
```python
VAPID_PUBLIC_KEY = "TU_CLAVE_PUBLICA"
VAPID_PRIVATE_KEY = "TU_CLAVE_PRIVADA"
```
Puedes generar estas claves con:
```sh
python -m pywebpush.generate
```

---

## Estructura del Proyecto
```
📂 Box's
├── 📄 index.html        # Interfaz web de la aplicación
├── 📄 server.py         # Servidor HTTP en Python
├── 📁 public/           # Directorio donde se almacenan los archivos subidos
├── 📄 chat.json         # Base de datos de mensajes del chat
├── 📄 files.json        # Metadatos de archivos subidos
├── 📄 users.json        # Información de usuarios y preferencias
├── 📄 logs.json         # Registro de eventos del servidor
```

---

## Uso

### Iniciar el Servidor
Ejecuta el servidor con:
```sh
python server.py
```
Esto levantará la aplicación en el puerto 80.

### Acceder a la Aplicación
Abre un navegador y accede a:
```
http://localhost
```

---

## Endpoints
### **GET**
| Ruta             | Descripción |
|-----------------|-------------|
| `/`             | Página principal (index.html) |
| `/files`        | Lista los archivos subidos |
| `/download?file=nombre` | Descarga un archivo |
| `/chat`         | Obtiene los mensajes del chat |
| `/userinfo`     | Obtiene información del usuario |

### **POST**
| Ruta             | Descripción |
|-----------------|-------------|
| `/upload`       | Sube un archivo |
| `/deleteFile`   | Elimina un archivo subido |
| `/chat`         | Envía un mensaje al chat |
| `/setusername`  | Cambia el nombre del usuario |
| `/subscribe`    | Registra la suscripción de notificaciones |
| `/updateNotifications` | Activa o desactiva las notificaciones push |
| `/updateView`   | Cambia la preferencia de vista (lista/cuadrícula) |

---

## Seguridad
- El sistema asocia cada usuario con su dirección IP.
- Sólo el usuario que sube un archivo puede eliminarlo.
- Se recomienda utilizar HTTPS para proteger la transmisión de datos.

---

## Créditos
Desarrollado por **Diego Lavallade** para **CaféFusión** - 2025. Todos los derechos reservados.

---

## Licencia
Este proyecto se distribuye bajo la licencia MIT.
