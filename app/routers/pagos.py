
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status
)

from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.wompi import obtener_configuracion_wompi

from app.dependencies import requiere_rol

from app.models.orden import Orden
from app.models.pago_orden import PagoOrden

from app.schemas.pago import IniciarPagoSolicitud

from app.services.wompi_service import (
    generar_referencia_pago,
    convertir_a_centavos,
    generar_firma_integridad
)

from app.services.wompi_webhook_service import (
    verificar_firma_evento
)


router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"]
)

# Administrador de rutas para modulo de pagos, WOMPI

# INICIAR PAGO WOMPI

@router.post(
    "/wompi/iniciar",
    status_code=status.HTTP_201_CREATED
)
def iniciar_pago_wompi(
    datos: IniciarPagoSolicitud,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    try:

        orden = db.query(Orden).with_hint(
            Orden,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            Orden.IdOrden == datos.IdOrden,
            Orden.IdUsuario == usuario.IdUsuario
        ).first()

        if not orden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La orden no existe o no te pertenece"
            )

        if orden.EstadoOrden != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no permite iniciar un pago"
            )

        if orden.EstadoPago not in (
            "PENDIENTE",
            "RECHAZADA"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden ya tiene un pago confirmado"
            )

        if orden.MetodoPago not in ("TARJETA", "PSE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta orden no utiliza Wompi"
            )

        # Bloquear después los intentos de pago.
        pago_existente = db.query(PagoOrden).with_hint(
            PagoOrden,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            PagoOrden.IdOrden == orden.IdOrden,
            PagoOrden.EstadoPago.in_([
                "PENDIENTE",
                "APROBADO"
            ])
        ).first()

        if pago_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "La orden ya tiene un intento pendiente "
                    "o un pago aprobado"
                )
            )

        monto_centavos = convertir_a_centavos(
            orden.Total
        )

        referencia = generar_referencia_pago(
            orden.IdOrden
        )

        firma = generar_firma_integridad(
            referencia,
            monto_centavos
        )

        configuracion = obtener_configuracion_wompi()

        pago = PagoOrden(
            IdOrden=orden.IdOrden,
            Referencia=referencia,
            IdTransaccionWompi=None,
            EstadoPago="PENDIENTE",
            MontoCentavos=monto_centavos,
            MetodoPago=orden.MetodoPago,
            FechaCreacion=datetime.now(),
            FechaActualizacion=None
        )

        db.add(pago)

        orden.EstadoPago = "PENDIENTE"

        db.flush()

        id_pago = pago.IdPago
        id_orden = orden.IdOrden

        db.commit()

        return {
            "mensaje": "Intento de pago creado correctamente",
            "IdPago": id_pago,
            "IdOrden": id_orden,
            "public_key": configuracion["WOMPI_PUBLIC_KEY"],
            "currency": "COP",
            "amount_in_cents": monto_centavos,
            "reference": referencia,
            "signature": {
                "integrity": firma
            },
            "payment_method": orden.MetodoPago
        }

    except HTTPException:
        db.rollback()
        raise

    except ValueError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible iniciar el pago"
        )

# RECUPERAR PAGO WOMPI PENDIENTE

@router.get("/wompi/pendiente/{id_orden}")
def recuperar_pago_wompi(
    id_orden: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    try:
        # Consultar la orden y validar propietario.
        orden = db.query(Orden).filter(
            Orden.IdOrden == id_orden,
            Orden.IdUsuario == usuario.IdUsuario
        ).first()

        if not orden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La orden no existe o no te pertenece"
            )

        if orden.EstadoOrden != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no permite recuperar este pago"
            )

        # Buscar el intento pendiente.
        pago = db.query(PagoOrden).filter(
            PagoOrden.IdOrden == id_orden,
            PagoOrden.EstadoPago == "PENDIENTE"
        ).first()

        if not pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un intento de pago pendiente"
            )

        # Verificar que el monto coincida con la orden.
        monto_actual = convertir_a_centavos(orden.Total)

        if pago.MontoCentavos != monto_actual:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El monto del intento no coincide con la orden"
            )

        if pago.MetodoPago != orden.MetodoPago:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El método de pago no coincide con la orden"
            )

        # Regenerar firma con los datos originales.
        firma = generar_firma_integridad(
            pago.Referencia,
            pago.MontoCentavos
        )

        configuracion = obtener_configuracion_wompi()

        return {
            "mensaje": "Datos del pago recuperados correctamente",
            "IdPago": pago.IdPago,
            "IdOrden": orden.IdOrden,
            "public_key": configuracion["WOMPI_PUBLIC_KEY"],
            "currency": "COP",
            "amount_in_cents": pago.MontoCentavos,
            "reference": pago.Referencia,
            "signature": {
                "integrity": firma
            },
            "payment_method": pago.MetodoPago
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible recuperar los datos del pago"
        )


# CONSULTAR ESTADO ACTUAL DEL PAGO WOMPI

