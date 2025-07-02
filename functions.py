import streamlit as st
import supabase 
import psycopg2
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import date
from psycopg2.extras import RealDictCursor

# Load environment variables from .env file
load_dotenv()

def connect_to_supabase():
    """
    Connects to the Supabase PostgreSQL database using transaction pooler details
    and credentials stored in environment variables.
    """
    try:
        # Retrieve connection details from environment variables
        host = os.getenv("SUPABASE_DB_HOST")
        port = os.getenv("SUPABASE_DB_PORT")
        dbname = os.getenv("SUPABASE_DB_NAME")
        user = os.getenv("SUPABASE_DB_USER")
        password = os.getenv("SUPABASE_DB_PASSWORD")

        # Check if all required environment variables are set
        if not all([host, port, dbname, user, password]):
            print("Error: One or more Supabase environment variables are not set.")
            print("Please set SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER, and SUPABASE_DB_PASSWORD.")
            return None

        # Establish the connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
        print("Successfully connected to Supabase database.")
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to Supabase database: {e}")
        return None


def execute_query(query, params= None, conn=None, is_select=True):
    """
    Executes a SQL query and returns the results as a pandas DataFrame for SELECT queries,
    or executes DML operations (INSERT, UPDATE, DELETE) and returns success status.
    
    Args:
        query (str): The SQL query to execute
        conn (psycopg2.extensions.connection, optional): Database connection object.
            If None, a new connection will be established.
        is_select (bool, optional): Whether the query is a SELECT query (True) or 
            a DML operation like INSERT/UPDATE/DELETE (False). Default is True.
            
    Returns:
        pandas.DataFrame or bool: A DataFrame containing the query results for SELECT queries,
            or True for successful DML operations, False otherwise.
    """
    try:
        # Create a new connection if one wasn't provided
        close_conn = False
        if conn is None:
            conn = connect_to_supabase()
            close_conn = True
        
        # Create cursor and execute query
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if is_select:
            # Fetch all results for SELECT queries
            results = cursor.fetchall()
            
            # Get column names from cursor description
            colnames = [desc[0] for desc in cursor.description]
            
            # Create DataFrame
            df = pd.DataFrame(results, columns=colnames)
            result = df
        else:
            # For DML operations, commit changes and return success
            conn.commit()
            result = True
        
        # Close cursor and connection if we created it
        cursor.close()
        if close_conn:
            conn.close()
            
        return result
    except Exception as e:
        print(f"Error executing query: {e}")
        # Rollback any changes if an error occurred during DML operation
        if conn and not is_select:
            conn.rollback()
        return pd.DataFrame() if is_select else False
    
def execute_query_simple(query, params=None, is_select=True):
    """
    Versión simplificada que siempre maneja su propia conexión.
    """
    try:
        # Crear conexión
        conn = connect_to_supabase()
        cursor = conn.cursor()
        
        # Ejecutar query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if is_select:
            # Para SELECT queries
            results = cursor.fetchall()
            
            # Obtener nombres de columnas
            if cursor.description:
                colnames = [desc[0] for desc in cursor.description]
                
                # Crear DataFrame
                if results:
                    df = pd.DataFrame(results, columns=colnames)
                else:
                    # DataFrame vacío pero con columnas
                    df = pd.DataFrame(columns=colnames)
                
                cursor.close()
                conn.close()
                return df
            else:
                cursor.close()
                conn.close()
                return pd.DataFrame()
        else:
            # Para INSERT/UPDATE/DELETE
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
    except Exception as e:
        print(f"Error executing query: {e}")
        try:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                if not is_select:
                    conn.rollback()
                conn.close()
        except:
            pass
        
        return pd.DataFrame() if is_select else False

def add_user(dni, nombre_usuario, contraseña, rol):
    """
    Agrega un nuevo usuario a la tabla 'users'.
    """
    query = """
        INSERT INTO users (id, nombre_usuario, contraseña, rol)
        VALUES (%s, %s, %s, %s)
    """
    params = (dni, nombre_usuario, contraseña, rol)
    print(f"Ejecutando query: {query} con params: {params}")  # Depuración
    return execute_query(query, params=params, is_select=False)

