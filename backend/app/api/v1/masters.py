from app.api.v1.crud_factory import make_crud_router
from app.models.masters import Customer, Employee, Product, ProductBatch, Route, Vehicle, Warehouse
from app.schemas.masters import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    ProductBatchCreate,
    ProductBatchOut,
    ProductBatchUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    RouteCreate,
    RouteOut,
    RouteUpdate,
    VehicleCreate,
    VehicleOut,
    VehicleUpdate,
    WarehouseCreate,
    WarehouseOut,
    WarehouseUpdate,
)

warehouses_router = make_crud_router(
    model=Warehouse,
    create_schema=WarehouseCreate,
    update_schema=WarehouseUpdate,
    out_schema=WarehouseOut,
    prefix="/warehouses",
    tag="warehouses",
    write_permission="can_manage_masters",
)

products_router = make_crud_router(
    model=Product,
    create_schema=ProductCreate,
    update_schema=ProductUpdate,
    out_schema=ProductOut,
    prefix="/products",
    tag="products",
    write_permission="can_manage_products",
    order_by=[Product.volume_ml, Product.name],
)

routes_router = make_crud_router(
    model=Route,
    create_schema=RouteCreate,
    update_schema=RouteUpdate,
    out_schema=RouteOut,
    prefix="/routes",
    tag="routes",
    write_permission="can_manage_masters",
)

customers_router = make_crud_router(
    model=Customer,
    create_schema=CustomerCreate,
    update_schema=CustomerUpdate,
    out_schema=CustomerOut,
    prefix="/customers",
    tag="customers",
    write_permission="can_manage_masters",
)

employees_router = make_crud_router(
    model=Employee,
    create_schema=EmployeeCreate,
    update_schema=EmployeeUpdate,
    out_schema=EmployeeOut,
    prefix="/employees",
    tag="employees",
    write_permission="can_manage_users",
)

vehicles_router = make_crud_router(
    model=Vehicle,
    create_schema=VehicleCreate,
    update_schema=VehicleUpdate,
    out_schema=VehicleOut,
    prefix="/vehicles",
    tag="vehicles",
    write_permission="can_manage_masters",
)

product_batches_router = make_crud_router(
    model=ProductBatch,
    create_schema=ProductBatchCreate,
    update_schema=ProductBatchUpdate,
    out_schema=ProductBatchOut,
    prefix="/product-batches",
    tag="product-batches",
    write_permission="can_manage_products",
)
