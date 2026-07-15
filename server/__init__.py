"""
server/ — Backend de aprendizaje colectivo de LoL Coach.

Paquete independiente del cliente: la app Streamlit NO importa nada de
aquí (solo le habla por HTTP). Sus dependencias viven en
server/requirements.txt y no se instalan en el cliente.

Ejecución local:
    pip install -r server/requirements.txt
    uvicorn server.app:app --port 8787

Producción:
    DATABASE_URL=postgresql+psycopg://... uvicorn server.app:app
"""
