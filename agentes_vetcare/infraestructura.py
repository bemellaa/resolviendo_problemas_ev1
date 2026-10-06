import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# Carga opcional de librerías vectoriales (FAISS y Embeddings)
try:
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings
    FAISS_DISPONIBLE = True
except ImportError:
    FAISS_DISPONIBLE = False


@dataclass
class Configuracion:
    """Carga variables de entorno para los modelos."""
    api_key: str
    modelo: str

    @classmethod
    def desde_entorno(cls) -> "Configuracion":
        api_key = os.getenv("GROQ_API_KEY", "")
        modelo = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return cls(api_key=api_key, modelo=modelo)


class GestorSesionesJSON:
    """Maneja la persistencia de chats anteriores por cliente en un archivo JSON."""

    def __init__(self, ruta_archivo: str = "historial_sesiones.json"):
        self.ruta_archivo = ruta_archivo
        self._inicializar_storage()

    def _inicializar_storage(self):
        if not os.path.exists(self.ruta_archivo):
            with open(self.ruta_archivo, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _leer_todas(self) -> dict:
        try:
            with open(self.ruta_archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def guardar_mensaje(self, correo: str, id_sesion: str, rol: str, contenido: str):
        datos = self._leer_todas()
        if correo not in datos:
            datos[correo] = {}
        if id_sesion not in datos[correo]:
            datos[correo][id_sesion] = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        datos[correo][id_sesion].append({
            "rol": rol,
            "contenido": contenido,
            "timestamp": timestamp
        })

        with open(self.ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def obtener_sesiones_usuario(self, correo: str) -> Dict[str, List[dict]]:
        datos = self._leer_todas()
        return datos.get(correo, {})


class ServicioVectorialFAISS:
    """Carga y consulta la base vectorial FAISS existente en el proyecto."""

    def __init__(self, ruta_base_vectorial: str = "base_vectorial_vetcare"):
        self.ruta = ruta_base_vectorial
        self.vector_store = None
        self._cargar_indice()

    def _cargar_indice(self):
        if not FAISS_DISPONIBLE:
            print(" [INFRAESTRUCTURA]: LangChain/FAISS no instalado. Se usará búsqueda de respaldo.")
            return

        if os.path.exists(self.ruta):
            try:
                # Usamos un modelo estándar de HuggingFace para embeddings de contexto
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                self.vector_store = FAISS.load_local(
                    self.ruta,
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f" [INFRAESTRUCTURA]: Base Vectorial FAISS cargada exitosamente desde '{self.ruta}'.")
            except Exception as e:
                print(f" ⚠️ [INFRAESTRUCTURA]: Error al cargar FAISS ({e}). Usando modo seguro.")
        else:
            print(f" ⚠️ [INFRAESTRUCTURA]: No se encontró el directorio '{self.ruta}'.")

    def buscar_informacion(self, consulta: str, k: int = 2) -> str:
        """Realiza búsqueda por similitud en la base vectorial de VetCare."""
        if self.vector_store:
            docs = self.vector_store.similarity_search(consulta, k=k)
            return "\n".join([doc.page_content for doc in docs])
        
        # Respuesta de respaldo en caso de no tener FAISS cargado en memoria
        return (
            "Pautas generales: Mantener a la mascota tranquila, evitar administración "
            "de fármacos sin indicación médica presencial y transportar en kennel seguro."
        )


class ServicioCorreoSimulado:
    """Servicio de infraestructura para el envío de correos de confirmación."""

    @staticmethod
    def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
        print("\n" + "=" * 60)
        print(" ✉️  [SERVICIO SMTP DE INFRAESTRUCTURA - CORREO SALIENTE]")
        print(f" Para: {destinatario}")
        print(f" Asunto: {asunto}")
        print("------------------------------------------------------------")
        print(cuerpo)
        print("------------------------------------------------------------")
        print(" ✅ Estado: Correo entregado al servidor de destino correctamente.")
        print("=" * 60 + "\n")
        return True