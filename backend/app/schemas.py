"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal


# ==================== Product Schemas ====================

class ProductBase(BaseModel):
    code: str = Field(..., max_length=50)
    barcode: Optional[str] = Field(None, max_length=100)
    name: str = Field(..., max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    unit: str = Field("ชิ้น", max_length=20)
    price: Decimal = Field(0, ge=0)
    cost: Decimal = Field(0, ge=0)
    stock: int = Field(0, ge=0)
    min_stock: int = Field(0, ge=0)
    expiry_date: Optional[datetime] = None
    description: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    barcode: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    price: Optional[Decimal] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    min_stock: Optional[int] = Field(None, ge=0)
    expiry_date: Optional[datetime] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


# ==================== Sale Schemas ====================

class SaleItemBase(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    unit: str = "ชิ้น"
    quantity: int = Field(1, gt=0)
    unit_price: Decimal = Field(0, ge=0)
    discount: Decimal = Field(0, ge=0)
    line_total: Decimal = Field(0, ge=0)

    class Config:
        from_attributes = True


class SaleItemCreate(SaleItemBase):
    pass


class SaleItemResponse(SaleItemBase):
    id: int

    class Config:
        from_attributes = True


class SaleBase(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    discount: Decimal = Field(0, ge=0)
    vat: Decimal = Field(0, ge=0)
    payment_method: str = Field("cash", pattern="^(cash|transfer|card|credit)$")
    paid_amount: Decimal = Field(0, ge=0)
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class SaleCreate(SaleBase):
    items: List[SaleItemCreate] = Field(..., min_length=1)


class SaleUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    discount: Optional[Decimal] = Field(None, ge=0)
    vat: Optional[Decimal] = Field(None, ge=0)
    payment_method: Optional[str] = Field(None, pattern="^(cash|transfer|card|credit)$")
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(completed|held|cancelled)$")
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class SaleResponse(SaleBase):
    id: int
    bill_no: str
    subtotal: Decimal
    total: Decimal
    change_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    items: List[SaleItemResponse] = []

    class Config:
        from_attributes = True


class SaleListResponse(BaseModel):
    items: List[SaleResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


# ==================== Purchase Schemas ====================

class PurchaseItemBase(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    unit: str = "ชิ้น"
    quantity: int = Field(1, gt=0)
    unit_cost: Decimal = Field(0, ge=0)
    line_total: Decimal = Field(0, ge=0)
    received_qty: int = Field(0, ge=0)

    class Config:
        from_attributes = True


class PurchaseItemCreate(PurchaseItemBase):
    pass


class PurchaseItemResponse(PurchaseItemBase):
    id: int

    class Config:
        from_attributes = True


class PurchaseBase(BaseModel):
    supplier_name: Optional[str] = Field(None, max_length=200)
    supplier_phone: Optional[str] = Field(None, max_length=20)
    status: str = Field("pending", pattern="^(pending|received|cancelled)$")
    notes: Optional[str] = None
    expected_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchaseCreate(PurchaseBase):
    items: List[PurchaseItemCreate] = Field(..., min_length=1)


class PurchaseUpdate(BaseModel):
    supplier_name: Optional[str] = Field(None, max_length=200)
    supplier_phone: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, pattern="^(pending|received|cancelled)$")
    notes: Optional[str] = None
    expected_date: Optional[datetime] = None
    received_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class PurchaseResponse(PurchaseBase):
    id: int
    po_no: str
    total: Decimal
    received_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    items: List[PurchaseItemResponse] = []

    class Config:
        from_attributes = True


class PurchaseListResponse(BaseModel):
    items: List[PurchaseResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


# ==================== Debt Schemas ====================

class DebtPaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field("cash", pattern="^(cash|transfer|card)$")
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class DebtPaymentCreate(DebtPaymentBase):
    pass


class DebtPaymentResponse(DebtPaymentBase):
    id: int
    debt_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DebtBase(BaseModel):
    customer_name: str = Field(..., max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class DebtCreate(DebtBase):
    pass


class DebtUpdate(BaseModel):
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class DebtResponse(DebtBase):
    id: int
    total_debt: Decimal
    paid_amount: Decimal
    remaining: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    payments: List[DebtPaymentResponse] = []

    class Config:
        from_attributes = True


class DebtListResponse(BaseModel):
    items: List[DebtResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


# ==================== Expense Schemas ====================

class ExpenseBase(BaseModel):
    category: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    amount: Decimal = Field(..., gt=0)
    payment_method: str = Field("cash", pattern="^(cash|transfer|card)$")
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ExpenseCreate(ExpenseBase):
    date: Optional[datetime] = None


class ExpenseUpdate(BaseModel):
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    amount: Optional[Decimal] = Field(None, gt=0)
    payment_method: Optional[str] = Field(None, pattern="^(cash|transfer|card)$")
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ExpenseResponse(ExpenseBase):
    id: int
    date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    items: List[ExpenseResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


# ==================== Stock Movement Schemas ====================

class StockMovementBase(BaseModel):
    product_id: int
    movement_type: str = Field(..., pattern="^(in|out|adjust|waste|return)$")
    quantity: int = Field(..., gt=0)
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[int] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class StockMovementCreate(StockMovementBase):
    pass


class StockMovementResponse(StockMovementBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Hold Bill Schemas ====================

class HoldBillBase(BaseModel):
    items: str  # JSON string
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    subtotal: Decimal = Field(0, ge=0)
    discount: Decimal = Field(0, ge=0)
    vat: Decimal = Field(0, ge=0)
    total: Decimal = Field(0, ge=0)

    class Config:
        from_attributes = True


class HoldBillCreate(HoldBillBase):
    pass


class HoldBillResponse(HoldBillBase):
    id: int
    bill_no: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Setting Schemas ====================

class SettingBase(BaseModel):
    key: str = Field(..., max_length=100)
    value: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SettingResponse(SettingBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Category Mapping Schemas ====================

class CategoryMappingBase(BaseModel):
    code_prefix: str = Field(..., max_length=20)
    category: str = Field(..., max_length=100)

    class Config:
        from_attributes = True


class CategoryMappingCreate(CategoryMappingBase):
    pass


class CategoryMappingUpdate(BaseModel):
    category: Optional[str] = Field(None, max_length=100)

    class Config:
        from_attributes = True


class CategoryMappingResponse(CategoryMappingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Sync/Backup Schemas ====================

class SyncRequest(BaseModel):
    """Request to sync localStorage data to backend."""
    products: List[ProductCreate] = []
    sales: List[SaleCreate] = []
    purchases: List[PurchaseCreate] = []
    debts: List[DebtCreate] = []
    expenses: List[ExpenseCreate] = []
    stock_movements: List[StockMovementCreate] = []
    hold_bills: List[HoldBillCreate] = []
    settings: List[SettingCreate] = []
    category_mappings: List[CategoryMappingCreate] = []

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    """Response after sync."""
    success: bool
    message: str
    counts: dict

    class Config:
        from_attributes = True


class BackupResponse(BaseModel):
    """Full backup response."""
    timestamp: datetime
    version: str
    data: dict

    class Config:
        from_attributes = True