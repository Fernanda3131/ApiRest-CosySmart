# CosySmart – API REST

API REST oficial de **CosySmart**, una plataforma web y móvil para la gestión, exhibición y comercialización de muebles multifuncionales orientados a optimizar espacios pequeños.

El backend centraliza la lógica de negocio, la autenticación, la administración de usuarios, el catálogo de productos, el carrito de compras, las órdenes y la integración de pagos. Está desarrollado con FastAPI y utiliza Microsoft SQL Server como sistema de gestión de base de datos.

---

## Tecnologías utilizadas

| Tecnología | Uso |
| Python | Lenguaje de programación |
| FastAPI | Framework para el desarrollo de la API REST |
| SQLAlchemy | ORM y acceso a datos |
| Microsoft SQL Server | Sistema gestor de base de datos |
| JWT | Autenticación y autorización |
| Pydantic | Validación y serialización de datos |
| Uvicorn | Servidor ASGI |
| ECDSA P-256 y SHA-256 | Verificación criptográfica de credenciales biométricas |
| Wompi Sandbox | Integración de pagos en ambiente de pruebas |
| Git y GitHub | Control de versiones |

## Características principales

### 1. Gestión de usuarios y autenticación

- Registro e inicio de sesión.
- Autenticación mediante tokens JWT.
- Gestión de roles diferenciados:
  - Comprador (Buyer).
  - Vendedor (Seller).
  - Administrador (Admin).
- Protección de endpoints mediante autenticación y autorización.
- Validación de permisos según el rol del usuario.

### 2. Catálogo y gestión de productos

- Registro de productos de mobiliario multifuncional.
- Asociación de productos con sus categorías.
- Administración de información, características y precios.
- Carga de entre una y cinco imágenes por producto.
- Validación de formatos y tamaño de archivos.
- Consulta de productos para su exhibición en la aplicación.

### 3. Carrito de compras

- Agregar productos al carrito.
- Consultar los productos agregados.
- Actualizar cantidades.
- Calcular subtotales.
- Eliminar productos individuales.
- Vaciar el carrito.

La información del carrito se gestiona mediante el backend y se persiste en Microsoft SQL Server.

### 4. Gestión de órdenes

- Creación de órdenes a partir de los productos del carrito.
- Registro de información de entrega.
- Asociación de la orden con el comprador.
- Registro del método y estado de pago.
- Consulta del historial de órdenes.
- Consulta del detalle de una orden.
- Administración de estados de las órdenes.
- Cancelación de órdenes bajo las validaciones del backend.

La creación de órdenes se encuentra conectada con el flujo de compra de la aplicación Android.

### 5. Integración de pagos con Wompi

CosySmart integra **Wompi Web Checkout en ambiente Sandbox**, permitiendo iniciar transacciones de prueba mediante una página de pago externa.

Las funcionalidades desarrolladas incluyen:

- Creación de intentos de pago asociados a una orden.
- Generación de referencias únicas de pago.
- Conversión de montos a centavos.
- Generación de firmas de integridad mediante SHA-256.
- Recuperación de intentos de pago pendientes.
- Consulta del estado de pago de una orden.
- Recepción de eventos de Wompi mediante webhook.
- Verificación de firmas de eventos.
- Validación de referencias, montos y moneda.

**Flujo general de pago:**

1. El comprador crea una orden.
2. La aplicación solicita iniciar el pago.
3. El backend genera la referencia y la firma de integridad.
4. Android abre Wompi Web Checkout en el navegador.
5. Wompi procesa la transacción en Sandbox.
6. Wompi envía el evento correspondiente al webhook.
7. El backend verifica la firma y procesa el evento.

**Importante:** la confirmación del pago depende de la notificación verificada del webhook. El retorno del navegador no constituye por sí mismo una confirmación de pago.

La integración está destinada a pruebas. No debe considerarse una implementación de producción hasta completar las pruebas de conciliación, idempotencia, estados de transacción, inventario y seguridad.

