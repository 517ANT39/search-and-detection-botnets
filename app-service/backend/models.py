from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class FilterData(BaseModel):
    start_time: Optional[str] = None
    end_time:   Optional[str] = None
    src_ip:     Optional[str] = None
    dst_ip:     Optional[str] = None
    host_ip:    Optional[str] = None
    protocol:   Optional[int] = None
    direction:  Optional[int] = None
    min_packets: Optional[int] = 10
    minutes:    Optional[int] = 60


class FilterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    filter_data: FilterData


class FilterOut(BaseModel):
    id: int
    name: str
    filter_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True