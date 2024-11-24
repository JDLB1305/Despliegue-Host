from flask import Flask,redirect,url_for,render_template,request, session, flash, jsonify, g
from flask_sqlalchemy import SQLAlchemy 
import json  
from datetime import date
from datetime import timedelta, datetime
from flask_mail import Mail
from flask_mail import Message 
from werkzeug.security import generate_password_hash, check_password_hash
import re 
from functools import wraps
import itsdangerous
import os 
import time
import random
import calendar
from collections import defaultdict 
from sqlalchemy.orm import load_only
from sqlalchemy import or_
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import qrcode 
from flask import send_file
from PIL import Image, ImageDraw, ImageFont
import io
from io import BytesIO 
from sqlalchemy import BLOB
import base64
import hashlib
from sqlalchemy.orm import joinedload 
from sqlalchemy import LargeBinary, Table
from babel.dates import format_date
from math import ceil


app=Flask(__name__)
#postgresql://bdplatacero_user:Jk1DnAPh5GFugIbl0zw47N66n6WaaTJt@dpg-csk0g4lds78s7395pqgg-a.oregon-postgres.render.com/bdplatacero
#app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://bdplatacero_user:Jk1DnAPh5GFugIbl0zw47N66n6WaaTJt@dpg-csk0g4lds78s7395pqgg-a.oregon-postgres.render.com/bdplatacero"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Estabilisador12345@localhost/PlatAcero'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "tu_clave_secreta"
app.permanent_session_lifetime = timedelta(minutes=30) # La sesión expira en 30 minutos
db=SQLAlchemy(app)



# Configuración para enviar correos electrónicos 

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'plattformacero01@gmail.com' 
app.config['MAIL_DEFAULT_SENDER'] = 'plattformacero01@gmail.com'
app.config['MAIL_PASSWORD'] = 'kangmnoerusqxrba'

# Configuración del generador de tokens
s = itsdangerous.URLSafeTimedSerializer(app.secret_key)
#Cookie sameSite 
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # Asegúrate de que esté habilitado para HTTPS



mail = Mail(app)
 
global datos_clase
datos_clase = {"nombres": "", "apellidos": "", "documento": ""} 
 
 
# Diccionario que mapea IDs de profesores a sus nombres
nombres_profesores = {
    70: "Ricardo Acero",
    80: "Andrés Florez",
    90: "Mauricio Acero",
    100: "Manuel Bravo",
    110: "Juan Carlos Urbano"
}

def obtener_nombre_profesor(profesor_id):
    return nombres_profesores.get(profesor_id, "Desconocido")
 
 
# Modelo para roles
class rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

# Modelo para registro de usuarios
class registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(50), unique=True, nullable=False)
    contrasena = db.Column(db.String(2000), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)

    # Relación con roles
    rol = db.relationship('rol', backref='usuarios') 
    
    #Método para verificar contrasena 
    def verify(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)



# Modelo para personas
class persona(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False) 
    numero_doc=db.Column(db.String(12),nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    edad = db.Column(db.Integer, nullable=False)
    sexo = db.Column(db.String(10), nullable=False)
    direccion_residencia = db.Column(db.String(100), nullable=False)
    barrio = db.Column(db.String(50), nullable=False)
    numero_telefono = db.Column(db.String(15), nullable=False)
    uso_imagenes = db.Column(db.String(10))
    nivel_educativo = db.Column(db.String(50), nullable=False)
    grupo_poblacional = db.Column(db.String(50), nullable=False)

    # Campos de información de salud
    eps = db.Column(db.String(50), nullable=False)
    nombre_acudiente = db.Column(db.String(50), nullable=False)
    numero_acudiente = db.Column(db.String(15), nullable=False)
    discapacidad = db.Column(db.String(50), nullable=True)
    enfermedad_cronica = db.Column(db.String(50), nullable=True)
    hospitalizaciones = db.Column(db.String(50), nullable=True)
    tratamientos = db.Column(db.String(50), nullable=True)
    condicion_fisica = db.Column(db.String(50), nullable=True)
    talla = db.Column(db.String(10), nullable=False)
    peso = db.Column(db.Integer, nullable=False)
    clases_inscritas = db.Column(db.Integer,default=0)
    clases_pagadas = db.Column(db.Integer, default=0) 
    
    #Control de pago/asistencia 
    
    clases_pay = db.Column(db.Integer, default=0)  # Estado de pago
    clases_ava = db.Column(db.Integer, default=0)  # Estado de disponibilidad de clases
    
    #Vista como completado de clases tomadas y guardadas como asistencia por un profesor
    clases_totales = db.Column(db.Integer, default=0)  # Total de clases en el plan
    clases_restantes = db.Column(db.Integer, default=0)  # Clases restantes
    
    # Relación con usuarios
    usuario_id = db.Column(db.Integer, db.ForeignKey('registro.id'), nullable=False)
    usuario = db.relationship('registro', backref='personas') 
    
    #Parámetros propios (imagen de perfil y QR) 
    qr_person = db.Column(db.String, nullable=True)  # QR asociado a la persona
    info_qr = db.Column(LargeBinary, nullable=True)  # Información mutable referenciada por el QR


# Modelo para clases
class Clase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    duracion = db.Column(db.Integer, nullable=False)  # Duración de la clase en minutos
    hora_inicio=db.Column(db.String(10)) 
    hora_fin=db.Column(db.String(10)) 
    profesor_id = db.Column(db.Integer, db.ForeignKey('registro.id'), nullable=False)  # Relación con el profesor
    profesor = db.relationship('registro', backref='clases')  # Relación inversa
    ubicacion = db.Column(db.String(100), nullable=False)  # Ubicación de la clase
    fecha_programada = db.Column(db.String(100), nullable=False)  # Fecha y hora de la clase
    descripcion = db.Column(db.String(200), nullable=False)  # Descripción de la clase
    numero_cupos = db.Column(db.Integer, nullable=False)  # Número de cupos disponibles
    estado = db.Column(db.String(20), nullable=False, default="pendiente")  # Estado de la clase 
    lista = db.Column(db.Text)
    # Relación con personas que asisten a la clase
    asistentes = db.relationship('persona', secondary='asistencia', backref='clases_asistidas')    

# Tabla intermedia para asistencia a clases
asistencia = db.Table(
    'asistencia',
    db.Column('persona_id', db.Integer, db.ForeignKey('persona.id'), primary_key=True),
    db.Column('clase_id', db.Integer, db.ForeignKey('clase.id'), primary_key=True)
)

# Modelo para información financiera
class InformacionFinanciera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nivel_inscripcion = db.Column(db.String(50), nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)
    verificacion = db.Column(db.String(50), nullable=False)

    # Relación con personas
    persona_id = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    persona = db.relationship('persona', backref='informacion_financiera')
   
#Modelo de consignación de toma de asistencias
class AsistenciaClase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clase_id = db.Column(db.Integer, db.ForeignKey('clase.id'), nullable=False)
    persona_id = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    presente = db.Column(db.Boolean, nullable=False)

    clase = db.relationship('Clase', backref='asistencias')
    persona = db.relationship('persona', backref='asistencias_clase')
 
# Modelo para la tabla de asistencia
class AsistenciaTotal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clase.id'), nullable=False)
    asistentes = db.Column(db.Integer, nullable=False)
    ausentes = db.Column(db.Integer, nullable=False)

    # Relación con la clase
    clase = db.relationship('Clase', backref='asistencias_totales')     
     
class Descuento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    porcentaje = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(50), nullable=False)
    habilitado = db.Column(db.String(2), default="SI")

class cursos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    precio = db.Column(db.Integer, nullable=False)  # Precio principal
    precio2 = db.Column(db.String(20), nullable=True)  # Precio alternativo 1
    precio3 = db.Column(db.Integer, nullable=True)


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)
    factor1 = db.Column(db.Float, nullable=True)  # Factor adicional para otros cálculos, si necesario
    factor2 = db.Column(db.Float, nullable=True)  # Segundo factor adicional

    # Relación con el registro de usuarios
    registro_id = db.Column(db.Integer, db.ForeignKey('registro.id'), nullable=False, unique=True)
    registro = db.relationship('registro', backref='teacher_profile')



   
     
# Creación de la base de datos y tablas
with app.app_context():
    db.create_all()    
 
 
#Definición para nombres de meses
# Función para obtener el nombre del mes en español
def nombre_del_mes(mes):
    meses = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }
    return meses.get(mes, "Desconocido") 
 
 
# Diccionario de mapeo de IDs de profesores a nombres
profesores_nombres = {
    7: "Andrés Florez",
    8: "Mauricio Acero",
    9: "Profesor 3"
}
  
 
#Métodos para mostrar mensajes 

def set_message(category, message):
    session['message'] = (category, message)

def get_message():
    message = session.pop('message', None)
    return message

@app.context_processor
def inject_get_message():
    return dict(get_message=get_message)


  
#Decorador para proteger rutas
def login_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs): 
        if "user_id" not in session:
            set_message("error", "Debe iniciar sesión para acceder a esta página.")
            return redirect(url_for("login")) 
        return f(*args, **kwargs) 
    return decorador
    
    
@app.route('/',methods=['GET','POST'])
def home():
    if request.method=='POST':
        # Handle POST Request here
        return render_template('login.html')
    return render_template('login.html')

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        #obtener valor username de forma segura
        username = request.form.get("username")
        contrasena = request.form.get("password")        

        if not username: 
            
            set_message("error", "Debe ingresar un nombre de usuario") 
            
            return render_template("login.html")        
        
        # Consultar si existe el usuario
        user = registro.query.filter_by(correo=request.form["username"]).first()
        #contrasena=request.form["password"]  

 
        # Validar si el usuario existe y la contrasena coincide
        if user and check_password_hash(user.contrasena, contrasena):
            session.permanent = True # Sesión permanente en el tiempo de
            session["user_id"] = user.id 
            session["correo"] = user.correo
            
            #Redirigir según el rol existente 
            if user.rol_id== 0: 
                print("Entra como rol cero")
                #generar código de verificación para administradores
                codigo_verificacion=random.randint(100000,999999)
                session["codigo_verificacion"]=codigo_verificacion #Almacenar código en la session 
                #Enviar código por correo
                asunto="Código de verificación"
                cuerpo= f"Tu código de verificación es: {codigo_verificacion}.Este código es válido por 5 minutos"
                enviar_correo(user.correo, asunto, cuerpo)
                
                set_message("info","Código de verificación enviado por correo")
                
                return render_template("verificar_codigo.html") 
            
            elif user.rol_id==1:
                return render_template("nav_user.html") 
            
            elif user.rol_id==2: 
                
                return render_template("nav_teacher.html")

            else:
                return("Rol no especificado")
        
        flash("Credenciales Invalidas", "error")
        return render_template("login.html")
    
    return render_template("login.html")




@app.route("/go_regi")
def step_r():
    return render_template('nav_user.html')

@app.route("/go_new_user", methods=['POST'])
def step_g():
    return render_template('new.html')

@app.route("/go_class", methods=['POST','GET'])
def step_gc():
    return render_template('programar_clases.html')

@app.route("/go_ins", methods=['POST','GET'])       
def step_iu():
    lista_cursos = cursos.query.all()
    return render_template('inscripciones.html', cursos=lista_cursos)

