# CosySmart - API REST

API REST oficial de **CosySmart**, una plataforma web y móvil diseñada para la gestión, exhibición y comercialización de muebles multifuncionales orientados a optimizar espacios pequeños.

El backend proporciona servicios para la administración de usuarios, gestión del catálogo de mobiliario, autenticación y seguridad de la plataforma.

## Tecnologías utilizadas

- **Lenguaje de programación:** Python.
- **Framework backend:** FastAPI.
- **ORM:** SQLAlchemy.
- **Base de datos:** Microsoft SQL Server.
- **Autenticación:** JWT (JSON Web Tokens).
- **Criptografía biométrica:** ECDSA P-256 y SHA-256.
- **Control de versiones:** Git y GitHub.

## Características principales

### Gestión de usuarios
- Registro e inicio de sesión.
- Autenticación mediante tokens JWT.
- Gestión de roles diferenciados: compradores, vendedores y administradores.
- Protección de endpoints según los permisos de autenticación.

### Catálogo de mobiliario
- Administración y consulta de muebles multifuncionales.
- Gestión de productos orientados a la optimización de espacios pequeños.
- Consultas y filtros relacionados con las características y dimensiones del mobiliario.

### Seguridad y autenticación
- Autenticación tradicional mediante credenciales.
- Protección de rutas mediante JWT.
- Registro de dispositivos autorizados.
- Autenticación biométrica basada en criptografía asimétrica.
- Validación de firmas digitales mediante ECDSA P-256 y SHA-256.
- Generación de desafíos criptográficos de un solo uso.
- Expiración de desafíos para reducir ataques de repetición.
- Revocación de dispositivos registrados.

## Autenticación biométrica

CosySmart implementa un mecanismo de autenticación biométrica basado en la verificación de firmas digitales.

El backend no almacena huellas dactilares ni imágenes faciales. La autenticación biométrica se plantea para realizarse localmente en el dispositivo Android, mientras que el servidor verifica la posesión de una clave criptográfica privada autorizada.

### Funcionamiento

**1. Registro del dispositivo**

El usuario debe autenticarse previamente mediante el mecanismo tradicional.

Posteriormente, el dispositivo se registra enviando su nombre, clave pública y algoritmo criptográfico permitido.

El backend almacena la clave pública y genera un identificador único de credencial (`IdCredencial`) asociado al dispositivo.

**2. Generación del desafío**

El dispositivo solicita un desafío al endpoint `/biometria/desafio`.

El backend genera un nonce criptográficamente aleatorio de 32 bytes, almacena su hash SHA-256 y establece una expiración de dos minutos.

La respuesta contiene:
- `ChallengeId`: identificador único del desafío.
- `Nonce`: valor aleatorio codificado en Base64 URL-safe.
- `FechaExpiracion`: fecha límite para completar la autenticación.

**3. Firma digital**

El dispositivo debe utilizar su clave privada para firmar un mensaje que contiene:

- Identificador del proceso de autenticación.
- Identificador del desafío.
- Identificador de la credencial.
- Nonce recibido del servidor.

La firma utiliza el algoritmo ECDSA con curva P-256 y SHA-256.

El mensaje canónico tiene la siguiente estructura:

```text
COSYSMART|BIOMETRIA_LOGIN|V1
ChallengeId
IdCredencial
Nonce
```

Los elementos se concatenan mediante saltos de línea. El nonce se incorpora en su representación binaria.

**4. Verificación de la firma**

El dispositivo envía al backend el correo del usuario, el identificador de credencial, el identificador del desafío, el nonce y la firma digital.

El servidor verifica:

- Que el dispositivo exista y pertenezca al usuario.
- Que el dispositivo esté activo y tenga habilitada la biometría.
- Que la credencial corresponda al dispositivo registrado.
- Que el desafío exista y no haya sido utilizado.
- Que el desafío no haya expirado.
- Que el nonce recibido coincida con el hash almacenado.
- Que la firma digital sea válida utilizando la clave pública registrada.

**5. Emisión del JWT**

Cuando todas las validaciones son satisfactorias, el backend marca el desafío como utilizado, actualiza la fecha del último acceso y permite completar la autenticación mediante la emisión de un JWT.

El token resultante permite acceder a los endpoints protegidos de la API, de acuerdo con los permisos del usuario.

### Endpoints biométricos

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/biometria/dispositivos` | Registra un dispositivo y su clave pública. Requiere autenticación JWT. |
| POST | `/biometria/desafio` | Genera un desafío para iniciar la autenticación biométrica. |
| POST | `/biometria/verificar` | Verifica la firma digital y completa la autenticación. |
| PATCH | `/biometria/dispositivos/{id_dispositivo}/revocar` | Revoca un dispositivo registrado. Requiere autenticación JWT. |

### Consideraciones de seguridad

- La clave privada no debe enviarse ni almacenarse en el backend.
- Los desafíos tienen una vigencia de dos minutos.
- Cada desafío solo puede utilizarse una vez.
- Las firmas digitales se validan mediante la clave pública registrada.
- Los dispositivos revocados no deben poder autenticarse.
- La implementación móvil debe proteger la clave privada mediante Android Keystore y autorizar su uso mediante BiometricPrompt.

**Estado de implementación:** el flujo de registro, generación de desafíos, verificación criptográfica y emisión de JWT ha sido probado en el backend mediante herramientas de prueba. La integración con los mecanismos biométricos nativos de Android está pendiente de desarrollo.

## Arquitectura del proyecto

El backend utiliza una arquitectura modular para separar responsabilidades:

- `app/models/`: modelos y entidades de base de datos.
- `app/schemas/`: esquemas de validación y serialización.
- `app/routers/`: definición de endpoints y rutas.
- `app/services/`: lógica de negocio y servicios.
- `main.py`: punto de entrada de la aplicación FastAPI.

Los componentes biométricos principales son:

- `app/models/dispositivo_usuario.py`: modelo de dispositivos registrados.
- `app/models/desafio_biometrico.py`: modelo de desafíos criptográficos.
- `app/schemas/biometria.py`: esquemas de entrada y salida.
- `app/services/biometria.py`: lógica criptográfica y validaciones.
- `app/routers/biometria.py`: endpoints de autenticación biométrica.

## Documentación de la API

La documentación interactiva de FastAPI está disponible en:

```text
http://127.0.0.1:8000/docs
```

La documentación alternativa está disponible en:

```text
http://127.0.0.1:8000/redoc
```

## Estado del proyecto

El backend contempla los siguientes módulos:

- Gestión de usuarios y roles.
- Autenticación tradicional mediante JWT.
- Administración del catálogo de mobiliario.
- Registro y administración de dispositivos.
- Autenticación biométrica basada en desafíos y firmas digitales.
- Validación de tokens y protección de endpoints.

La siguiente etapa contempla la integración de la autenticación biométrica con una aplicación Android nativa desarrollada en Kotlin.

## Control de versiones

El proyecto utiliza Git y GitHub para el control de versiones y la gestión colaborativa del código fuente.

---

**CosySmart - API REST**

Plataforma para la gestión y comercialización de muebles multifuncionales.