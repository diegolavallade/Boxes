import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs
import cgi
from pywebpush import webpush, WebPushException
from datetime import datetime

PORT = 80
PUBLIC_DIR = "Z:/public"
CHAT_FILE = "chat.json"
LOG_FILE = "logs.json"
FILES_METADATA = "files.json"
USERS_FILE = "users.json"

# Aseguramos la existencia de directorios y archivos necesarios
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)

for filename in [CHAT_FILE, LOG_FILE, FILES_METADATA, USERS_FILE]:
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            if filename == FILES_METADATA:
                json.dump([], f)
            elif filename == USERS_FILE:
                json.dump({}, f)
            else:
                json.dump([], f)

# Configura tus claves VAPID (genera estas claves previamente)
VAPID_PUBLIC_KEY = "TU_CLAVE_PUBLICA"
VAPID_PRIVATE_KEY = "TU_CLAVE_PRIVADA"

def send_push_notification(subscription_info, data):
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(data),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": "mailto:tu_email@example.com"}
        )
    except WebPushException as ex:
        print("Error enviando notificación push:", repr(ex))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/":
            self.path = "/index.html"
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        elif parsed_path.path == "/files":
            # Devuelve la metadata de los archivos en formato JSON
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            with open(FILES_METADATA, "r") as f:
                files_metadata = json.load(f)
            self.wfile.write(json.dumps(files_metadata).encode())
        elif parsed_path.path == "/download":
            # Permite descargar un archivo a través de su nombre
            qs = parse_qs(parsed_path.query)
            if "file" in qs:
                filename = qs["file"][0]
                filepath = os.path.join(PUBLIC_DIR, filename)
                if os.path.exists(filepath):
                    self.send_response(200)
                    self.send_header("Content-Disposition", f"attachment; filename={filename}")
                    self.send_header("Content-type", "application/octet-stream")
                    self.end_headers()
                    with open(filepath, "rb") as f:
                        self.wfile.write(f.read())
                    self.log_event(f"Archivo descargado: {filename} por IP: {self.client_address[0]}")
                else:
                    self.send_error(404, "Archivo no encontrado")
            else:
                self.send_error(400, "Parámetro 'file' faltante")
        elif parsed_path.path == "/chat":
            # Devuelve los mensajes del chat en formato JSON
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            with open(CHAT_FILE, "r") as f:
                messages = json.load(f)
            self.wfile.write(json.dumps(messages).encode())
        elif parsed_path.path == "/vapidPublicKey":
            # Endpoint para obtener la clave pública VAPID
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(VAPID_PUBLIC_KEY.encode())
        elif parsed_path.path == "/userinfo":
            client_ip = self.client_address[0]
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
            # Si el usuario no existe, se retorna un usuario por defecto
            user_info = users.get(client_ip, {
                "username": "Anonimo",
                "subscription": None,
                "notifications": False
            })
            # Agregamos la IP del cliente a la respuesta
            user_info["client_ip"] = client_ip
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(user_info).encode())
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/upload":
            # Procesar la subida de archivo preservando el nombre original
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'})
            if "file" not in form:
                self.send_error(400, "Campo 'file' no encontrado")
                return
            file_field = form['file']
            original_filename = file_field.filename
            if not original_filename:
                self.send_error(400, "Nombre de archivo no encontrado")
                return
            file_data = file_field.file.read()
            filepath = os.path.join(PUBLIC_DIR, original_filename)
            with open(filepath, "wb") as f:
                f.write(file_data)
            # Se obtienen los campos alias y nota
            alias = form.getvalue("alias", "")
            nota = form.getvalue("nota", "")
            # Extraer la extensión del archivo
            _, ext = os.path.splitext(original_filename)
            extension = ext.lower().strip('.')
            # Almacenar la metadata en files.json, incluyendo la extensión
            with open(FILES_METADATA, "r") as f:
                file_metadata = json.load(f)
            file_metadata.append({
                "filename": original_filename,
                "alias": alias,
                "nota": nota,
                "extension": extension,
                "uploader_ip": self.client_address[0]
            })
            with open(FILES_METADATA, "w") as f:
                json.dump(file_metadata, f)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Archivo subido correctamente")
            self.log_event(f"Archivo subido: {original_filename} por {alias}")
            
            # Enviar notificación a usuarios con notificaciones habilitadas
            notification_data = {
                "title": "Nuevo Archivo Subido",
                "body": f"Archivo {original_filename} subido por {alias}"
            }
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
            for ip, user_data in users.items():
                if user_data.get("notifications") and user_data.get("subscription"):
                    send_push_notification(user_data["subscription"], notification_data)

        elif parsed_path.path == "/deleteFile":
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            filename = data.get("filename")
            if not filename:
                self.send_error(400, "Falta campo 'filename'")
                return
            with open(FILES_METADATA, "r") as f:
                files_metadata = json.load(f)
            file_entry = next((f for f in files_metadata if f["filename"] == filename), None)
            if not file_entry:
                self.send_error(404, "Archivo no encontrado")
                return
            client_ip = self.client_address[0]
            if file_entry.get("uploader_ip") != client_ip:
                self.send_error(403, "No autorizado para borrar este archivo")
                return
            # Eliminar el archivo físico
            filepath = os.path.join(PUBLIC_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            # Actualizar la metadata eliminando el registro
            files_metadata = [f for f in files_metadata if f["filename"] != filename]
            with open(FILES_METADATA, "w") as f:
                json.dump(files_metadata, f)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Archivo borrado correctamente")
            self.log_event(f"Archivo borrado: {filename} por IP: {client_ip}")

        elif parsed_path.path == "/chat":
            # Procesar un mensaje del chat
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            try:
                message = json.loads(post_data.decode())
                if "message" not in message:
                    self.send_error(400, "Formato de mensaje invalido, falta 'message'")
                    return
                # Obtener el nombre de usuario asociado a la IP
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
                client_ip = self.client_address[0]
                username = users.get(client_ip, {}).get("username", "Anonimo")
                message["user"] = username
                message["timestamp"] = datetime.now().isoformat()
                with open(CHAT_FILE, "r") as f:
                    chat = json.load(f)
                chat.append(message)
                with open(CHAT_FILE, "w") as f:
                    json.dump(chat, f)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Mensaje agregado")
                self.log_event(f"Mensaje de chat de {username}")
                
                # Enviar notificación de chat a usuarios habilitados
                notification_data = {
                    "title": "Nuevo Mensaje en el Chat",
                    "body": f"{username}: {message['message']}"
                }
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
                for ip, user_data in users.items():
                    if user_data.get("notifications") and user_data.get("subscription"):
                        send_push_notification(user_data["subscription"], notification_data)
            except Exception as e:
                self.send_error(400, f"Error al procesar JSON: {e}")

        elif parsed_path.path == "/setusername":
            # Actualizar el nombre de usuario del cliente
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode())
                if "username" not in data:
                    self.send_error(400, "Falta campo 'username'")
                    return
                username = data["username"]
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
                client_ip = self.client_address[0]
                if client_ip in users:
                    users[client_ip]['username'] = username
                else:
                    users[client_ip] = {
                        "username": username,
                        "subscription": None,
                        "notifications": True
                    }
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Nombre de usuario actualizado")
                self.log_event(f"Nombre de usuario actualizado a: {username} para IP: {self.client_address[0]}")
            except Exception as e:
                self.send_error(400, f"Error al procesar JSON: {e}")

        elif parsed_path.path == "/subscribe":
            # Registrar la suscripción del cliente para notificaciones push
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            try:
                subscription = json.loads(post_data.decode())
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
                client_ip = self.client_address[0]
                if client_ip in users:
                    users[client_ip]['subscription'] = subscription
                    users[client_ip]['notifications'] = True
                else:
                    users[client_ip] = {
                        "username": "Anonimo",
                        "subscription": subscription,
                        "notifications": True
                    }
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Suscripcion guardada")
                self.log_event(f"Suscripción guardada para IP: {self.client_address[0]}")
            except Exception as e:
                self.send_error(400, f"Error procesando la suscripcion: {e}")

        elif parsed_path.path == "/updateNotifications":
            # Actualizar la preferencia de notificaciones del usuario
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode())
                if "notifications" not in data:
                    self.send_error(400, "Falta campo 'notifications'")
                    return
                notifications = bool(data["notifications"])
                with open(USERS_FILE, "r") as f:
                    users = json.load(f)
                client_ip = self.client_address[0]
                if client_ip in users:
                    users[client_ip]["notifications"] = notifications
                else:
                    users[client_ip] = {
                        "username": "Anonimo",
                        "subscription": None,
                        "notifications": notifications
                    }
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Preferencia de notificaciones actualizada")
                self.log_event(f"Preferencia de notificaciones actualizada a {notifications} para IP: {self.client_address[0]}")
            except Exception as e:
                self.send_error(400, f"Error actualizando notificaciones: {e}")

        elif parsed_path.path == "/updateView":
            content_length = int(self.headers.get('Content-Length'))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            view = data.get("view")
            if view not in ["grid", "list"]:
                self.send_error(400, "Valor de vista inválido")
                return
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
            client_ip = self.client_address[0]
            if client_ip in users:
                users[client_ip]["view"] = view
            else:
                users[client_ip] = {"username": "Anonimo", "subscription": None, "notifications": True, "view": view}
            with open(USERS_FILE, "w") as f:
                json.dump(users, f)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Preferencia de vista actualizada")
            self.log_event(f"Cambio de vista a {view} para IP: {client_ip}")

        else:
            self.send_error(404, "Endpoint no encontrado")

    def log_event(self, event):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        logs.append(event)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f)

Handler = MyHandler
with socketserver.TCPServer(("192.168.100.252", PORT), Handler) as httpd:
    print("Servidor corriendo en el puerto", PORT)
    httpd.serve_forever()
