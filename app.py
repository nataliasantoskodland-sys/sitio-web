#from flask import Flask, render_template
# from flask import request  Importamos request para manejar datos del formulario
# Necesitamos 'redirect' y 'url_for' para navegar entre páginas después de guardar/borrar
#from flask import Flask, render_template, request, redirect, url_for, jsonify

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify 
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash 

#clase 7
import os
import qrcode
from twilio.rest import Client

#clase 9 modifique otras cosas masabajo secret key y base de datos y agregue la parte de autenticacion twilio
from dotenv import load_dotenv
load_dotenv()  # Carga las variables de entorno desde el archivo .env


app = Flask(__name__)


 
# Guardamos hash_clave en la DB clase 9
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')




#clase 7
# 1. CREDENCIALES DE TWILIO (Sustituir con datos de la consola Twilio)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER') # Número por defecto del Sandbox
# Inicializamos cliente
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)






#clase 7
@app.route('/')
def main():
    return render_template('reserva.html')
@app.route('/reservar', methods=['POST'])
def reservar():
    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono') # Debe incluir prefijo internacional (ej. +573001234567)
    servicio = request.form.get('servicio')

    if not nombre or not telefono or not servicio:
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('index'))

    # Generamos código de ticket ficticio
    ticket_id = "TKT-2026-99"

    # --- PASO 2: GENERACIÓN DE CÓDIGO QR ---
    try:
        qr_data = f"Ticket: {ticket_id} | Cliente: {nombre} | Servicio: {servicio}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Generar imagen usando Pillow
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ruta donde se almacenará de manera pública
        ruta_qr = f"static/qrs/{ticket_id}.png"
        
        # Aseguramos que la carpeta exista
        os.makedirs("static/qrs", exist_ok=True)
        img.save(ruta_qr)
    except Exception as e:
        print(f"Error generando QR: {e}")
        flash("Error interno al procesar el código QR", "error")
        return redirect(url_for('index'))

    # --- PASO 3: ENVÍO ASÍNCRONO DE WHATSAPP ---
    try:
        mensaje_texto = f"¡Hola {nombre}! 🌿 Tu reserva para el servicio de '{servicio}' ha sido procesada con éxito.\n\n🎟️ Código de Ticket: {ticket_id}\n\nMuestra el QR adjunto al momento de tu cita."
        
        # Opcional: Twilio Sandbox permite enviar URLs públicas de imágenes en sus mensajes.
        # Si usas Render/Railway, puedes colocar la URL pública aquí.
        
        mensaje = twilio_client.messages.create(
            body=mensaje_texto,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{telefono}"
        )
        print(f"Mensaje despachado con SID: {mensaje.sid}")
        flash("¡Felicidades! Reserva confirmada. Te hemos enviado un mensaje a tu WhatsApp.", "success")
    except Exception as e:
        print(f"Error de envío API: {e}")
        flash("Reserva exitosa localmente, pero ocurrió un problema al contactar la API de WhatsApp.", "warning")

    return redirect(url_for('index'))
    








# 2. CONFIGURACIÓN DE LA BASE DE DATOS
# 'sqlite:///catalogo.db' creará un archivo real en la carpeta de tu proyecto.
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializamos la herramienta de Base de Datos
db = SQLAlchemy(app)



# --- MODELO DE USUARIO --- 
class Usuario(db.Model): 
    id = db.Column(db.Integer, primary_key=True) 
    username = db.Column(db.String(50), unique=True, nullable=False) 
    # Nunca guardamos la clave real, guardamos el HASH 
    password_hash = db.Column(db.String(255), nullable=False) 
 
with app.app_context(): 
    db.create_all() 
 
# --- RUTAS DE AUTENTICACIÓN --- 
 
@app.route('/registro', methods=['GET', 'POST']) 
def registro(): 
    if request.method == 'POST': 
        usuario = request.form.get('username') 
        clave = request.form.get('password') 
         
        # Encriptamos la contraseña con scrypt 
        hash_seguro = generate_password_hash(clave, method='scrypt') 
         
        nuevo_usuario = Usuario(username=usuario, password_hash=hash_seguro) 
        try: 
            db.session.add(nuevo_usuario) 
            db.session.commit() 
            flash("Registro exitoso. Ahora puedes iniciar sesión.", "success") 
            return redirect(url_for('login')) 
        except: 
            flash("Ese nombre de usuario ya existe.", "error") 
             
    return render_template('registro.html') 
 
@app.route('/login', methods=['GET', 'POST']) 
def login(): 
    if request.method == 'POST': 
        username = request.form.get('username') 
        password = request.form.get('password') 
         
        user = Usuario.query.filter_by(username=username).first() 
         
        # Verificamos si el usuario existe Y si el hash coincide 
        if user and check_password_hash(user.password_hash, password): 
            # CREACIÓN DE LA SESIÓN (Recordar al usuario) 
            session['user_id'] = user.id 
            session['username'] = user.username 
            return redirect(url_for('dashboard')) 
        else: 
            # Mensaje genérico por seguridad 
            flash("Credenciales inválidas. Inténtalo de nuevo.", "error") 
             
    return render_template('login.html') 
 
# --- RUTA PROTEGIDA (DASHBOARD) --- 
@app.route('/dashboard') 
def dashboard(): 
    # Verificamos si existe la sesión 
    if 'user_id' not in session: 
        flash("Debes iniciar sesión para acceder.", "warning") 
        return redirect(url_for('login')) 
         
    return render_template('dashboard.html', nombre=session['username']) 
 
