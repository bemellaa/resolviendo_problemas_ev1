# Arquitectura del chatbot VetCare

El sistema utiliza una arquitectura RAG que combina documentos internos simulados de VetCare con fuentes externas oficiales. Las consultas pasan por reglas de seguridad, recuperación de información y generación de respuestas mediante Groq. LangSmith registra y evalúa el funcionamiento del sistema.

```mermaid
flowchart TD
    subgraph BC["Preparación de la base de conocimiento"]
        A["Documentos internos de VetCare<br/>agenda, servicios, urgencias y FAQ"]
        B["Fuentes externas verificadas<br/>FDA, ASPCA y WSAVA"]
        C["Carga de documentos<br/>y asignación de metadatos"]
        D["Fragmentación del texto<br/>500 caracteres y solapamiento 80"]
        E["Embeddings multilingües<br/>MiniLM-L12-v2"]
        F[("Base vectorial FAISS<br/>128 fragmentos")]

        A --> C
        B --> C
        C --> D
        D --> E
        E --> F
    end

    subgraph RAG["Procesamiento de una consulta"]
        G["Usuario"]
        H["Interfaz VetBot<br/>ipywidgets"]
        I["Orquestador VetCare V5<br/>detección de intención"]
        J{"Tipo de consulta"}
        K["Recuperación exacta<br/>de agenda"]
        L["Barreras determinísticas<br/>seguridad y dominio"]
        M["Recuperador vectorial<br/>FAISS, k = 6"]
        N["Construcción del contexto<br/>y selección de fuentes"]
        O["Prompt del sistema<br/>reglas y restricciones"]
        P["Modelo Groq<br/>openai/gpt-oss-120b"]
        Q["Respuesta fundamentada<br/>con fuentes recuperadas"]

        G --> H
        H --> I
        I --> J
        J -->|"Agenda"| K
        J -->|"Medicamentos, urgencias<br/>o fuera del dominio"| L
        J -->|"Consulta general"| M
        K --> N
        L --> N
        M --> N
        N --> O
        O --> P
        P --> Q
        Q --> H
    end

    F --> M
    A --> K
    A --> L
    B --> L

    S["LangSmith<br/>trazas, datasets y evaluaciones"]
    S -. "Observabilidad" .-> I
    S -. "Evaluación" .-> P
    S -. "Métricas" .-> Q
```

## Componentes principales

- **Fuentes internas:** información simulada sobre agenda, servicios, cuidados, preguntas frecuentes y urgencias de VetCare.
- **Fuentes externas:** documentos elaborados a partir de información oficial de FDA, ASPCA y WSAVA.
- **Embeddings:** modelo `paraphrase-multilingual-MiniLM-L12-v2`.
- **Base vectorial:** FAISS con los fragmentos de los documentos internos y externos.
- **Modelo generativo:** `openai/gpt-oss-120b`, utilizado mediante la API de Groq.
- **Seguridad:** barreras determinísticas para medicamentos, urgencias, reservas y preguntas fuera del dominio.
- **Observabilidad:** LangSmith registra las ejecuciones y permite evaluar recuperación, seguridad y uso de fuentes.