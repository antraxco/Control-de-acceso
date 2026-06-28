from flask import Flask, render_template, request, session, redirect, send_from_directory, flash
import sqlite3
import os
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)

app.secret_key = "control_acceso_2026"



# ===================================
# CONEXION BASE DATOS
# ===================================

def conectar():

    return sqlite3.connect(
        os.path.join(BASE_DIR, "control_acceso.db")
    )




# ===================================
# OBTENER ESTADISTICAS SEGUN ROL
# ===================================

def obtener_estadisticas():

    conexion = sqlite3.connect(
        os.path.join(BASE_DIR,"control_acceso.db")
    )

    cursor = conexion.cursor()


    fecha_actual = datetime.now().strftime("%d/%m/%Y")


    filtro = ""
    parametros = [fecha_actual]


    # GUARDA SOLO SU PORTON
    if session.get("rol") == "GUARDA":

        filtro = """
        AND porton = ?
        """

        parametros.append(
            session.get("porton")
        )


    # SUPERVISOR SEGUN SU GRUPO
    # (lo dejaremos preparado para cuando registremos grupo en accesos)
    elif session.get("rol") == "SUPERVISOR":

        filtro = ""


    cursor.execute(f"""
        SELECT COUNT(*)
        FROM registros
        WHERE tipo_acceso='ENTRADA'
        AND fecha=?
        {filtro}
    """,
    parametros)

    entradas = cursor.fetchone()[0]



    cursor.execute(f"""
        SELECT COUNT(*)
        FROM registros
        WHERE tipo_acceso='SALIDA'
        AND fecha=?
        {filtro}
    """,
    parametros)

    salidas = cursor.fetchone()[0]



    cursor.execute(f"""
        SELECT COUNT(*)
        FROM registros
        WHERE tipo_acceso='DENEGADO'
        AND fecha=?
        {filtro}
    """,
    parametros)

    denegados = cursor.fetchone()[0]


    conexion.close()


    return entradas, salidas, denegados



# ===================================
# OBTENER ESTADO ESTUDIANTE
# ===================================

def obtener_estado(carnet):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute("""
        SELECT tipo_acceso, fecha, hora, porton
        FROM registros
        WHERE carnet=?
        ORDER BY id DESC
        LIMIT 1
    """,
    (carnet,))


    ultimo = cursor.fetchone()


    conexion.close()



    if ultimo is None:

        return {
            "estado":"FUERA",
            "movimiento":"SIN REGISTRO",
            "fecha":"",
            "hora":"",
            "porton":""
        }



    if ultimo[0] == "ENTRADA":

        estado = "DENTRO"

    else:

        estado = "FUERA"



    return {

        "estado":estado,
        "movimiento":ultimo[0],
        "fecha":ultimo[1],
        "hora":ultimo[2],
        "porton":ultimo[3]

    }





# ===================================
# LOGIN
# ===================================

@app.route('/', methods=['GET','POST'])
def login():


    if request.method == "POST":


        usuario = request.form['usuario']

        password = request.form['password']



        conexion = conectar()

        cursor = conexion.cursor()



        cursor.execute("""
            SELECT *
            FROM usuarios
            WHERE usuario=?
            AND password=?
            AND estado='ACTIVO'
        """,
        (usuario,password))



        usuario_encontrado = cursor.fetchone()


        conexion.close()



        if usuario_encontrado:


            session['usuario'] = usuario_encontrado[2]

            session['rol'] = usuario_encontrado[4]

            session['grupo'] = usuario_encontrado[6]

            session['turno'] = usuario_encontrado[7]

            session['porton'] = usuario_encontrado[8]



            return redirect('/dashboard')



        return "Usuario incorrecto"



    return render_template("login.html")





# ===================================
# DASHBOARD
# ===================================

