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
    ServicioIndicadoresEconomicos,
    ServicioGeneradorQR,
    Configuracion
)


class AgenteTriajeYMemoria:
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
        if any(p in mensaje_lower for p in ["sangre", "convulsion", "atropellado", "no respira"]):
            urgencia = "ALTA (URGENCIA MÉDICA)"
            indicacion = "Atención prioritaria inmediata recomendada."
        elif any(p in mensaje_lower for p in ["vomito", "vomitos", "diarrea", "decai", "no come", "fiebre"]):
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
    def __init__(self, servicio_rag: ServicioVectorialFAISS, servicio_uf: ServicioIndicadoresEconomicos, config: Configuracion):
        self.rag = servicio_rag
        self.servicio_uf = servicio_uf
        self.config = config

    def elaborar_ficha(self, datos_triaje: dict, especie: str, nombre_mascota: str) -> RespuestaAgente:
        urgencia = datos_triaje.get("nivel_urgencia", "BAJA")
        sintomas = datos_triaje.get("consulta", "Sin especificar")

        contexto_recuperado = self.rag.buscar_informacion(f"cuidados transporte seguridad {especie} {sintomas}")
        valor_uf = self.servicio_uf.obtener_valor_uf()
        arancel_clp = 35000
        equivalencia_uf = arancel_clp / valor_uf if valor_uf > 0 else 0.85

        if especie.lower() in ["gato", "gata", "felino"]:
            transporte = "Utilizar caja de transporte rígida y cubierta con manta para reducir estrés."
        else:
            transporte = "Llevar con arnés/correa corta y bozal si presenta dolor o inquietud."

        indicaciones = (
            f"1. {transporte}\n"
            f"2. Mantener en reposo sin administrar fármacos de uso humano o veterinario sin orden presencial.\n"
            f"3. Pauta RAG base conocimiento: {contexto_recuperado[:120]}...\n"
            f"4. Arancel estimado consulta presencial: $35.000 CLP (~{equivalencia_uf:.2f} UF para seguro médico)."
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
            contenido=f"Ficha pre-clínica elaborada para '{nombre_mascota}' ({especie}) incorporando RAG y cotización UF ({equivalencia_uf:.2f} UF).",
            datos_extra={
                "ficha": ficha,
                "indicaciones_previas": indicaciones
            }
        )


class AgenteNotificadorCitas:
    def __init__(self, servicio_correo: ServicioCorreoReal, servicio_qr: ServicioGeneradorQR):
        self.servicio_correo = servicio_correo
        self.servicio_qr = servicio_qr

    def agendar_y_confirmar(self, cita: Cita) -> RespuestaAgente:
        # Formato de Ticket Digital estructurado para lectura móvil
        ticket_qr_texto = (
            "========================================\n"
            "   🏥 CENTRO MÉDICO VETCARE             \n"
            "   🎫 TICKET DIGITAL DE CHECK-IN        \n"
            "========================================\n"
            f"🐾 Mascota: {cita.mascota}\n"
            f"📅 Fecha/Hora: {cita.fecha_hora}\n"
            f"📧 Tutor: {cita.correo}\n"
            f"📋 Motivo: {cita.motivo[:30]}\n"
            "========================================\n"
            " STATUS: RESERVA CONFIRMADA EN SISTEMA   \n"
            " Presente este ticket en recepción.     \n"
            "========================================"
        )

        url_qr = self.servicio_qr.generar_url_qr(ticket_qr_texto)

        asunto = f"Confirmación de Cita Veterinaria - {cita.mascota}"
        
        cuerpo = (
            f"Estimado/a Cliente VetCare,\n\n"
            f"Confirmamos la reserva de su cita veterinaria presencial con el equipo de VetCare.\n\n"
            f" 🗓  Mascota: {cita.mascota}\n"
            f" 📅 Fecha y Hora: {cita.fecha_hora}\n"
            f" 📋 Motivo de Consulta: {cita.motivo}\n\n"
            f" 📲 SU PASE DE ATENCIÓN DIGITAL / CÓDIGO QR:\n"
            f" Muestre el siguiente código QR desde su celular al llegar a la recepción:\n"
            f" {url_qr}\n\n"
            f" ⚠️ INSTRUCCIONES DE PREPARACIÓN Y SEGURIDAD:\n"
            f"{cita.indicaciones_previas}\n\n"
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
            contenido=f"Cita confirmada para el {cita.fecha_hora}. Se adjuntó pase QR y correo enviado a {cita.correo}.",
            exitoso=exito
        )