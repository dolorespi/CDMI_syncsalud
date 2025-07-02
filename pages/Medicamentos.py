import streamlit as st
from datetime import date
from psycopg2.extras import RealDictCursor
from functions import get_connection, execute_query
from functions import crear_logo
from Inicio import manage_page_access 
from functions import id_tipo_a_tipo_med

st.set_page_config(
    page_title="SyncSalud - Medicamentos",
    page_icon="images/logo_syncsalud.png",
    layout="centered"
)

# --- Funciones ---
def obtener_medicamentos():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id_medicamento, nombre FROM medicamentos")
    medicamentos = cur.fetchall()
    cur.close()
    conn.close()
    return medicamentos

def insertar_medicamento_recetado(id_paciente, id_medico, id_medicamento, indicaciones, fecha_inicio, fecha_fin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO medicamento_recetado 
        (id_paciente, id_medico, id_medicamento, indicaciones, fecha_inicio_medicamento, fecha_terminacion_medicamento)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (id_paciente, id_medico, id_medicamento, indicaciones, fecha_inicio, fecha_fin))
    conn.commit()
    cur.close()
    conn.close()

def obtener_id_medico_por_dni(dni):
    query = "SELECT id_medico FROM medicos WHERE dni = %s"
    resultado = execute_query(query, params=(dni,), is_select=True)

    if resultado.empty:
        return {
            'success': False,
            'id_medico': None,
            'message': 'No se encontró ningún médico con ese DNI.'
        }

    return {
        'success': True,
        'id_medico': int(resultado.iloc[0]['id_medico']),
        'message': 'ID del médico encontrado correctamente.'
    }

def obtener_medicacion_actual(dni_paciente):
    query = """
        SELECT m.nombre AS nombre_medicamento, m.tipo AS tipo_medicamento,
               mr.indicaciones, mr.fecha_inicio_medicamento, mr.fecha_terminacion_medicamento
        FROM medicamento_recetado mr
        JOIN medicamentos m ON mr.id_medicamento = m.id_medicamento
        WHERE mr.id_paciente = %s
        AND (mr.fecha_terminacion_medicamento IS NULL OR mr.fecha_terminacion_medicamento >= CURRENT_DATE)
        AND mr.fecha_inicio_medicamento <= CURRENT_DATE
        ORDER BY mr.fecha_inicio_medicamento DESC
    """
    resultado = execute_query(query, params=(dni_paciente,), is_select=True)
    return resultado.to_dict("records") if not resultado.empty else []

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

def existe_paciente(dni_paciente):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pacientes WHERE dni_paciente = %s", (dni_paciente,))
    existe = cur.fetchone() is not None
    cur.close()
    conn.close()
    return existe

def obtener_nombre_paciente(dni_paciente):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM pacientes WHERE dni_paciente = %s", (dni_paciente,))
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    return resultado[0] if resultado else None

# --- Interfaz ---
if not st.session_state.get("logged_in", False):
    st.error("Debes iniciar sesión para acceder a esta página")

if st.session_state.get("logged_in"):
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
    if st.session_state.get("rol", "") != "Médico":
        st.error("No tienes acceso a esta página")
    else:
        st.title("💊 Recetar medicamentos")

        dni_medico = st.session_state.dni
        buscar_id_medico = obtener_id_medico_por_dni(dni_medico)

        if not buscar_id_medico["success"]:
            st.error("No se encontró el ID del médico. Verificá que estés registrado correctamente.")
        else:
            id_medico = buscar_id_medico["id_medico"]

            with st.form("form_dni_receta"):
                dni_paciente_input = st.text_input("🆔 Ingrese el DNI del paciente")
                buscar_btn = st.form_submit_button("🔍 Buscar paciente")

            if buscar_btn:
                id_paciente = dni_paciente_input.strip()

                if id_paciente == "":
                    st.warning("⚠ Por favor ingrese un DNI.")
                elif not existe_paciente(id_paciente):
                    st.error("❌ No se encontró un paciente con ese DNI.")
                else:
                    nombre_paciente = obtener_nombre_paciente(id_paciente)
                    st.session_state.dni_paciente_actual = id_paciente
                    st.session_state.nombre_paciente_actual = nombre_paciente
                    st.success(f"👤 Paciente encontrado: *{nombre_paciente}* (DNI: {id_paciente})")

            if "dni_paciente_actual" in st.session_state:
                id_paciente = st.session_state.dni_paciente_actual
                nombre_paciente = st.session_state.nombre_paciente_actual

                medicamentos = obtener_medicamentos()
                opciones_medicamentos = {med['nombre']: med['id_medicamento'] for med in medicamentos}

                with st.form("form_receta"):
                    st.subheader(f"Recetando medicamentos para: *{nombre_paciente}*")
                    meds_seleccionados = st.multiselect(
                        "Busca y selecciona medicamentos",
                        options=list(opciones_medicamentos.keys()),
                        help="Podés escribir para buscar"
                    )

                    fecha_inicio = st.date_input("📅 Fecha de inicio del medicamento", value=date.today())
                    fecha_fin = st.date_input("📅 Fecha de finalización del medicamento", value=date.today())

                    st.subheader("✍ Indicaciones")
                    indicaciones = st.text_area("Escribí las indicaciones para los medicamentos seleccionados")

                    enviar = st.form_submit_button("💾 Guardar receta")

                if enviar:
                    if not meds_seleccionados:
                        st.warning("⚠ Debes seleccionar al menos un medicamento.")
                    elif fecha_fin < fecha_inicio:
                        st.error("❌ La fecha de terminación no puede ser anterior a la de inicio.")
                    elif not indicaciones.strip():
                        st.warning("⚠ Debes ingresar indicaciones.")
                    else:
                        try:
                            for med_nombre in meds_seleccionados:
                                id_medicamento = opciones_medicamentos[med_nombre]
                                insertar_medicamento_recetado(
                                    id_paciente, id_medico, id_medicamento,
                                    indicaciones, fecha_inicio, fecha_fin
                                )
                            st.success("✅ Receta guardada correctamente.")
                        except Exception as e:
                            st.error(f"❌ Error al guardar la receta: {e}")

                st.subheader("💊 Medicación actual")
                meds_actuales = obtener_medicacion_actual(id_paciente)
                if not meds_actuales:
                    st.info("No hay medicamentos activos actualmente.")
                else:
                    for m in meds_actuales:
                        encontrar_tipo = id_tipo_a_tipo_med(m['tipo_medicamento'])
                        st.markdown(f"""
                            - {m['nombre_medicamento']}
                              ({encontrar_tipo})   
                              {m['indicaciones']}  
                              *Inicio:* {m['fecha_inicio_medicamento']}  
                              *Fin:* {m['fecha_terminacion_medicamento'] or 'No especificado'}
                        """)

                with st.expander("🔽 Ver historial de medicamentos anteriores"):
                    meds_pasados = obtener_medicacion_anterior(id_paciente)
                    if not meds_pasados:
                        st.info("No hay medicamentos anteriores registrados.")
                    else:
                        for m in meds_pasados:
                            encontrar_tipo = id_tipo_a_tipo_med(m['tipo_medicamento'])
                            st.markdown(f"""
                                - *{m['nombre_medicamento']}*
                                ({encontrar_tipo})   
                                {m['indicaciones']}  
                                *Inicio:* {m['fecha_inicio_medicamento']}  
                                *Fin:* {m['fecha_terminacion_medicamento'] or 'No especificado'}
                            """)