@app.route('/dashboard')
def dashboard():


    if 'usuario' not in session:

        return redirect('/')



    entradas,salidas,denegados = obtener_estadisticas()



    return render_template(
    "dashboard.html",
    estudiante=None,
    entradas=entradas,
    salidas=salidas,
    denegados=denegados,
    usuario=session['usuario'],
    rol=session['rol'],
    grupo=session['grupo'],
    turno=session['turno'],
    porton=session['porton']

    )





# ===================================
# BUSCAR ESTUDIANTE
# ===================================

@app.route('/buscar', methods=['POST'])
def buscar():


    if 'usuario' not in session:

        return redirect('/')



    carnet=request.form['carnet']



    conexion=conectar()

    cursor=conexion.cursor()



    cursor.execute("""
        SELECT *
        FROM estudiantes
        WHERE carnet=?
    """,
    (carnet,))



    estudiante=cursor.fetchone()


    conexion.close()



    entradas,salidas,denegados=obtener_estadisticas()


    estado=None


    if estudiante:

        estado=obtener_estado(carnet)



    return render_template(
        "dashboard.html",
        estudiante=estudiante,
        entradas=entradas,
        salidas=salidas,
        denegados=denegados,
        estado=estado,
        usuario=session['usuario'],
        rol=session['rol'],
        porton=session['porton']
    )
    
# ===================================
# REGISTRAR ENTRADA
# ===================================

@app.route('/registrar_entrada', methods=['POST'])
def registrar_entrada():

    if 'usuario' not in session:
        return redirect('/')


    carnet = request.form['carnet']

    nombre = request.form['nombre']


    conexion = conectar()

    cursor = conexion.cursor()



    cursor.execute("""
        SELECT estado
        FROM estudiantes
        WHERE carnet=?
    """,
    (carnet,))


    estudiante_estado = cursor.fetchone()



    if estudiante_estado:

        estado_estudiante = estudiante_estado[0]

    else:

        estado_estudiante = "DESCONOCIDO"



    # ==============================
    # ESTUDIANTE EXPULSADO
    # ==============================

    if estado_estudiante == "EXPULSADO":

        conexion.close()

        flash(
            "Acceso rechazado: el estudiante se encuentra expulsado.",
            "danger"
        )

        return redirect('/dashboard')



    # ==============================
    # VALIDAR SI YA ESTA DENTRO
    # ==============================

    estado = obtener_estado(carnet)



    if estado["estado"] == "DENTRO":

        conexion.close()

        flash(
            "Acceso rechazado: el estudiante ya se encuentra dentro del recinto.",
            "danger"
        )

        return redirect('/dashboard')



    fecha = datetime.now().strftime("%d/%m/%Y")

    hora = datetime.now().strftime("%H:%M:%S")



    cursor.execute("""
        INSERT INTO registros(
            carnet,
            nombre,
            fecha,
            hora,
            tipo_acceso,
            porton,
            usuario_operador,
            estado_estudiante
        )
        VALUES(?,?,?,?,?,?,?,?)
    """,
    (
        carnet,
        nombre,
        fecha,
        hora,
        "ENTRADA",
        session['porton'],
        session['usuario'],
        estado_estudiante
    ))



    conexion.commit()

    conexion.close()



    # ==============================
    # AVISOS ESPECIALES
    # ==============================

    if estado_estudiante in ["EGRESADO","SIN_MATRICULA"]:

        flash(
            f"Entrada registrada. Aviso: estudiante {estado_estudiante}.",
            "warning"
        )

    else:

        flash(
            "Entrada registrada correctamente.",
            "success"
        )



    return redirect('/dashboard')





# ===================================
# REGISTRAR SALIDA
# ===================================