### Endpoints de pagos Wompi

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/pagos/wompi/iniciar` | Crea un intento de pago para una orden. |
| GET | `/pagos/wompi/pendiente/{id_orden}` | Recupera un intento de pago pendiente. |
| GET | `/pagos/wompi/estado/{id_orden}` | Consulta el estado del pago de una orden. |
| POST | `/pagos/wompi/eventos` | Recibe y verifica las notificaciones de Wompi. |

Los endpoints protegidos requieren el token JWT correspondiente, según las reglas de autorización implementadas. El webhook utiliza su mecanismo propio de verificación de eventos.

### 6. Autenticación biométrica

CosySmart contempla un mecanismo de autenticación biométrica basado en criptografía asimétrica y verificación de firmas digitales.

El backend no almacena huellas dactilares ni imágenes faciales. La autenticación se plantea para realizarse localmente en el dispositivo Android, mientras el servidor verifica la posesión de una clave privada asociada a una clave pública previamente registrada.

#### Funcionamiento

**1. Registro del dispositivo**

El usuario debe autenticarse previamente mediante el mecanismo tradicional.

Posteriormente, el dispositivo envía su nombre, clave pública y algoritmo criptográfico permitido. El backend registra la credencial y la asocia con el usuario.

**2. Generación del desafío**

El dispositivo solicita un desafío al endpoint `/biometria/desafio`.

El backend genera un nonce criptográficamente aleatorio de 32 bytes, almacena su hash SHA-256 y establece una expiración de dos minutos.

La respuesta contiene:

- `ChallengeId`: identificador del desafío.
- `Nonce`: valor aleatorio codificado en Base64 URL-safe.
- `FechaExpiracion`: fecha límite para completar la autenticación.

**3. Firma digital**

El dispositivo utiliza la clave privada para firmar un mensaje que contiene el identificador del desafío, el identificador de la credencial y el nonce recibido.

Se utiliza ECDSA con curva P-256 y SHA-256.

El mensaje canónico tiene la siguiente estructura:

```text
COSYSMART|BIOMETRIA_LOGIN|V1
ChallengeId
IdCredencial
Nonce
```

Los elementos se concatenan mediante saltos de línea y el nonce se incorpora en su representación binaria.

**4. Verificación de la firma**

El dispositivo envía al backend los datos necesarios para verificar la autenticación.

El servidor comprueba:

- Que el dispositivo exista y pertenezca al usuario.
- Que el dispositivo esté activo.
- Que la credencial corresponda al dispositivo registrado.
- Que el desafío exista y no haya sido utilizado.
- Que el desafío no haya expirado.
- Que el nonce coincida con el hash almacenado.
- Que la firma digital sea válida utilizando la clave pública registrada.

**5. Emisión del JWT**

Cuando las validaciones son satisfactorias, el backend marca el desafío como utilizado, actualiza la fecha del último acceso y permite completar la autenticación mediante la emisión de un JWT.

#### Endpoints biométricos

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/biometria/dispositivos` | Registra un dispositivo y su clave pública. |
| POST | `/biometria/desafio` | Genera un desafío de autenticación. |
| POST | `/biometria/verificar` | Verifica la firma digital y completa la autenticación. |
| PATCH | `/biometria/dispositivos/{id_dispositivo}/revocar` | Revoca un dispositivo registrado. |

#### Consideraciones de seguridad

- La clave privada no debe enviarse ni almacenarse en el backend.
- Los desafíos tienen una vigencia de dos minutos.
- Cada desafío solo puede utilizarse una vez.
- Las firmas digitales se validan mediante la clave pública registrada.
- Los dispositivos revocados no deben poder autenticarse.
- La implementación Android debe proteger la clave privada mediante Android Keystore y autorizar su uso mediante BiometricPrompt.

**Estado de implementación:** el flujo de registro, generación de desafíos, verificación criptográfica y emisión de JWT ha sido probado en el backend. La integración con los mecanismos biométricos nativos de Android está pendiente de desarrollo.

---

## Arquitectura del proyecto

El backend utiliza una arquitectura modular para separar responsabilidades y facilitar el mantenimiento.

```text
API-CosySmart/
│
├── app/
│   ├── models/
│   │   ├── dispositivo_usuario.py
│   │   ├── desafio_biometrico.py
│   │   └── ...
│   │
│   ├── schemas/
│   │   ├── biometria.py
│   │   └── ...
│   │
│   ├── routers/
│   │   ├── biometria.py
│   │   ├── pagos.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── biometria.py
│   │   ├── wompi_service.py
│   │   ├── wompi_webhook_service.py
│   │   └── ...
│   │
│   └── config/
│       └── wompi.py
│
├── main.py
├── requirements.txt
├── .env
└── README.md
```

*Nota: la estructura es representativa de los componentes principales. Los nombres y archivos deben contrastarse con la estructura real del repositorio.*

### Organización de componentes

| Directorio | Responsabilidad |
|---|---|
| `app/models/` | Modelos y entidades de la base de datos. |
| `app/schemas/` | Esquemas de validación y serialización. |
| `app/routers/` | Definición de endpoints y rutas. |
| `app/services/` | Lógica de negocio y servicios especializados. |
| `app/config/` | Configuración de servicios e integraciones. |
| `main.py` | Punto de entrada de la aplicación FastAPI. |

---

## Instalación y configuración

### Requisitos previos

- Python instalado.
- Microsoft SQL Server.
- Git.
- Un entorno de desarrollo compatible con Python.
- Acceso a las dependencias declaradas en `requirements.txt`.

