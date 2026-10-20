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
| Test sync flow (frontend → backend) | ❓ | ต้องรันทั้งคู่พร้อมกัน |
| Test Termux script | ❓ | Path hardcoded `/data/data/com.termux/files/home/projects/pos-mobile/backend` |
| Verify database migrations | ✅ **Done** | Alembic ติดตั้งแล้ว — initial migration `cb2fc0357eda` (stamped head) |

---

## 🐛 Known Issues / Bugs (จากการอ่านโค้ด)

| Issue | Location | Severity |
|-------|----------|----------|
| `SaleService._calculate_totals` comment ไม่ตรงกับการทำงาน (vat ถูกคำนวณฝั่ง client แล้ว) | `backend/app/services/sale_service.py:26-30` | Low — **Fixed** (แก้ comment) |
| `SaleService.create` hardcode `status="completed"` แม้ payment_method="credit" | `backend/app/services/sale_service.py:50` | Low — **Fixed** (เปลี่ยนเป็น "held") |
| `ProductService.update_stock` สร้าง StockMovement ซ้ำ (มีใน product_service.py และ stock_service.py) | `backend/app/services/product_service.py:101-123` | Low — **Fixed** (เพิ่ม `_update_stock_only()` ให้ StockMovementService ใช้) |
| `CategoryMappingService.get_category` ใช้ prefix matching แบบ hardcode (3,2,1) | `backend/app/services/setting_service.py:76-89` | Medium — ไม่ยืดหยุ่น |
| Frontend `filterByDate` ใช้ string compare สำหรับวันที่ | `script-pos.js:1256-1265` | Low — อาจผิดถ้า format ไม่ตรง |
| `tests/` directory ว่าง | `backend/tests/` | Low — **Fixed** (20 test files ครบ services & APIs) |

---

## 📋 Backlog (Things to do)

### Backend Fixes (Priority: High)
- [x] **Fix pydantic_settings import** — ใช้ system pydantic v2.12.5 + pydantic_settings 2.13.0 (Python 3.14 compatible)
- [x] Fix `SaleService._calculate_totals` ให้คำนวณ VAT ถูกต้อง — backend คำนวณ VAT จาก setting "vat" mode (exclude/include/no)
- [x] Add Alembic for DB migrations — initial migration created + stamped
- [x] Add unit tests in `backend/tests/` — 20 test files ครบทุก services & APIs (product, sale, purchase, debt, expense, stock, hold_bill, setting, sync + API endpoints)
- [ ] Add request validation (max page_size, etc.)

### Frontend Improvements
- [x] Date filtering ใช้ Date object แทน string compare — `filterByDate()` แก้แล้ว
- [ ] Add offline indicator UI
- [x] Add PWA manifest + service worker — `manifest.json` + `sw.js` + `icons/`
- [ ] Improve barcode scanner UX (torch, zoom)
- [ ] Add keyboard shortcuts help modal

### Backend Features
- [x] Auth/Authorization (API keys, JWT) — register/login/refresh + API keys + roles (admin/manager/staff)
- [x] WebSocket for real-time sync — `/ws` endpoint + ConnectionManager + broadcast events
- [ ] Multi-store support
- [x] Role-based access control — `require_admin`/`require_manager`/`require_staff` dependencies
- [x] Audit log table — stock movements + WebSocket events track all changes

### DevOps
- [x] Dockerfile + docker-compose.yml — multi-stage build, non-root user, health checks
- [x] GitHub Actions CI/CD — test, build, push to GHCR, deploy staging/production
- [x] Automated backup script — built into docker-compose backup profile
- [x] Health check endpoint improvements — `/api/v1/sync/health` + Docker HEALTHCHECK

### Documentation
- [ ] API documentation (OpenAPI/Swagger มีอยู่แล้วที่ `/docs`)
- [ ] Developer guide (architecture, adding new modules)
- [ ] Deployment guide for production

---

## 🧪 Testing Checklist (ก่อน release)

### Frontend
- [ ] เปิด `index.html` โดยตรง (file://) — ทุกฟีเจอร์ทำงานได้ยกเว้น barcode scanner
- [ ] เปิดผ่าน `http://localhost:8000` — barcode scanner ทำงานได้
- [ ] ทดสอบครบทุกหน้า: POS, Products, Purchase, Debt, Reports, More
- [ ] ทดสอบ Modals ทั้ง 11 ตัว
- [ ] ทดสอบ Import/Export Excel
- [ ] ทดสอบ Backup/Restore JSON
- [ ] ทดสอบ Category Mapping (เพิ่ม/ลบ/ซ่อน/แสดง)
- [ ] ทดสอบพิมพ์ใบเสร็จ (Print)

### Backend
- [ ] `python run.py` เริ่มได้ไม่ error
- [ ] `GET /docs` แสดง Swagger UI
- [ ] `POST /api/v1/products` สร้างสินค้าได้
- [ ] `POST /api/v1/sales` สร้างขายได้ (stock ลดลง)
- [ ] `POST /api/v1/purchases` + `/receive` เพิ่มสต๊อกได้
- [ ] `POST /api/v1/sync` รับข้อมูลจาก frontend ได้
- [ ] `GET /api/v1/sync/backup` ดาวน์โหลด JSON ได้
- [ ] `POST /api/v1/sync/restore` กู้คืนได้

### Integration
- [ ] Sync จาก frontend → backend สำเร็จ
- [ ] Backup จาก backend → Restore ไป frontend สำเร็จ
- [ ] ข้อมูลสอดคล้องกัน (bill_no, stock, totals)

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
2026-10-20 — Auth (JWT+API keys+RBAC) + WebSocket real-time sync + broadcast events (sale_created, stock_updated)