connect_to_supabase()

def get_connection():
    return psycopg2.connect(
        host="aws-0-us-east-1.pooler.supabase.com",
        database="postgres",
        user="postgres.oubnxmdpdosmyrorjiqp",
        password="$EB6Y5rbR#z8_qh",
        port="5432"
    )


def autenticar_usuario(nombre_usuario, contraseña):
    """
    Verifica si el usuario existe y si la contraseña es correcta.

    Args:
        nombre_usuario (str): El nombre de usuario ingresado.
        contraseña (str): La contraseña ingresada.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = "SELECT contraseña FROM users WHERE nombre_usuario = %s"
    params = (nombre_usuario,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return {'success': False, 'message': 'El usuario no existe.'}
    
    contraseña_en_bd = resultado.iloc[0]['contraseña']
    
    if contraseña == contraseña_en_bd:
        return {'success': True, 'message': f'Bienvenido, {nombre_usuario}!'}
    else:
        return {'success': False, 'message': 'Contraseña incorrecta.'}

def buscar_rol(nombre_usuario, contraseña):
    """
    Devuelve el rol de un usuario si las credenciales son correctas.

    Args:
        nombre_usuario (str): Nombre de usuario ingresado.
        contraseña (str): Contraseña ingresada.

    Returns:
        dict: {'success': bool, 'rol': str or None, 'message': str}
    """
    query = "SELECT contraseña, rol FROM users WHERE nombre_usuario = %s"
    params = (nombre_usuario,)  
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return {'success': False, 'rol': None, 'message': 'El usuario no existe.'}

    contraseña_en_bd = resultado.iloc[0]['contraseña']
    rol_en_bd = resultado.iloc[0]['rol']

    if contraseña == contraseña_en_bd:
        return {'success': True, 'rol': rol_en_bd, 'message': f"{rol_en_bd}"}
    
    



def obtener_dni_por_usuario(nombre_usuario):
    """
    Devuelve el DNI (columna 'id') de un usuario a partir de su nombre de usuario.

    Args:
        nombre_usuario (str): Nombre de usuario registrado en la tabla 'users'.

    Returns:
        dict: {'success': bool, 'dni': str or None, 'message': str}
    """
    query = "SELECT id FROM users WHERE nombre_usuario = %s"
    params = (nombre_usuario,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return {
            'success': False,
            'dni': None,
            'message': 'No se encontró ningún usuario con ese nombre.'
        }

    dni = resultado.iloc[0]['id']
    return {
        'success': True,
        'dni': f"{dni}",
        'message': f"El DNI del usuario '{nombre_usuario}' es {dni}."
    }

def verificar_medico_por_dni(dni):
    """
    Verifica si un médico existe por su DNI y retorna formato diccionario.

    Args:
        dni (str or int): DNI del médico.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = "SELECT COUNT(*) as total FROM medicos WHERE dni = %s"
    params = (dni,)
    resultado = execute_query_simple(query, params=params, is_select=True)

   
    if resultado.empty:
        return False
    
    count = resultado.iloc[0]['total']
    
    if count > 0:
        return True
    else:
        return False
    
def verificar_si_existe_user_con_dni(id):
    """
    Verifica si un ya hay un usuario existente con el dni insertado

    Args:
        dni (str or int): DNI del usuario.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = "SELECT COUNT(*) as total FROM users WHERE id = %s"
    params = (id,)
    resultado = execute_query_simple(query, params=params, is_select=True)

   
    if resultado.empty:
        return False
    
    count = resultado.iloc[0]['total']
    
    if count > 0:
        return True
    else:
        return False
    

def verificar_si_existe_user_name(new_user):
    """
    Verifica si un ya hay un usuario existente con el mismo nombre

    Args:
        nombre_usuario (str): Nombre del usuario.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = "SELECT COUNT(*) as total FROM users WHERE nombre_usuario = %s"
    params = (new_user,)
    resultado = execute_query_simple(query, params=params, is_select=True)

   
    if resultado.empty:
        return False
    
    count = resultado.iloc[0]['total']
    
    if count > 0:
        return True
    else:
        return False
    


