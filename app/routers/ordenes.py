
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload, joinedload

from app.config.database import get_db
from app.dependencies import requiere_rol

from app.models.carrito import Carrito
from app.models.producto import Producto
from app.models.orden import Orden
from app.models.detalle_orden import DetalleOrden
from app.models.despacho_orden import DespachoOrden
from app.models.pago_orden import PagoOrden

from app.schemas.orden import (
    CrearOrdenSolicitud,
    OrdenRespuesta,
    DespachoRespuesta,
    EnviarDespachoSolicitud
)


router = APIRouter(
    prefix="/ordenes",
    tags=["Órdenes"]
)

# Administrador de rutas para el modulo de ordenes

@router.post(
    "/crear",
    response_model=OrdenRespuesta,
    status_code=status.HTTP_201_CREATED
)
def crear_orden(
    datos: CrearOrdenSolicitud,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    try:
        carrito = db.query(Carrito).options(
            selectinload(Carrito.detalles)
        ).with_hint(
            Carrito,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            Carrito.IdUsuario == usuario.IdUsuario,
            Carrito.Estado == "ACTIVO"
        ).first()

        if not carrito or not carrito.detalles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tienes productos en tu carrito"
            )

        fecha_actual = datetime.now()
        subtotal_total = Decimal("0.00")
        detalles_orden = []

        for detalle in carrito.detalles:

            producto = db.query(Producto).with_hint(
                Producto,
                "WITH (UPDLOCK, ROWLOCK)",
                dialect_name="mssql"
            ).filter(
                Producto.IdProducto == detalle.IdProducto
            ).first()

            if not producto or producto.Estado != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"El producto con ID {detalle.IdProducto} "
                        "ya no está disponible"
                    )
                )

            if detalle.Cantidad <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La cantidad de un producto no es válida"
                )

            if producto.Stock < detalle.Cantidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Stock insuficiente para {producto.Nombre}. "
                        f"Disponible: {producto.Stock}"
                    )
                )

            precio = Decimal(str(producto.Precio))
            cantidad = detalle.Cantidad
            subtotal = precio * cantidad

            subtotal_total += subtotal

            detalles_orden.append({
                "producto": producto,
                "IdProducto": producto.IdProducto,
                "NombreProducto": producto.Nombre,
                "PrecioUnitario": precio,
                "Cantidad": cantidad,
                "Subtotal": subtotal
            })

        orden = Orden(
            IdUsuario=usuario.IdUsuario,
            FechaOrden=fecha_actual,
            EstadoOrden="PENDIENTE",
            MetodoPago=datos.MetodoPago,
            Subtotal=subtotal_total,
            Total=subtotal_total,
            NombreDestinatario=datos.NombreDestinatario,
            TelefonoDestinatario=datos.TelefonoDestinatario,
            CiudadEntrega=datos.CiudadEntrega,
            DireccionEntrega=datos.DireccionEntrega,
            NotasEntrega=datos.NotasEntrega,
            Latitud=datos.Latitud,
            Longitud=datos.Longitud
        )

        db.add(orden)
        db.flush()

        ids_vendedores = {
            item["producto"].IdVendedor
            for item in detalles_orden
        }

        for id_vendedor in ids_vendedores:
            despacho = DespachoOrden(
                IdOrden=orden.IdOrden,
                IdVendedor=id_vendedor,
                EstadoDespacho="PENDIENTE"
            )
            db.add(despacho)

        for item in detalles_orden:

            producto = item["producto"]
            producto.Stock -= item["Cantidad"]

            detalle_orden = DetalleOrden(
                IdOrden=orden.IdOrden,
                IdProducto=item["IdProducto"],
                NombreProducto=item["NombreProducto"],
                PrecioUnitario=item["PrecioUnitario"],
                Cantidad=item["Cantidad"],
                Subtotal=item["Subtotal"]
            )

            db.add(detalle_orden)

        for detalle in list(carrito.detalles):
            db.delete(detalle)

        carrito.FechaActualizacion = fecha_actual

        db.commit()

        orden_respuesta = db.query(Orden).options(
            selectinload(Orden.detalles)
        ).filter(
            Orden.IdOrden == orden.IdOrden,
            Orden.IdUsuario == usuario.IdUsuario
        ).first()

        if not orden_respuesta:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La orden se creó, pero no fue posible recuperarla"
            )

        return orden_respuesta

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible crear la orden"
        )

