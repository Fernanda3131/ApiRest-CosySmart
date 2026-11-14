
from pathlib import Path
from getpass import getpass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


BASE_DIR = Path(__file__).resolve().parent

ARCHIVO_PRIVADA = BASE_DIR / "clave_privada_biometrica.pem"
ARCHIVO_PUBLICA = BASE_DIR / "clave_publica_biometrica.pem"


def main():
    if ARCHIVO_PRIVADA.exists() or ARCHIVO_PUBLICA.exists():
        print("Ya existen archivos de claves. No se sobrescribirán.")
        return

    password = getpass("Crea una contraseña para proteger la clave privada: ")
    confirmacion = getpass("Confirma la contraseña: ")

    if len(password) < 8 or password != confirmacion:
        print("La contraseña debe tener al menos 8 caracteres y coincidir.")
        return

    # Generar clave privada ECDSA usando curva P-256
    clave_privada = ec.generate_private_key(ec.SECP256R1())

    # Exportar clave privada protegida con contraseña
    privada_pem = clave_privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(
            password.encode("utf-8")
        )
    )

    # Obtener y exportar clave pública
    clave_publica = clave_privada.public_key()

    publica_pem = clave_publica.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    ARCHIVO_PRIVADA.write_bytes(privada_pem)
    ARCHIVO_PUBLICA.write_bytes(publica_pem)

    print("\nClaves generadas correctamente.")
    print(f"Clave privada: {ARCHIVO_PRIVADA.name}")
    print(f"Clave pública: {ARCHIVO_PUBLICA.name}")
    print("\nLa clave privada NO debe compartirse.")


if __name__ == "__main__":
    main()
