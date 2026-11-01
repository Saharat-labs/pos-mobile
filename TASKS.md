# POS-MOBILE TASKS.md

> Tasks derived from actual code inspection — **not guessed**

---

## ✅ Completed / Working (จากโค้ดจริง)

- [x] Frontend Single-Page App (index.html + script-pos.js + style-pos.css)
- [x] 6 หน้าหลัก: POS, Products, Purchase, Debt, Reports, More
- [x] 11 Modals ครบถ้วน
- [x] LocalStorage persistence (prefix `qpos_`)
- [x] Barcode scanning (กล้องสด + ถ่ายรูป) + Fallback
- [x] Excel Import/Export (SheetJS CDN)
- [x] Charts (Chart.js CDN) — Sales, Stock, Expense, Compare
- [x] Category Mapping (Official 124 codes + Custom)
- [x] Full Backup/Restore JSON
- [x] Backend FastAPI + SQLite (13 tables)
- [x] REST API `/api/v1/*` ครบทุกโมดูล
- [x] Sync endpoint (client → server)
- [x] Backup/Restore API endpoints
- [x] Termux startup script
- [x] Systemd service file

---

## 🔄 In Progress / Needs Verification

| Task | Status | Notes |
|------|--------|-------|
| Verify pydantic_settings import | ✅ **Fixed** | ใช้ `from pydantic_settings import BaseSettings` — ใช้ system pydantic v2.12.5 (Python 3.14 compatible) |
| Test backend startup | ✅ **Done** | `python run.py` เริ่มได้ ไม่ error — Swagger UI at /docs ทำงาน |
| Test sync flow (frontend → backend) | ❌ **ยังไม่ได้** | `backend/scripts/smoke_test.py` ยืนยันว่าไฟล์ export ของ frontend ถูก `POST /api/v1/sync` ปฏิเสธ `422` (schema ไม่ตรง) — ดู Known Issues |
| Test Termux script | ❓ | Path hardcoded `/data/data/com.termux/files/home/projects/pos-mobile/backend` |
| Verify database migrations | ✅ **Done** | Alembic revisions `001` (initial schema) → `002` (auth tables) → `003` (multi-store, head) ใน `backend/alembic/versions/` |

---

## 🐛 Known Issues / Bugs (จากการอ่านโค้ด)

| Issue | Location | Severity |
|-------|----------|----------|
| `SaleService._calculate_totals` comment ไม่ตรงกับการทำงาน (vat ถูกคำนวณฝั่ง client แล้ว) | `backend/app/services/sale_service.py:26-30` | Low — **Fixed** (แก้ comment) |
| `SaleService.create` hardcode `status="completed"` แม้ payment_method="credit" | `backend/app/services/sale_service.py:50` | Low — **Fixed** (เปลี่ยนเป็น "held") |
| `ProductService.update_stock` สร้าง StockMovement ซ้ำ (มีใน product_service.py และ stock_service.py) | `backend/app/services/product_service.py:101-123` | Low — **Fixed** (เพิ่ม `_update_stock_only()` ให้ StockMovementService ใช้) |
| `CategoryMappingService.get_category` ใช้ prefix matching แบบ hardcode (3,2,1) | `backend/app/services/setting_service.py` | Medium — **Fixed** (เปลี่ยนเป็น longest-prefix match จริง) |
| Frontend `filterByDate` ใช้ string compare สำหรับวันที่ | `script-pos.js:1256-1265` | Low — อาจผิดถ้า format ไม่ตรง |
| `tests/` directory ว่าง | `backend/tests/` | Low — **Fixed** (20 test files ครบ services & APIs) |
| `SaleService._calculate_totals` ใช้ `line_total` ที่ client ส่งมา (ถ้าไม่ส่งได้ subtotal=0) | `backend/app/services/sale_service.py` | Medium — **Fixed** (คำนวณจาก unit_price*qty-discount เอง) |
| Test เรียก `service.sync()` แต่ method จริงชื่อ `sync_from_client` | `tests/test_sync_service.py` | Low — **Fixed** (แก้ชื่อ method) |
| `pytest-asyncio` ไม่ได้ติดตั้ง (อยู่ใน requirements แต่ลงไม่ครบ) | `backend/` | Medium — **Fixed** (ติดตั้ง `pip install --break-system-packages pytest-asyncio==0.24.0`) |
| Test bugs ทั้งหมด (ชื่อ method ผิด, คาดค่า hardcoded, status code ไม่ตรง) | `tests/*` | Medium — **Fixed** ทั้งหมด → `167 passed, 0 failed` |
| Bug จริงที่แก้เพิ่ม: hold_bill/po_no ชนกันถ้าสร้างในวินาทีเดียว / `GET /settings/mappings` ถูก `/{key}` shadow (404) / sales ไม่เช็คสต็อกก่อนขาย | `app/services/hold_bill_service.py`, `purchase_service.py`, `app/api/settings.py`, `sale_service.py` | High — **Fixed** (เพิ่ม microseconds+random, แยก `mappings_router` register ก่อน, เพิ่ม stock validation) |

