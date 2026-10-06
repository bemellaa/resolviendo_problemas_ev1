from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class MensajeChat:
    """Modelo para registrar cada mensaje del historial."""
    rol: str
    contenido: str
    timestamp: str


@dataclass
class FichaClinicaPrevia:
    """Modelo de dominio para la ficha pre-consulta (Agente 2)."""
    nombre_mascota: str
    especie: str
    sintomas: str
    nivel_urgencia: str
    indicaciones_transporte: str


@dataclass
class Cita:
    """Modelo de dominio para la reserva de citas (Agente 3)."""
    dueno: str
    mascota: str
    correo: str
    fecha_hora: str
    motivo: str
    indicaciones_previas: Optional[str] = None


@dataclass
class RespuestaAgente:
    """Respuesta estandarizada que devuelve cada uno de los 3 agentes."""
    agente_emisor: str
    contenido: str
    datos_extra: Optional[Dict[str, Any]] = None
    exitoso: bool = True
    error: Optional[str] = None