@router.get("/wompi/estado/{id_orden}")
def consultar_estado_pago_wompi(
    id_orden: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    try:
        # Verificar que la orden pertenezca al comprador.
        orden = db.query(Orden).filter(
            Orden.IdOrden == id_orden,
            Orden.IdUsuario == usuario.IdUsuario
        ).first()

        if not orden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La orden no existe o no te pertenece"
            )

        # Obtener el intento más reciente de la orden.
        pago = db.query(PagoOrden).filter(
            PagoOrden.IdOrden == id_orden
        ).order_by(
            PagoOrden.IdPago.desc()
        ).first()

        if not pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La orden no tiene intentos de pago registrados"
            )

        return {
            "IdOrden": orden.IdOrden,
            "IdPago": pago.IdPago,
            "EstadoPago": pago.EstadoPago,
            "EstadoPagoOrden": orden.EstadoPago,
            "EstadoOrden": orden.EstadoOrden,
            "MetodoPago": pago.MetodoPago,
            "MontoCentavos": pago.MontoCentavos,
            "IdTransaccionWompi": pago.IdTransaccionWompi,
            "FechaActualizacion": (
                pago.FechaActualizacion.isoformat()
                if pago.FechaActualizacion
                else None
            )
        }

    except HTTPException:
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible consultar el estado del pago"
        )

# RECIBIR EVENTOS DE WOMPI

@router.post(
    "/wompi/eventos",
    status_code=status.HTTP_200_OK
)
async def recibir_evento_wompi(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        evento = await request.json()

        if evento.get("environment") != "test":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El evento no pertenece al entorno Sandbox"
            )

        if not verificar_firma_evento(evento):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firma del evento inválida"
            )

        if evento.get("event") != "transaction.updated":
            return {
                "mensaje": "Evento recibido sin procesamiento"
            }

        transaccion = evento.get(
            "data", {}
        ).get(
            "transaction", {}
        )

        referencia = transaccion.get("reference")
        id_transaccion = transaccion.get("id")
        estado_wompi = transaccion.get("status")
        monto = transaccion.get("amount_in_cents")
        moneda = transaccion.get("currency")

        if not all([
            referencia,
            id_transaccion,
            estado_wompi,
            monto is not None,
            moneda
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El evento no contiene los datos necesarios"
            )

        if moneda != "COP":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Moneda no permitida"
            )

        if (
            not isinstance(monto, int)
            or isinstance(monto, bool)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monto de transacción inválido"
            )

        # Buscar el pago sin bloquear para conocer la orden.
        pago_referencia = db.query(PagoOrden).filter(
            PagoOrden.Referencia == referencia
        ).first()

        if not pago_referencia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe un intento con esa referencia"
            )

        id_orden_pago = pago_referencia.IdOrden

        # Bloquear primero la orden.
        orden = db.query(Orden).with_hint(
            Orden,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            Orden.IdOrden == id_orden_pago
        ).first()

        if not orden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe la orden asociada al pago"
            )

        # Bloquear después el intento de pago.
        pago = db.query(PagoOrden).with_hint(
            PagoOrden,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            PagoOrden.Referencia == referencia,
            PagoOrden.IdOrden == id_orden_pago
        ).first()

        if not pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el intento de pago asociado a la orden"
            )

        if pago.MontoCentavos != monto:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El monto no coincide con el intento registrado"
            )

        if pago.IdTransaccionWompi not in (
            None,
            id_transaccion
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El intento ya está asociado a otra transacción"
            )

        # No reprocesar intentos finalizados.
        if pago.EstadoPago in (
            "APROBADO",
            "RECHAZADO"
        ):
            db.rollback()

            return {
                "mensaje": "El intento ya tiene un estado final",
                "EstadoPago": pago.EstadoPago
            }

        pago.IdTransaccionWompi = id_transaccion
        pago.FechaActualizacion = datetime.now()

        if estado_wompi == "APPROVED":

            pago.EstadoPago = "APROBADO"

            if orden.EstadoOrden == "CANCELADA":
                db.commit()

                return {
                    "mensaje": (
                        "Pago aprobado para una orden cancelada. "
                        "Requiere revisión y posible reembolso."
                    ),
                    "IdPago": pago.IdPago,
                    "IdOrden": orden.IdOrden,
                    "EstadoPago": pago.EstadoPago
                }

            if orden.EstadoPago == "PAGADA":
                db.commit()

                return {
                    "mensaje": (
                        "La orden ya tiene un pago confirmado. "
                        "Este intento requiere revisión."
                    ),
                    "IdPago": pago.IdPago,
                    "IdOrden": orden.IdOrden,
                    "EstadoPago": pago.EstadoPago
                }

            # No aprobar órdenes que ya fueron enviadas.
            if orden.EstadoOrden not in (
                "PENDIENTE",
                "PARCIALMENTE_ENVIADA"
            ):
                db.rollback()

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="La orden no permite confirmar este pago"
                )

            orden.EstadoPago = "PAGADA"

        elif estado_wompi in (
            "DECLINED",
            "VOIDED",
            "ERROR"
        ):

            pago.EstadoPago = "RECHAZADO"

            if orden.EstadoPago != "PAGADA":
                orden.EstadoPago = "RECHAZADA"

        elif estado_wompi == "PENDING":

            pago.EstadoPago = "PENDIENTE"

        else:
            db.rollback()

            return {
                "mensaje": "Estado de Wompi no reconocido",
                "EstadoWompi": estado_wompi
            }

        db.commit()

        return {
            "mensaje": "Evento procesado correctamente",
            "IdPago": pago.IdPago,
            "IdOrden": orden.IdOrden,
            "EstadoPago": pago.EstadoPago,
            "EstadoOrdenPago": orden.EstadoPago
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible procesar el evento de Wompi"
        )
