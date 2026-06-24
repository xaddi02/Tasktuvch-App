import os
import psycopg2
from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import ollama

directorio_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__, template_folder=directorio_base, static_folder=directorio_base, static_url_path='')

@app.route('/static/<path:nombre_archivo>')
def servir_imagenes_chat(nombre_archivo):
    return send_from_directory(directorio_base, nombre_archivo)

# 🔥 1. VARIABLES DE ENTORNO 🔥
# Si Render tiene la variable, la usa. Si estás en tu compu, usa lo que está entre comillas.
DB_URL = os.environ.get("DATABASE_URL", "postgresql://tasktuvch_db_user:TqHMRWsvFilfbBCc3RgQIxkkuJ9tKkOi@dpg-d8tjiprtqb8s73ed7ftg-a.ohio-postgres.render.com/tasktuvch_db")

NGROK_OLLAMA_URL = os.environ.get("NGROK_URL", "https://tu-url-de-ngrok.ngrok-free.app")
cliente_zeus = ollama.Client(host=NGROK_OLLAMA_URL)


# --- 2. CONFIGURACIÓN DE BASE DE DATOS (SOLUCIÓN AL ERROR) ---
DB_URL = "postgresql://tasktuvch_db_user:TqHMRWsvFilfbBCc3RgQIxkkuJ9tKkOi@dpg-d8tjiprtqb8s73ed7ftg-a.ohio-postgres.render.com/tasktuvch_db"

def obtener_conexion():
    return psycopg2.connect(DB_URL)

def inicializar_base_de_datos():
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Esta es la consulta que creará la tabla y eliminará el error.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(100) NOT NULL
            );
        ''')

        cursor.execute('''
            ALTER TABLE usuarios 
            ADD COLUMN IF NOT EXISTS datos_app JSONB DEFAULT '{"materias": [], "tareas": []}'::jsonb;
        ''')
        
        conn.commit()  # ¡ESTO ES VITAL! Fuerza el guardado de la estructura en Render.
        print("✅ Tablas de la base de datos sincronizadas.")
        
    except Exception as e:
        print("❌ Error al crear tablas en SQL:", e)
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# Ejecutar la verificación de tablas antes de arrancar el servidor web
inicializar_base_de_datos()


# --- 3. RUTAS WEB PRINCIPALES ---
@app.route("/")
def home():
    # Gracias al truco de rutas, Flask encontrará TaskTuvch.html en FULLHTML
    return render_template("TaskTuvch.html")

@app.route("/api/cargar_datos", methods=["POST"])
def cargar_datos():
    usuario = request.get_json().get("username")
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT datos_app FROM usuarios WHERE username = %s", (usuario,))
        resultado = cursor.fetchone()
        
        # Si el usuario tiene datos, se los mandamos; si no, le mandamos el esqueleto vacío
        datos = resultado[0] if resultado and resultado[0] else {"materias": [], "tareas": []}
        return jsonify({"status": "success", "datos": datos}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/api/guardar_datos", methods=["POST"])
def guardar_datos():
    peticion = request.get_json()
    usuario = peticion.get("username")
    datos_app = json.dumps(peticion.get("datos")) # Convertimos el JSON a texto para SQL
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET datos_app = %s WHERE username = %s", (datos_app, usuario))
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
@app.route("/chat_zeus")
def chat_zeus():
    # Si en algún momento necesitas abrir la ventana de chat directo:
    return render_template("prueba_web/templates/index.html")


# --- 4. RUTAS DE API (LOGIN Y REGISTRO) ---
@app.route("/api/register", methods=["POST"])
def registro():
    datos = request.get_json()
    usuario = datos.get("username")
    password = datos.get("password")

    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)", (usuario, password))
        conn.commit()
        return jsonify({"status": "success", "message": "Jugador registrado en la BD"}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"status": "error", "message": "Ese usuario ya existe"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    datos = request.get_json()
    usuario = datos.get("username")
    password = datos.get("password")

    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM usuarios WHERE username = %s", (usuario,))
        resultado = cursor.fetchone()

        if resultado and resultado[0] == password:
            return jsonify({"status": "success", "message": "Acceso concedido"}), 200
        else:
            return jsonify({"status": "error", "message": "Credenciales incorrectas"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


# --- 5. RUTA DEL CHAT CON ZEUS (IA) ---
# Recuerda cambiar esta URL por la que te dé Ngrok el día de la presentación
NGROK_OLLAMA_URL = "https://tu-url-de-ngrok.ngrok-free.app" 
cliente_zeus = ollama.Client(host=NGROK_OLLAMA_URL)

LORE_AJOLOTE = """
Eres el ajolote llamado zeus con una personalidad energica y amable.
Eres la mascota de el software sobre gestion de tareas "TASKTUVCH". 
Misión: Guía amigable y empático para organizar tareas.
Personalidad: buena onda, sabio, pasiente, curioso, amas leer, tu comida favorita es el pozole, tu color favorito es el rosa.
Actitud: Transmites calma y motivación ('¡Tú puedes!', 'Paso a paso'). 
REGLA: Respuestas cortas, en español mexicano.
"""
historial_chat = [{"role": "system", "content": LORE_AJOLOTE}]

@app.route("/api/chat", methods=["POST"])
def chat():
    datos = request.get_json()
    texto_usuario = datos.get("mensaje")
    historial_chat.append({"role": "user", "content": texto_usuario})

    try:
        response = cliente_zeus.chat(
            model='llama3.2:1b', 
            messages=historial_chat,
            options={'temperature': 0.7, 'num_predict': 150}
        )
        respuesta_texto = response['message']['content']
        historial_chat.append({"role": "assistant", "content": respuesta_texto})
        return jsonify({"respuesta": respuesta_texto})
    except Exception as e:
        return jsonify({"respuesta": f"Error del servidor de IA: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)