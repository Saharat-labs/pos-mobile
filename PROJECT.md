# POS-MOBILE Project Documentation

> Generated from actual code inspection — **not guessed**

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```
pos-mobile/
├── index.html           # Frontend: หน้าเว็บหลัก Single-Page App (588 บรรทัด)
├── script-pos.js        # Frontend: Logic ทั้งหมด ~1,865 บรรทัด
├── style-pos.css        # Frontend: Theme, Layout, Responsive, Print CSS (804 บรรทัด)
├── README.md            # Project overview (83 บรรทัด)
├── USER_GUIDE.md        # คู่มือการใช้งานฉบับสมบูรณ์ (601 บรรทัด)
├── LICENSE              # MIT License
├── .gitignore           # Python/Node/IDE ignores
├── .nojekyll            # GitHub Pages
└── backend/
    ├── run.py                 # Python entry point (uvicorn)
    ├── requirements.txt       # Python dependencies
    ├── start_termux.sh        # Termux startup script
    ├── pos-mobile.service     # Systemd service (Termux)
    ├── pos_mobile.db          # SQLite DB (LOCKED - ห้ามลบ/เขียนทับ)
    ├── .env.example           # Config template
    ├── app/
    │   ├── __init__.py        # version = "1.0.0"
    │   ├── config.py          # Pydantic Settings (BaseSettings)
    │   ├── database.py        # SQLAlchemy async engine + session
    │   ├── main.py            # FastAPI app + lifespan + CORS
    │   ├── schemas.py         # Pydantic models (498 บรรทัด)
    │   ├── models/
    │   │   └── __init__.py    # 13 SQLAlchemy models (253 บรรทัด)
    │   ├── services/
    │   │   ├── __init__.py    # exports 10 services
    │   │   ├── product_service.py
    │   │   ├── sale_service.py
    │   │   ├── purchase_service.py
    │   │   ├── debt_service.py
    │   │   ├── expense_service.py
    │   │   ├── stock_service.py
    │   │   ├── hold_bill_service.py
    │   │   ├── setting_service.py
    │   │   └── sync_service.py
    │   └── api/
    │       ├── __init__.py    # api_router prefix /api/v1
    │       ├── products.py
    │       ├── sales.py
    │       ├── purchases.py
    │       ├── debts.py
    │       ├── expenses.py
    │       ├── stock_movements.py
    │       ├── hold_bills.py
    │       ├── settings.py
    │       └── sync.py
    └── tests/                 # (ว่างเปล่า)
```

---

## 🔧 เทคโนโลยีและ Dependencies

### Frontend (Vanilla, ไม่มี build step)
| Library | Version | ใช้ทำอะไร | โหลดผ่าน |
|---------|---------|-----------|----------|
| SheetJS (xlsx.js) | 0.18.5 | นำเข้า/ส่งออก Excel | CDN + SRI |
| Chart.js | 4.4.0 | กราฟรายงาน | CDN + SRI |
| Font: Sarabun | - | ฟอนต์ไทย | Google Fonts |

### Backend (Python 3.10+)
| Package | Version |
|---------|---------|
| fastapi | 0.109.2 |
| uvicorn[standard] | 0.32.0 |
| sqlalchemy | 2.0.36 |
| aiosqlite | 0.20.0 |
| pydantic | 1.10.15 |
| python-dotenv | 1.0.1 |
| python-multipart | 0.0.12 |
| httpx | 0.28.1 |
| pytest | 9.0.0 |
| pytest-asyncio | 0.24.0 |
| pytest-cov | 6.0.0 |

---

## 🗄️ Database Schema (จาก pos_mobile.db จริง)

