
import base64
import getpass
import json
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def decodificar_base64(valor):
    padding = "=" * (-len(valor) % 4)
    return base64.urlsafe_b64decode(valor + padding)


def codificar_base64(valor):
    return base64.urlsafe_b64encode(valor).decode("ascii").rstrip("=")


print("=== PRUEBA DE FIRMA BIOMÉTRICA COSYSMART ===")

challenge_id = input("ChallengeId: ").strip()
id_credencial = input("IdCredencial: ").strip()
nonce = input("Nonce: ").strip()

contrasena = getpass.getpass("Contraseña de la clave privada: ")

ruta_clave = Path(__file__).parent / "clave_privada_biometrica.pem"

with open(ruta_clave, "rb") as archivo:
    clave_privada = serialization.load_pem_private_key(
        archivo.read(),
        password=contrasena.encode("utf-8")
    )

nonce_bytes = decodificar_base64(nonce)

mensaje = b"\n".join([
    b"COSYSMART|BIOMETRIA_LOGIN|V1",
    challenge_id.lower().encode("ascii"),
    id_credencial.lower().encode("ascii"),
    nonce_bytes
])

firma = clave_privada.sign(
    mensaje,
    ec.ECDSA(hashes.SHA256())
)

resultado = {
    "Correo": input("Correo del usuario: ").strip(),
    "IdCredencial": id_credencial,
    "ChallengeId": challenge_id,
    "Nonce": nonce,
    "Firma": codificar_base64(firma)
}

print("\n=== JSON PARA SWAGGER ===")
print(json.dumps(resultado, indent=4))