| **ยังเปิดอยู่ (พบจาก final review — ยังไม่แก้)** | | |
| Frontend ↔ backend sync schema ไม่ตรงกัน: ไฟล์ export ของ frontend (`products[].product_id`, `debts[].customer`, `holdBills`, `billCounter`, `categoryMapping` ฯลฯ) ถูก `POST /api/v1/sync` ปฏิเสธ `422` ต้องมี mapping ก่อนจะ sync ได้ | `script-pos.js` `exportBackupJSON()`, `backend/app/schemas.py` `SyncRequest` | High |
| `/sync/restore` ทำข้อมูลหาย: sale `created_at`/`status`, PO `po_number`/`received_qty`/วันที่, debt `paid`/`payments`/`status`, และ stock movement ไม่ผูก product ใหม่ | `backend/app/services/sync_service.py` `restore_backup()` | High |
| `POST /api/v1/sync` ไม่ idempotent — ส่ง payload เดิมซ้ำจะสร้าง sale/expense/debt ซ้ำ | `backend/app/services/sync_service.py` `sync_from_client()` | Medium |
| ไฟล์สำรอง JSON ของ frontend ไม่มี `hiddenMappingPrefixes` (หมวดที่ซ่อนไว้กลับมาแสดงหลังกู้คืน) | `script-pos.js` `exportBackupJSON()` | Low |
| `confirmPayDebt()` รับยอด 0 และยอดเกินหนี้ได้ (ไม่ validate) | `script-pos.js` `confirmPayDebt()` | Medium |
| ขายเชื่อบันทึก `subtotal` เป็นยอดหลังหักส่วนลดและ `discount: 0` (ส่วนลดหายจากรายงาน/ใบเสร็จ) | `script-pos.js` `finalizeCreditSale()` | Low |
| Import Excel จับคู่สินค้าด้วย `product_id` ที่ว่าง (`'' === ''`) — แถวที่ไม่มีรหัสอาจไปทับสินค้าที่ไม่มีรหัสตัวแรก | `script-pos.js` `importExcel()` | Medium |
| แตะปุ่มสแกนสองครั้งเร็ว ๆ เปิด `getUserMedia` สองครั้ง stream แรกไม่ถูกปิด (กล้องค้าง) | `script-pos.js` `openLiveScanner()` | Low |
| `nginx.conf` ไม่ส่ง header `Upgrade`/`Connection` และไม่ proxy `/ws` — WebSocket ใช้ผ่านพอร์ต 8080 ไม่ได้ | `nginx.conf` `location /api/` | Low |
| ไม่มี `backend/.dockerignore` — `backend/.env`, `*.db`, `venv/` ใน `backend/` จะถูก copy เข้า image | `backend/` | Medium |
| `docker-compose.yml` ไม่ส่ง `AUTH_ENABLED`/`JWT_SECRET` ให้ backend (ต้องใช้ override) | `docker-compose.yml` service `backend` `environment:` | Medium |
| เมื่อ `AUTH_ENABLED=false` ระบบสร้าง `dev@local` / `devpass` เป็น **admin** อัตโนมัติ (ค้างอยู่ใน DB ถ้าเปิด auth ทีหลัง) | `backend/app/auth.py` | Medium |

---

## 📋 Backlog (Things to do)

### Backend Fixes (Priority: High)
- [x] **Fix pydantic_settings import** — ใช้ system pydantic v2.12.5 + pydantic_settings 2.13.0 (Python 3.14 compatible)
- [x] Fix `SaleService._calculate_totals` ให้คำนวณ VAT ถูกต้อง — backend คำนวณ VAT จาก setting "vat" mode (exclude/include/no)
- [x] Add Alembic for DB migrations — initial migration created + stamped
- [x] Add unit tests in `backend/tests/` — 20 test files ครบทุก services & APIs (product, sale, purchase, debt, expense, stock, hold_bill, setting, sync + API endpoints)
- [x] Add request validation (max page_size, etc.) — list endpoints ใช้ `Query(ge=1, le=MAX_PAGE_SIZE)` ครบ รวม `GET /auth/users` ที่เคยไม่จำกัด (+ tests)

