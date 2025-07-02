# --- historial.py ---
import streamlit as st
import pandas as pd
import datetime
from psycopg2.extras import RealDictCursor
from functions import get_connection, execute_query
from functions import obtener_historial_legible_por_dni
from Inicio import manage_page_access
from functions import crear_logo
from functions import id_tipo_a_tipo_med


st.set_page_config(
    page_title="SyncSalud - Historial",
    page_icon="images/logo_syncsalud.png",
    layout="centered"
)

# --- ESTILOS ---
st.markdown("""
    <style>
    .streamlit-expanderContent {
        color: black !important;
    }
    </style>
""", unsafe_allow_html=True)

def obtener_datos_paciente(dni):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT nombre, sexo, fecha_nacimiento, grupo_sanguineo, obra_social, 
               telefono, contacto_emergencia, altura, peso
        FROM pacientes WHERE dni_paciente = %s
    """, (dni,))
    datos = cur.fetchone()
    cur.close()
    conn.close()
    return datos

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


def obtener_medicacion_anterior(dni_paciente):
    query = """
        SELECT m.nombre AS nombre_medicamento, m.tipo AS tipo_medicamento,
               mr.indicaciones, mr.fecha_inicio_medicamento, mr.fecha_terminacion_medicamento
        FROM medicamento_recetado mr
        JOIN medicamentos m ON mr.id_medicamento = m.id_medicamento
        WHERE mr.id_paciente = %s
        AND mr.fecha_terminacion_medicamento < CURRENT_DATE
        ORDER BY mr.fecha_terminacion_medicamento DESC
    """
    resultado = execute_query(query, params=(dni_paciente,), is_select=True)
    return resultado.to_dict("records") if not resultado.empty else []

def obtener_medicamentos_actuales(dni, fecha_consulta):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT mr.id_medicamento, m.nombre AS nombre_medicamento, tm.tipo_de_medicamento AS tipo_medicamento,
               mr.indicaciones, mr.fecha_inicio_medicamento, mr.fecha_terminacion_medicamento
        FROM medicamento_recetado mr
        JOIN medicamentos m ON mr.id_medicamento = m.id_medicamento
        JOIN tipo_medicamento tm ON m.tipo = tm.id_tipo_med
        WHERE mr.id_paciente = %s 
          AND (mr.fecha_terminacion_medicamento IS NULL OR mr.fecha_terminacion_medicamento >= %s)
        ORDER BY mr.fecha_inicio_medicamento DESC
    """, (dni, fecha_consulta))
    medicamentos = cur.fetchall()
    cur.close()
    conn.close()
    return medicamentos


# --- INTERFAZ ---
if not st.session_state.get("logged_in", False):
    st.error("Debes iniciar sesión para acceder a esta página")
elif st.session_state.get("rol") != "Médico":
    st.error("Acceso restringido a médicos")
