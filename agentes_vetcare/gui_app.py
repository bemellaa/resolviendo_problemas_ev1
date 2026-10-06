import sys
import os
import re
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agentes_vetcare.infraestructura import (
    Configuracion,
    GestorSesionesJSON,
    ServicioCorreoReal,
    ServicioVectorialFAISS,
    ServicioIndicadoresEconomicos,
    ServicioGeneradorQR
)
from agentes_vetcare.agentes import (
    AgenteTriajeYMemoria,
    AgentePreConsulta,
    AgenteNotificadorCitas
)
from agentes_vetcare.dominio import Cita

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="VetCare - Centro Veterinario",
    page_icon="🐾",
    layout="centered"
)

ESPECIES_PERMITIDAS = ["Perro", "Gato", "Conejo", "Hurón", "Ave", "Cobaya", "Hámster", "Tortuga"]

# Inicializar servicios en la sesión visual
@st.cache_resource
def inicializar_servicios():
    config = Configuracion.desde_entorno()
    gestor = GestorSesionesJSON("historial_sesiones.json")
    correo = ServicioCorreoReal(config)
    rag = ServicioVectorialFAISS("base_vectorial_vetcare")
    uf = ServicioIndicadoresEconomicos()
    qr = ServicioGeneradorQR()

    a1 = AgenteTriajeYMemoria(gestor, config)
    a2 = AgentePreConsulta(rag, uf, config)
    a3 = AgenteNotificadorCitas(correo, qr)

    return config, gestor, a1, a2, a3

config, gestor_sesiones, agente_1, agente_2, agente_3 = inicializar_servicios()

# ==============================================================================
# INTERFAZ GRÁFICA (UI)
# ==============================================================================

st.title("🐾 Centro Veterinario VetCare")
st.subheader("Sistema Multi-Agente de Atención Virtual")

# Estado de la sesión
if "paso" not in st.session_state:
    st.session_state.paso = 1
if "datos_consulta" not in st.session_state:
    st.session_state.datos_consulta = {}

# ------------------------------------------------------------------------------
# PASO 1: REGISTRO E INGRESO DEL PACIENTE
# ------------------------------------------------------------------------------
if st.session_state.paso == 1:
    st.info("👋 Bienvenido al portal de atención. Por favor ingrese sus datos.")

    with st.form("form_registro"):
        correo = st.text_input("📧 Correo electrónico (donde recibirá la confirmación):")
        nombre_mascota = st.text_input("🐶 Nombre de su mascota:")
        especie = st.selectbox("🐱 Especie de la mascota:", ESPECIES_PERMITIDAS)
        
        btn_iniciar = st.form_submit_button("Ingresar al Portal")

    if btn_iniciar:
        patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(patron_correo, correo):
            st.error("Ingrese un correo electrónico válido (ej: usuario@gmail.com).")
        elif len(nombre_mascota.strip()) < 2:
            st.error("El nombre de la mascota debe tener al menos 2 caracteres.")
        else:
            id_sesion = f"sesion_{os.urandom(2).hex()}"
            st.session_state.datos_consulta = {
                "correo": correo.strip().lower(),
                "nombre_mascota": nombre_mascota.strip().capitalize(),
                "especie": especie,
                "id_sesion": id_sesion
            }
            st.session_state.paso = 2
            st.rerun()

# ------------------------------------------------------------------------------
# PASO 2: CONSULTA DE SÍNTOMAS (EVALUACIÓN MULTI-AGENTE)
# ------------------------------------------------------------------------------
elif st.session_state.paso == 2:
    datos = st.session_state.datos_consulta
    st.success(f"Sesión activa para **{datos['nombre_mascota']}** ({datos['especie']}) | Tutor: {datos['correo']}")

    consulta = st.text_area("Describa los síntomas o el motivo de su consulta:", placeholder="Ej. Presenta vómitos y decaimiento desde la mañana...")

    if st.button("Enviar Consulta a los Agentes"):
        if len(consulta.strip()) < 4:
            st.warning("Por favor describa los síntomas con mayor detalle.")
        else:
            with st.spinner("Procesando consulta con el equipo multi-agente..."):
                # Agente 1
                res_triaje = agente_1.procesar_consulta(datos["correo"], datos["id_sesion"], consulta)
                # Agente 2
                res_preconsulta = agente_2.elaborar_ficha(
                    datos_triaje=res_triaje.datos_extra,
                    especie=datos["especie"],
                    nombre_mascota=datos["nombre_mascota"]
                )

                st.session_state.datos_consulta["consulta"] = consulta
                st.session_state.datos_consulta["res_triaje"] = res_triaje
                st.session_state.datos_consulta["res_preconsulta"] = res_preconsulta
                st.session_state.paso = 3
                st.rerun()

# ------------------------------------------------------------------------------
# PASO 3: DIAGNÓSTICO PREVIO Y AGENDAMIENTO DE CITA
# ------------------------------------------------------------------------------
elif st.session_state.paso == 3:
    datos = st.session_state.datos_consulta
    res_triaje = datos["res_triaje"]
    res_preconsulta = datos["res_preconsulta"]

    st.markdown("### 🤖 Evaluación Multi-Agente")
    st.info(f"**Agente 1 (Triaje):** {res_triaje.contenido}")
    st.warning(f"**Agente 2 (Ficha y Cotización):** {res_preconsulta.contenido}")

    st.markdown("---")
    st.markdown("### 📅 ¿Desea agendar una cita presencial?")

    horario = st.radio(
        "Seleccione el horario disponible en la clínica:",
        [
            "Mañana (Miércoles) a las 10:00 hrs",
            "Mañana (Miércoles) a las 15:30 hrs",
            "Pasado Mañana (Jueves) a las 11:00 hrs"
        ]
    )

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Confirmar y Reservar Cita", type="primary"):
            with st.spinner("Generando pase QR y enviando correo de confirmación..."):
                cita = Cita(
                    dueno="Cliente VetCare",
                    mascota=datos["nombre_mascota"],
                    correo=datos["correo"],
                    fecha_hora=horario,
                    motivo=datos["consulta"],
                    indicaciones_previas=res_preconsulta.datos_extra["indicaciones_previas"]
                )

                res_cita = agente_3.agendar_y_confirmar(cita)
                st.session_state.res_cita = res_cita
                st.session_state.paso = 4
                st.rerun()

    with col2:
        if st.button("Finalizar sin Agendar"):
            st.session_state.paso = 1
            st.rerun()

# ------------------------------------------------------------------------------
# PASO 4: CONFIRMACIÓN FINAL
# ------------------------------------------------------------------------------
elif st.session_state.paso == 4:
    st.balloons()
    st.success("🎉 ¡Cita confirmada exitosamente!")
    st.markdown(f"**{st.session_state.res_cita.contenido}**")
    st.info("Revisa tu correo electrónico para ver tu pase de atención en código QR.")

    if st.button("Realizar otra consulta"):
        st.session_state.paso = 1
        st.rerun()