#Inscripcion para usuarios 
@app.route("/inscripcion_clases", methods=['GET'])
def inscripcion_clases():
    # Obtiene la fecha actual en formato 'YYYY-MM-DD'
    fecha_actual = datetime.now().strftime("%Y-%m-%d")

    # Obtiene las clases ordenadas por fecha_programada
    clases_por_fecha = obtener_clases_desde_fecha(fecha_actual)

    # Renderiza la plantilla con la lista de clases
    return render_template("ver_clases_desde_hoy1.html", clases_por_fecha=clases_por_fecha)

#Forma secundaria --- agrupación por meses
# Función para obtener el nombre del mes en español
def nombre_del_mes(month):
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return meses[month - 1]

@app.route('/ver_clases_desde_hoy', methods=['GET', 'POST'])
def ver_clases_desde_hoy():
    hoy = datetime.today()
    current_month = hoy.month
    current_year = hoy.year
    
    # Calcular la fecha de mañana y la fecha límite de dos meses a partir de mañana
    tomorrow = hoy + timedelta(days=1)
    limit_date = tomorrow + timedelta(days=60)

    # Obtener el ID de la persona en sesión (esto depende de cómo manejes la autenticación)
    persona_id = session.get('persona_id')  # Ajusta esto según tu lógica de sesión

    # Filtrar las clases que no sean de "Seleccion" y estén dentro de los próximos dos meses
    clases = Clase.query.filter(
        Clase.descripcion != "Natación (Selección Kraken)",
        Clase.fecha_programada >= str(tomorrow.date()),
        Clase.fecha_programada <= str(limit_date.date())
    ).order_by(Clase.fecha_programada).all()

    # Cargar la tabla `asistencia`
    asistencia = Table('asistencia', db.metadata, autoload_with=db.engine)

    # Obtener las clases en las que la persona ya está inscrita
    clases_inscritas = db.session.query(asistencia).filter_by(persona_id=persona_id).all()

    # Extraer los IDs de las clases en las que ya está inscrita
    clases_inscritas_ids = {c.clase_id for c in clases_inscritas}

    # Filtrar las clases que aún no ha inscrito
    clases_no_inscritas = [clase for clase in clases if clase.id not in clases_inscritas_ids]

    # Agrupar las clases no inscritas por mes
    clases_por_mes = defaultdict(list)
    for clase in clases_no_inscritas:
        fecha = datetime.strptime(clase.fecha_programada, "%Y-%m-%d")
        año_mes = (fecha.year, fecha.month)
        clases_por_mes[año_mes].append(clase)

    # Obtener nombres de profesores
    profesores = registro.query.filter_by(rol_id=2).all()
    profesores_nombres = {profesor.id: f"{profesor.correo}" for profesor in profesores}

    # Pasar la función nombre_del_mes y otros datos al template
    return render_template(
        'ver_clases_desde_hoy.html',
        clases_por_mes=clases_por_mes,
        datetime=datetime,  # Para usar en la plantilla
        nombre_del_mes=nombre_del_mes,  # Para obtener el nombre del mes
        current_month=current_month,  # Para el mes actual
        current_year=current_year,  # Para el año actual
        profesores_nombres=profesores_nombres  # Para renderizar nombres de profesores desde el diccionario
    )



# Función para agrupar clases por mes
def agrupar_clases_por_mes(clases):
    clases_por_mes = defaultdict(list)

    for clase in clases:
        # Extraer el año y el mes de la fecha programada
        fecha = datetime.strptime(clase.fecha_programada, "%Y-%m-%d")
        año_mes = (fecha.year, fecha.month)

        # Añadir la clase al grupo correspondiente
        clases_por_mes[año_mes].append(clase)

    return clases_por_mes


# Función para convertir 'YYYY-MM' a 'YYYY-Mes'
def formato_fecha(mes_anio):
    year, month = map(int, mes_anio.split('-'))
    fecha = datetime(year, month, 1)
    # Formateamos con Babel para que salga en español
    return format_date(fecha, format='MMMM yyyy', locale='es_ES')



@app.route('/gestion_usuarios')
@login_requerido
def gestion_usuarios():
    if not es_admin():
        set_message("info", "Solo los administradores tienen acceso a esta funcionalidad")
        return redirect(url_for("login"))
    
    # Obtener la lista de usuarios y, si son profesores, traer sus nombres desde la tabla Teacher
    lista_usuarios = db.session.query(registro).outerjoin(persona, registro.id == persona.usuario_id).all()
    
    # Crear un diccionario para los nombres de profesores
    nombres_profesores = {}
    for user in lista_usuarios:
        if user.rol_id == 2:  # Si el usuario tiene el rol de profesor
            profesor = db.session.query(Teacher).filter_by(registro_id=user.id).first()
            if profesor:
                nombres_profesores[user.id] = f"{profesor.nombres} {profesor.apellidos}"
    
    return render_template('admin_vusers.html', lista_usuarios=lista_usuarios, nombres_profesores=nombres_profesores)



#Método para poner clases a usuarios 
@app.route('/asignar_clases/<int:user_id>', methods=['GET', 'POST'])
def asignar_clases(user_id):
    # Obtén el usuario con el id proporcionado
    usuario = registro.query.get_or_404(user_id)

    # Verifica que el rol del usuario sea 'Usuario' (rol_id == 1)
    if usuario.rol_id != 1:
        flash('Solo se pueden asignar clases a usuarios.', 'danger')
        return redirect(url_for('gestion_usuarios'))

    # Obtener todas las personas asociadas a este usuario
    personas = persona.query.filter_by(usuario_id=user_id).all()

    if request.method == 'POST':
        # Lógica para manejar la asignación de clases
        # Esta parte se puede ajustar según tus necesidades específicas
        # Por ejemplo, podrías procesar los datos del formulario aquí
        for persona_id in request.form.getlist('persona_id'):
            persona_obj = persona.query.get(persona_id)
            # Aquí puedes agregar la lógica para asignar clases a la persona
            # Por ejemplo, actualizar los datos de la persona con nuevas clases

        flash('Clases asignadas correctamente.', 'success')
        return redirect(url_for('gestion_usuarios'))

    return render_template('asignar_clases.html', usuario=usuario, personas=personas)

@app.route("/add_classuser", methods=['POST'])
def add_classuser():  
    persona_id = request.form.get('persona_id')
    num_clases = request.form.get('num_clases')

    print(f"persona_id: {persona_id}, num_clases: {num_clases}")

    if persona_id and num_clases:
        try:
            personak = persona.query.get(int(persona_id))
            num_clases = int(num_clases)
        except Exception as e:
            print(f"Error: {e}")
            flash("Error al obtener la persona o el número de clases.", "error")
            return redirect(url_for('admin_vusers'))
        
        if personak.clases_pay == 1 and personak.clases_ava == 1: 
            #El usuario ha pagado y programado clases 
            #Se le da ese número de clases, y no tendría que pagar por estas añadiduras
            personak.clases_pagadas = num_clases  # Disponibilidad para programar clases de más
            personak.clases_restantes += num_clases #para la asistencia aumenta el número de casillas
            personak.clases_ava = 0
        elif personak.clases_pay == 1 and personak.clases_ava == 0: 
            # La persona pagó un número de clases, pero no ha programado su horario aún. Se espera que esta persona tenga un número mayor de clases a las que pagó (Por x o y motivo)
            #personak.clases_inscritas += num_clases 
            personak.clases_restantes += num_clases #para la asistencia 
            personak.clases_pagadas = personak.clases_inscritas + num_clases#Para no causar conflicto entre un valor y el otro
            
        elif personak.clases_pay == 0  and personak.clases_ava == 0:
            # La persona no ha pagado ni ha programado clases, por lo que estas clases serian de "regalo", y ya estaria habilitada para programar dichas clases añadidas "sin pagar"
            #personak.clases_inscritas += num_clases 
            personak.clases_ava = 0
            personak.clases_restantes += num_clases
            personak.clases_pagadas = num_clases 
            

        db.session.commit()
        flash(f"Se han asignado {num_clases} clases a la persona con ID {persona_id}.", "success")
    else:
        flash("Faltan datos para la asignación de clases.", "error")
    
    return redirect(url_for('admin_vusers'))




def guardar_profesor(nombres, apellidos, correo, password, cargo, factor1, factor2):
    # Crear el registro en la tabla `registro`
    hashed_password = generate_password_hash(password)
    nuevo_registro = registro(correo=correo, contrasena=hashed_password, rol_id=2)
    db.session.add(nuevo_registro)
    db.session.flush()  # Hace que se cree el ID para usarlo en `Teacher`

    # Crear el registro en la tabla `Teacher` usando el id del nuevo registro
    nuevo_teacher = Teacher(
        nombres=nombres,
        apellidos=apellidos,
        cargo=cargo,
        factor1=factor1,
        factor2=factor2,
        registro_id=nuevo_registro.id
    )
    db.session.add(nuevo_teacher)
    db.session.commit()  # Guardamos ambas tablas

@app.route('/crear_profesor', methods=['GET', 'POST'])
def crear_profesor():
    if request.method == 'POST':
        # Recogemos los datos del formulario
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        correo = request.form['correo']
        password = request.form['password']
        cargo = request.form['cargo']
        factor1 = request.form['factor1']
        factor2 = request.form['factor2']

        # Llamada a la función para guardar el profesor en la base de datos
        guardar_profesor(nombres, apellidos, correo, password, cargo, factor1, factor2)

        flash('Profesor creado exitosamente', 'success')
        return redirect(url_for('admin_vusers'))

    return render_template('crear_profesor.html')



@app.route("/admin_vusers", methods=['GET'])
def admin_vusers():
    # Obtener todos los usuarios
    lista_usuarios = db.session.query(registro).join(rol).all()
    # Obtener todas las personas
    personas = db.session.query(persona).all()
    return render_template('admin_vusers.html', lista_usuarios=lista_usuarios, personas=personas)

    





#Verificación de administrador(): 
def es_admin():
    user_id = session.get("user_id")
    user = registro.query.get(user_id)
    return user and user.rol_id == 0 # id es cero (es admin)



# Función para validar contraseñas según los requisitos
def validar_contrasena(contrasena):
    # Verificar longitud mínima de 10 caracteres
    msjj=  "La contrasena debe tener al menos 10 caracteres, una letra mayúscula, un número y al menos un carácter especial (por ejemplo, !, @, #, etc.)."
    if len(contrasena) < 10:
        return msjj
    # Verificar que contenga al menos una letra mayúscula
    if not re.search(r'[A-Z]', contrasena):
        return msjj    
    # Verificar que contenga al menos un número
    if not re.search(r'\d', contrasena):
        return msjj    
    # Verificar que contenga al menos un carácter especial
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', contrasena):
        return msjj
    return None  # Si no hay errores, devolver None


def calcular_clases_mes_siguiente(persona_id):
    # Obtener el mes y el año siguiente
    hoy = date.today()
    mes_siguiente = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1).month
    anio_siguiente = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1).year

    # Filtrar las clases para la persona en el mes siguiente
    clases_siguientes = Clase.query.join(asistencia, Clase.id == asistencia.c.clase_id) \
                                   .filter(asistencia.c.persona_id == persona_id) \
                                   .filter(Clase.fecha_programada.startswith(f"{anio_siguiente}-{mes_siguiente:02d}")) \
                                   .all()




    # Contar las clases disponibles en el próximo mes (excluyendo martes)
    clases_nuevas = 0
    total_dias_mes = calendar.monthrange(anio_siguiente, mes_siguiente)[1]

    for dia in range(1, total_dias_mes + 1):
        fecha = date(anio_siguiente, mes_siguiente, dia)
        if fecha.weekday() != 1:  # Excluir los martes (weekday == 1)
            clases_nuevas += 1
    print("el numero de clases nuevas es:", clases_nuevas) 
    
    # Si ya existen clases asociadas para la persona el mes siguiente
    if clases_siguientes: 
        clases_nuevas=2.5
        print("Existen clases del mes siguiente(Ya renovado)")    
    
    return clases_nuevas  # Regresamos el número de clases para el próximo mes






