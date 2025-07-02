# --- Consultas_médicas.py ---
import streamlit as st
import pandas as pd
from psycopg2.extras import RealDictCursor
from functions import get_connection, execute_query, crear_logo
from Inicio import manage_page_access

st.set_page_config(
    page_title="SyncSalud - Consultas médicas",
    page_icon="images/logo_syncsalud.png",
    layout="centered"
)

# --- Fix visual para texto blanco en fondo blanco dentro de expanders ---
st.markdown("""
    <style>
    .streamlit-expanderContent {
        color: black !important;
    }
    </style>
""", unsafe_allow_html=True)

def obtener_historial_legible_por_dni(dni):
    conn = get_connection()
    cur = conn.cursor()

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

    if not resultados:
        return "Este paciente no posee un historial."

    columnas = ["Detalle Consulta", "Gravedad", "Fecha Consulta", "Hospital", "Especialidad", "Médico"]
    return pd.DataFrame(resultados, columns=columnas)


def obtener_pacientes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT dni_paciente, nombre FROM pacientes")
    pacientes = cur.fetchall()
    cur.close()
    conn.close()
    return [(p['dni_paciente'], p['nombre']) for p in pacientes]


def obtener_hospitales():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id_hospital, nombre_hospital FROM hospital")
    hospitales = cur.fetchall()
    cur.close()
    conn.close()
    return [(h['id_hospital'], h['nombre_hospital']) for h in hospitales]


def obtener_tipo_categorias():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id_tipo_categoria, nombre_categoria FROM categorias")
    categorias = cur.fetchall()
    cur.close()
    conn.close()
    return [(c['id_tipo_categoria'], c['nombre_categoria']) for c in categorias]


def insertar_consulta(id_paciente, id_medico, id_hospital, id_categoria, gravedad, detalle, fecha_consulta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO consulta_medica (id_paciente, id_medico, id_hospital, id_categoria, clasificacion, detalle_consulta, fecha_consulta)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (id_paciente, id_medico, id_hospital, id_categoria, gravedad, detalle, fecha_consulta))
    conn.commit()
    cur.close()
    conn.close()

def obtener_id_medico_por_dni(dni):
    """
    Devuelve el id_medico correspondiente a un DNI.

    Args:
        dni (str or int): DNI del médico.

    Returns:
        dict: {'success': bool, 'id_medico': int or None, 'message': str}
    """
    query = "SELECT id_medico FROM medicos WHERE dni = %s"
    params = (dni,)
    resultado = execute_query(query, params=params, is_select=True)

    if resultado.empty:
        return {
            'success': False,
            'id_medico': None,
            'message': 'No se encontró ningún médico con ese DNI.'
        }

    id_medico = int(resultado.iloc[0]['id_medico'])
    return {
        'success': True,
        'id_medico': id_medico,
        'message': 'ID del médico encontrado correctamente.'
    }


# -- INTERFAZ --

if not st.session_state.get("logged_in", False):
    st.error("Debes iniciar sesión para acceder a esta página")
else:
    if st.session_state.get("rol", "") != "Médico":
        st.error("No tienes acceso a esta página")
    else:
        st.title("🩺 Consultas médicas")
        st.markdown("### ¿Qué acción desea realizar?")

        opcion = st.radio("Seleccione operación", ("📄 Ver historial", "➕ Agregar consulta"))

        if opcion == "📄 Ver historial":
            with st.form("form_historial"):
                dni_paciente = st.text_input("🆔 DNI del paciente")
                btn_buscar = st.form_submit_button("🔍 Buscar historial")

            if btn_buscar:
                if dni_paciente.strip() == "":
                    st.warning("Por favor ingrese un DNI.")
                else:
                    df_historial = obtener_historial_legible_por_dni(dni_paciente.strip())
                    if isinstance(df_historial, str):
                        st.info(df_historial)
                    else:
                        st.dataframe(df_historial[["Fecha Consulta", "Especialidad", "Detalle Consulta", "Gravedad"]])

                        st.markdown("### 🗂 Detalles adicionales por consulta")
                        for idx, row in df_historial.iterrows():
                            with st.expander(f"🗓 {row['Fecha Consulta']} | Gravedad: {row['Gravedad']}"):
                                st.write(f"👩‍⚕ Médico: {row['Médico']}")
                                st.write(f"🏥 Hospital: {row['Hospital']}")
                                st.write(f"🩻 Detalle: {row['Detalle Consulta']}")
                                st.write(f"📚 Especialidad: {row['Especialidad']}")
                                st.write(f"📅 Fecha: {row['Fecha Consulta']}")
                                st.write(f"⚠ Gravedad: {row['Gravedad']}")

        elif opcion == "➕ Agregar consulta":
            st.title("➕ Nueva consulta médica")

            dni_medico = st.session_state.dni  # Este valor debería venir del login
            buscar_id_medico = obtener_id_medico_por_dni(dni_medico)
            id_medico = buscar_id_medico["id_medico"]

            with st.form("form_consulta"):
                pacientes = obtener_pacientes()
                opciones_pacientes = [f"{dni} - {nombre}" for dni, nombre in pacientes]
                paciente_sel = st.selectbox("👤 Paciente", opciones_pacientes)

                hospitales = obtener_hospitales()
                opciones_hosp = [f"{id_h} - {nombre}" for id_h, nombre in hospitales]
                hospital_sel = st.selectbox("🏥 Hospital", opciones_hosp)

                categorias = obtener_tipo_categorias()
                opciones_cat = [f"{id_c} - {nombre}" for id_c, nombre in categorias]
                categoria_sel = st.selectbox("📚 Especialidad", opciones_cat)

                col1, col2 = st.columns(2)
                with col1:
                    gravedad = st.slider("⚠ Gravedad (1=leve, 5=crítico)", 1, 5, 3)
                with col2:
                    fecha_consulta = st.date_input("📅 Fecha de la consulta")

                detalle = st.text_area("📝 Detalles de la consulta")

                enviar = st.form_submit_button("💾 Guardar consulta")

                if enviar:
                    try:
                        id_paciente = paciente_sel.split(" - ")[0]
                        id_hospital = int(hospital_sel.split(" - ")[0])
                        id_categoria = int(categoria_sel.split(" - ")[0])

                        insertar_consulta(id_paciente, id_medico, id_hospital, id_categoria, gravedad, detalle, fecha_consulta)
                        st.success("✅ Consulta médica agregada correctamente.")
                    except Exception as e:
                        st.error(f"❌ Error al guardar la consulta: {e}")


if st.session_state.get("logged_in"):
    # Sidebar con información del usuario
   with st.sidebar:
        crear_logo()
        st.markdown("---")
        st.markdown(f"👤 Usuario:** {st.session_state.username}")
        st.markdown(f"👥 Rol:** {st.session_state.rol}")
        st.markdown("---")
        
        # Mostrar información sobre páginas accesibles
        if st.session_state.rol == "Médico":
            st.success("✅ Tienes acceso a: Consultas médicas, Estudios y Medicamentos")
            st.error("❌ No tienes acceso a: Administración")
        elif st.session_state.rol == "Admisiones":
            st.success("✅ Tienes acceso a: Administración")
            st.error("❌ No tienes acceso a: Consultas médicas, Estudios y Medicamentos")
        
        st.markdown("---")
        if st.button("🚪 Cerrar sesión"):
            # Restablecer estado y bloquear páginas
            st.session_state.clear()
            try:
                manage_page_access()
            except:
                pass
            st.rerun()