# Obtener el vendedor y sus despechos

@router.get(
    "/vendedor/despachos",
    response_model=list[DespachoRespuesta],
    status_code=status.HTTP_200_OK
)
def listar_despachos_vendedor(
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("VENDEDOR"))
):
    despachos = db.query(DespachoOrden).options(
        joinedload(DespachoOrden.orden)
    ).filter(
        DespachoOrden.IdVendedor == usuario.IdUsuario
    ).order_by(
        DespachoOrden.IdDespacho.desc()
    ).all()

    resultado = []

    for despacho in despachos:
        orden = despacho.orden

        detalles = db.query(DetalleOrden).join(
            Producto,
            DetalleOrden.IdProducto == Producto.IdProducto
        ).filter(
            DetalleOrden.IdOrden == despacho.IdOrden,
            Producto.IdVendedor == usuario.IdUsuario
        ).all()

        resultado.append({
            "IdDespacho": despacho.IdDespacho,
            "IdOrden": despacho.IdOrden,
            "IdVendedor": despacho.IdVendedor,
            "EstadoDespacho": despacho.EstadoDespacho,
            "FechaEnvio": despacho.FechaEnvio,
            "NumeroGuia": despacho.NumeroGuia,
            "FechaOrden": orden.FechaOrden,
            "NombreDestinatario": orden.NombreDestinatario,
            "TelefonoDestinatario": orden.TelefonoDestinatario,
            "CiudadEntrega": orden.CiudadEntrega,
            "DireccionEntrega": orden.DireccionEntrega,
            "NotasEntrega": orden.NotasEntrega,
            "Detalles": detalles
        })

    return resultado


@router.patch(
    "/vendedor/despachos/{id_despacho}/enviar",
    status_code=status.HTTP_200_OK
)
def marcar_despacho_enviado(
    id_despacho: int,
    datos: EnviarDespachoSolicitud,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("VENDEDOR"))
):
    try:
        despacho = db.query(DespachoOrden).options(
            joinedload(DespachoOrden.orden)
        ).with_hint(
            DespachoOrden,
            "WITH (UPDLOCK, ROWLOCK)",
            dialect_name="mssql"
        ).filter(
            DespachoOrden.IdDespacho == id_despacho,
            DespachoOrden.IdVendedor == usuario.IdUsuario
        ).first()

        if not despacho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El despacho no existe o no te pertenece"
            )

        if despacho.EstadoDespacho != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este despacho ya fue procesado"
            )

        orden = despacho.orden

        if not orden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró la orden asociada"
            )

        if orden.EstadoOrden not in (
            "PENDIENTE",
            "PARCIALMENTE_ENVIADA"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no permite registrar este envío"
            )

        despacho.EstadoDespacho = "ENVIADA"
        despacho.FechaEnvio = datetime.now()

        numero_guia = datos.NumeroGuia

        despacho.NumeroGuia = (
            numero_guia.strip()
            if numero_guia and numero_guia.strip()
            else None
        )

        db.flush()

        estados_despachos = db.query(
            DespachoOrden.EstadoDespacho
        ).filter(
            DespachoOrden.IdOrden == despacho.IdOrden
        ).all()

        total_despachos = len(estados_despachos)

        enviados = sum(
            1 for estado in estados_despachos
            if estado[0] == "ENVIADA"
        )

        if enviados == 0:
            orden.EstadoOrden = "PENDIENTE"

        elif enviados < total_despachos:
            orden.EstadoOrden = "PARCIALMENTE_ENVIADA"

        else:
            orden.EstadoOrden = "ENVIADA"

        db.commit()

        db.refresh(despacho)
        db.refresh(orden)

        return {
            "mensaje": "Despacho actualizado correctamente",
            "IdDespacho": despacho.IdDespacho,
            "IdOrden": despacho.IdOrden,
            "EstadoDespacho": despacho.EstadoDespacho,
            "FechaEnvio": despacho.FechaEnvio,
            "NumeroGuia": despacho.NumeroGuia,
            "EstadoOrden": orden.EstadoOrden
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible actualizar el despacho"
        )