@app.route("/verificar_codigo", methods=["GET","POST"])
def verificar_codigo():
    if "codigo_verificacion" not in session:
        set_message("error","El código ha exprirado o no es válido.") 
        
        return redirect(url_for("login"))
    
    
    
    if request.method == "POST":
        codigo_ingresado= int(request.form["codigo"])
        
        if codigo_ingresado == session["codigo_verificacion"]:
            #Eliminar el código de la sesión para seguridad 
            session.pop("codigo_verificacion")
            session["admin_autenticado"] = True # Marcar administradir como ingreso valido
            
            set_message("success","Inicio de sesión exitoso.") 
            return render_template("nav_admin.html")
    set_message("error","Código incorrecto. Inténtelo nuevamente.") 
    
    return render_template("verificar_codigo.html")


@app.route("/mew", methods=["POST"])
def mew():
    # Obtener los datos del formulario
    correo = request.form["correo"]
    contrasena = request.form["contrasena"] 
    confirmar_contrasena = request.form["confirmar_contrasena"]
    rol_id =  1 # Establecer el rol como False por defecto

    # Verificar si las contraseñas coinciden
    if contrasena != confirmar_contrasena:
        set_message("error","Las contraseñas no coinciden. Por favor, digitelas nuevamente") 
        
        return render_template("new.html", correo=correo)
    
    # Verificar si el correo ya está registrado en la base de datos
    existing_user = registro.query.filter_by(correo=correo).first()
    if existing_user:
        set_message("error","El correo electronico ya está registrado. Por favor, use otro")
        return render_template("new.html", correo=correo)
    
    #Validar la seguridad de la contraseña
    mensaje_error = validar_contrasena(contrasena)
    if mensaje_error:
        set_message("error", mensaje_error)
        return render_template("new.html", correo = correo)
    
    
    #Cifrar la contrasena antes de guardarla
    contrasena_hash=generate_password_hash(contrasena)
    
    # Si el correo no está registrado, crear un nuevo usuario
    new_user = registro(correo=correo, contrasena=contrasena_hash, rol_id=rol_id)
    
    # Agregar el nuevo usuario a la sesión de la base de datos
    db.session.add(new_user)
    # Confirmar los cambios en la base de datos
    db.session.commit()
    
    # Redireccionar a la página de inicio de sesión después del registro exitoso
    return redirect(url_for("login"))



def enviar_correo(destinatario, asunto, cuerpo):
    mensaje = Message(asunto, recipients=[destinatario])
    mensaje.body = cuerpo
    try:
        mail.send(mensaje)
        return True
    except Exception as e:
        print(e)
        return False


@app.route("/solicitar_restablecimiento", methods=["GET", "POST"])
def solicitar_restablecimiento():
    if request.method == "POST":
        correo = request.form.get("correo")
        
        if not correo:
            set_message("error","Por favor, ingrese un correo electrónico.")
            return render_template("solicitar_restablecimiento.html")

        # Verificar si el usuario existe
        user = registro.query.filter_by(correo=correo).first()
        if not user:
            set_message("error", "No se encontró una cuenta con ese correo electrónico.")
            return render_template("solicitar_restablecimiento.html")

        # Generar token seguro con tiempo de expiración (3600 segundos = 1 hora)
        token = s.dumps(correo, salt='restablecer-contrasena')

        # Crear enlace con el token
        enlace = url_for("restablecer_contrasena", token=token, _external=True)

        # Enviar correo electrónico con el enlace
        mensaje = Message("Restablecimiento de Contraseña", sender="plattformacero01@gmail.com", recipients=[correo])
        mensaje.body = f"Para restablecer su contraseña, haga clic en el siguiente enlace: {enlace}"
        mail.send(mensaje)

        set_message("success", "Se ha enviado un enlace para restablecer su contraseña. Por favor, revise su correo electrónico.")
        return redirect(url_for("login"))

    return render_template("solicitar_restablecimiento.html")  # Formulario para solicitar restablecimiento 



@app.route("/restablecer_contrasena/<token>", methods=["GET", "POST"])
def restablecer_contrasena(token):
    try:
        # Verificar el token (expira en 1 hora)
        correo = s.loads(token, salt='restablecer-contrasena', max_age=3600)
    except itsdangerous.SignatureExpired:
        set_message("error","El enlace para restablecer la contraseña ha expirado.")
        return redirect(url_for("solicitar_restablecimiento"))

    if request.method == "POST":
        nueva_contrasena = request.form["nueva_contrasena"]
        confirmar_contrasena = request.form["confirmar_contrasena"]

        # Verificar si las contraseñas coinciden
        if nueva_contrasena != confirmar_contrasena:
            print("Las contraseñas no coinciden. Inténtelo nuevamente.", "error")
            return render_template("restablecer_contrasena.html", token=token)

        # Verificar el usuario por correo
        user = registro.query.filter_by(correo=correo).first()
        if user:
            # Actualizar la contraseña con un hash seguro
            user.contrasena = generate_password_hash(nueva_contrasena)
            db.session.commit()

            print("La contraseña ha sido restablecida. Ahora puede iniciar sesión.", "success")
            return redirect(url_for("login"))

        print("Hubo un error al restablecer la contraseña. Inténtelo nuevamente.", "error")
        return redirect(url_for("solicitar_restablecimiento"))

    return render_template("restablecer_contrasena.html", token=token)  # Formulario para restablecer contraseña


# Ruta para el restablecimiento de contraseña por parte del administrador
@app.route("/cambiar_contrasena/<int:id>", methods=["GET", "POST"])
#@es_admin  # Asegura que solo administradores pueden acceder
def cambiar_contrasena(id):
    # Obtener el usuario por ID
    user = registro.query.get(id)
    if not user:
        set_message("error","Usuario no encontrado.")
        return redirect(url_for("gestion_usuarios"))

    if request.method == "POST":
        nueva_contrasena = request.form["nueva_contrasena"]
        confirmar_contrasena = request.form["confirmar_contrasena"]

        # Verificar si las contraseñas coinciden
        if nueva_contrasena != confirmar_contrasena:
            set_message("error","Las contraseñas no coinciden. Inténtelo nuevamente.")
            return render_template("cambiar_contrasena.html", user=user)

        # Validar la seguridad de la contraseña
        mensaje_error = validar_contrasena(nueva_contrasena)
        if mensaje_error:
            set_message("error", mensaje_error)
            return render_template("cambiar_contrasena.html", user=user)

        # Actualizar la contraseña del usuario
        user.contrasena = generate_password_hash(nueva_contrasena)
        db.session.commit()

        set_message("success","La contraseña ha sido cambiada exitosamente.") 
        
        return redirect(url_for("gestion_usuarios"))

    # Mostrar el formulario para cambiar la contraseña
    return render_template("cambiar_contrasena.html", user=user)


#Lógica para distición de fechas 
def obtener_semanas_del_mes(año, mes):
    semanas = []
    calendario = calendar.Calendar()

    # Obtener las semanas y días del mes
    semanas_del_mes = calendario.monthdatescalendar(año, mes)

    for semana in semanas_del_mes:
        dias = []
        for dia in semana:
            if dia.month == mes:
                dias.append(dia)
            else:
                dias.append(None)  # Día no perteneciente al mes actual
        semanas.append(dias)

    return semanas


@app.route('/calendario', methods=['GET'])
def calendario_actual():
    # Obtener el mes y el año actuales
    ahora = datetime.now()
    return redirect(url_for('calendario', year=ahora.year, month=ahora.month))


#Ruta que recoge el mes y semana actual y lo imprime como vista futura
@app.route('/calendario/<int:year>/<int:month>', methods=['GET', 'POST'])
def calendario(year, month):
    # Asegurarse de que el mes está dentro de los límites
    if month < 1 or month > 12:
        raise ValueError("El mes debe estar entre 1 y 12")

    # Obtener semanas del mes actual
    semanas = obtener_semanas_del_mes(year, month)

    # Obtener las fechas con clases programadas para el mes actual
    fechas_clases = db.session.query(Clase.fecha_programada).filter(
        Clase.fecha_programada.like(f"{year}-{month:02d}%")
    ).all()

    # Convertir el resultado a una lista de fechas
    fechas_clases = [item[0] for item in fechas_clases]

    # Renderizar la plantilla con las semanas y las fechas programadas
    return render_template('programar_clases.html', semanas=semanas, year=year, month=month, fechas_clases=fechas_clases)






@app.route('/programar_clase', methods=['POST'])
def programar_clase():
    # Obtener todos los campos del formulario global
    form_data = request.form

    # Crear una lista para almacenar las clases válidas
    clases_validas = []

    # Recorrer todos los días posibles para recoger información de los formularios
    for day in range(1, 32):  # Días del 1 al 31, adaptable según el mes
        # Campos para la primera clase
        fecha_1 = form_data.get(f"fecha_programada_{day}_1")
        hora_inicio_1 = form_data.get(f"hora_inicio_{day}_1")
        hora_final_1 = form_data.get(f"hora_final_{day}_1")
        ubicacion_1 = form_data.get(f"ubicacion_{day}_1")
        descripcion_1 = form_data.get(f"descripcion_{day}_1")
        numero_cupos_1 = form_data.get(f"numero_cupos_{day}_1") 
        profesor_1 = form_data.get(f"profesor_{day}_1")
        
        

        if hora_inicio_1 and hora_final_1:  # Si los campos son válidos, crear la clase 

            print(profesor_1)
            if profesor_1 == "Ricardo Acero" :
                teacher_value=70
            elif profesor_1 == "Andres Florez":
                teacher_value=80
            elif profesor_1 == "Mauricio Acero":
                teacher_value=90
            elif profesor_1 == "Manuel Bravo":
                teacher_value=100            
            elif profesor_1 == "Juan Carlos Urbano":
                teacher_value=110                        
                
            clase1 = Clase(
                duracion=60,  # Duración fija
                hora_inicio=hora_inicio_1,
                hora_fin=hora_final_1,
                profesor_id=teacher_value,  # Profesor fijo
                ubicacion=ubicacion_1,
                fecha_programada=fecha_1,
                descripcion=descripcion_1,
                numero_cupos=numero_cupos_1,
                estado="pendiente"  # Estado por defecto para nuevas clases
            )
            clases_validas.append(clase1)  # Añadir a la lista de clases válidas

        # Campos para la segunda clase
        fecha_2 = form_data.get(f"fecha_programada_{day}_2")
        hora_inicio_2 = form_data.get(f"hora_inicio_{day}_2")
        hora_final_2 = form_data.get(f"hora_final_{day}_2")
        ubicacion_2 = form_data.get(f"ubicacion_{day}_2")
        descripcion_2 = form_data.get(f"descripcion_{day}_2")
        numero_cupos_2 = form_data.get(f"numero_cupos_{day}_2") 
        profesor_2 = form_data.get(f"profesor_{day}_2") 
        
        
        if hora_inicio_2 and hora_final_2:  # Si los campos son válidos, crear la clase 

            if profesor_2 == "Ricardo Acero" :
                teacher_value2=70
            elif profesor_2 == "Andres Florez":
                teacher_value2=80
            elif profesor_2 == "Mauricio Acero":
                teacher_value2=90
            elif profesor_2 == "Manuel Bravo":
                teacher_value2=100          
            elif profesor_2 == "Juan Carlos Urbano":
                teacher_value2=110 
        
        
        

        if hora_inicio_2 and hora_final_2:  # Si los campos son válidos, crear la segunda clase
            clase2 = Clase(
                duracion=60,  # Duración fija
                hora_inicio=hora_inicio_2,
                hora_fin=hora_final_2,
                profesor_id=teacher_value2,  
                ubicacion=ubicacion_2,
                fecha_programada=fecha_2,
                descripcion=descripcion_2,
                numero_cupos=numero_cupos_2,
                estado="pendiente"  # Estado por defecto para nuevas clases
            )
            clases_validas.append(clase2)  # Añadir a la lista de clases válidas

    # Agregar todas las clases válidas a la base de datos y confirmar
    for clase in clases_validas:
        db.session.add(clase)

    db.session.commit()  # Guardar cambios en la base de datos

    # Mensaje para indicar éxito
    print("Clases programadas con éxito.", "success")

    return redirect(request.referrer)

      