### Tables (13 ตาราง)
| Table | Columns สำคัญ | Indexes / Constraints |
|-------|--------------|----------------------|
| **products** | id, code(UNIQUE), barcode(UNIQUE), name, category, unit, price, cost, stock, min_stock, expiry_date, description, is_active, created_at, updated_at | ix_products_category_active, ix_products_stock |
| **sales** | id, bill_no(UNIQUE), customer_name, customer_phone, subtotal, discount, vat, total, payment_method, paid_amount, change_amount, status, notes, created_at, updated_at | |
| **sale_items** | id, sale_id(FK→sales CASCADE), product_id(FK→products), product_code, product_name, unit, quantity, unit_price, discount, line_total | |
| **purchases** | id, po_no(UNIQUE), supplier_name, supplier_phone, total, status, notes, expected_date, received_date, created_at, updated_at | |
| **purchase_items** | id, purchase_id(FK→purchases CASCADE), product_id(FK→products), product_code, product_name, unit, quantity, unit_cost, line_total, received_qty | |
| **debts** | id, customer_name, customer_phone, total_debt, paid_amount, remaining, status, notes, created_at, updated_at | |
| **debt_payments** | id, debt_id(FK→debts CASCADE), amount, payment_method, notes, created_at | |
| **expenses** | id, date, category, description, amount, payment_method, notes, created_at, updated_at | ix_expenses_date_category |
| **stock_movements** | id, product_id(FK→products), movement_type, quantity, reference_type, reference_id, notes, created_at | ix_stock_movements_product_date |
| **hold_bills** | id, bill_no(UNIQUE), items(JSON text), customer_name, customer_phone, subtotal, discount, vat, total, created_at, updated_at | |
| **settings** | id, key(UNIQUE), value, description, updated_at | uq_settings_key |
| **category_mappings** | id, code_prefix(UNIQUE), category, created_at, updated_at | |

---

## 📱 Frontend Features (จาก index.html + script-pos.js)

### Pages (Single-Page App, สลับด้วย `showPage()`)
| Page ID | Title | Icon | Key Features |
|---------|-------|------|--------------|
| `pos` | ขายสินค้า | 🛒 | ค้นหา/สแกน barcode, ตะกร้า, ส่วนลด, VAT 7%, ชำระเงินสด/โอน/บัตร/เชื่อ, พักบิล, คีย์แพดเงินทอน |
| `products` | สินค้า | 📦 | CRUD สินค้า, ค้นหา/กรอง, auto-fill จาก Master Product, นำเข้า/ส่งออก Excel, ปรับสต๊อก |
| `purchase` | สั่งซื้อ | 🚚 | สร้าง PO, รับเข้า (เพิ่มสต๊อก), ค้นหาตามวันที่, Export Excel |
| `debt` | ลูกหนี้ | 💳 | บันทึกหนี้, รับชำระบางส่วน/เต็ม, สรุปยอดค้าง |
| `reports` | รายงาน | 📊 | 3 แท็บ: ยอดขาย (กราฟแท่ง/โดนัท/สินค้าขายดี/เปรียบเทียบช่วงเวลา), สต๊อก, รายจ่าย — Export Excel ทุกแท็บ |
| `more` | เพิ่มเติม/ตั้งค่า | ⚙️ | รายจ่าย, ปรับสต็อกด่วน, บิลพัก, นำเข้า/ส่งออก, Backup/Restore JSON, Category Mapping, Settings |

### Modals (ทั้งหมดอยู่ใน index.html)
- `cart-sheet` — ตะกร้าสินค้า (slide-up)
- `modal-payment` — ชำระเงิน (Cash/Transfer/Card + Keypad)
- `modal-receipt` — ใบเสร็จ (พิมพ์ได้)
- `modal-hold` — บิลพัก
- `modal-product` — เพิ่ม/แก้ไขสินค้า
- `modal-master-search` — ค้นหาจาก Master Product
- `modal-stock-adjust` — ปรับสต๊อก
- `modal-purchase` — บันทึกสั่งซื้อ
- `modal-debt` — เพิ่ม/แก้ไขลูกหนี้
- `modal-pay-debt` — รับชำระหนี้
- `modal-expense` — บันทึกรายจ่าย

### LocalStorage Keys (prefix `qpos_`)
| Key | Description |
|-----|-------------|
| `products` | Array of products |
| `sales` | Array of sales |
| `purchases` | Array of purchases |
| `debts` | Array of debts |
| `expenses` | Array of expenses |
| `holdBills` | Array of held bills |
| `billCounter` | Running bill number |
| `settings` | Store + system settings |
| `categoryMapping` | Custom category mappings |
| `hiddenMappingPrefixes` | Hidden prefixes in mapping UI |
| `cart` | Current cart |