@router.get(
    "/{id_orden}",
    response_model=OrdenRespuesta,
    status_code=status.HTTP_200_OK
)
def consultar_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    orden = db.query(Orden).options(
        selectinload(Orden.detalles)
    ).filter(
        Orden.IdOrden == id_orden,
        Orden.IdUsuario == usuario.IdUsuario
    ).first()

    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La orden no existe o no tienes permiso para consultarla"
        )

    return orden


@router.get(
    "/",
    response_model=list[OrdenRespuesta],
    status_code=status.HTTP_200_OK
)
def listar_historial_ordenes(
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    ordenes = db.query(Orden).options(
        selectinload(Orden.detalles)
    ).filter(
        Orden.IdUsuario == usuario.IdUsuario
    ).order_by(
        Orden.FechaOrden.desc(),
        Orden.IdOrden.desc()
    ).all()

    return ordenes


@router.patch(
    "/{id_orden}/cancelar",
    status_code=status.HTTP_200_OK
)
def cancelar_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("COMPRADOR"))
):
    try:
        # Bloquear primero la orden.
        orden = db.query(Orden).with_hint(
            Orden,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            Orden.IdOrden == id_orden,
            Orden.IdUsuario == usuario.IdUsuario
        ).first()

        if not orden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La orden no existe o no tienes permiso para cancelarla"
            )

        if orden.EstadoOrden != "PENDIENTE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden cancelar órdenes pendientes"
            )

        if orden.EstadoPago not in ("PENDIENTE", "RECHAZADA"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede cancelar una orden con un pago confirmado"
            )

        # Bloquear después los intentos de pago.
        pago_pendiente = db.query(PagoOrden).with_hint(
            PagoOrden,
            "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)",
            dialect_name="mssql"
        ).filter(
            PagoOrden.IdOrden == id_orden,
            PagoOrden.EstadoPago == "PENDIENTE"
        ).first()

        if pago_pendiente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No puedes cancelar esta orden porque tiene "
                    "un pago pendiente de confirmación en Wompi. "
                    "Espera a que Wompi confirme o rechace el pago."
                )
            )

        despachos = db.query(DespachoOrden).with_hint(
            DespachoOrden,
            "WITH (UPDLOCK, ROWLOCK)",
            dialect_name="mssql"
        ).filter(
            DespachoOrden.IdOrden == id_orden
        ).all()

        if any(
            despacho.EstadoDespacho != "PENDIENTE"
            for despacho in despachos
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden tiene despachos procesados y no puede cancelarse"
            )

        detalles = db.query(DetalleOrden).filter(
            DetalleOrden.IdOrden == id_orden
        ).all()

        if not detalles:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no contiene productos para devolver al inventario"
            )

        for detalle in detalles:

            producto = db.query(Producto).with_hint(
                Producto,
                "WITH (UPDLOCK, ROWLOCK)",
                dialect_name="mssql"
            ).filter(
                Producto.IdProducto == detalle.IdProducto
            ).first()

            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"No se encontró el producto "
                        f"{detalle.NombreProducto}"
                    )
                )

            producto.Stock += detalle.Cantidad

        for despacho in despachos:
            despacho.EstadoDespacho = "CANCELADO"

        orden.EstadoOrden = "CANCELADA"

        db.commit()

        return {
            "mensaje": "Orden cancelada correctamente",
            "IdOrden": orden.IdOrden,
            "EstadoOrden": orden.EstadoOrden,
            "EstadoPago": orden.EstadoPago,
            "productosDevueltos": len(detalles)
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible cancelar la orden"
        )
