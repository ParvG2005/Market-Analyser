from pydantic import BaseModel, ConfigDict


class InstrumentIn(BaseModel):
    symbol: str
    asset_class: str
    exchange: str


class InstrumentPatch(BaseModel):
    active: bool | None = None


class InstrumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    asset_class: str
    exchange: str
    active: bool
    delayed: bool
    delay_minutes: int