@app.route('/autocompletar_clases/<int:year>/<int:month>', methods=['POST'])
def autocompletar_clases(year, month):
    # Configuración para autocompletar horarios de clases
    import calendar
    from datetime import datetime

    # Definiciones para los horarios y días de la semana
    autocompletado_config = {
        'Monday': [('20:00', '21:00'), ('21:00', '22:00')],
        'Wednesday': [('20:00', '21:00'), ('21:00', '22:00')],
        'Thursday': [('20:00', '21:00'), ('21:00', '22:00')],
        'Friday': [('20:00', '21:00'), ('21:00', '22:00')],
        'Sunday': [('09:00', '10:00'), ('10:00', '11:00')],
    }

    # Valores comunes para autocompletado
    profesor = "Andrés Florez"
    ubicacion = "Parque acuático Mosquera a4-163 Calle 10 #41, Cundinamarca"
    descripcion = "Natación (libre elección)"
    numero_cupos = 15

    # Lista para almacenar clases a crear
    autocompleted_classes = []

    # Obtener el número de días del mes
    num_days = calendar.monthrange(year, month)[1]

    # Autocompletar según el día de la semana
    for day in range(1, num_days + 1):
        date = datetime(year, month, day)
        weekday = date.strftime('%A')  # Día de la semana

        if weekday in autocompletado_config:
            horarios = autocompletado_config[weekday]

            for index, horario in enumerate(horarios, start=1):
                hora_inicio, hora_final = horario
                autocompleted_classes.append({
                    "fecha_programada": f"{year}-{month:02d}-{day:02d}",
                    "hora_inicio": hora_inicio,
                    "hora_final": hora_final,
                    "profesor": profesor,
                    "ubicacion": ubicacion,
                    "descripcion": descripcion,
                    "numero_cupos": numero_cupos,
                })

    # Aquí podrías insertar las clases en la base de datos, o realizar acciones adicionales
    for clase in autocompleted_classes:
        # Crea las clases a partir de la lista
        nueva_clase = Clase(
            duracion=60,
            hora_inicio=clase["hora_inicio"],
            hora_fin=clase["hora_final"],
            profesor_id=80,  # Andres Florez, id
            ubicacion=clase["ubicacion"],
            fecha_programada=clase["fecha_programada"],
            descripcion=clase["descripcion"],
            numero_cupos=clase["numero_cupos"],
            estado="pendiente",
        )
        db.session.add(nueva_clase)

    # Confirmar y guardar los cambios en la base de datos
    db.session.commit()

    return redirect(request.referrer)



@app.route('/autocompletar_clases_seleccion/<int:year>/<int:month>', methods=['POST'])
def autocompletar_clases_seleccion(year, month):
    # Configuración para autocompletar horarios de clases
    import calendar
    from datetime import datetime

    # Definiciones para los horarios y días de la semana
    autocompletado_config = {
        'Monday': [('20:00', '22:00')],
        'Wednesday': [('20:00', '22:00')],
        'Thursday': [('20:00', '22:00')],
        'Friday': [('20:00', '22:00')],
        'Saturday': [('20:00', '22:00')],
        'Sunday': [('09:00', '11:00')],
    }

    # Valores comunes para autocompletado
    profesor = "Andrés Florez"
    ubicacion = "Parque acuático Mosquera a4-163 Calle 10 #41, Cundinamarca"
    descripcion = "Natación (Selección Kraken)"
    numero_cupos = 30

    # Lista para almacenar clases a crear
    autocompleted_classes = []

    # Obtener el número de días del mes
    num_days = calendar.monthrange(year, month)[1]

    # Autocompletar según el día de la semana
    for day in range(1, num_days + 1):
        date = datetime(year, month, day)
        weekday = date.strftime('%A')  # Día de la semana

        if weekday in autocompletado_config:
            horarios = autocompletado_config[weekday]

            for index, horario in enumerate(horarios, start=1):
                hora_inicio, hora_final = horario
                autocompleted_classes.append({
                    "fecha_programada": f"{year}-{month:02d}-{day:02d}",
                    "hora_inicio": hora_inicio,
                    "hora_final": hora_final,
                    "profesor": profesor,
                    "ubicacion": ubicacion,
                    "descripcion": descripcion,
                    "numero_cupos": numero_cupos,
                })

    # Aquí podrías insertar las clases en la base de datos, o realizar acciones adicionales
    for clase in autocompleted_classes:
        # Crea las clases a partir de la lista
        nueva_clase = Clase(
            duracion=60,
            hora_inicio=clase["hora_inicio"],
            hora_fin=clase["hora_final"],
            profesor_id=70,  # Ricardo Acero, id
            ubicacion=clase["ubicacion"],
            fecha_programada=clase["fecha_programada"],
            descripcion=clase["descripcion"],
            numero_cupos=clase["numero_cupos"],
            estado="pendiente",
        )
        db.session.add(nueva_clase)

    # Confirmar y guardar los cambios en la base de datos
    db.session.commit()

    return redirect(request.referrer)





@app.route('/modificar_clases', methods=['GET'])
def modificar_clases():
    # Filtros recibidos desde la solicitud GET
    filtro_ano = request.args.get('filtro_ano', '')
    filtro_mes = request.args.get('filtro_mes', '')
    filtro_kraken = request.args.get('filtro_kraken', 'false') == 'true'
    filtro_otros = request.args.get('filtro_otros', 'false') == 'true'

    # Filtrar las clases según los filtros
    query = Clase.query

    # Filtrar por año
    if filtro_ano:
        query = query.filter(Clase.fecha_programada.contains(filtro_ano))

    # Filtrar por mes
    if filtro_mes:
        query = query.filter(Clase.fecha_programada.contains(f'-{filtro_mes.zfill(2)}-'))

    # Filtrar por Selección Kraken o Cursos regulares
    if filtro_kraken:
        query = query.filter(Clase.descripcion.ilike('%Selección Kraken%'))
    elif filtro_otros:
        query = query.filter(~Clase.descripcion.ilike('%Selección Kraken%'))

    # Obtener las clases filtradas
    clases = query.all()

    # Variables de filtro para pasar a la vista
    return render_template('modificar_clases.html', clases=clases, filtro_ano=filtro_ano, filtro_mes=filtro_mes, filtro_kraken=filtro_kraken, filtro_otros=filtro_otros, obtener_nombre_profesor=obtener_nombre_profesor)



@app.route('/gift', methods=['GET', 'POST'])
def gift():
    if request.method == 'POST':
        # Datos básicos
        nombres = request.form.get("nombres")
        apellidos = request.form.get("apellidos")
        edad = int(request.form.get("edad"))
        numero_telefono = request.form.get("tel")
        tipo_documento = request.form.get("tipoDocumento")
        numero_doc = request.form.get("documento")
        fecha_nacimiento = request.form.get("fechaNacimiento")
        sexo = request.form.get("sexo")
        direccion_residencia = request.form.get("direccion")
        barrio = request.form.get("barrio") 
        uso_imagenes = request.form.get("autorizo_si_no")
        nivel_educativo = request.form.get("edu")
        grupo_poblacional = request.form.get("Poblacion")

        # Información de salud
        eps = request.form.get("eps")
        nombre_acudiente = request.form.get("nombreAcu")
        numero_acudiente = request.form.get("telAcu")
        discapacidad = request.form.get("dis")

        # Información adicional de salud 
        enfermedad_cronica_si = request.form.get("enfermedadDesc")
        enfermedad_descripcion = "No"  
        if enfermedad_cronica_si != "":
            enfe = request.form.get("enfermedadDesc", "")
            if enfe.strip():
                enfermedad_descripcion = "Sí, " + enfe 

        hospitalizacion_si = request.form.get("hospitalizacionDesc")  
        hospitalizacion_descripcion = "No"
        if hospitalizacion_si != "": 
            hospi = request.form.get("hospitalizacionDesc", "") 
            if hospi.strip():
                hospitalizacion_descripcion = "Sí, " + hospi

        tratamientos_radio = request.form.get("tratamientosRadio")
        tratamientos_desc = request.form.get("tratamientosDesc") if tratamientos_radio == "Si" else "No"
        tratamientos = tratamientos_radio if tratamientos_radio == "No" else f"Sí, {tratamientos_desc}"
        condicion_fisica = request.form.get("radio_condicion")
        talla = float(request.form.get("talla"))
        peso = int(request.form.get("peso"))

        # Comprueba si el 'user_id' está presente en la sesión
        if "user_id" not in session:
            print("Error: No se encontró el ID del usuario en la sesión", "error")
            return redirect(url_for("login"))

        usuario_id = session["user_id"]

        clases_inscritas = request.form.get("flexRadioDefaultC")
        #Determinar si el usuario es de mensualidad o no        
        if clases_inscritas == "mensualidad":
            today = datetime.today()
            next_month = today.replace(day=28) + timedelta(days=4)
            next_month = next_month.replace(day=1)
            days_in_month = calendar.monthrange(next_month.year, next_month.month)[1]

            # Contar días del mes siguiente excepto los martes
            days_without_tuesdays = sum(1 for day in range(1, days_in_month + 1) 
                                        if (next_month + timedelta(days=day-1)).weekday() != 1)

            clases_inscritas = days_without_tuesdays
        else: 
            clases_inscritas = int(request.form.get("flexRadioDefaultC")) 

        clases_pagadas = clases_inscritas 
        

        # Crear la nueva persona
        nueva_persona = persona(
            nombres=nombres,
            apellidos=apellidos,
            edad=edad,
            numero_telefono=numero_telefono,
            tipo_documento=tipo_documento,
            numero_doc=numero_doc,
            fecha_nacimiento=datetime.strptime(fecha_nacimiento, "%Y-%m-%d"),
            sexo=sexo,
            direccion_residencia=direccion_residencia,
            barrio=barrio,
            uso_imagenes=uso_imagenes,
            nivel_educativo=nivel_educativo,
            grupo_poblacional=grupo_poblacional,
            eps=eps,
            nombre_acudiente=nombre_acudiente,
            numero_acudiente=numero_acudiente,
            discapacidad=discapacidad,
            enfermedad_cronica=enfermedad_descripcion,
            hospitalizaciones=hospitalizacion_descripcion,
            condicion_fisica=condicion_fisica,
            talla=talla,
            peso=peso,
            clases_inscritas=clases_inscritas,
            clases_pagadas=clases_pagadas,
            usuario_id=usuario_id,
            clases_pay=0,
            clases_ava=0
        )

        # Guardar en la base de datos
        db.session.add(nueva_persona)
        db.session.commit()

        print("Paso 1 de inscripción realizado!", "success")
        persona_id = nueva_persona.id
        session["persona_id"] = persona_id
        session["c_disponible"] = nueva_persona.clases_inscritas

        # Redirigir a una página de éxito o al índice
        return redirect(url_for("step_r"))