else:
    st.title("📋 Historial del paciente")
    with st.form("form_historial"):
        dni_paciente = st.text_input("🆔 Ingrese DNI del paciente")
        fecha_consulta = st.date_input("Seleccionar fecha actual", value=datetime.date.today())
        buscar = st.form_submit_button("🔍 Buscar historial")

    if buscar:
        if not dni_paciente.strip():
            st.warning("Por favor ingrese un DNI válido.")
        else:
            # Sección 1: Datos personales
            datos = obtener_datos_paciente(dni_paciente)
            if not datos:
                st.error("Paciente no encontrado.")
            else:
                st.subheader("👤 Datos personales")
    
                col1, col2 = st.columns(2)
    
                with col1:
                    st.markdown(f"👤 Nombre:  {datos['nombre']}")
                    st.markdown(f"❔ Sexo:  {datos['sexo']}")
                    st.markdown(f"🎂 Fecha de nacimiento:  {datos['fecha_nacimiento']}")
                    st.markdown(f"🩸 Grupo sanguíneo:  {datos['grupo_sanguineo']}")
                    st.markdown(f"🏥 Obra social:  {datos['obra_social']}")
        
                with col2:
                    st.markdown(f"📞 Teléfono:  {datos['telefono']}")
                    st.markdown(f"📟 Contacto de emergencia:  {datos['contacto_emergencia']}")
                    st.markdown(f"📏 Altura:  {datos['altura']} cm")
                    st.markdown(f"⚖ Peso:  {datos['peso']} kg")

                # Sección 2: Medicación actual
                st.subheader("💊 Medicación actual")
                medicamentos = obtener_medicamentos_actuales(dni_paciente, fecha_consulta)
                if not medicamentos:
                    st.info("No hay medicamentos activos actualmente.")
                else:
                    for m in medicamentos:
                        st.markdown(f"""
                            - {m['nombre_medicamento']}
                              ({m['tipo_medicamento']})  
                              {m['indicaciones']}  
                              *Inicio:* {m['fecha_inicio_medicamento']}  
                              *Fin:* {m['fecha_terminacion_medicamento'] or 'No especificado'}
                        """)
                        with st.expander("🔽 Ver historial de medicamentos anteriores"):
                            meds_pasados = obtener_medicacion_anterior(dni_paciente)
                            if not meds_pasados:
                                st.info("No hay medicamentos anteriores registrados.")

                with st.expander("🔽 Ver historial de medicamentos anteriores"):
                    meds_pasados = obtener_medicacion_anterior(dni_paciente)
                    if not meds_pasados:
                        st.info("No hay medicamentos anteriores registrados.")
                    else:
                        for m in meds_pasados:
                            encontrar_tipo = id_tipo_a_tipo_med(m['tipo_medicamento'])
                            st.markdown(f"""
                                - *{m['nombre_medicamento']}* ({encontrar_tipo})  
                                {m['indicaciones']}  
                                *Inicio:* {m['fecha_inicio_medicamento']}  
                                *Fin:* {m['fecha_terminacion_medicamento']}
                            """)


                # Sección 3: Estudios realizados
                st.subheader("🧪 Estudios realizados")
                estudios = obtener_estudios_por_dni(dni_paciente)

                if not estudios:
                    st.info("No hay estudios registrados.")
                else:
                    # Convierte la lista de dicts en un DataFrame
                    df_estudios = pd.DataFrame(estudios)
                    
                    # Renombra las columnas para que coincidan con el formato de consultas
                    df_estudios.rename(columns={
                        'fecha': 'Fecha',
                        'tipo_de_estudio': 'Categoría',
                        'nombre_estudio': 'Estudio',
                        'observaciones': 'Observaciones'
                    }, inplace=True)
                    
                    # Muestra la tabla resumen
                    st.dataframe(df_estudios[["Fecha", "Categoría", "Estudio"]])
                    
                    # Expander para detalles de cada estudio
                    for idx, row in df_estudios.iterrows():
                        with st.expander(f"📅 {row['Fecha']} | {row['Estudio']}"):
                            st.write(f"🔬 Categoría: {row['Categoría']}")
                            st.write(f"📋 Estudio: {row['Estudio']}")
                            st.write(f"📅 Fecha: {row['Fecha']}")
                            st.write(f"🔍 Observaciones: {row['Observaciones'] if row['Observaciones'] else 'Sin observaciones'}")


                # Sección 4: Consultas médicas
                st.subheader("🩺 Consultas médicas previas")
                historial_response = obtener_historial_legible_por_dni(dni_paciente)

                # Verifica si la consulta fue exitosa
                if historial_response['success']:
                    data = historial_response['data']
                    if data:
                        # Convierte la lista de dicts en un DataFrame
                        df = pd.DataFrame(data)
                        
                        # Renombra las columnas
                        df.rename(columns={
                            'fecha_consulta': 'Fecha Consulta',
                            'detalle_consulta': 'Detalle Consulta',
                            'gravedad': 'Gravedad',
                            'hospital': 'Hospital',
                            'especialidad': 'Especialidad',
                            'medico': 'Médico'
                        }, inplace=True)
                        
                        # Ahora ya es un DataFrame, por lo que sí puedes hacer:
                        st.dataframe(df[["Fecha Consulta", "Especialidad", "Detalle Consulta", "Gravedad"]])
                        
                        # Expander para detalles
                        for idx, row in df.iterrows():
                            with st.expander(f"🗓 {row['Fecha Consulta']} | Gravedad: {row['Gravedad']}"):
                                st.write(f"👩‍⚕ Médico: {row['Médico']}")
                                st.write(f"🏥 Hospital: {row['Hospital']}")
                                st.write(f"🩻 Detalle: {row['Detalle Consulta']}")
                                st.write(f"📚 Especialidad: {row['Especialidad']}")
                    else:
                        st.info("No se encontraron registros de historial para este paciente.")
                else:
                    st.error(historial_response['message'])


if st.session_state.get("logged_in"):
    # Sidebar con información del usuario
    with st.sidebar:
        crear_logo()
        st.markdown("---")
        st.markdown(f"👤 Usuario: {st.session_state.username}")
        st.markdown(f"👥 Rol: {st.session_state.rol}")
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