### Frontend Improvements
- [x] Date filtering ใช้ Date object แทน string compare — `filterByDate()` แก้แล้ว
- [x] Add offline indicator UI — แดง = ออฟไลน์, เหลือง = เชื่อม backend ไม่ได้ (health check ทุก 30 วิ, ข้าม static host ที่ไม่มี backend)
- [x] Add PWA manifest + service worker — `manifest.json` + `sw.js` + `icons/`
- [x] Improve barcode scanner UX (torch, zoom) — `openLiveScanner()` มีพรีวิว สแกนต่อเนื่อง ไฟฉาย/ซูมตาม `track.getCapabilities()`
- [x] Add keyboard shortcuts help modal — F2 / F4 F8 F9 Esc ? + `#modal-shortcuts`

### Backend Features
- [x] Auth/Authorization (API keys, JWT) — register/login/refresh + API keys + roles (admin/manager/staff)
- [x] WebSocket for real-time sync — `/ws` endpoint + ConnectionManager + broadcast events
- [x] Multi-store support (Backend) — Store model + migration 003 + store_id ในทุก model + StoreService/Store API + Products/Sales store-scoped + service อื่นรับ store_id (default=1) + get_current_store dependency
- [x] Multi-store frontend (store switcher UI) — แยกข้อมูลใน localStorage ต่อร้าน (ร้าน 1 = prefix `qpos_` เดิม, ร้านอื่น `qpos_s<id>_`) ยังไม่ผูกกับ store ของ backend
- [x] Multi-store API routes ที่เหลือ (purchases/debts/expenses/stock/hold_bills/settings) ใช้ get_current_store แล้ว — ทดสอบข้ามร้านจริง: แต่ละร้านเห็นเฉพาะข้อมูลตัวเอง
- [x] Sync แบบ multi-store — `sync_from_client`/`full_backup`/`restore_backup` รับ store_id, API ส่ง `get_current_store`; restore ลบเฉพาะข้อมูลร้านตัวเอง (category_mappings ยังเป็น global) — ทดสอบข้ามร้านผ่าน
- [x] Role-based access control — `require_admin`/`require_manager`/`require_staff` dependencies
- [x] Audit log table — stock movements + WebSocket events track all changes

### DevOps
- [x] Dockerfile + docker-compose.yml — multi-stage build, non-root user, health checks
- [x] GitHub Actions CI/CD — test, build, push to GHCR, deploy staging/production
- [x] Automated backup script — built into docker-compose backup profile
- [x] Health check endpoint improvements — `/api/v1/sync/health` + Docker HEALTHCHECK

