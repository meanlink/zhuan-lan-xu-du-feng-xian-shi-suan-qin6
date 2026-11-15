from pydantic import BaseModel, Field, field_validator
def _url(v):
    if v is not None and not v.startswith(('http://', 'https://')):
        raise ValueError('收件地址需以 http:// 或 https:// 开头')
    return v
class RecipientInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=8, max_length=300)
    @field_validator('address')
    @classmethod
    def check_address(cls, v): return _url(v)
class RecipientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, min_length=8, max_length=300)
    enabled: bool | None = None
    @field_validator('address')
    @classmethod
    def check_address(cls, v): return _url(v)
class RedispatchInput(BaseModel):
    recipient_id: int
class InboxModeInput(BaseModel):
    drop_receipts: bool
