from typing import Dict, Any, Optional
from agentes_vetcare.dominio import (
    RespuestaAgente,
    FichaClinicaPrevia,
    Cita
)
from agentes_vetcare.infraestructura import (
    GestorSesionesJSON,
    ServicioCorreoReal,
    ServicioVectorialFAISS,
    Configuracion
)


class AgenteTriajeYMemoria:
    """AGENTE 1: Recepción, gestión de historial de chats y clasificación de urgencia."""

    PROMPT_SISTEMA = (
        "Eres el Agente de Triaje de VetCare. Tu función es recibir al cliente, "
        "gestionar su historial de atención previo y clasificar el nivel de urgencia."
    )

    def __init__(self, gestor_sesiones: GestorSesionesJSON, config: Configuracion):
        self.gestor = gestor_sesiones
        self.config = config

    def gestionar_ingreso_cliente(self, correo: str) -> Dict[str, Any]:
        sesiones = self.gestor.obtener_sesiones_usuario(correo)
        if not sesiones:
            return {
                "tiene_historial": False,
                "mensaje": "No se encontraron consultas anteriores. Creando un nuevo chat."
            }

        resumen = []
        for id_ses, msgs in sesiones.items():
            ultimo_msg = msgs[-1]["contenido"] if msgs else "Sin mensajes"
            fecha = msgs[0]["timestamp"] if msgs else "Sin fecha"
            resumen.append(f"• ID: [{id_ses}] - Fecha: {fecha} - Último tema: '{ultimo_msg[:35]}...'")

        return {
            "tiene_historial": True,
            "mensaje": "Se encontraron las siguientes consultas anteriores:\n" + "\n".join(resumen),
            "ids_sesiones": list(sesiones.keys())
        }

    def procesar_consulta(self, correo: str, id_sesion: str, mensaje_usuario: str) -> RespuestaAgente:
        self.gestor.guardar_mensaje(correo, id_sesion, "usuario", mensaje_usuario)

        mensaje_lower = mensaje_usuario.lower()
        palabras_criticas = ["sangre", "convulsion", "atropellado", "no respira", "inconsciente"]
        
        if any(p in mensaje_lower for p in palabras_criticas):
            urgencia = "ALTA (URGENCIA MÉDICA)"
            indicacion = "Atención prioritaria inmediata recomendada."
        elif any(p in mensaje_lower for p in ["vomito", "diarrea", "decai", "no come", "fiebre"]):
            urgencia = "MEDIA"
            indicacion = "Evaluación dentro de las próximas 24 horas."
        else:
            urgencia = "BAJA"
            indicacion = "Consulta general o preventiva."

        respuesta_texto = f"Consulta registrada. Evaluación de triaje: Urgencia {urgencia}. {indicacion}"
        self.gestor.guardar_mensaje(correo, id_sesion, "agente_triaje", respuesta_texto)

        return RespuestaAgente(
            agente_emisor="Agente 1 (Triaje y Memoria)",
            contenido=respuesta_texto,
            datos_extra={
                "nivel_urgencia": urgencia,
                "consulta": mensaje_usuario,
                "correo": correo,
                "id_sesion": id_sesion
            }
        )


class AgentePreConsulta:
    """AGENTE 2: Genera la Ficha Pre-Clínica apoyándose en RAG (Base Vectorial FAISS)."""

    def __init__(self, servicio_rag: ServicioVectorialFAISS, config: Configuracion):
        self.rag = servicio_rag
        self.config = config

    def elaborar_ficha(self, datos_triaje: dict, especie: str, nombre_mascota: str) -> RespuestaAgente:
        urgencia = datos_triaje.get("nivel_urgencia", "BAJA")
        sintomas = datos_triaje.get("consulta", "Sin especificar")

        contexto_recuperado = self.rag.buscar_informacion(f"cuidados transporte seguridad {especie} {sintomas}")

        if especie.lower() in ["gato", "felino"]:
            transporte = "Utilizar caja de transporte rígida y cubierta con manta para reducir estrés."
        else:
            transporte = "Llevar con arnés/correa corta y bozal si presenta dolor o inquietud."

        indicaciones = (
            f"1. {transporte}\n"
            f"2. Mantener en reposo sin administrar fármacos de uso humano o veterinario sin orden presencial.\n"
            f"3. Pauta basada en base de conocimiento: {contexto_recuperado[:120]}...\n"
            f"4. Traer carnet de vacunación y registro de atenciones previas."
        )

        ficha = FichaClinicaPrevia(
            nombre_mascota=nombre_mascota,
            especie=especie,
            sintomas=sintomas,
            nivel_urgencia=urgencia,
            indicaciones_transporte=indicaciones
        )

        return RespuestaAgente(
            agente_emisor="Agente 2 (Pre-Consulta y Ficha Clínica)",
            contenido=f"Ficha pre-clínica elaborada para '{nombre_mascota}' incorporando RAG de la base vectorial.",
            datos_extra={
                "ficha": ficha,
                "indicaciones_previas": indicaciones
            }
        )


class AgenteNotificadorCitas:
    """AGENTE 3: Gestión de reserva de hora y envío de correos de confirmación."""

    def __init__(self, servicio_correo: ServicioCorreoReal):
        self.servicio_correo = servicio_correo

    def agendar_y_confirmar(self, cita: Cita) -> RespuestaAgente:
        asunto = f"Confirmación de Cita Veterinaria - {cita.mascota}"
        
        cuerpo = (
            f"Estimado/a {cita.dueno},\n\n"
            f"Confirmamos la reserva de su cita veterinaria presencial con el equipo de VetCare.\n\n"
            f" 🗓️  Mascota: {cita.mascota}\n"
            f" 📅 Fecha y Hora: {cita.fecha_hora}\n"
            f" 📋 Motivo de Consulta: {cita.motivo}\n\n"
            f" ⚠️ INSTRUCCIONES DE PREPARACIÓN Y SEGURIDAD:\n"
            f"{cita.indicaciones_previas or 'Llegar 10 minutos antes de la hora acordada.'}\n\n"
            f"La ficha clínica previa ya ha sido cargada en nuestro sistema para la revisión del veterinario.\n\n"
            f"Atentamente,\n"
            f"Centro Médico Veterinario VetCare"
        )

        exito = self.servicio_correo.enviar_correo(
            destinatario=cita.correo,
            asunto=asunto,
            cuerpo=cuerpo
        )

        return RespuestaAgente(
            agente_emisor="Agente 3 (Gestión de Citas y Correos)",
            contenido=f"Cita confirmada exitosamente para el {cita.fecha_hora} y correo enviado a {cita.correo}.",
            exitoso=exito
        )