### Documentation
- [x] API documentation — Swagger `/docs` (+ ReDoc `/redoc`, `/openapi.json`) และตาราง router ใน [docs/DEVELOPER_GUIDE.md §6](docs/DEVELOPER_GUIDE.md#6-การรันและทดสอบ--api-documentation)
- [x] Developer guide (architecture, adding new modules) → [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
- [x] Deployment guide for production → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 🧪 Testing Checklist (ก่อน release)

### Frontend
> อัตโนมัติด้วย `tests/e2e/run.sh` (Playwright + Chromium, ดู [tests/e2e/README.md](tests/e2e/README.md)) — ชื่อเทสต์ในวงเล็บ

- [x] เปิด `index.html` โดยตรง (file://) — ทุกฟีเจอร์ทำงานได้ยกเว้น barcode scanner (`file:// — index.html opened from disk loads and works without page errors`)
- [x] เปิดผ่าน http (secure context: `http://127.0.0.1`) — barcode scanner ทำงานได้ (`camera scanner (stubbed BarcodeDetector)…` — กล้องจำลอง + BarcodeDetector stub; ยังควรลองกับกล้องมือถือจริงตาม checklist ใน docs/DEPLOYMENT.md §10.1)
- [x] ทดสอบครบทุกหน้า: POS, Products, Purchase, Debt, Reports, More (`every page renders without page errors…`)
- [x] ทดสอบ Modals ทุกตัว (ตอนนี้มี 13 `modal-*` + cart sheet) (`every modal opens and closes…`)
- [x] ทดสอบ Import/Export Excel (`Excel: every export button…`, `Excel import: …` 2 เทสต์)
- [x] ทดสอบ Backup/Restore JSON (`JSON backup download → modify data → restore…`)
- [x] ทดสอบ Category Mapping (เพิ่ม/ลบ/ซ่อน/แสดง) (`category mapping add / hide / show / delete…`)
- [x] ทดสอบพิมพ์ใบเสร็จ (Print) (`print button calls window.print` — `window.print` ถูกจำลอง)

### Backend
> ตรวจด้วย `python3 backend/scripts/smoke_test.py --base-url http://localhost:8000` กับ backend ที่รันอยู่ (ใช้ DB ทดลอง — ขั้น restore แทนที่ข้อมูลร้าน)

- [x] `python run.py` เริ่มได้ไม่ error (smoke test ต้องมี server ที่เริ่มแล้ว + ดูตาราง In Progress ข้างบน)
- [x] `GET /docs` แสดง Swagger UI (check `docs + openapi`)
- [x] `POST /api/v1/products` สร้างสินค้าได้ (check `products create/get`)
- [x] `POST /api/v1/sales` สร้างขายได้ (stock ลดลง) (check `sales: stock, totals, oversell, bill_no`)
- [x] `POST /api/v1/purchases` + `/receive` เพิ่มสต๊อกได้ (check `purchases create + receive`)
- [ ] `POST /api/v1/sync` รับข้อมูลจาก frontend ได้ — **ยังไม่ได้**: payload ตาม schema ของ backend ผ่าน (`sync: backend schema shape`) แต่ไฟล์ export ของ frontend ได้ `422` (`sync: frontend export shape` = WARN)
- [x] `GET /api/v1/sync/backup` ดาวน์โหลด JSON ได้ (check `backup -> restore round trip`)
- [x] `POST /api/v1/sync/restore` กู้คืนได้ — จำนวนแถว, stock, bill_no ครบ (check เดียวกัน; ฟิลด์ที่ยังหายดู Known Issues)

### Integration
- [ ] Sync จาก frontend → backend สำเร็จ — **ยังไม่ได้**: frontend ไม่มีปุ่ม sync และไฟล์ export ถูก `/sync` ปฏิเสธ `422` (schema mismatch — ดู Known Issues)
- [ ] Backup จาก backend → Restore ไป frontend สำเร็จ — ยังไม่ได้ (รูปแบบไฟล์ต่างกัน); backup → restore ภายใน backend ผ่าน API ผ่านแล้วด้วย smoke test
- [ ] ข้อมูลสอดคล้องกัน (bill_no, stock, totals) ข้าม frontend ↔ backend — รอ sync; ฝั่ง backend อย่างเดียว smoke test ยืนยัน stock + bill_no หลัง restore

---

## 🔧 Quick Commands

```bash
# Backend dev
cd /root/projects/pos-mobile/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py                    # http://localhost:8000

# Frontend dev (serves index.html)
cd /root/projects/pos-mobile
python3 -m http.server 8080      # http://localhost:8080

# Termux
cd /root/projects/pos-mobile/backend
./start_termux.sh

# Run tests (when available)
cd /root/projects/pos-mobile/backend
python -m pytest tests/ -v

# Check DB schema
python3 -c "
import sqlite3
conn = sqlite3.connect('pos_mobile.db')
for row in conn.execute('SELECT sql FROM sqlite_master WHERE type=\"table\"'):
    print(row[0])
"
```

---

## ⚠️ Locked Rules (ห้ามละเมิด)

1. **`pos_mobile.db`** — ห้ามลบ/เขียนทับ/ย้าย ต้อง backup ก่อนแก้ schema
2. **OFFICIAL_CATEGORY_MAPPING** — ห้ามลบ/แก้ 124 รายการ CP All
3. **Master Product list** — ไฟล์ `master-products.js` ไม่อยู่ใน repo ห้ามเพิ่มเข้า repo
4. **`.env`** — ห้าม commit (อยู่ใน .gitignore)
5. **`venv/`** — ห้าม commit (อยู่ใน .gitignore)

---

## 📅 Last Updated
2026-10-21 — แก้ 🔴A restore/sync ตัด stock ซ้ำ: ตอน sync/restore สร้าง sale + stock movement แบบ `deduct_stock=False` (stock ใน payload เป็นค่าปัจจุบันอยู่แล้ว ห้ามหัก/บวกซ้ำ), sale item ผูก product ใหม่ด้วย `product_code` (id เปลี่ยนหลัง restore), และ `bulk_create` upsert ไม่ให้ payload ทับ `store_id` (sync สินค้าซ้ำรอบ 2 เดิมพัง NOT NULL) — **tests 169 passed, 0 failed** (ใหม่ 2: sync ไม่ตัดซ้ำ + restore backup ที่มีขายสำเร็จ)

**วิธีรัน:** `cd ~/projects/pos-mobile/backend && python3 run.py` → http://localhost:8000
**รัน test:** `cd ~/projects/pos-mobile/backend && PYTHONPATH=/usr/lib/python3/dist-packages:/data/data/com.termux/files/usr/lib/python3.14/site-packages python3 -m pytest tests/ -q`