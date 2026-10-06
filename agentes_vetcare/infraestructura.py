import json
import os
import smtplib
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# Carga opcional de librerías vectoriales
try:
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings
    FAISS_DISPONIBLE = True
except ImportError:
    FAISS_DISPONIBLE = False


@dataclass
class Configuracion:
    """Carga variables de entorno para los modelos y credenciales de correo."""
    api_key: str
    modelo: str
    email_emisor: str
    email_password: str

    @classmethod
    def desde_entorno(cls) -> "Configuracion":
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        return cls(
            api_key=os.getenv("GROQ_API_KEY", "").strip(),
            modelo=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
            email_emisor=os.getenv("EMAIL_EMISOR", "").strip(),
            email_password=os.getenv("EMAIL_PASSWORD", "").replace(" ", "").strip()
        )


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
    """Carga y consulta la base vectorial FAISS con Lazy Loading."""

    def __init__(self, ruta_base_vectorial: str = "base_vectorial_vetcare"):
        self.ruta = ruta_base_vectorial
        self.vector_store = None
        self._intentado_cargar = False

    def _cargar_indice_lazy(self):
        if self._intentado_cargar:
            return
        self._intentado_cargar = True

        if not FAISS_DISPONIBLE:
            return

        if os.path.exists(self.ruta):
            try:
                print("\n ⏳ [INFRAESTRUCTURA]: Cargando base vectorial FAISS en segundo plano...")
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                self.vector_store = FAISS.load_local(
                    self.ruta,
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                print(" ✅ [INFRAESTRUCTURA]: Base Vectorial FAISS lista para consultas.\n")
            except Exception as e:
                print(f" ⚠️ [INFRAESTRUCTURA]: Error al cargar FAISS ({e}). Usando respuesta de respaldo.")

    def buscar_informacion(self, consulta: str, k: int = 2) -> str:
        self._cargar_indice_lazy()
        if self.vector_store:
            docs = self.vector_store.similarity_search(consulta, k=k)
            return "\n".join([doc.page_content for doc in docs])
        return "Mantener a la mascota tranquila y libre de estrés durante el traslado."


# ==============================================================================
# INTEGRACIÓN DE APIS EXTERNAS
# ==============================================================================

class ServicioIndicadoresEconomicos:
    """API EXTERNA 1: Consulta en tiempo real el valor de la UF desde mindicador.cl."""

    def obtener_valor_uf(self) -> float:
        try:
            url = "https://mindicador.cl/api"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                valor_uf = float(data.get('uf', {}).get('valor', 38000.0))
                print(f" 🌐 [API EXTERNA mindicador.cl]: Valor UF obtenido en tiempo real: ${valor_uf:,.2f} CLP")
                return valor_uf
        except Exception:
            print(" ⚠️ [API EXTERNA]: No se pudo conectar a mindicador.cl. Usando valor estimado de respaldo.")
            return 38500.0


class ServicioGeneradorQR:
    """API EXTERNA 2: Genera un pase de atención con código QR único mediante qrserver.com."""

    def generar_url_qr(self, resumen_cita: str) -> str:
        texto_encodeado = urllib.parse.quote(resumen_cita)
        url_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={texto_encodeado}"
        print(" 🌐 [API EXTERNA qrserver.com]: Enlace de pase QR generado con éxito.")
        return url_qr


class ServicioCorreoReal:
    """Servicio de infraestructura para el envío REAL de correos mediante SMTP SSL Gmail (Puerto 465)."""

    def __init__(self, config: Configuracion):
        self.emisor = config.email_emisor
        self.password = config.email_password

    def enviar_correo(self, destinatario: str, asunto: str, cuerpo: str) -> bool:
        if not self.emisor or not self.password or "tu_correo" in self.emisor:
            print("\n ⚠️  [SMTP]: Credenciales incompletas en .env.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.emisor
            msg['To'] = destinatario
            msg['Subject'] = asunto
            msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
                servidor.login(self.emisor, self.password)
                servidor.send_message(msg)

            print(f"\n ✉️  [SMTP REAL]: ¡Correo electrónico enviado con éxito a '{destinatario}'!")
            return True

        except Exception as e:
            print(f"\n ❌ [SMTP ERROR]: Falló el envío del correo real: {e}")
            return False