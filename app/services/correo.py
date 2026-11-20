
import os

from email.message import EmailMessage
from aiosmtplib import send

"""Descripción:
    Centraliza las operaciones de envío de correos
    electrónicos utilizadas por CosySmart.

Responsabilidades:
    - Preparar el contenido de los mensajes.
    - Configurar los datos del destinatario.
    - Gestionar el envío de correos electrónicos.
    - Procesar errores durante la comunicación con
      el servidor de correo.
    - Mantener separada la lógica de correo de los routers.

Configuración:
    Los datos de conexión y las credenciales del servidor
    de correo deben obtenerse de variables de entorno."""


async def enviar_codigo_recuperacion(
    destinatario: str,
    codigo: str
):
    mensaje = EmailMessage()

    mensaje["From"] = os.getenv("SMTP_FROM")
    mensaje["To"] = destinatario
    mensaje["Subject"] = "Recuperación de contraseña - CosySmart"

    mensaje.set_content(
        f"""
Hola,

Hemos recibido una solicitud para recuperar tu contraseña de CosySmart.

Tu código de verificación es:

{codigo}

Este código tiene una vigencia de 10 minutos.

Si no solicitaste este proceso, puedes ignorar este correo.

Por seguridad, no compartas este código con nadie.

Equipo CosySmart
"""
    )

    await send(
        mensaje,
        hostname=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASSWORD"),
        start_tls=True,
        timeout=20
    )