### 1. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
cd NOMBRE_DEL_PROYECTO
```

Reemplaza los valores de ejemplo por la URL y el nombre reales del repositorio.

### 2. Crear un entorno virtual

En Windows:

```powershell
python -m venv venv
```

Activarlo:

```powershell
.\venv\Scripts\Activate.ps1
```

En caso de utilizar CMD:

```cmd
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

Crear el archivo `.env` en la raíz del proyecto y definir las variables requeridas por la configuración del backend.

La conexión a SQL Server debe configurarse de acuerdo con los parámetros utilizados por el proyecto.

Para Wompi Sandbox se utilizan las siguientes variables:

```env
WOMPI_PUBLIC_KEY=
WOMPI_PRIVATE_KEY=
WOMPI_INTEGRITY_SECRET=
WOMPI_EVENTS_SECRET=
WOMPI_BASE_URL=https://sandbox.wompi.co/v1
```

Los valores deben corresponder exclusivamente a las credenciales de pruebas.

**Seguridad:**

- No subir el archivo `.env` a GitHub.
- No incluir claves privadas, secretos de integridad ni secretos de eventos en el código fuente.
- No compartir tokens JWT ni credenciales de conexión.
- Utilizar variables de entorno diferentes para pruebas y producción.

### 5. Ejecutar el servidor

Si el punto de entrada está configurado como `main.py`:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Si el proyecto utiliza `app.main:app`, ejecutar:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Utiliza el comando que corresponda a la ubicación real de la instancia FastAPI.

---

## Documentación de la API

FastAPI proporciona documentación interactiva para consultar y probar los endpoints.

Una vez iniciado el servidor, están disponibles las siguientes direcciones locales:

**Swagger UI**

```text
http://127.0.0.1:8000/docs
```

**ReDoc**

```text
http://127.0.0.1:8000/redoc
```

Desde Swagger se pueden consultar los métodos HTTP, parámetros, esquemas de entrada, respuestas y mecanismos de autenticación de los endpoints registrados.

---

## Integración con Wompi Sandbox

Para realizar pruebas de pagos desde un entorno local, el webhook debe contar con una URL HTTPS accesible desde Internet.

El backend puede exponerse temporalmente mediante un servicio de túnel HTTPS, por ejemplo, Cloudflare Tunnel, ngrok o LocalTunnel.

La URL pública debe apuntar a:

```text
https://DOMINIO_PUBLICO/pagos/wompi/eventos
```

El túnel debe permanecer activo mientras se realizan las pruebas.

**Recomendaciones:**

- Configurar la URL de eventos en el ambiente Sandbox de Wompi.
- Verificar que el endpoint reciba solicitudes POST.
- Validar la firma del evento antes de modificar la base de datos.
- No confiar en la redirección del navegador para confirmar transacciones.
- Probar tanto transacciones aprobadas como rechazadas.
- Revisar los registros del backend y los estados persistidos en SQL Server.

---

## Estado actual del proyecto

| Módulo | Estado |
|---|---|
| Gestión de usuarios y roles | Implementado |
| Autenticación JWT | Implementado |
| Gestión y creación de productos | Implementado |
| Carga y validación de imágenes | Implementado |
| Operaciones del carrito | Implementado y probado |
| Creación de órdenes | Implementada; requiere validación integral |
| Historial y detalle de órdenes | Implementados; sujetos a validación funcional |
| Gestión de estados y cancelación de órdenes | Implementada; requiere pruebas de integración |
| Integración Wompi Sandbox | Implementada en backend y Android; pruebas integrales y conciliación pendientes |
| Webhook de Wompi | Implementado; requiere validación de recepción y procesamiento de eventos |
| Autenticación biométrica en backend | Probada mediante herramientas de prueba |
| Integración biométrica nativa Android | Pendiente |
| Geolocalización | Pendiente de integración funcional completa |
| Pasarela de pagos en producción, funcionamiento exitoso, pendiente cambio de estado al no estar el proyecto desplegado

### Consideraciones técnicas pendientes

1. Reforzar la conciliación de transacciones ante eventos atrasados o múltiples intentos de pago.
2. Revisar el ciclo de reserva y liberación del inventario cuando una orden no se paga.
3. Validar la seguridad y configuración del entorno antes de cualquier despliegue de producción.

---

## Control de versiones

El proyecto utiliza Git y GitHub para el control de versiones y la gestión colaborativa del código fuente.

Se recomienda mantener actualizada la documentación cuando se incorporen nuevos módulos, endpoints o cambios en la arquitectura.

---

**CosySmart – API REST**

Plataforma para la gestión y comercialización de muebles multifuncionales.