#Metodo para inscripcion de usuarios

#Obtener datos de clases desde sesión de usuario en adelante
def obtener_clases_desde_fecha(fecha_inicio):
    # Convierte la fecha de inicio a un objeto datetime
    fecha_inicio_datetime = datetime.strptime(fecha_inicio, "%Y-%m-%d")

    # Ordena las clases por fecha_programada
    clases = Clase.query.filter(Clase.fecha_programada >= fecha_inicio_datetime).order_by(Clase.fecha_programada).all()

    return clases


#Inscribir la clase de un usuario 

@app.route('/asociar_clases', methods=['POST'])
def asociar_clases():
    # Obtener el ID de la persona que está asociando las clases
    persona_id = session.get("user_id")

    # Verificar si la persona existe en la base de datos
    persona_actual = persona.query.get(persona_id) 
    print("La persona actual es:", persona_actual)
    if not persona_actual: 
        set_message("error", "No se encontró a la persona")
        return redirect(url_for("ver_clases_desde_hoy"))

    # Obtener las clases seleccionadas del formulario
    clases_seleccionadas = []
    for key, value in request.form.items():
        if key.startswith("seleccionar_") and value == "true":
            clase_id = int(key.split("_")[1])
            clases_seleccionadas.append(clase_id)

    #Verificar que el usuario seleccionó las clases de acuerdo a su plan


    # Verificar que el número de clases seleccionadas no exceda el número máximo permitido
    if len(clases_seleccionadas) > persona_actual.clases_inscritas:
        set_message("error", "Has seleccionado más clases de las permitidas.")
        return redirect(request.referrer)

    # Asignar las clases seleccionadas a la persona mediante la tabla intermedia 'asistencia'
    for clase_id in clases_seleccionadas:
        clase = Clase.query.get(clase_id)
        
        if clase and clase.numero_cupos > 0:  # Asegurarse de que hay cupos disponibles
            nueva_asistencia = asistencia(persona_id=persona_id, clase_id=clase_id)
            db.session.add(nueva_asistencia)
            clase.numero_cupos -= 1  # Reducir el número de cupos disponibles
        else:
            set_message("error","No hay cupos disponibles para esta clase.")
            return redirect(request.referrer)

    # Guardar los cambios en la base de datos
    db.session.commit()

    set_message("success","Clases programadas con éxito")
    return redirect(url_for("step_r"))


#Código alternativo de prueba para determinar el metodo de asociación
@app.route('/imprimir_clases_seleccionadas', methods=['POST'])
def imprimir_clases_seleccionadas():
    # Buscar el ID de la persona seleccionada en el formulario 
    persona_id = session.get('persona_id')  
    persona_class = persona.query.filter_by(id=persona_id).first()
   

    if not persona_id:
        print("Error: No se encontró el ID de la persona en la sesión")
        return jsonify({"status": "error", "message": "No se encontró el ID de la persona en la sesión"}), 400

    # Obtener las clases seleccionadas del formulario
    clases_seleccionadas = []
    for key, value in request.form.items():
        if key.startswith("seleccionar_") and value == "true":
            clase_id = int(key.split("_")[1])
            clases_seleccionadas.append(clase_id)

    # Lógica para restringir el número de selecciones (de acuerdo al valor puesto en la inscripción, u otra añadidura) 
    numero_elegido = persona_class.clases_pagadas
    if len(clases_seleccionadas) != numero_elegido: 
        abu = "Usted seleccionó "+str(len(clases_seleccionadas))+" clases, por favor, seleccione la cantidad de clases de acuerdo al número que seleccionó anteriormente, es decir: "+str(numero_elegido)
        return jsonify({"status": "info", "message": abu}), 400

    # Asociar a la persona con las clases seleccionadas en la base de datos
    persona_encontrada = persona.query.get(persona_id)
    if persona_encontrada: 
        for clase_id in clases_seleccionadas:
            clase = Clase.query.get(clase_id)
            if clase:
                if len(clase.asistentes) < clase.numero_cupos:
                    persona_encontrada.clases_asistidas.append(clase)
                    clase.numero_cupos -= 1
                    persona_encontrada.clases_ava = 1  
                    persona_encontrada.clases_pay = 1
                    db.session.commit()
                else:
                    return jsonify({"status": "error", "message": f"La clase {clase_id} ya alcanzó el número máximo de asistentes"}), 400
            else:
                return jsonify({"status": "error", "message": f"No se encontró la clase con ID {clase_id}"}), 400
    else:
        return jsonify({"status": "error", "message": f"No se encontró la persona con ID {persona_id}"}), 400

    # Generar la URL con el ID de la persona
    url_qr = url_for('qr_asistencia', persona_id=persona_encontrada.id, _external=True)

    # Generar el código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url_qr)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    
    # Convertir la imagen QR a binario
    img_binario = BytesIO()
    img.save(img_binario, format="PNG")
    img_binario.seek(0)
    qr_binario = img_binario.getvalue()

    # Almacenar la URL del QR y la imagen QR en la base de datos
    persona_encontrada.qr_person = url_qr
    persona_encontrada.info_qr = qr_binario
    db.session.commit()

    # Enviar el correo con el QR
    correo_destinatario = persona_encontrada.usuario.correo
    asunto = "Confirmación de Inscripción de Clases"
    cuerpo = "Gracias por inscribirse en nuestras clases. A continuación, encontrará su código QR para verificar su inscripción."

    # Crear el mensaje de correo con el QR adjunto
    mensaje = Message(asunto, recipients=[correo_destinatario])
    mensaje.body = cuerpo
    mensaje.attach("codigo_qr.png", "image/png", qr_binario)

    try:
        mail.send(mensaje)
        print("Correo enviado correctamente")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return jsonify({"status": "error", "message": "Hubo un error al enviar el correo"}), 500

    # Redirigir de nuevo a la página de ver clases después de la inscripción
    return jsonify({"status": "success", "message": "Sus clases fueron seleccionadas satisfactoriamente"}), 200



#Vista de añadir clases a la inscripción
@app.route('/visualizar_mi', methods=['GET'])
def visualizar_mi():
    # Verificar si el usuario está autenticado
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Obtener el ID del usuario actual
    usuario_id = session["user_id"]

    # Recuperar las personas asociadas al usuario actual
    personas = persona.query.filter_by(usuario_id=usuario_id).all()

    # Verificar si las renovaciones están habilitadas
    descuento = Descuento.query.get(1)
    renovaciones_habilitadas = descuento.habilitado == 'SI' if descuento else False

    # Renderizar la plantilla con las personas asociadas y el estado de renovaciones
    return render_template('inscripciones_personas.html', personas=personas, renovaciones_habilitadas=renovaciones_habilitadas)


#Filtro de clases de selección 
@app.route('/ver_clases_seleccion', methods=['GET'])
def ver_clases_seleccion():
    # Verificar si el usuario está autenticado
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Verificar si hay una persona seleccionada en la sesión
    if "persona_id" not in session:
        return "No se ha seleccionado ninguna persona", 400

    # Obtener el ID de la persona seleccionada de la sesión
    personex_id = session["persona_id"]

    # Obtener la fecha de mañana
    tomorrow = datetime.now().date() + timedelta(days=1)

    # Calcular la fecha límite de 35 días a partir de mañana
    limit_date = tomorrow + timedelta(days=40)

    # Obtener las clases a las que el usuario ya está inscrito
    clases_inscritas_ids = db.session.query(Clase.id).join(asistencia).filter(
        asistencia.c.persona_id == personex_id
    ).all()
    clases_inscritas_ids = {clase_id for (clase_id,) in clases_inscritas_ids}  # Convertir a un conjunto para facilitar la búsqueda

    # Filtrar las clases de selección que ocurren dentro de los próximos 35 días,
    # excluyendo las clases a las que el usuario ya está inscrito
    clases = Clase.query.filter(
        Clase.descripcion == "Natación (Selección Kraken)",
        Clase.fecha_programada >= str(tomorrow),
        Clase.fecha_programada <= str(limit_date),
        Clase.id.notin_(clases_inscritas_ids)  # Excluir clases inscritas
    ).order_by(Clase.fecha_programada).all()

    # Agrupar las clases por año y mes
    clases_por_mes = {}
    for clase in clases:
        fecha = datetime.strptime(clase.fecha_programada, '%Y-%m-%d').date()
        ano_mes = (fecha.year, fecha.month)
        if ano_mes not in clases_por_mes:
            clases_por_mes[ano_mes] = []
        clases_por_mes[ano_mes].append(clase)

    # Obtener el mes y año actuales para el título
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year

    # Obtener nombres de profesores
    profes_found = registro.query.filter_by(rol_id=2).all()
    profes_nombres = {profes.id: f"{profes.correo}" for profes in profes_found}

    return render_template('clases_seleccion.html', clases_por_mes=clases_por_mes, nombre_del_mes=nombre_del_mes, current_month=current_month, current_year=current_year, profesores_nombres=profes_nombres)



#Visualización óptima de información de personas
@app.route('/detalles_persona/<int:persona_id>')
def detalles_persona(persona_id):
    # Consultar la base de datos para obtener los detalles de la persona
    persona = persona.query.get(persona_id)
    if persona:
        # Devolver todos los detalles de la persona en formato JSON
        return jsonify({
            'id': persona.id,
            'nombres': persona.nombres,
            'apellidos': persona.apellidos,
            'tipoDocumento': persona.tipo_documento,
            'numeroDocumento': persona.numero_doc,
            'fechaNacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d'),  # Formato de fecha
            'edad': persona.edad,
            'sexo': persona.sexo,
            'direccionResidencia': persona.direccion_residencia,
            'barrio': persona.barrio,
            'numeroTelefono': persona.numero_telefono,
            'usoImagenes': persona.uso_imagenes,
            'nivelEducativo': persona.nivel_educativo,
            'grupoPoblacional': persona.grupo_poblacional,
            'eps': persona.eps,
            'nombreAcudiente': persona.nombre_acudiente,
            'numeroAcudiente': persona.numero_acudiente,
            'discapacidad': persona.discapacidad,
            'enfermedadCronica': persona.enfermedad_cronica,
            'hospitalizaciones': persona.hospitalizaciones,
            'tratamientos': persona.tratamientos,
            'condicionFisica': persona.condicion_fisica,
            'talla': persona.talla,
            'peso': persona.peso,
            'clasesInscritas': persona.clases_inscritas,
            'clasesPagadas': persona.clases_pagadas
        })
    else:
        return jsonify({'error': 'Persona no encontrada'}), 404


