import sys
import os
import re

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
# VALIDACIONES DE ENTRADA (GUARDRAILS)
# ==============================================================================

ESPECIES_PERMITIDAS = [
    "perro", "perra", "gato", "gata", "conejo", "coneja", 
    "huron", "hurón", "ave", "pajaro", "pájaro", "cobaya", 
    "hamster", "hámster", "tortuga", "erizo"
]

def pedir_correo_valido() -> str:
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    while True:
        correo = input("👉 Ingrese su correo electrónico: ").strip().lower()
        if re.match(patron, correo):
            return correo
        print(" ❌ Correo inválido. Ingrese un formato correcto (ej: usuario@gmail.com).")


def pedir_texto_valido(prompt: str, min_len: int = 2, campo: str = "texto") -> str:
    while True:
        valor = input(prompt).strip()
        if len(valor) >= min_len and any(c.isalpha() for c in valor):
            return valor
        print(f" ❌ Entrada no válida para '{campo}'. Debe contener al menos {min_len} letras.")


def pedir_especie_valida() -> str:
    """Valida que la mascota sea una especie doméstica atendida por la clínica."""
    while True:
        especie = input("👉 Especie (ej. Perro, Gato, Conejo): ").strip().lower()
        if especie in ESPECIES_PERMITIDAS:
            return especie.capitalize()
        print(" ❌ Especie no admitida. VetCare atiende únicamente especies domésticas (Perro, Gato, Conejo, Hurón, Ave, Cobaya, Hámster, Tortuga).")


def pedir_confirmacion_si_no(prompt: str) -> bool:
    while True:
        respuesta = input(prompt).strip().lower()
        if respuesta in ["s", "si", "sí", "yes", "y"]:
            return True
        elif respuesta in ["n", "no"]:
            return False
        print(" ❌ Opción inválida. Responda únicamente 's' (Sí) o 'n' (No).")


def seleccionar_horario_disponible() -> str:
    opciones = {
        "1": "Mañana (Miércoles) a las 10:00 hrs",
        "2": "Mañana (Miércoles) a las 15:30 hrs",
        "3": "Pasado Mañana (Jueves) a las 11:00 hrs"
    }

    print("\n" + "📅 HORARIOS DISPONIBLES EN CENTRO VETCARE:")
    for clave, horario in opciones.items():
        print(f"   [{clave}] {horario}")
    print("-" * 50)

    while True:
        eleccion = input("👉 Seleccione el número de su preferencia (1, 2 o 3): ").strip()
        if eleccion in opciones:
            horario_seleccionado = opciones[eleccion]
            print(f" ✅ Horario reservado: {horario_seleccionado}")
            return horario_seleccionado
        print(" ❌ Selección fuera de rango. Por favor ingrese solo 1, 2 o 3.")


# ==============================================================================
# BUCLE PRINCIPAL
# ==============================================================================

def iniciar_chat_interactivo():
    print("=" * 70)
    print("       CENTRO VETERINARIO VETCARE - SISTEMA MULTI-AGENTE")
    print("=" * 70)

    config = Configuracion.desde_entorno()
    if config.email_emisor:
        print(f" 🔑 [SISTEMA]: Credenciales SMTP detectadas para: {config.email_emisor}")

    gestor_sesiones = GestorSesionesJSON("historial_sesiones.json")
    servicio_correo = ServicioCorreoReal(config)
    servicio_rag = ServicioVectorialFAISS("base_vectorial_vetcare")
    servicio_uf = ServicioIndicadoresEconomicos()
    servicio_qr = ServicioGeneradorQR()

    agente_1 = AgenteTriajeYMemoria(gestor_sesiones, config)
    agente_2 = AgentePreConsulta(servicio_rag, servicio_uf, config)
    agente_3 = AgenteNotificadorCitas(servicio_correo, servicio_qr)

    print("\nBienvenido al portal de atención VetCare.")
    correo_cliente = pedir_correo_valido()

    ingreso = agente_1.gestionar_ingreso_cliente(correo_cliente)
    
    if ingreso["tiene_historial"]:
        print("\n" + "-" * 50)
        print(ingreso["mensaje"])
        print("-" * 50)
        opcion = input("\n¿Desea CONTINUAR una consulta existente (escriba el ID) o crear una NUEVA (presione Enter)?: ").strip()
        
        if opcion in ingreso["ids_sesiones"]:
            id_sesion = opcion
            print(f"✅ Reanudando la sesión '{id_sesion}'.")
        else:
            id_sesion = f"sesion_{os.urandom(2).hex()}"
            print(f"✨ Creando nueva sesión con ID '{id_sesion}'.")
    else:
        id_sesion = f"sesion_{os.urandom(2).hex()}"
        print(f"\n✨ {ingreso['mensaje']} (ID de sesión: {id_sesion})")

    nombre_mascota = pedir_texto_valido("👉 Nombre de su mascota: ", min_len=2, campo="Nombre de mascota")
    especie_mascota = pedir_especie_valida()

    print("\n" + "=" * 70)
    print(" Puede escribir sus síntomas o la razón de su consulta.")
    print(" Escriba 'salir' en cualquier momento para terminar.")
    print("=" * 70 + "\n")

    while True:
        consulta = input(f"👤 [{nombre_mascota}]: ").strip()
        
        if consulta.lower() in ["salir", "exit", "quit"]:
            print("\nGracias por consultar en VetCare. ¡Hasta pronto!")
            break

        if len(consulta) < 4 or not any(c.isalpha() for c in consulta):
            print(" ❌ Por favor, describa los síntomas con más detalle (ej: 'tiene tos y vomita').")
            continue

        res_triaje = agente_1.procesar_consulta(correo_cliente, id_sesion, consulta)
        print(f"\n🤖 [{res_triaje.agente_emisor}]: {res_triaje.contenido}")

        res_preconsulta = agente_2.elaborar_ficha(
            datos_triaje=res_triaje.datos_extra,
            especie=especie_mascota,
            nombre_mascota=nombre_mascota
        )
        print(f"🤖 [{res_preconsulta.agente_emisor}]: {res_preconsulta.contenido}")

        desea_agendar = pedir_confirmacion_si_no("\n¿Desea agendar una cita presencial para este caso? (s/n): ")
        
        if desea_agendar:
            horario_elegido = seleccionar_horario_disponible()
            
            cita = Cita(
                dueno="Cliente VetCare",
                mascota=nombre_mascota,
                correo=correo_cliente,
                fecha_hora=horario_elegido,
                motivo=consulta,
                indicaciones_previas=res_preconsulta.datos_extra["indicaciones_previas"]
            )

            res_cita = agente_3.agendar_y_confirmar(cita)
            print(f"🤖 [{res_cita.agente_emisor}]: {res_cita.contenido}")
            
            gestor_sesiones.guardar_mensaje(correo_cliente, id_sesion, "agente_citas", res_cita.contenido)
            break
        
        print("\n" + "-" * 50)


if __name__ == "__main__":
    iniciar_chat_interactivo()