### Barcode Scanning
- **กล้องสด**: `BarcodeDetector` + `getUserMedia` (ต้อง HTTPS/localhost)
- **ถ่าย/เลือกรูป**: `BarcodeDetector` + `createImageBitmap` (ทำงานได้บน file://)
- Fallback: กรอกรหัสด้วยมือ

---

## 🖥️ Backend API (FastAPI, prefix `/api/v1`)

### Endpoints สำคัญ

| Module | Endpoints |
|--------|-----------|
| **Products** | `GET/POST /products`, `GET /products/{id}`, `GET /products/code/{code}`, `GET /products/barcode/{barcode}`, `PUT /products/{id}`, `DELETE /products/{id}` (soft), `POST /products/bulk`, `POST /products/{id}/stock`, `GET /products/low-stock`, `GET /products/expiring`, `GET /products/categories` |
| **Sales** | `POST /sales`, `GET /sales`, `GET /sales/{id}`, `GET /sales/bill/{bill_no}`, `PUT /sales/{id}`, `GET /sales/summary/daily`, `GET /sales/summary/top-products` |
| **Purchases** | `POST /purchases`, `GET /purchases`, `GET /purchases/{id}`, `GET /purchases/po/{po_no}`, `PUT /purchases/{id}`, `POST /purchases/{id}/receive` |
| **Debts** | `POST /debts`, `GET /debts`, `GET /debts/{id}`, `GET /debts/customer/{name}`, `PUT /debts/{id}`, `POST /debts/{id}/payments`, `GET /debts/summary` |
| **Expenses** | `POST /expenses`, `GET /expenses`, `GET /expenses/{id}`, `PUT /expenses/{id}`, `DELETE /expenses/{id}`, `GET /expenses/categories`, `GET /expenses/summary/monthly`, `GET /expenses/summary/yearly` |
| **Stock Movements** | `POST /stock-movements`, `GET /stock-movements`, `GET /stock-movements/product/{id}` |
| **Hold Bills** | `POST /hold-bills`, `GET /hold-bills`, `GET /hold-bills/{id}`, `GET /hold-bills/bill/{bill_no}`, `DELETE /hold-bills/{id}` |
| **Settings** | `GET/POST/PUT/DELETE /settings`, `GET /settings/{key}`, `GET/POST/PUT/DELETE /settings/mappings`, `POST /settings/mappings/bulk` |
| **Sync/Backup** | `POST /sync` (sync from client), `GET /sync/backup` (full backup JSON), `POST /sync/restore`, `GET /sync/health` |

### Sync/Backup Payload (SyncRequest)
```json
{
  "products": [...],
  "sales": [...],
  "purchases": [...],
  "debts": [...],
  "expenses": [...],
  "stock_movements": [...],
  "hold_bills": [...],
  "settings": [...],
  "category_mappings": [...]
}
```

---

## ⚙️ Configuration (backend/.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | "POS-MOBILE API" | ชื่อแอป |
| `APP_VERSION` | "1.0.0" | เวอร์ชัน |
| `DEBUG` | true | Debug mode |
| `DATABASE_URL` | `sqlite+aiosqlite:///./pos_mobile.db` | SQLite path |
| `DATABASE_ECHO` | false | SQL logging |
| `HOST` | "0.0.0.0" | Bind address |
| `PORT` | 8000 | Port |
| `DATA_DIR` | `/data/data/com.termux/files/home/pos-mobile-data` | Termux data dir |
| `CORS_ORIGINS` | `["http://localhost:8000", "http://127.0.0.1:8000", "file://", "null"]` | CORS origins |

---

## 🏃‍♂️ การรัน (How to Run)

### Frontend Only (Offline-first)
```bash
# เปิดไฟล์โดยตรง
open index.html
# หรือ
python3 -m http.server 8080
# เข้า http://localhost:8080
```

### Backend + Frontend (Termux/Android)
```bash
cd /root/projects/pos-mobile/backend
chmod +x start_termux.sh
./start_termux.sh
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Backend + Frontend (Desktop/Server)
```bash
cd /root/projects/pos-mobile/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
# API: http://localhost:8000
```

### Systemd (Linux server)
```bash
sudo cp pos-mobile.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pos-mobile
sudo systemctl start pos-mobile
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    POS-MOBILE SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Browser)              Backend (FastAPI + SQLite) │
│  ┌─────────────────────┐         ┌─────────────────────┐   │
│  │ index.html          │ ◄─────► │ Port 8000           │   │
│  │ script-pos.js       │  Sync   │ pos_mobile.db       │   │
│  │ style-pos.css       │         │                     │   │
│  └─────────────────────┘         └─────────────────────┘   │
│         ▲                                  ▲                │
│         │ localStorage                     │                │
│         │ (Offline-first)                  │                │
│         ▼                                  ▼                │
│  📱 ใช้งานบนมือถือ/แท็บเล็ต         💾 เก็บข้อมูลถาวร      │
└─────────────────────────────────────────────────────────────┘
```

- **Offline-first**: Frontend ทำงานได้เต็มที่ใน localStorage
- **Sync เมื่อต้องการ**: POST `/api/v1/sync` จากหน้าตั้งค่า หรือ console
- **Backup/Restore**: JSON ผ่าน `/api/v1/sync/backup` และ `/api/v1/sync/restore`

---

## 📋 Category Mapping System

### OFFICIAL_CATEGORY_MAPPING (Locked, 124 รายการ)
- รหัส 01-99 ตามมาตรฐาน CP All
- `locked: true` — ลบ/แก้ไม่ได้ใน UI
- เก็บใน `script-pos.js` บรรทัด 36-124

### Custom Mappings
- ผู้ใช้เพิ่มได้ผ่านหน้า "เพิ่มเติม/ตั้งค่า"
- เก็บใน localStorage `categoryMapping` + `hiddenMappingPrefixes`
- Sync ไป backend ผ่าน `category_mappings` table

---

## 🔐 Locked Items (ล็อกแล้ว - ห้ามแก้)

> **⚠️ สำคัญ: สิ่งต่อไปนี้ห้ามลบ/เขียนทับ/เปลี่ยนแปลง**

1. **`pos_mobile.db`** — SQLite database file
   - ห้าม `rm`, `mv`, เขียนทับ
   - ต้อง **สำรองก่อนแก้โครงสร้างตาราง** (backup JSON หรือ copy file)
   - Schema จริงอยู่ใน `backend/app/models/__init__.py` (SQLAlchemy models)

2. **OFFICIAL_CATEGORY_MAPPING** (script-pos.js:36-124)
   - 124 รายการ CP All standard codes
   - `locked: true` — UI กันการลบ

3. **Master Product List** (`master-products.js`)
   - ไฟล์นี้ **ไม่ได้อยู่ใน repo** (ตาม README)
   - ถ้าต้องการใช้ ให้สร้างเองแล้ววางข้าง index.html

---

## 🤔 ไม่แน่ใจ (Uncertain Items)

| Item | Reason |
|------|--------|
| `tests/` directory ว่าง | ไม่มี test files จริง — อาจจะเพิ่มภายหลัง |
| `master-products.js` ไม่ได้ใน repo | README บอกว่า "ไฟล์นี้ไม่ได้รวมอยู่ใน repo" แต่ USER_GUIDE.md อ้างถึง |
| `pydantic_settings` import ใน config.py | `requirements.txt` มีแค่ `pydantic==1.10.15` — pydantic v1 ไม่มี `pydantic_settings` module แยก (อาจจะติดตั้งแยกหรือใช้ `pydantic.BaseSettings`) |
| `MASTER_PRODUCTS` variable | ใช้ใน script-pos.js แต่ไม่ได้ประกาศไว้ — ต้องมาจาก `master-products.js` |
| Termux service user | `pos-mobile.service` ใช้ `User=termux` แต่อาจจะต้องปรับตามเครื่องจริง |
| `pos_mobile.db` ขนาด 167KB | มีข้อมูลตัวอย่างอยู่แล้ว — ไม่แน่ใจว่าเป็น seed data หรือข้อมูลจริง |

---

## 📝 หมายเหตุเพิ่มเติม

- **Frontend**: ไม่มี build process, ไม่มี node_modules, รันได้ทันที
- **Backend**: ใช้ SQLAlchemy async + aiosqlite, Pydantic v1
- **Data sync**: One-way (client → server) ผ่าน `/api/v1/sync`
- **Print receipt**: ใช้ `@media print` CSS ใน style-pos.css
- **Thai language**: UI และ comments เป็นไทยทั้งหมด
- **Mobile-first**: CSS ใช้ `dvh`, touch-friendly, bottom nav