@app.route('/registrar_salida', methods=['POST'])
def registrar_salida():

    if 'usuario' not in session:
        return redirect('/')


    carnet = request.form['carnet']

    nombre = request.form['nombre']


    conexion = conectar()

    cursor = conexion.cursor()



    cursor.execute("""
        SELECT estado
        FROM estudiantes
        WHERE carnet=?
    """,
    (carnet,))


    estudiante_estado = cursor.fetchone()



    if estudiante_estado:

        estado_estudiante = estudiante_estado[0]

    else:

        estado_estudiante = "DESCONOCIDO"



    estado = obtener_estado(carnet)



    # ==============================
    # VALIDAR QUE ESTE DENTRO
    # ==============================

    if estado["estado"] == "FUERA":

        conexion.close()

        flash(
            "Salida rechazada: el estudiante no tiene una entrada activa.",
            "danger"
        )

        return redirect('/dashboard')



    fecha = datetime.now().strftime("%d/%m/%Y")

    hora = datetime.now().strftime("%H:%M:%S")



    cursor.execute("""
        INSERT INTO registros(
            carnet,
            nombre,
            fecha,
            hora,
            tipo_acceso,
            porton,
            usuario_operador,
            estado_estudiante
        )
        VALUES(?,?,?,?,?,?,?,?)
    """,
    (
        carnet,
        nombre,
        fecha,
        hora,
        "SALIDA",
        session['porton'],
        session['usuario'],
        estado_estudiante
    ))



    conexion.commit()

    conexion.close()



    flash(
        "Salida registrada correctamente.",
        "success"
    )


    return redirect('/dashboard')






# ===================================
# VER REGISTROS
# ===================================
# ===================================
# VER REGISTROS SEGUN ROL
# ===================================

@app.route('/ver_registros')
def ver_registros():


    if 'usuario' not in session:

        return redirect('/')



    conexion = sqlite3.connect(
        os.path.join(BASE_DIR,"control_acceso.db")
    )


    cursor = conexion.cursor()



    rol = session.get("rol")



    # ==========================
    # GUARDA
    # SOLO SU PORTON
    # ==========================

    if rol == "GUARDA":


        cursor.execute("""
            SELECT *
            FROM registros
            WHERE porton=?
            ORDER BY id DESC
        """,
        (
            session.get("porton"),
        ))



    # ==========================
    # SUPERVISOR
    # POR AHORA GENERAL
    # (luego se filtra por grupo)
    # ==========================

    elif rol == "SUPERVISOR":


        cursor.execute("""
            SELECT *
            FROM registros
            ORDER BY id DESC
        """)



    # ==========================
    # ADMINISTRADOR
    # SUPER ADMIN
    # TODO
    # ==========================

    else:


        cursor.execute("""
            SELECT *
            FROM registros
            ORDER BY id DESC
        """)




    registros = cursor.fetchall()


    conexion.close()



    return render_template(
        "registros.html",
        registros=registros
    )



# ===================================
# CERRAR SESION
# ===================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')







# ===================================
# INICIAR FLASK
# ===================================
# ===================================
# ADMINISTRAR USUARIOS
# ===================================

@app.route('/usuarios')
def usuarios():

    if 'usuario' not in session:
        return redirect('/')


    if session['rol'] != "SUPER_ADMIN":

        return "Acceso denegado"



    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute("""
        SELECT *
        FROM usuarios
        ORDER BY id DESC
    """)


    lista_usuarios = cursor.fetchall()


    conexion.close()


    return render_template(
        "usuarios.html",
        usuarios=lista_usuarios
    )





# ===================================
# CREAR USUARIO
# ===================================

@app.route('/crear_usuario', methods=['POST'])
def crear_usuario():


    if session.get('rol') != "SUPER_ADMIN":

        return "Acceso denegado"



    nombre = request.form['nombre']

    usuario = request.form['usuario']

    password = request.form['password']

    rol = request.form['rol']

    grupo = request.form['grupo']

    turno = request.form['turno']

    porton = request.form['porton']



    conexion = conectar()

    cursor = conexion.cursor()



    cursor.execute("""
        INSERT INTO usuarios(
            nombre_completo,
            usuario,
            password,
            rol,
            grupo,
            turno,
            porton_asignado,
            estado
        )
        VALUES(?,?,?,?,?,?,?,?)
    """,
    (
        nombre,
        usuario,
        password,
        rol,
        grupo,
        turno,
        porton,
        "ACTIVO"
    ))


    conexion.commit()

    conexion.close()



    return redirect('/usuarios')