def obtener_hospital_por_dni_medico(dni):
    """
    Obtiene el ID del hospital al que pertenece un médico por su DNI.

    Args:
        dni (str or int): DNI del médico.

    Returns:
        dict: {'success': bool, 'id_hospital': int or None, 'message': str}
    """
    query = "SELECT id_hospital FROM medicos WHERE dni = %s"
    params = (dni,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return {
            'success': False,
            'id_hospital': None,
            'message': 'No se encontró ningún médico con ese DNI.'
        }

    id_hospital = resultado.iloc[0]['id_hospital']
    return {
        'success': True,
        'id_hospital': id_hospital,
        'message': f'Médico encontrado. Pertenece al hospital ID: {id_hospital}'
    }

def obtener_id_categoria_por_dni_medico(dni):
    """
    Obtiene el ID de categoria que tiene un médico

    Args:
        dni (str or int): DNI del médico.

    Returns:
        dict: {'success': bool, 'id_categoria': int or None, 'message': str}
    """
    query = "SELECT id_categoria FROM medicos WHERE dni = %s"
    params = (dni,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return {
            'success': False,
            'id_hospital': None,
            'message': 'No se encontró ningún médico con ese DNI.'
        }

    id_categoria =  resultado.iloc[0]['id_categoria']
    return {
        'success': True,
        'id_categoria': id_categoria
    }

def obtener_categoria_por_id(id_tipo_categoria):
    """
    Obtiene categoria con el ID

    Args:
        dni (str or int): id_tipo_categoria

    Returns:
        dict: {'success': bool, 'nombre_categoria':str or None, 'message': str}
    """
    query = "SELECT nombre_categoria FROM categorias WHERE id_tipo_categoria = %s"
    params = (id_tipo_categoria,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return {
            'success': False,
            'nombre_categoria': None
        }

    nombre_categoria = resultado.iloc[0]['nombre_categoria']
    return {
        'success': True,
        'nombre_categoria': nombre_categoria
    }

def id_tipo_a_tipo_med(id_tipo_med):
    """
    Devuelve el tipo de medicamento a partir del id del tipo de medicamento

    Args:
        id_tipo_med (str): Id de tipo de medicaamento en tabla "tipo_medicamento".

    Returns:
        dict: {'success': bool, 'tipo_de_medicamento': str or None, 'message': str}
    """
    query = "SELECT tipo_de_medicamento FROM tipo_medicamento WHERE id_tipo_med = %s"
    params = (id_tipo_med,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return "No se encontro tipo de medicamento"

    tipo_de_medicamento = resultado.iloc[0]['tipo_de_medicamento']
    return tipo_de_medicamento

def obtener_historial_legible_por_dni(dni):
    """
    Obtiene el historial médico legible de un paciente por su DNI.

    Args:
        dni (str or int): DNI del paciente.

    Returns:
        dict: {'success': bool, 'data': list of dict or None, 'message': str}
    """
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
        SELECT 
            cm.detalle_consulta,
            cm.clasificacion AS gravedad,
            cm.fecha_consulta,
            h.nombre_hospital AS hospital,
            c.nombre_categoria AS especialidad,
            m.nombre AS medico
        FROM consulta_medica cm
        JOIN pacientes p ON cm.id_paciente = p.dni_paciente
        JOIN hospital h ON h.id_hospital = cm.id_hospital
        JOIN categorias c ON c.id_tipo_categoria = cm.id_categoria
        JOIN medicos m ON m.id_medico = cm.id_medico
        WHERE p.dni_paciente = %s
        ORDER BY cm.clasificacion DESC;
        """
        cur.execute(query, (dni,))
        resultados = cur.fetchall()

        cur.close()
        conn.close()

        if resultados:
            return {
                'success': True,
                'data': resultados,
                'message': f'Se encontraron {len(resultados)} registros del historial.'
            }
        else:
            return {
                'success': False,
                'data': [],
                'message': 'No se encontró historial para este paciente.'
            }
    except Exception as e:
        print(f"Error al obtener historial: {e}")
        return {
            'success': False,
            'data': None,
            'message': 'Error al consultar el historial.'
        }

def obtener_nombre_por_dni(dni):
    """
    Devuelve el DNI (columna 'id') de un usuario a partir de su nombre de usuario.

    Args:
        nombre_usuario (str): Nombre de usuario registrado en la tabla 'users'.

    Returns:
        dict: {'success': bool, 'dni': str or None, 'message': str}
    """
    query = "SELECT nombre FROM medicos WHERE dni = %s"
    params = (dni,)
    resultado = execute_query_simple(query, params=params, is_select=True)

    if resultado.empty:
        return "No se encontro un medico con este dni"

    nombre = resultado.iloc[0]['nombre']
    return nombre

def obtener_estudios_por_dni(dni):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT 
            er.fecha,
            te.tipo_de_estudio,
            e.nombre_estudio,
            er.observaciones
        FROM estudios_realizados er
        JOIN estudios e ON er.id_estudio = e.id_estudio
        JOIN tipo_estudio te ON er.id_categoria_estudio = te.id_categoria_estudio
        WHERE er.dni_paciente = %s
        ORDER BY er.fecha DESC
    """, (dni,))
    estudios = cur.fetchall()
    cur.close()
    conn.close()
    return estudios

def init_supabase():
            url = "https://oubnxmdpdosmyrorjiqp.supabase.co"
            key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91Ym54bWRwZG9zbXlyb3JqaXFwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ4MjUzMjcsImV4cCI6MjA2MDQwMTMyN30.4yszlmTe3NkDLAss6HACnfGlxprHyJLQYTLRrgRmj04"
            return supabase.create_client(url, key)

def add_new_study(dni_paciente: str, doctor_id: int, hospital_id: int, id_categoria_estudio: int, estudio_id: int, 
                 study_date: date, observations: str) -> bool:
            """Agregar nuevo estudio usando dni_paciente directamente"""
            try:
                client = init_supabase()

                # Verificar que el paciente existe
                patient_response = client.table('pacientes').select('dni_paciente').eq('dni_paciente', dni_paciente).execute()
                
                if not patient_response.data:
                    st.error("No se encontró el paciente")
                    return False
                
                # Usar dni_paciente directamente
                new_study = {
                    'dni_paciente': dni_paciente,
                    'id_medico': doctor_id,
                    'id_hospital': hospital_id,
                    'id_categoria_estudio': id_categoria_estudio,
                    'id_estudio': estudio_id,
                    'fecha': study_date.strftime('%Y-%m-%d'),
                    'observaciones': observations
                }
                
                response = client.table('estudios_realizados').insert(new_study).execute()
                
                if response.data:
                    st.success("Estudio agregado exitosamente")
                    # Limpiar cache para mostrar el nuevo estudio inmediatamente
                    st.cache_data.clear()
                    return True
                else:
                    st.error("Error al insertar el estudio")
                    return False
                
            except Exception as e:
                st.error(f"Error al agregar estudio: {str(e)}")
                return False

def crear_logo():
    # Mejor distribución: logo más pequeño y más espacio para el texto
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("images/logo_syncsalud.png", width=80)
    with col2:
        st.markdown(
            '<div style="display: flex; align-items: center; height: 80px;">'
            '<span style="font-size: 2.5rem; color: #1a73e8; font-weight: bold;">SyncSalud</span>'
            '</div>',
            unsafe_allow_html=True
        )

def crear_logo_centrado():
    # Centra todo el bloque
    col1, col2, col3 = st.columns([2, 1, 3])
    with col2:
        st.image("images/logo_syncsalud.png", width=100)
    with col3:
        st.markdown(
            '<div style="display: flex; align-items: center; height: 100px;">'
            '<span style="font-size: 3rem; color: #1a73e8; font-weight: bold;">SyncSalud</span>'
            '</div>',
            unsafe_allow_html=True
        )

