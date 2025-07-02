# --- Estudios.py ---
import streamlit as st
from functions import  execute_query, add_new_study
from Inicio import manage_page_access
from functions import crear_logo
from datetime import date

st.set_page_config(
    page_title="SyncSalud - Estudios",
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

def obtener_nombre_por_dni(dni):
    """
    Obtiene el nombre del paciente por su DNI
    """
    query = "SELECT nombre FROM pacientes WHERE dni_paciente = %s"
    resultado = execute_query(query, params=(dni,), is_select=True)
    
    if resultado.empty:
        return None
    
    return resultado.iloc[0]['nombre']

def obtener_estudios_por_dni(dni):
    """
    Obtiene todos los estudios de un paciente por DNI
    """
    query = """
    SELECT 
        er.fecha,
        er.observaciones,
        te.tipo_de_estudio AS categoria,
        e.nombre_estudio AS estudio,
        h.nombre_hospital AS hospital,
        m.nombre AS medico
    FROM estudios_realizados er
    JOIN tipo_estudio te ON er.id_categoria_estudio = te.id_categoria_estudio
    JOIN estudios e ON er.id_estudio = e.id_estudio
    JOIN hospital h ON er.id_hospital = h.id_hospital
    JOIN medicos m ON er.id_medico = m.id_medico
    WHERE er.dni_paciente = %s
    ORDER BY er.fecha DESC
    """
    
    resultado = execute_query(query, params=(dni,), is_select=True)
    
    if resultado.empty:
        return "Este paciente no posee estudios registrados."
    
    return resultado

def obtener_pacientes():
    """
    Obtiene lista de pacientes con DNI y nombre
    """
    query = "SELECT dni_paciente, nombre FROM pacientes"
    resultado = execute_query(query, is_select=True)
    return [(row['dni_paciente'], row['nombre']) for _, row in resultado.iterrows()]

def obtener_hospitales():
    """
    Obtiene lista de hospitales
    """
    query = "SELECT id_hospital, nombre_hospital FROM hospital"
    resultado = execute_query(query, is_select=True)
    return [(row['id_hospital'], row['nombre_hospital']) for _, row in resultado.iterrows()]

def obtener_categorias_estudio():
    """
    Obtiene categorías de estudios
    """
    query = "SELECT id_categoria_estudio, tipo_de_estudio FROM tipo_estudio"
    resultado = execute_query(query, is_select=True)
    return [(row['id_categoria_estudio'], row['tipo_de_estudio']) for _, row in resultado.iterrows()]

def obtener_estudios_por_categoria(categoria_id):
    """
    Obtiene estudios específicos por categoría
    """
    query = "SELECT id_estudio, nombre_estudio FROM estudios WHERE tipo_estudio = %s"
    resultado = execute_query(query, params=(categoria_id,), is_select=True)
    return [(row['id_estudio'], row['nombre_estudio']) for _, row in resultado.iterrows()]

def obtener_id_medico_por_dni(dni):
    """
    Obtiene el ID del médico por su DNI
    """
    query = "SELECT id_medico FROM medicos WHERE dni = %s"
    resultado = execute_query(query, params=(dni,), is_select=True)
    
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

def insertar_estudio(dni_paciente, id_medico, id_hospital, id_categoria_estudio, id_estudio, fecha, observaciones):
    """
    Inserta nuevo estudio en la base de datos
    """
    query = """
        INSERT INTO estudios_realizados 
        (dni_paciente, id_medico, id_hospital, id_categoria_estudio, id_estudio, fecha, observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        execute_query(query, params=(dni_paciente, id_medico, id_hospital, id_categoria_estudio, id_estudio, fecha, observaciones))
        return True
    except Exception as e:
        st.error(f"Error al insertar estudio: {str(e)}")
        return False

# -- INTERFAZ --

if not st.session_state.get("logged_in", False):
    st.error("Debes iniciar sesión para acceder a esta página")
else:
    if st.session_state.get("rol", "") != "Médico":
        st.error("No tienes acceso a esta página")
    else:
        st.title("🔬 Estudios médicos")
        st.markdown("### ¿Qué acción desea realizar?")

        opcion = st.radio("Seleccione operación", ("📄 Ver estudios", "➕ Agregar estudio"))

        if opcion == "📄 Ver estudios":
            # Inicializar variables de session_state para mantener el estado
            if 'estudios_data' not in st.session_state:
                st.session_state.estudios_data = None
            if 'nombre_paciente_actual' not in st.session_state:
                st.session_state.nombre_paciente_actual = None
            if 'dni_paciente_actual' not in st.session_state:
                st.session_state.dni_paciente_actual = None

            with st.form("form_estudios"):
                dni_paciente = st.text_input("🆔 DNI del paciente")
                btn_buscar = st.form_submit_button("🔍 Buscar estudios")

            if btn_buscar:
                if dni_paciente.strip() == "":
                    st.warning("Por favor ingrese un DNI.")
                else:
                    # Verificar si el paciente existe y obtener su nombre
                    nombre_paciente = obtener_nombre_por_dni(dni_paciente.strip())
                    
                    if nombre_paciente is None:
                        st.error("❌ No se encontró ningún paciente con ese DNI")
                        st.info("💡 Verifique que el DNI esté correctamente ingresado")
                        # Limpiar datos anteriores
                        st.session_state.estudios_data = None
                        st.session_state.nombre_paciente_actual = None
                        st.session_state.dni_paciente_actual = None
                    else:
                        # Obtener estudios del paciente
                        df_estudios = obtener_estudios_por_dni(dni_paciente.strip())
                        
                        if isinstance(df_estudios, str):
                            st.success(f"✅ Paciente encontrado: **{nombre_paciente}**")
                            st.info(df_estudios)
                            # Limpiar datos de estudios pero mantener info del paciente
                            st.session_state.estudios_data = None
                            st.session_state.nombre_paciente_actual = nombre_paciente
                            st.session_state.dni_paciente_actual = dni_paciente.strip()
                        else:
                            # Guardar datos en session_state
                            st.session_state.estudios_data = df_estudios
                            st.session_state.nombre_paciente_actual = nombre_paciente
                            st.session_state.dni_paciente_actual = dni_paciente.strip()

            # Mostrar resultados si hay datos en session_state
            if st.session_state.estudios_data is not None and not st.session_state.estudios_data.empty:
                df_estudios = st.session_state.estudios_data
                nombre_paciente = st.session_state.nombre_paciente_actual
                dni_paciente = st.session_state.dni_paciente_actual

                # Mostrar información del paciente encontrado
                st.success(f"✅ Estudios encontrados para el paciente: **{nombre_paciente}** (DNI: *{dni_paciente}*)")
                
                # Sección de filtros
                st.markdown("---")
                st.subheader("📋 Filtros de Búsqueda")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Filtro por hospital
                    hospitales_unicos = ["Todos"] + sorted(df_estudios['hospital'].unique().tolist())
                    hospital_filtro = st.selectbox("🏥 Hospital:", hospitales_unicos, key="hospital_filter")
                
                with col2:
                    # Filtro por médico
                    medicos_unicos = ["Todos"] + sorted(df_estudios['medico'].unique().tolist())
                    medico_filtro = st.selectbox("👨‍⚕ Médico:", medicos_unicos, key="medico_filter")
                
                with col3:
                    # Filtro por tipo de estudio
                    categorias_unicas = ["Todos"] + sorted(df_estudios['categoria'].unique().tolist())
                    categoria_filtro = st.selectbox("🔬 Tipo de Estudio:", categorias_unicas, key="categoria_filter")
                
                # Aplicar filtros
                df_filtrado = df_estudios.copy()
                
                if hospital_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['hospital'] == hospital_filtro]
                
                if medico_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['medico'] == medico_filtro]
                
                if categoria_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['categoria'] == categoria_filtro]
                
                st.markdown("---")
                
                if not df_filtrado.empty:
                    # Mostrar tabla resumen
                    st.subheader(f"📊 Estudios Encontrados ({len(df_filtrado)} de {len(df_estudios)})")
                    st.dataframe(df_filtrado[["fecha", "categoria", "estudio", "hospital"]])

                    st.markdown("### 🗂️ Detalles adicionales por estudio")
                    for idx, row in df_filtrado.iterrows():
                        with st.expander(f"🗓 {row['fecha']} | {row['estudio']}"):
                            st.write(f"🔬 Tipo de estudio: {row['categoria']}")
                            st.write(f"📋 Estudio: {row['estudio']}")
                            st.write(f"👩‍⚕ Médico: {row['medico']}")
                            st.write(f"🏥 Hospital: {row['hospital']}")
                            st.write(f"📅 Fecha: {row['fecha']}")
                            st.write(f"📝 Observaciones: {row['observaciones'] if row['observaciones'] else 'Sin observaciones'}")
                else:
                    st.warning("🔍 No se encontraron estudios con los filtros aplicados")
                    st.info("💡 Intente modificar los filtros para ver más resultados")

            elif st.session_state.nombre_paciente_actual and st.session_state.estudios_data is None:
                # Caso donde se encontró el paciente pero no tiene estudios
                st.success(f"✅ Paciente encontrado: **{st.session_state.nombre_paciente_actual}**")
                st.info("Este paciente no posee estudios registrados.")

        elif opcion == "➕ Agregar estudio":
            st.title("➕ Nuevo estudio médico")
            
            # Obtener ID del médico logueado
            dni_medico = st.session_state.dni
            buscar_id_medico = obtener_id_medico_por_dni(dni_medico)
            id_medico = buscar_id_medico["id_medico"]
            
            # Mostrar información del médico
            if buscar_id_medico["success"]:
                st.info(f"👨‍⚕ Médico: {st.session_state.username} (ID: {id_medico})")
            else:
                st.error("No se pudo obtener la información del médico logueado")
                st.stop()

            # Input directo para DNI del paciente (sin formulario separado para ser más rápido)
            dni_paciente_input = st.text_input("🆔 DNI del paciente", key="dni_input_fast")
            
            # Verificación automática del paciente cuando se ingresa DNI
            nombre_paciente_encontrado = None
            if dni_paciente_input.strip():
                nombre_paciente_encontrado = obtener_nombre_por_dni(dni_paciente_input.strip())
                if nombre_paciente_encontrado:
                    st.success(f"👤 Paciente: **{nombre_paciente_encontrado}**")
                else:
                    st.warning("⚠️ No se encontró paciente con este DNI")

            # Formulario principal - solo se muestra si hay un paciente válido
            if nombre_paciente_encontrado:
                col1, col2 = st.columns(2)
                
                # Cargar datos solo una vez y cachearlos
                if 'hospitales_fast' not in st.session_state:
                    st.session_state.hospitales_fast = obtener_hospitales()
                
                if 'categorias_fast' not in st.session_state:
                    st.session_state.categorias_fast = obtener_categorias_estudio()
                
                with col1:
                    # Selector de hospital
                    opciones_hosp = [f"{id_h} - {nombre}" for id_h, nombre in st.session_state.hospitales_fast]
                    hospital_sel = st.selectbox("🏥 Hospital", opciones_hosp, key="hospital_fast")
                    
                    # Selector de categoría
                    opciones_cat = [f"{id_c} - {nombre}" for id_c, nombre in st.session_state.categorias_fast]
                    categoria_sel = st.selectbox("📚 Tipo de estudio", opciones_cat, key="categoria_fast")

                with col2:
                    # Selector de estudio específico
                    estudio_sel = None
                    if categoria_sel:
                        id_categoria = int(categoria_sel.split(" - ")[0])
                        
                        # Cache rápido para estudios por categoría
                        cache_key = f"estudios_fast_{id_categoria}"
                        if cache_key not in st.session_state:
                            st.session_state[cache_key] = obtener_estudios_por_categoria(id_categoria)
                        
                        estudios_especificos = st.session_state[cache_key]
                        
                        if estudios_especificos:
                            opciones_estudios = [f"{id_e} - {nombre}" for id_e, nombre in estudios_especificos]
                            estudio_sel = st.selectbox("🔬 Estudio específico", opciones_estudios, key="estudio_fast")
                        else:
                            st.warning("No hay estudios disponibles para esta categoría")
                    
                    # Fecha del estudio
                    fecha_estudio = st.date_input("📅 Fecha del estudio", value=date.today())

                # Observaciones
                observaciones = st.text_area(
                    "📝 Observaciones del estudio",
                    placeholder="Ingrese observaciones sobre el estudio...",
                    height=100
                )

                # Botón de guardar - Acción directa y rápida
                if st.button("💾 Guardar estudio", type="primary"):
                    if not estudio_sel:
                        st.error("❌ Por favor seleccione un estudio específico")
                    else:
                        # Preparar datos y guardar directamente
                        dni_paciente = dni_paciente_input.strip()
                        id_hospital = int(hospital_sel.split(" - ")[0])
                        id_categoria_estudio = int(categoria_sel.split(" - ")[0])
                        id_estudio = int(estudio_sel.split(" - ")[0])

                        # Usar función rápida y directa
                        success = add_new_study(
                            dni_paciente=dni_paciente,
                            doctor_id=id_medico,
                            hospital_id=id_hospital,
                            id_categoria_estudio=id_categoria_estudio,
                            estudio_id=id_estudio,
                            study_date=fecha_estudio,
                            observations=observaciones
                        )
                        
                        if success:
                            st.success("✅ Estudio médico agregado correctamente.")
                            # Limpiar solo los campos necesarios
                            st.rerun()
                        else:
                            st.error("❌ Error al guardar el estudio")

            # Información adicional
            with st.expander("ℹ️ Información sobre estudios médicos"):
                st.markdown("""
                **Instrucciones para agregar un estudio:**
                
                1. 🔍 Busque al paciente ingresando su DNI
                2. 🏥 Seleccione el hospital donde se realizará
                3. 📋 Elija la categoría del estudio
                4. 🔬 Seleccione el estudio específico
                5. 📅 Indique la fecha del estudio
                6. 📝 Agregue observaciones si es necesario
                7. 💾 Guarde el estudio
                
                **Nota:** Los estudios específicos se actualizan automáticamente según la categoría seleccionada.
                """)



# Sidebar con información del usuario
if st.session_state.get("logged_in"):
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