@app.route('/logout') 
def logout(): 
    # Limpiamos la "mochila" del servidor 
    session.clear() 
    flash("Has cerrado sesión correctamente.", "info") 
    return redirect(url_for('login'))






# 3. MODELO DE DATOS (La estructura de nuestra tabla)
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Identificador único
    nombre = db.Column(db.String(100), nullable=False) # Texto de hasta 100 caracteres
    precio = db.Column(db.Float, nullable=False) # Números con decimales
    categoria = db.Column(db.String(50), nullable=True) # Categoría opcional

    def to_dict(self):
        """Convierte el objeto a un diccionario para poder enviarlo como JSON"""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": self.precio,
            "categoria": self.categoria
        }


# 4. CREACIÓN AUTOMÁTICA DE LA BASE DE DATOS
# Este bloque revisa si el archivo .db existe, si no, lo crea basado en el modelo arriba.
with app.app_context():
    db.create_all()



@app.route('/api/buscar')
def buscar_productos():
    """
    Esta es la ruta que usará JavaScript. 
    Busca en la base de datos real sin recargar la página.
    """
    query_text = request.args.get('q', '').lower()
    
    if not query_text:
        return jsonify([])

    # Buscamos en la base de datos (SQLAlchemy)
    # Filtramos donde el nombre contenga el texto buscado
    resultados = Producto.query.filter(Producto.nombre.ilike(f'%{query_text}%')).all()
    
    # Convertimos los resultados a una lista de diccionarios
    return jsonify([p.to_dict() for p in resultados])



# --- RUTAS DE LA APLICACIÓN (CRUD) ---

# [R] READ: Listar productos
@app.route('/')
def index():
    # Consultamos TODOS los registros de la tabla Producto
    productos_db = Producto.query.all()
    return render_template('index.html', productos=productos_db)

# [C] CREATE: Agregar un nuevo producto
@app.route('/agregar', methods=['POST'])
def agregar_producto():
    # Recibimos los datos del formulario (visto en Clase 3)
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')

    if nombre and precio:
        # Creamos el objeto basado en el Modelo
        nuevo_producto = Producto(nombre=nombre, precio=float(precio))
        
        # Guardamos en la sesión y confirmamos (commit)
        db.session.add(nuevo_producto)
        db.session.commit()
    
    # Redireccionamos al inicio para ver el nuevo producto en la lista
    return redirect(url_for('index'))

# [D] DELETE: Borrar un producto por su ID
# Usamos una variable en la URL <int:id> para saber exactamente qué borrar
@app.route('/borrar/<int:id>')
def eliminar_producto(id):
    # Buscamos el producto por su ID único
    producto = Producto.query.get(id)
    
    if producto:
        db.session.delete(producto)
        db.session.commit()
        
    return redirect(url_for('index'))

# [U] UPDATE: Editar un producto (Lógica básica)
@app.route('/editar/<int:id>', methods=['POST'])
def editar_producto(id):
    producto = Producto.query.get(id)
    
    if producto:
        producto.nombre = request.form.get('nombre')
        producto.precio = float(request.form.get('precio'))
        db.session.commit()
        
    return redirect(url_for('index'))






# --- RUTAS ---

@app.route('/')
def home():
    # Pasamos una variable 'titulo' para que base.html la use en la pestaña del navegador
    return render_template('index.html', titulo="Inicio")

@app.route('/servicios')
def servicios():
    # Simulamos datos que vendrían de una base de datos
    datos_servicios = [
        {"nombre": "Corte de Cabello", "precio": 25, "disponible": True},
        {"nombre": "Barba Premium", "precio": 15, "disponible": True},
        {"nombre": "Tinte Pro", "precio": 40, "disponible": False},
        {"nombre": "Masaje Facial", "precio": 20, "disponible": True}
    ]
    return render_template('servicios.html', 
                           titulo="Servicios", 
                           servicios=datos_servicios)


  # --- RUTA DE CONTACTO ---
# Importante: Debemos permitir explícitamente el método POST para recibir datos.
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    # Variables para controlar los mensajes en la interfaz
    mensaje_error = None
    mensaje_exito = None

    # Verificamos si el usuario envió el formulario (POST)
    if request.method == 'POST':
        # 1. RECOLECCIÓN DE DATOS
        # Usamos .get() para evitar errores si el campo no existe
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        mensaje = request.form.get('mensaje')

        # 2. VALIDACIONES DE SEGURIDAD (Lógica de Negocio)
        
        # Validación: Campos vacíos
        if not nombre or not email or not telefono:
            mensaje_error = "⚠️ Los campos Nombre, Email y Teléfono son obligatorios."
        
        # Validación: Formato de Email básico
        elif "@" not in email or "." not in email:
            mensaje_error = "📧 El formato del correo electrónico no es válido."
        
        # Validación: Teléfono (solo números y longitud mínima)
        elif not telefono.isdigit() or len(telefono) < 7:
            mensaje_error = "📞 Por favor, ingresa un número de teléfono válido (solo números)."
        
        # 3. PROCESAMIENTO EXITOSO
        else:
            # Aquí es donde más adelante guardaremos en Base de Datos
            mensaje_exito = f"✅ ¡Perfecto {nombre}! Hemos recibido tu información."
            print(f"DEBUG: Datos recibidos -> {nombre}, {email}, {telefono}")

    # Renderizamos la plantilla pasando los mensajes (si existen)
    return render_template('contacto.html', 
                           titulo="Registro de Contacto", 
                           error=mensaje_error, 
                           exito=mensaje_exito)


if __name__ == '__main__':
    app.run(debug=True)
