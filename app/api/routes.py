import math
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressRead, AddressUpdate, NearbyAddress

router = APIRouter(tags=["addresses"])
logger = logging.getLogger("address_book")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two coordinates in kilometers."""
    earth_radius_km = 6371.0

    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


@router.post("/addresses", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(payload: AddressCreate, db: Session = Depends(get_db)) -> Address:
    """Create a new address record and return the persisted result."""
    try:
        address = Address(**payload.model_dump())
        db.add(address)
        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to create address")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create address",
        ) from None


@router.get("/addresses", response_model=list[AddressRead])
def list_addresses(db: Session = Depends(get_db)) -> list[Address]:
    """Return all addresses ordered by ID ascending."""
    try:
        return db.query(Address).order_by(Address.id.asc()).all()
    except SQLAlchemyError:
        logger.exception("Failed to list addresses")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list addresses",
        ) from None


@router.get("/addresses/{address_id}", response_model=AddressRead)
def get_address(address_id: int, db: Session = Depends(get_db)) -> Address:
    """Return one address by ID or raise a 404 error."""
    try:
        address = db.get(Address, address_id)
    except SQLAlchemyError:
        logger.exception("Failed to fetch address with id=%s", address_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch address",
        ) from None

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    return address


@router.put("/addresses/{address_id}", response_model=AddressRead)
def update_address(address_id: int, payload: AddressUpdate, db: Session = Depends(get_db)) -> Address:
    """Replace an existing address with validated payload values."""
    try:
        address = db.get(Address, address_id)
    except SQLAlchemyError:
        logger.exception("Failed to fetch address for update with id=%s", address_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address",
        ) from None

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    try:
        for field, value in payload.model_dump().items():
            setattr(address, field, value)

        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to update address with id=%s", address_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address",
        ) from None


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(address_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an address by ID or raise a 404 error."""
    try:
        address = db.get(Address, address_id)
    except SQLAlchemyError:
        logger.exception("Failed to fetch address for deletion with id=%s", address_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete address",
        ) from None

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    try:
        db.delete(address)
        db.commit()
        return None
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to delete address with id=%s", address_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete address",
        ) from None


@router.get("/addresses/search/nearby", response_model=list[NearbyAddress])
def get_nearby_addresses(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    distance_km: float = Query(..., gt=0, le=20000),
    db: Session = Depends(get_db),
) -> list[NearbyAddress]:
    """Return addresses within a radius of the given coordinate pair."""
    try:
        addresses = db.query(Address).all()
    except SQLAlchemyError:
        logger.exception("Failed to search nearby addresses")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search nearby addresses",
        ) from None

    results: list[NearbyAddress] = []

    for address in addresses:
        distance = haversine_km(latitude, longitude, address.latitude, address.longitude)
        if distance <= distance_km:
            results.append(
                NearbyAddress(
                    **AddressRead.model_validate(address).model_dump(),
                    distance_km=round(distance, 3),
                )
            )

    results.sort(key=lambda item: item.distance_km)
    return results