# ===================================
# CAMBIAR ESTADO USUARIO
# ===================================

@app.route('/cambiar_estado_usuario/<int:id>')
def cambiar_estado_usuario(id):


    if session.get('rol') != "SUPER_ADMIN":

        return "Acceso denegado"



    conexion = conectar()

    cursor = conexion.cursor()



    cursor.execute("""
        UPDATE usuarios
        SET estado =
        CASE
            WHEN estado='ACTIVO'
            THEN 'INACTIVO'
            ELSE 'ACTIVO'
        END
        WHERE id=?
    """,
    (id,))


    conexion.commit()

    conexion.close()



    return redirect('/usuarios')
    
    # ===================================
# ADMINISTRAR ESTUDIANTES
# ===================================

@app.route('/estudiantes')
def estudiantes():

    if 'usuario' not in session:
        return redirect('/')


    if session['rol'] != "SUPER_ADMIN":

        return "Acceso denegado"



    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute("""
        SELECT *
        FROM estudiantes
        ORDER BY id DESC
    """)


    lista_estudiantes = cursor.fetchall()


    conexion.close()


    return render_template(
        "estudiantes.html",
        estudiantes=lista_estudiantes
    )




# ===================================
# AGREGAR ESTUDIANTE
# ===================================

@app.route('/agregar_estudiante', methods=['POST'])
def agregar_estudiante():

    if session.get('rol') != "SUPER_ADMIN":

        return "Acceso denegado"


    carnet = request.form['carnet']

    nombre = request.form['nombre_completo']

    carrera = request.form['carrera']

    area = request.form['area_conocimiento']

    celular = request.form['celular']


    foto = request.files.get('foto')


    nombre_foto = ""


    if foto and foto.filename != "":

        extension = foto.filename.rsplit('.',1)[1].lower()

        nombre_foto = carnet + "." + extension


        carpeta = os.path.join(
            BASE_DIR,
            "fotos_estudiantes"
        )


        if not os.path.exists(carpeta):

            os.makedirs(carpeta)


        foto.save(
            os.path.join(
                carpeta,
                nombre_foto
            )
        )



    conexion = conectar()

    cursor = conexion.cursor()



    cursor.execute("""
        INSERT INTO estudiantes(
            carnet,
            nombre_completo,
            carrera,
            area_conocimiento,
            celular,
            foto_estudiante,
            estado
        )
        VALUES(?,?,?,?,?,?,?)
    """,
    (
        carnet,
        nombre,
        carrera,
        area,
        celular,
        nombre_foto,
        "ACTIVO"
    ))



    conexion.commit()

    conexion.close()


    return redirect('/estudiantes')





# ===================================
# CAMBIAR ESTADO ESTUDIANTE
# ===================================

@app.route('/cambiar_estado_estudiante/<int:id>', methods=['POST'])
def cambiar_estado_estudiante(id):


    if 'usuario' not in session:

        return redirect('/')


    if session.get('rol') not in ["SUPER_ADMIN","ADMINISTRADOR"]:

        return "Acceso denegado"



    nuevo_estado = request.form['estado']


    conexion = conectar()

    cursor = conexion.cursor()



    cursor.execute("""
        UPDATE estudiantes
        SET estado=?
        WHERE id=?
    """,
    (
        nuevo_estado,
        id
    ))



    conexion.commit()

    conexion.close()


    return redirect('/estudiantes')





# ===================================
# SERVIR FOTOS ESTUDIANTES
# ===================================

@app.route('/fotos_estudiantes/<nombre>')
def servir_foto(nombre):

    return send_from_directory(
        os.path.join(BASE_DIR, "fotos_estudiantes"),
        nombre
    )


# ===================================
# INICIAR FLASK
# ===================================

if __name__=="__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        
    )