# Método para pagar
@app.route('/pago_provisional/<int:persona_id>', methods=['GET'])
def pago_provisional(persona_id):
    personax = persona.query.get_or_404(persona_id)
    valor_clase = session.get('valor_clase')
    valor_final = session.get('valor_final', valor_clase)
    descripcion_pago = session.get('number_clases')
    
    # Asegúrate de que 'clases_inscritas' es el atributo correcto en tu modelo Persona
    clases_inscritas = personax.clases_inscritas
    
    session['persona_id'] = personax.id
    session['c_disponible'] = clases_inscritas  # Almacena el número de clases inscritas en la sesión

    print(f"Persona ID: {personax.id}, Clases Inscritas: {clases_inscritas}")  # Para depuración

    return render_template('pago_provisional.html', persona=personax, valor_final=valor_final, descripcion_pago=descripcion_pago)






#Metodo intermedio para acceder a la pestaña de apliacion de descuentos 
@app.route("/confirmar_pago/<int:persona_id>", methods=["POST","GET"])
def confirmar_pago(persona_id):
    return redirect(url_for('pago_provisional', persona_id=persona_id))


@app.route('/pagar/<int:persona_id>', methods=['GET', 'POST'])
def pagar(persona_id):
    personax = persona.query.get_or_404(persona_id)
    print("el id de persona actual es:", personax.id)
    session['persona_id'] = personax.id 
    
    # Calcular el valor inicial según el número de clases inscritas
    # Filtrar según el número de clases inscritas
    if personax.clases_inscritas >= 24:
        # Caso para personas de Selección Kraken o mensualidad
        curso_asociado = cursos.query.filter_by(precio2="mensualidad").first()
        valor_clase = curso_asociado.precio  # Precio de la mensualidad
        descripcion_pago = curso_asociado.descripcion 

    else:
        # Caso para personas con un número fijo de clases
        curso_asociado = cursos.query.filter_by(precio2=personax.clases_inscritas).first()
        valor_clase = curso_asociado.precio
        descripcion_pago = curso_asociado.descripcion


    valor_final = valor_clase  
    indicator=0 # No mostrar valor final inicialmente

    # Procesar el descuento si se envía el formulario
    if request.method == 'POST':
        codigo_descuento = request.form.get('codigo_descuento')
        
        if codigo_descuento:
            descuento = Descuento.query.filter_by(code=codigo_descuento, habilitado="SI").first()
            if descuento:
                porcentaje_descuento = descuento.porcentaje
                valor_final = valor_clase - (valor_clase * (porcentaje_descuento / 100)) 
                indicator=1
                flash(f'Descuento aplicado: {porcentaje_descuento}%. Valor final: ${valor_final:.2f}', 'success')
            else: 
                valor_final = valor_clase  # Mantener el valor sin descuento
                flash('Código de descuento inválido o expirado. Contacte al administrador.', 'danger')
        else:
            valor_final = valor_clase  # Mantener el valor sin descuento
            flash('Por favor, ingrese un código de descuento válido.', 'warning')

        # Guardamos el valor en la sesión para su uso posterior en la pasarela de pago
        session['valor_final'] = valor_final
    
    # Solo mostrar el valor final si hubo un intento de aplicar el descuento
    return render_template('pago.html', persona=personax, valor_clase=valor_clase, valor_final=valor_final, descripcion_pago=descripcion_pago, indicator=indicator)


#Confirmacion pago/ adaptacion php
@app.route('/confirmacion_pago', methods=['POST'])
def confirmacion_pago():
    # Datos de configuración ePayco
    p_cust_id_cliente = '1473251'
    p_key = '9fc63fff38c92268e7cf680b7f11e1d40e263469'

    # Datos recibidos en la solicitud
    x_ref_payco = request.form.get('x_ref_payco')
    x_transaction_id = request.form.get('x_transaction_id')
    x_amount = request.form.get('x_amount')
    x_currency_code = request.form.get('x_currency_code')
    x_signature = request.form.get('x_signature')

    # Cálculo de la firma
    signature = hashlib.sha256((p_cust_id_cliente + '^' + p_key + '^' + x_ref_payco + '^' + x_transaction_id + '^' + x_amount + '^' + x_currency_code).encode('utf-8')).hexdigest()

    # Valores del pedido en el sistema del comercio
    numOrder = '2531'  # Reemplazar con el número de orden real
    valueOrder = '10000'  # Reemplazar con el valor real

    x_response = request.form.get('x_response')
    x_motivo = request.form.get('x_response_reason_text')
    x_id_invoice = request.form.get('x_id_invoice')
    x_autorizacion = request.form.get('x_approval_code')

    # Validar número de orden y valor
    if x_id_invoice == numOrder and x_amount == valueOrder:
        # Validar firma
        if x_signature == signature:
            x_cod_response = int(request.form.get('x_cod_response'))
            if x_cod_response == 1:
                # Transacción aceptada
                pass
            elif x_cod_response == 2:
                # Transacción rechazada
                pass
            elif x_cod_response == 3:
                # Transacción pendiente
                pass
            elif x_cod_response == 4:
                # Transacción fallida
                pass
            return "OK", 200
        else:
            return "Firma no válida", 400
    else:
        return "Número de orden o valor pagado no coinciden", 400

@app.route('/respuesta_pago', methods=['GET'])
def respuesta_pago():
    ref_payco = request.args.get('ref_payco')
    persona_id = session.get('persona_id')
    persona_clases=session.get('c_disponible')
    return render_template('respuesta_pago.html', ref_payco=ref_payco, persona_id=persona_id, persona_clases=persona_clases)


@app.route('/inscripcion_clases2', methods=['GET','POST'])
def inscripcion_clases2(): 
    # Es necesario poner en sesion para los métodos las clases que ha inscrito la persona 
    #Cuando es persona de cursos:  
    
    persona_id = session.get('persona_id')
    print("id de la persona es", persona_id)
    personax = persona.query.get_or_404(persona_id) 
    print("clases pagadas: ", personax.clases_pay)
    personax.clases_pay = 1 
    personax.clases_restantes=session.get('c_disponible')
    db.session.commit()    
    
    if personax.clases_inscritas >= 24: 
        return redirect(url_for('ver_clases_seleccion')) 
    else:
        return redirect(url_for('ver_clases_desde_hoy'))

@app.route('/notificar_administracion', methods=['GET'])
def notificar_administracion():
    try:
        persona_id = session.get('persona_id')
        if not persona_id:
            flash("No se pudo encontrar la identificación de la persona en la sesión.", "error")
            return redirect(url_for('ruta_anterior_o_inicio'))

        personax = persona.query.get_or_404(persona_id)
        correo_destino = "gutorresg@unal.edu.co"  # Cambia esto al correo de la administración
        asunto = "Notificación de Pago Pendiente"
        cuerpo = f"""
        Hola,

        Hay un pago pendiente para la siguiente persona:

        Nombre: {personax.nombres} {personax.apellidos}
        Correo electrónico: {personax.usuario.correo}
        Número de clases pagadas: {session.get('c_disponible', 0)}
        Valor de la transacción: {session.get('valor_final', 'N/A')}

        Por favor, revisa y toma las acciones necesarias.

        Gracias.
        """

        if enviar_correo(correo_destino, asunto, cuerpo):
            flash("La notificación de pago pendiente ha sido enviada exitosamente.", "success")
        else:
            flash("Hubo un error al enviar la notificación de pago pendiente.", "error")
    except Exception as e:
        flash(f"Error: {e}", "error")

    return redirect(url_for('go_home3'))


@app.route('/navegacion_e')
def navegacion_e():
    # Lógica para regresar a la navegación tal que sea posible programar las clases
    persona_id = session.get('persona_id')
    personax = persona.query.get_or_404(persona_id) 
    print(personax.clases_pay)
    personax.clases_pay = 1 
    personax.clases_restantes=session.get('c_disponible')
    db.session.commit()
    return redirect(url_for('go_home3'))

@app.route('/navegacion_f')
def navegacion_f():
    # Lógica para regresar a la navegación tal que vuelva a pagar
    return redirect(url_for('go_home3'))




#Método de programación de clases (definitivo) 
@app.route('/programar_clases', methods=['POST']) 
def programar_clases():
    if request.method == 'POST':
        # Obtener el ID de la persona seleccionada del formulario
        persona_id = request.form.get('persona_id')

        # Consultar la base de datos para obtener los datos de la persona
        person = persona.query.get(persona_id) 
        
        #Crear la sesión para llevar a cabo la programación de clases 
        session["persona_id"]=persona_id 
        
        print(persona_id, "registrado")
        
        # Imprimir los datos de la persona en la consola
        if person:
            print("Datos de la persona seleccionada:")
            print("Nombres:", person.nombres)
            print("Apellidos:", person.apellidos) 
            print("ID, si joder si", person.id)
            session["c_disponible"] = person.clases_inscritas 
            
            # Imprime los demás campos según sea necesario

        hj=person.clases_inscritas
        
        #Direccionar a la vista según la persona acceda a cursos o a selección 
        if hj >= 24:
            return redirect(url_for('ver_clases_seleccion'))
        # Direccionar nuevamente a la navegación
        else: 
            return redirect(url_for('ver_clases_desde_hoy'))


#Métodos para el rol de profesor, tomar y revisar assitencia asociada 

# Método para tomar la asistencia de una clase@app.route("/tomar_asistencia")
@app.route("/tomar_asistencia")
def tomar_asistencia():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = registro.query.get(user_id)

    # Obtener la fecha actual y la fecha del día anterior
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    # Convertir las fechas a formato de cadena para comparar con la columna `fecha_programada`
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    # Filtrar clases desde el día de ayer en adelante y ordenarlas cronológicamente
    clases = Clase.query.filter(
        Clase.profesor_id == user_id,
        Clase.fecha_programada >= yesterday_str
    ).order_by(Clase.fecha_programada.asc()).all()

    return render_template("asistencia.html", clases=clases)


