from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressBase(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    address_line_1: str = Field(..., min_length=1, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    @field_validator("label", "address_line_1", "city", "state", "postal_code", "country")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        """Strip required string fields and reject values that become blank."""
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

    @field_validator("address_line_2")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        """Strip optional string fields and normalize empty values to ``None``."""
        if value is None:
            return value
        value = value.strip()
        return value or None


class AddressCreate(AddressBase):
    pass


class AddressUpdate(AddressBase):
    pass


class AddressRead(AddressBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class NearbyAddress(AddressRead):
    distance_km: float


class NearbyQuery(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    distance_km: float = Field(..., gt=0, le=20000)
