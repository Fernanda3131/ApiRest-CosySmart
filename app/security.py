
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

if not SECRET_KEY:
    raise ValueError("No se encontró JWT_SECRET_KEY en el archivo .env")


def crear_access_token(data: dict):
    """
    Genera un token JWT con tiempo de expiración.
    """

    datos_token = data.copy()

    fecha_expiracion = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    datos_token.update({
        "exp": fecha_expiracion
    })

    token = jwt.encode(
        datos_token,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token