@app.route('/detalle_asistencia/<int:clase_id>', methods=['GET'])
def detalle_asistencia(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    asistentes = clase.asistentes
    return render_template('detalle_asistencia.html', clase=clase, asistentes=asistentes)

@app.route('/guardar_asistencia/<int:clase_id>', methods=['POST'])
def guardar_asistencia(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    asistentes = clase.asistentes
    Lista_asis = []

    for persona in asistentes:
        presente = request.form.get(f'presente_{persona.id}') is not None

        if presente and persona.clases_ava > 0:
            persona.clases_restantes -= 1
            estadoA = "Presente"
        else:
            persona.clases_restantes -= 1
            estadoA = "Ausente"

        msg = f"Persona: {persona.nombres} {persona.apellidos},  Estado: {estadoA}"
        Lista_asis.append(msg)

    clase.lista = "\n".join(Lista_asis) 
    clase.estado = "finalizada"
    db.session.commit()

    return redirect(url_for("go_home2"))





@app.route('/clases_profesor')
def clases_profesor():
    profesor_id = session.get('user_id')
    clases_programadas = Clase.query.filter_by(profesor_id=profesor_id).order_by(Clase.fecha_programada).all()
    
    clases_seleccion = defaultdict(list)
    clases_no_seleccion = defaultdict(list)
    
    for clase in clases_programadas:
        fecha = datetime.strptime(clase.fecha_programada, "%Y-%m-%d")
        año_mes = (fecha.year, fecha.month)
        if clase.descripcion == "Natación (Selección Kraken)":
            clases_seleccion[año_mes].append(clase)
        else:
            clases_no_seleccion[año_mes].append(clase)
    
    return render_template('clases_profesor.html', 
                           clases_seleccion=clases_seleccion, 
                           clases_no_seleccion=clases_no_seleccion,
                           nombre_del_mes=nombre_del_mes)


@app.route('/revisar_asistencia/<int:clase_id>', methods=['GET'])
def revisar_asistencia(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    print(clase)
    print(clase.duracion)
    # Obtener el registro del profesor usando su ID
    profesor_registro = registro.query.get(clase.profesor_id)
    if not profesor_registro:
        profesor_nombre_completo = "Profesor no asignado"
    else:
        # Asumiendo que hay una relación entre registro y persona
        profesor_persona = persona.query.filter_by(usuario_id=profesor_registro.id).first()
        if profesor_persona:
            profesor_nombre_completo = f"{profesor_persona.nombres} {profesor_persona.apellidos}"
        else:
            profesor_nombre_completo = "Nombre del profesor no disponible"
    
    # Procesar la lista de asistentes
    asistentes = []
    print(clase.lista)
    for entrada in clase.lista.split('\n'):
        if entrada:
            partes = entrada.split(',')
            persona_info = partes[0].replace("Persona: ", "").strip()
            estado_info = partes[1].replace("Estado: ", "").strip()
            asistentes.append({"persona": persona_info, "estado": estado_info})
    
    # Devolver los datos como JSON
    return jsonify({
        'fecha': clase.fecha_programada,
        'profesor': profesor_nombre_completo,
        'descripcion': clase.descripcion,
        'asistentes': asistentes
    })







#Método de pago [prueba]
@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/success')
def success():
    return "<h1>Pago Exitoso</h1><p>¡Gracias por tu pago! Tu transacción ha sido completada.</p>"

@app.route('/cancel')
def cancel():
    return "<h1>Pago Cancelado</h1><p>Tu transacción ha sido cancelada. Si necesitas ayuda, por favor contáctanos.</p>" 
 
 
# visualización para clases del usuario 
 
@app.route('/personas_inscritas', methods=['GET'])
def personas_inscritas():
    usuario_id = session.get('user_id')
    if not usuario_id:
        return redirect(url_for('login'))  # Redirigir al login si no hay un usuario en sesión

    personas = persona.query.filter_by(usuario_id=usuario_id).all()

    return render_template('personas_inscritas.html', personas=personas) 


@app.route('/obtener_clases_persona', methods=['GET'])
def obtener_clases_persona():
    persona_id = request.args.get('persona_id')
    if not persona_id:
        return jsonify({'error': 'Falta el ID de la persona'}), 400

    clases = Clase.query.join(asistencia).filter(asistencia.c.persona_id == persona_id).all()

    clases_data = [
        {
            'fecha_programada': clase.fecha_programada,
            'hora_inicio': clase.hora_inicio,
            'hora_fin': clase.hora_fin,
            'ubicacion': clase.ubicacion,
            'descripcion': clase.descripcion
        }
        for clase in clases
    ]

    return jsonify({'clases': clases_data})


#Método administrador: ver las inscripciones y personas 
@app.route('/ver_inscripciones', methods=['GET'])
def ver_inscripciones():
    usuarios = registro.query.all()
    datos_inscripciones = []
    for usuario in usuarios:
        personas = persona.query.filter_by(usuario_id=usuario.id).all()
        datos_personas = []
        for persona_item in personas:
            clases = Clase.query.filter(Clase.asistentes.any(id=persona_item.id)).all()
            datos_clases = []
            for clase in clases:
                datos_clases.append({
                    'id': clase.id,
                    'descripcion': clase.descripcion,
                    'fecha_programada': clase.fecha_programada,
                    'hora_inicio': clase.hora_inicio,
                    'hora_fin': clase.hora_fin,
                    'ubicacion': clase.ubicacion
                })
            datos_personas.append({
                'id': persona_item.id,
                'nombres': persona_item.nombres,
                'apellidos': persona_item.apellidos,
                'tipo_documento': persona_item.tipo_documento,
                'numero_doc': persona_item.numero_doc,
                'clases': datos_clases
            })
        datos_inscripciones.append({
            'id': usuario.id,
            'correo': usuario.correo,
            'personas': datos_personas
        })

    return render_template('ver_inscripciones.html', inscripciones=datos_inscripciones)


#Procesamiento de descuentos
#Módulo de descuentos-- Administrador 

@app.route('/admin/descuentos')
def administrar_descuentos():
    descuentos = Descuento.query.all()
    return render_template('discounts.html', descuentos=descuentos)

@app.route('/admin/descuentos/editar/<int:id>', methods=['GET', 'POST'])
def editar_descuento(id):
    descuento = Descuento.query.get_or_404(id)
    if request.method == 'POST':
        descuento.porcentaje = request.form['porcentaje']
        descuento.code = request.form['code']
        db.session.commit()
        flash('Descuento actualizado exitosamente', 'success')
        return redirect(url_for('administrar_descuentos'))
    return render_template('editar_descuento.html', descuento=descuento)

@app.route('/admin/descuentos/habilitar/<int:id>', methods=['POST'])
def habilitar_descuento(id):
    descuento = Descuento.query.get_or_404(id)
    descuento.habilitado = "NO" if descuento.habilitado == "SI" else "SI"
    db.session.commit()
    flash(f"Descuento {'habilitado' if descuento.habilitado == 'SI' else 'deshabilitado'} exitosamente", 'success')
    return redirect(url_for('administrar_descuentos'))

@app.route('/admin/descuentos/agregar', methods=['GET', 'POST'])
def agregar_descuento():
    if request.method == 'POST':
        porcentaje = request.form['porcentaje']
        code = request.form['code']
        nuevo_descuento = Descuento(porcentaje=porcentaje, code=code, habilitado="SI")
        db.session.add(nuevo_descuento)
        db.session.commit()
        flash('Descuento agregado exitosamente', 'success')
        return redirect(url_for('administrar_descuentos'))
    return render_template('agregar_descuento.html')


#Funcionalidad: actualizar número de asistencias y ver sus clases disponibles 

#Boton de home Administrador
@app.route("/go_home1", methods=['POST', 'GET'])
def go_home1(): 
    return render_template("nav_admin.html") 

@app.route("/go_home4", methods=['POST'])
def go_home4(): 
    return render_template("nav_admin.html") 

@app.route("/go_home6", methods=['POST', 'GET'])
def go_home6():
    return render_template("nav_admin.html")


#Botón de home profesor
@app.route("/go_home2", methods=['POST', 'GET'])
def go_home2(): 
    return render_template("nav_teacher.html")


#Botón de home user
@app.route("/go_home3", methods=['POST', 'GET'])
def go_home3(): 
    return render_template("nav_user.html")

@app.route("/go_home5", methods=['POST', 'GET'])
def go_home5(): 
    return render_template("nav_user.html")

@app.route("/go_home7", methods=['POST', 'GET'])
def go_home7(): 
    return render_template("nav_user.html") 

@app.route("/go_home15", methods=['POST', 'GET'])
def go_home15(): 
    return redirect(url_for('visualizar_mi')) 




#Generar los parametros principales para el metodo de enviar el correo con los valores QR
def generar_datos_qr(persona, clases_seleccionadas, fecha_inicial, fecha_final):
    # Obtener el ID de la persona
    persona_id = persona.id

    # Almacenar la URL en la columna info_qr de la persona
    url_qr = url_for('qr_asistencia', persona_id=persona_id, _external=True)
    persona.info_qr = url_qr
    db.session.commit()

    return url_qr


#Enviar el codigo qr con un correo electronico
def enviar_correo_con_qr(destinatario, asunto, cuerpo, qr_data):
    # Generar el código QR con la URL
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # Guardar la imagen en un buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Crear el mensaje de correo
    mensaje = Message(asunto, recipients=[destinatario])
    mensaje.body = cuerpo

    # Adjuntar la imagen del código QR como un archivo
    mensaje.attach("codigo_qr.png", "image/png", buffer.getvalue())

    try:
        mail.send(mensaje)
        return True
    except Exception as e:
        print(e)
        return False




@app.route('/ver_info_qr/<int:persona_id>')
def ver_info_qr(persona_id):
    persona = persona.query.get_or_404(persona_id)
    return f"La información actual es: {persona.info_qr}"

def actualizar_info_qr(persona, nueva_info):
    persona.info_qr = nueva_info
    db.session.commit()

#Metodología para ver datos de QR 

from flask import render_template, abort 




@app.route('/qr_asistencia/<int:persona_id>', methods=['GET'])
def qr_asistencia(persona_id):  
    from collections import defaultdict
    from datetime import datetime, timedelta
    from babel.dates import format_date
    # Obtenemos la persona usando el ID proporcionado
    persona_paraqr = db.session.query(persona).filter_by(id=persona_id).first()
    if not persona_paraqr:
        flash('Persona no encontrada.', 'error')
        return redirect(url_for('home'))

    # Obtener el mes seleccionado desde la URL, si no se seleccionó, usar el mes actual
    mes_seleccionado = request.args.get('mes')
    if not mes_seleccionado:
        mes_seleccionado = datetime.now().strftime('%Y-%m')  # Formato por defecto: '2024-10'
    
    # Convertir el mes seleccionado en rango de fechas
    year, month = map(int, mes_seleccionado.split('-'))
    inicio_mes = datetime(year, month, 1)
    fin_mes = (inicio_mes + timedelta(days=31)).replace(day=1) - timedelta(days=1)  # Fin del mes

    # Consultamos las clases a las que la persona está inscrita usando la tabla intermedia "asistencia"
    clases = db.session.query(Clase).join(
        asistencia, asistencia.c.clase_id == Clase.id
    ).join(
        persona, asistencia.c.persona_id == persona_paraqr.id
    ).options(
        joinedload(Clase.asistencias)
    ).filter(
        persona.id == persona_paraqr.id,
        Clase.fecha_programada.between(inicio_mes, fin_mes)  # Filtrar por el mes seleccionado
    ).all()

    # Determinar el plan de la persona
    plan_n = persona_paraqr.clases_inscritas
    if plan_n < 23:
        plan_n = "Cursos de natación, " + str(plan_n) + " clases"
    else:
        plan_n = "Selección Kraken (Mensualidad)"

    # Agrupar las clases por mes usando defaultdict
    clases_por_mes = defaultdict(list)
    
    for clase in clases:
        # Convertir fecha_programada a un objeto datetime si es un string
        if isinstance(clase.fecha_programada, str):
            fecha_clase = datetime.strptime(clase.fecha_programada, '%Y-%m-%d')  # Ajusta el formato según como esté la fecha en la base de datos
        else:
            fecha_clase = clase.fecha_programada  # Si ya es datetime, no hacemos nada

        mes_anio = fecha_clase.strftime('%Y-%m')  # Ejemplo: '2024-10'
        
        color = 'sin_color'  # Por defecto, color sin sombra
        if clase.estado == 'finalizada':
            lista_asistencia = clase.lista.splitlines()
            for registro in lista_asistencia:
                if persona_paraqr.nombres in registro:
                    if 'Presente' in registro:
                        color = 'verde'  # Asistió a la clase
                    elif 'Ausente' in registro:
                        color = 'rojo'   # No asistió a la clase
                    break

        clases_por_mes[mes_anio].append({
            'clase': clase,
            'color': color
        })

    # Formatear el mes seleccionado para mostrar '2024-Octubre' en vez de '2024-10'
    mes_formateado = format_date(inicio_mes, format='MMMM yyyy', locale='es_ES')

    # Renderizar la vista y pasar los datos categorizados por mes
    return render_template('qr_asis.html', 
                           persona_paraqr=persona_paraqr, 
                           clases_por_mes=clases_por_mes, 
                           plan=plan_n, 
                           mes_actual=mes_seleccionado, 
                           mes_formateado=mes_formateado)





#Mandar a un usuario hacia 
def generar_datos_qr(persona):
    # Generar la URL que incluye el ID de la persona
    url_qr = url_for('qr_asistencia', persona_id=persona.id, _external=True)
    return url_qr

#Generar el canet de la persona 
@app.route('/generar_carnet/<int:persona_id>', methods=['GET', 'POST'])
def generar_carnet(persona_id):
    # Obtener la persona por ID
    persona_encontrada = persona.query.get(persona_id)
    
    if not persona_encontrada or not persona_encontrada.info_qr:
        flash('No es posible la generación del carnet por el momento', 'warning')
        return redirect(url_for('visualizar_mi')) 

    # Obtener el QR en formato binario
    qr_binario = persona_encontrada.info_qr
    
    # Convertir el binario de nuevo a imagen
    img_binario = BytesIO(qr_binario)
    img_binario.seek(0)
    qr_imagen = Image.open(img_binario)

    # Guardar la imagen en un buffer para mostrarla en la plantilla
    buffer = BytesIO()
    qr_imagen.save(buffer, format="PNG")
    buffer.seek(0)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                # Guardar la imagen en el perfil de la persona (esto depende de cómo manejes las fotos en tu modelo)
                persona_encontrada.foto = file.read()
                db.session.commit()
        return redirect(url_for('generar_carnet', persona_id=persona_id))

    return render_template('carnet.html', persona=persona_encontrada, qr_img=img_data)

@app.route('/guardar_carnet/<int:persona_id>', methods=['GET'])
def guardar_carnet(persona_id):
    persona_encontrada = persona.query.get(persona_id)
    
    if not persona_encontrada or not persona_encontrada.info_qr:
        return jsonify({"status": "error", "message": "No se encontró la persona o el QR asociado"}), 404

    # Obtener el QR en formato binario
    qr_binario = persona_encontrada.info_qr
    
    # Convertir el binario de nuevo a imagen
    img_binario = BytesIO(qr_binario)
    img_binario.seek(0)
    qr_imagen = Image.open(img_binario)

    # Guardar la imagen en un buffer
    buffer = BytesIO()
    qr_imagen.save(buffer, format="PNG")
    buffer.seek(0)
    qr_img = buffer.getvalue()

    # Crear el PDF con el carnet
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.image(buffer, x=10, y=10, w=50)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Carnet de {}".format(persona_encontrada.nombre), ln=True, align='C')

    # Guardar el PDF en un buffer
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name="carnet_{}.pdf".format(persona_encontrada.id))


@app.route('/renovar_suscripcion/<int:persona_id>', methods=['POST'])
def renovar_suscripcion(persona_id):
    import datetime
    from datetime import date, timedelta
    # Verificar si el usuario está autenticado
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Obtener el usuario actual y la persona correspondiente
    usuario_id = session["user_id"]
    personix = persona.query.get_or_404(persona_id)

    # Verificar si las renovaciones están habilitadas
    descuento = Descuento.query.get(1)
    if not descuento or descuento.habilitado != 'SI': 
        flash('Las renovaciones no están habilitadas en este momento.', 'warning')
        return redirect(url_for('visualizar_mi')) 
    
    if personix.clases_pay == 1 and personix.clases_ava == 0:
        flash('Las renovaciones se podrán realizar hasta que termines tu inscripción actual', 'warning')
        return redirect(url_for('visualizar_mi'))  
            
    # Obtener el mes actual y el siguiente
    resultado = calcular_clases_mes_siguiente(persona_id) 
    print(resultado)
    if isinstance(resultado, str):  # Si el resultado es un mensaje de error
        flash(resultado, 'warning')
        return


    if resultado == 2.5:
        flash(f'Ya renovaste para el mes siguiente', 'warning')
        return redirect(url_for('visualizar_mi'))

    # Resetear clases_pay y clases_ava
    #persona = persona.query.get(persona_id)
    personix.clases_pay = 0
    personix.clases_ava = 0

    if personix.clases_inscritas < 24: 
        personix.clases_pagadas = personix.clases_inscritas
        flash(f'Se renovó el curso regular con {personix.clases_inscritas} clases.', 'success')
    else:
        personix.clases_inscritas = resultado 
        personix.clases_restantes = resultado 
        personix.clases_pagadas = resultado
        flash(f'Se renovó la mensualidad de Selección Kraken con {resultado} clases.', 'success')


    db.session.commit()
    
    return redirect(url_for('visualizar_mi'))


@app.route('/admin/cursos', methods=['GET'])
def admin_cursos():
    # Consultamos todos los cursos disponibles en la base de datos
    cursosx = cursos.query.all()
    
    # Renderizamos la plantilla de administración de cursos
    return render_template('admin_cursos.html', cursos=cursosx)

# Ruta para mostrar el formulario de edición de un curso
@app.route('/admin/cursos/editar/<int:id>', methods=['GET'])
def editar_curso(id):
    # Buscar el curso por su ID
    curso = cursos.query.get_or_404(id)
    
    # Renderizamos la vista con los datos del curso actual
    return render_template('editar_curso.html', curso=curso)

# Ruta para actualizar el curso en la base de datos
@app.route('/admin/cursos/editar/<int:id>', methods=['POST'])
def actualizar_curso(id):
    # Buscar el curso por su ID
    curso = cursos.query.get_or_404(id)

    # Obtener los valores del formulario
    descripcion = request.form['descripcion']
    n_clases= request.form['num_clases']
    precio = request.form['precio']
    

    # Actualizar los datos del curso
    curso.descripcion = descripcion
    curso.precio = precio
    curso.precio2 = n_clases

    # Guardar los cambios en la base de datos
    try:
        db.session.commit()
        flash(f'Curso actualizado correctamente', 'success')
    except:
        db.session.rollback() 
        flash(f'Error al actualizar el curso', 'danger')

    # Redirigir a la página principal de administración
    return redirect(url_for('admin_cursos'))


# Ruta para eliminar un curso
@app.route('/admin/cursos/eliminar/<int:id>', methods=['GET'])
def eliminar_curso(id):
    # Buscar el curso por su ID
    curso = cursos.query.get_or_404(id)

    try:
        # Eliminar el curso de la base de datos
        db.session.delete(curso)
        db.session.commit()
        flash(f'Curso eliminado correctamente', 'success')
    except:
        db.session.rollback() 
        flash(f'Error al eliminar el curso', 'danger')

    # Redirigir a la página principal de administración
    return redirect(url_for('admin_cursos'))




@app.route('/admin/cursos/nuevo', methods=['GET', 'POST'])
def nuevo_curso():
    if request.method == 'POST':
        # Recibimos los datos del formulario
        descripcion = request.form['descripcion']
        precio2 = request.form['num_clases']
        precio = request.form['precio']

        # Creamos un nuevo curso
        nuevo_curso = cursos(descripcion=descripcion, precio=precio, precio2=precio2)

        # Lo guardamos en la base de datos
        db.session.add(nuevo_curso)
        db.session.commit()

        # Redireccionamos de vuelta a la página de administración de cursos
        return redirect(url_for('admin_cursos'))

    # Si es una solicitud GET, mostramos la página para agregar un curso
    return render_template('nuevo_curso.html')


@app.route('/editar_clase/<int:clase_id>', methods=['GET', 'POST'])
def editar_clase(clase_id):
    # Obtener la información de la clase desde la base de datos
    clase = Clase.query.get_or_404(clase_id)
    
    if request.method == 'POST':
        # Extraer datos del formulario
        clase.titulo = request.form['titulo']
        clase.duracion = request.form['duracion']
        clase.profesor_id = request.form['profesor_id']
        clase.ubicacion = request.form['ubicacion']
        clase.fecha_programada = request.form['fecha_programada']
        clase.numero_cupos = request.form['numero_cupos']

        # Guardar cambios en la base de datos
        db.session.commit()
        return redirect(url_for('modificar_clases'))  # Redirige a la vista principal de clases después de la edición

    # Filtrar solo los profesores (usuarios con rol_id = 2)
    profesores = registro.query.filter_by(rol_id=2).all()  # Obtener solo los profesores
    return render_template('editar_clase_modify.html', clase=clase, profesores=profesores)


#Aplicar modificación de clases para más de una clase con una misma configuración
@app.route('/editar_clase_multiples/<int:clase_id>', methods=['GET', 'POST'])
def editar_clase_multiples(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    print(clase)
    if request.method == 'POST':
        # Actualizar la clase principal
        clase.descripcion = request.form['titulo']
        clase.duracion = request.form['duracion']
        clase.profesor_id = request.form['profesor_id']
        clase.ubicacion = request.form['ubicacion']
        clase.fecha_programada = request.form['fecha_programada']
        clase.numero_cupos = request.form['numero_cupos']
        
        # Verificar si se desea aplicar a otras clases
        if 'aplicar_a_otras' in request.form:
            fechas = request.form['fechas'].split(',')  # lista de fechas seleccionadas
            descripcion_actual = clase.descripcion  # obtén la descripción de la clase

            # Buscar clases en las fechas seleccionadas que tengan la misma descripción
            clases_a_modificar = Clase.query.filter(
                Clase.fecha_programada.in_(fechas),
                Clase.descripcion == descripcion_actual
            ).all()

            # Aplicar cambios a las clases encontradas
            for clase_a_modificar in clases_a_modificar:
                print(clase_a_modificar)
                clase_a_modificar.descripcion = clase.descripcion
                clase_a_modificar.duracion = clase.duracion
                clase_a_modificar.profesor_id = clase.profesor_id
                clase_a_modificar.ubicacion = clase.ubicacion
                clase_a_modificar.numero_cupos = clase.numero_cupos

        # Guardar cambios en la base de datos
        db.session.commit()
        return redirect(url_for('modificar_clases'))

    # Obtener solo los profesores con rol_id=2
    profesores = registro.query.filter_by(rol_id=2).all()
    return render_template('editar_clase_modify.html', clase=clase, profesores=profesores)



@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
@login_requerido
def eliminar_usuario(id):
    if not es_admin():
        set_message("info", "Solo los administradores pueden realizar esta acción")
        return redirect(url_for("login"))
    
    usuario_a_eliminar = db.session.query(registro).filter_by(id=id).first()
    if usuario_a_eliminar:
        db.session.delete(usuario_a_eliminar)
        db.session.commit()
        set_message("success", "Usuario eliminado exitosamente.")
    else:
        set_message("error", "Usuario no encontrado.")
    
    return redirect(url_for('gestion_usuarios'))




if __name__ == '__main__':
    
    #DEBUG is SET to TRUE. CHANGE FOR PROD
    app.run(debug=False, host='0.0.0.0')
    
    