import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agentes_vetcare.infraestructura import (
    Configuracion,
    GestorSesionesJSON,
    ServicioCorreoSimulado,
    ServicioVectorialFAISS
)
from agentes_vetcare.agentes import (
    AgenteTriajeYMemoria,
    AgentePreConsulta,
    AgenteNotificadorCitas
)
from agentes_vetcare.dominio import Cita


def iniciar_chat_interactivo():
    print("=" * 70)
    print("       CENTRO VETERINARIO VETCARE - SISTEMA MULTI-AGENTE")
    print("=" * 70)

    # 1. Inicialización de Capa de Infraestructura
    config = Configuracion.desde_entorno()
    gestor_sesiones = GestorSesionesJSON("historial_sesiones.json")
    servicio_correo = ServicioCorreoSimulado()
    servicio_rag = ServicioVectorialFAISS("base_vectorial_vetcare")

    # 2. Inicialización de Agentes
    agente_1 = AgenteTriajeYMemoria(gestor_sesiones, config)
    agente_2 = AgentePreConsulta(servicio_rag, config)
    agente_3 = AgenteNotificadorCitas(servicio_correo)

    # 3. Datos iniciales del cliente
    print("\nBienvenido al portal de atención VetCare.")
    correo_cliente = input("👉 Ingrese su correo electrónico: ").strip()
    
    if not correo_cliente:
        correo_cliente = "cliente.demo@example.com"
        print(f"Usando correo predeterminado: {correo_cliente}")

    # Verificar historial en el Agente 1
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

    nombre_mascota = input("\n👉 Nombre de su mascota: ").strip() or "Mascota"
    especie_mascota = input("👉 Especie (ej. Perro, Gato): ").strip() or "Perro"

    print("\n" + "=" * 70)
    print(" Puede escribir sus síntomas o la razón de su consulta.")
    print(" Escriba 'salir' en cualquier momento para terminar.")
    print("=" * 70 + "\n")

    while True:
        consulta = input(f"👤 [{nombre_mascota}]: ").strip()
        
        if consulta.lower() in ["salir", "exit", "quit"]:
            print("\nGracias por consultar en VetCare. ¡Hasta pronto!")
            break

        if not consulta:
            continue

        # --- FLUJO MULTI-AGENTE EN SECUENCIA ---
        
        # AGENTE 1: Triaje y Memoria
        res_triaje = agente_1.procesar_consulta(correo_cliente, id_sesion, consulta)
        print(f"\n🤖 [{res_triaje.agente_emisor}]: {res_triaje.contenido}")

        # AGENTE 2: Pre-Consulta y Ficha Técnica
        res_preconsulta = agente_2.elaborar_ficha(
            datos_triaje=res_triaje.datos_extra,
            especie=especie_mascota,
            nombre_mascota=nombre_mascota
        )
        print(f"🤖 [{res_preconsulta.agente_emisor}]: {res_preconsulta.contenido}")

        # Preguntar si desea agendar cita
        agendar = input("\n¿Desea agendar una cita presencial para este caso? (s/n): ").strip().lower()
        if agendar in ["s", "si", "sí", "y"]:
            fecha = input("Ingrese la fecha y hora deseada (ej. Mañana a las 15:00): ").strip() or "Mañana a las 10:00 hrs"
            
            cita = Cita(
                dueno="Cliente VetCare",
                mascota=nombre_mascota,
                correo=correo_cliente,
                fecha_hora=fecha,
                motivo=consulta,
                indicaciones_previas=res_preconsulta.datos_extra["indicaciones_previas"]
            )

            res_cita = agente_3.agendar_y_confirmar(cita)
            print(f"🤖 [{res_cita.agente_emisor}]: {res_cita.contenido}")
            
            # Guardar hito de agendamiento en el historial JSON
            gestor_sesiones.guardar_mensaje(correo_cliente, id_sesion, "agente_citas", res_cita.contenido)
            break
        
        print("\n" + "-" * 50)


if __name__ == "__main__":
    iniciar_chat_interactivo()