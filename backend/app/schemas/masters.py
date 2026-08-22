from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.masters import EmployeeRole


# ---- Warehouse ----
class WarehouseCreate(BaseModel):
    name: str
    address: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    is_active: bool | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str | None
    is_active: bool


# ---- Product ----
class ProductCreate(BaseModel):
    sku: str
    name: str
    brand: str | None = None
    category: str | None = None
    unit: str
    volume_ml: Decimal | None = None
    hsn_code: str | None = None
    gst_rate: Decimal = Decimal("0")
    base_price: Decimal = Decimal("0")
    is_returnable: bool = False
    deposit_amount: Decimal = Decimal("0")
    reorder_level: Decimal = Decimal("0")


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    unit: str | None = None
    volume_ml: Decimal | None = None
    hsn_code: str | None = None
    gst_rate: Decimal | None = None
    base_price: Decimal | None = None
    is_returnable: bool | None = None
    deposit_amount: Decimal | None = None
    reorder_level: Decimal | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    brand: str | None
    category: str | None
    unit: str
    volume_ml: Decimal | None
    hsn_code: str | None
    gst_rate: Decimal
    base_price: Decimal
    is_returnable: bool
    deposit_amount: Decimal
    reorder_level: Decimal
    is_active: bool


# ---- Product Batch ----
class ProductBatchCreate(BaseModel):
    product_id: int
    batch_number: str
    manufacture_date: date | None = None
    expiry_date: date | None = None


class ProductBatchUpdate(BaseModel):
    manufacture_date: date | None = None
    expiry_date: date | None = None


class ProductBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    batch_number: str
    manufacture_date: date | None
    expiry_date: date | None


# ---- Route ----
class RouteCreate(BaseModel):
    name: str
    description: str | None = None


class RouteUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    is_active: bool


# ---- Customer ----
class CustomerCreate(BaseModel):
    name: str
    owner_name: str | None = None
    phone: str | None = None
    address: str | None = None
    gst_number: str | None = None
    route_id: int | None = None
    credit_limit: Decimal = Decimal("0")
    credit_days: int = 0


class CustomerUpdate(BaseModel):
    name: str | None = None
    owner_name: str | None = None
    phone: str | None = None
    address: str | None = None
    gst_number: str | None = None
    route_id: int | None = None
    credit_limit: Decimal | None = None
    credit_days: int | None = None
    is_active: bool | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner_name: str | None
    phone: str | None
    address: str | None
    gst_number: str | None
    route_id: int | None
    credit_limit: Decimal
    credit_days: int
    is_active: bool


# ---- Employee ----
class EmployeeCreate(BaseModel):
    name: str
    role: EmployeeRole
    phone: str | None = None
    joining_date: date
    monthly_salary: Decimal = Decimal("0")
    notes: str | None = None


class EmployeeUpdate(BaseModel):
    name: str | None = None
    role: EmployeeRole | None = None
    phone: str | None = None
    monthly_salary: Decimal | None = None
    notes: str | None = None
    is_active: bool | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    role: EmployeeRole
    phone: str | None
    joining_date: date
    monthly_salary: Decimal
    notes: str | None
    is_active: bool


# ---- Vehicle ----
class VehicleCreate(BaseModel):
    registration_number: str
    vehicle_type: str | None = None
    capacity: Decimal | None = None


class VehicleUpdate(BaseModel):
    vehicle_type: str | None = None
    capacity: Decimal | None = None
    is_active: bool | None = None


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    registration_number: str
    vehicle_type: str | None
    capacity: Decimal | None
    is_active: bool
