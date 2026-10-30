# 🖥️ POS-MOBILE Backend

### REST API + WebSocket สำหรับ POS-MOBILE — FastAPI + SQLAlchemy (async) + SQLite

> ⚠️ ปัจจุบัน **frontend (`script-pos.js`) ยังไม่เรียก API นี้เพื่อบันทึกข้อมูล** — แอปยังเก็บข้อมูลใน `localStorage`
> (เรียกเพียง `HEAD /api/v1/sync/health` ทุก 30 วินาทีเพื่อตรวจสถานะออนไลน์) backend นี้จึงใช้เรียกผ่าน HTTP/Swagger โดยตรงได้ แต่ยังไม่ได้ต่อกับหน้าเว็บ

---

## ✨ backend ทำอะไรได้

| ส่วน | รายละเอียด |
|:---|:---|
| 📦 **Products** | CRUD สินค้า, ค้นหาด้วย code/barcode, หมวดหมู่, สินค้าสต๊อกต่ำ/ใกล้หมดอายุ, นำเข้าหลายรายการ (bulk), ปรับสต๊อก |
| 🛒 **Sales** | บันทึก/ค้นหา/แก้ไขบิลขาย, สรุปยอดรายวัน, สินค้าขายดี |
| 🚚 **Purchases** | ใบสั่งซื้อ, รับสินค้าเข้าสต๊อก (`receive`) |
| 💳 **Debts** | ลูกหนี้, รับชำระหนี้, สรุปยอดค้าง |
| 💸 **Expenses** | รายจ่าย, สรุปรายเดือน/รายปี |
| 📋 **Stock movements / Hold bills** | ประวัติการเคลื่อนไหวสต๊อก, บิลพัก |
| ⚙️ **Settings / Category mappings** | key-value settings และ mapping หมวดหมู่ตาม prefix ของรหัสสินค้า |
| 🏪 **Stores** | หลายร้าน (multi-store) — ข้อมูลแยกตาม `store_id` |
| 🔄 **Sync / Backup** | รับข้อมูลจาก client (localStorage), สำรอง/กู้คืนข้อมูลทั้งร้าน |
| 🔐 **Auth** (ปิดเป็นค่า default) | JWT (access/refresh), API key (`X-API-Key`), role admin/manager/staff |
| 📡 **WebSocket** | แจ้งเตือน event แบบ real-time (เช่น `sale_created`, `stock_updated`) |

## 📁 โครงสร้างไฟล์

```
📦 backend
├── 🚀 run.py                → entry point (โหลด .env แล้วรัน uvicorn "app.main:app")
├── 📋 requirements.txt      → dependencies (pin version)
├── 🔧 .env.example          → ตัวอย่างไฟล์ตั้งค่า
├── 🐳 Dockerfile            → image ของ backend (python:3.12-slim, port 8000)
├── 🗄️ alembic.ini, alembic/ → migrations (versions/001, 002, 003)
├── 📱 start_termux.sh       → สคริปต์เริ่มระบบบน Termux (Android)
├── ⚙️ pos-mobile.service    → ตัวอย่าง systemd unit (path แบบ Termux)
├── 🧪 tests/                → pytest (api, services, websocket, auth)
└── 📂 app/
    ├── main.py              → FastAPI app, CORS, /health, /docs, /redoc
    ├── config.py            → Settings (อ่านจาก env / .env)
    ├── database.py, base.py → async engine/session, init_db()
    ├── auth.py              → JWT, API key, dependency get_current_user/get_current_store
    ├── schemas.py           → Pydantic schemas
    ├── api/                 → routers (auth, products, sales, purchases, debts, expenses,
    │                          stock_movements, hold_bills, settings, stores, sync, ws, websocket)
    ├── models/              → SQLAlchemy models
    ├── services/            → business logic
    └── websocket*.py        → connection manager
```

## 🚀 ติดตั้งและรันในเครื่อง

ต้องมี Python 3 (CI ใช้ 3.12 — ดู `.github/workflows/ci-cd.yml`)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # แล้วแก้ค่าตามต้องการ (ดูหัวข้อ Environment variables)
alembic upgrade head     # สร้างตาราง + ร้านเริ่มต้น (ต้องทำก่อนรันครั้งแรก)
python run.py            # เริ่มที่ http://0.0.0.0:8000
```

- 📖 Swagger UI: http://localhost:8000/docs  ·  ReDoc: `/redoc`  ·  OpenAPI: `/openapi.json`
- ❤️ Health: `GET /health` และ `GET`/`HEAD /api/v1/sync/health` (frontend เรียกแบบ `HEAD`)
- ถ้า `DEBUG=true` (ค่า default) `run.py` จะรัน uvicorn แบบ `reload`

> 💡 `DATA_DIR` มีค่า default เป็น `~/pos-mobile-data` (บน Termux คือ `/data/data/com.termux/files/home/pos-mobile-data`) — `run.py` จะสร้างโฟลเดอร์นี้ให้ตอนเริ่ม ตั้งค่าอื่นได้ผ่าน `DATA_DIR` ใน `.env`
>
> 💡 ควรรัน `alembic upgrade head` ก่อนเริ่มครั้งแรกเสมอ เพราะตอน start `init_db()` สร้างเฉพาะตาราง ไม่สร้างร้านเริ่มต้น

### 🧪 รันเทสต์

```bash
cd backend
python -m pytest tests/ -v
```

### 📱 Termux (Android)

`bash start_termux.sh` — สร้าง venv, ติดตั้ง dependencies, สร้าง `.env` จาก `.env.example`, เรียก `init_db()` แล้วรัน `run.py`
(path ในสคริปต์ hardcode เป็น `/data/data/com.termux/files/home/projects/pos-mobile/backend`)

## 🗄️ Database migrations (Alembic)

มี 3 revision ใน `alembic/versions/`: `001_initial_schema`, `002_add_auth_tables`, `003_add_multi_store`

```bash
alembic upgrade head        # ขึ้นเวอร์ชันล่าสุด
alembic downgrade -1        # ย้อนกลับ 1 revision
alembic revision -m "..."   # สร้าง revision ใหม่ (ตั้ง --autogenerate ได้)
```

หมายเหตุที่ตรวจจากโค้ด:
- `alembic/env.py` ใช้ `sqlalchemy.url` จาก `alembic.ini` (`sqlite+aiosqlite:///./pos_mobile.db`) เป็นค่าตั้งต้น แต่ถ้าตั้งตัวแปรสภาพแวดล้อม `DATABASE_URL` จะใช้ค่านั้นแทน (ทั้ง offline/online) เช่น `DATABASE_URL=sqlite+aiosqlite:////data/pos_mobile.db alembic upgrade head` — อ่านจาก environment จริงเท่านั้น (ไม่อ่านไฟล์ `.env`)
- `revision 003` สร้างร้านเริ่มต้น (`STORE001`) ให้ ส่วน `init_db()` ตอน start จะ `create_all` ตารางเท่านั้น ไม่สร้างร้าน — ถ้าเริ่มจาก DB เปล่าโดยไม่รัน `alembic upgrade head` การเรียก endpoint ที่ผูกกับร้านจะได้ `404 Store not found for current user` (ทดสอบแล้ว) `backend/Dockerfile` จึงรัน `alembic upgrade head` ก่อน `python run.py` ให้อัตโนมัติ

## 🔌 Endpoints

ทุก endpoint ด้านล่างมี prefix `/api/v1` ยกเว้นที่ระบุ — รายการเต็มและ schema ดูที่ `/docs`
(endpoint ข้อมูลส่วนใหญ่ผูกกับร้านปัจจุบันผ่าน `get_current_store`)

| Resource | Method + path |
|:---|:---|
| **Root** (ไม่มี prefix) | `GET /`, `GET /health` |
| **Products** `/products` | `POST ""`, `GET ""`, `GET /categories`, `GET /low-stock`, `GET /expiring`, `GET /{product_id}`, `GET /code/{code}`, `GET /barcode/{barcode}`, `PUT /{product_id}`, `DELETE /{product_id}`, `POST /bulk`, `POST /{product_id}/stock` |
| **Sales** `/sales` | `POST ""`, `GET ""`, `GET /summary/daily`, `GET /summary/top-products`, `GET /{sale_id}`, `GET /bill/{bill_no}`, `PUT /{sale_id}` |
| **Purchases** `/purchases` | `POST ""`, `GET ""`, `GET /{purchase_id}`, `GET /po/{po_no}`, `PUT /{purchase_id}`, `POST /{purchase_id}/receive` |
| **Debts** `/debts` | `POST ""`, `GET ""`, `GET /summary`, `GET /{debt_id}`, `GET /customer/{customer_name}`, `PUT /{debt_id}`, `POST /{debt_id}/payments` |
| **Expenses** `/expenses` | `POST ""`, `GET ""`, `GET /categories`, `GET /summary/monthly`, `GET /summary/yearly`, `GET /{expense_id}`, `PUT /{expense_id}`, `DELETE /{expense_id}` |
| **Stock movements** `/stock-movements` | `POST ""`, `GET ""`, `GET /product/{product_id}` |
| **Hold bills** `/hold-bills` | `POST ""`, `GET ""`, `GET /{bill_id}`, `GET /bill/{bill_no}`, `DELETE /{bill_id}` |
| **Settings** `/settings` | `GET ""`, `POST ""`, `GET /{key}`, `PUT /{key}`, `DELETE /{key}` |
| **Category mappings** `/settings/mappings` | `GET ""`, `POST ""`, `POST /bulk`, `GET /{code_prefix}`, `PUT /{code_prefix}`, `DELETE /{code_prefix}` |
| **Stores** `/stores` | `POST ""`, `GET ""`, `GET /default`, `GET /{store_id}`, `PUT /{store_id}`, `DELETE /{store_id}`, `GET /{store_id}/stats` |
| **Sync / Backup** `/sync` | `POST ""` (รับข้อมูลจาก client), `GET /backup`, `POST /restore`, `GET /health` |
| **Auth** `/auth` | `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `POST /logout-all`, `POST /change-password`, `POST /api-keys`, `GET /api-keys`, `DELETE /api-keys/{key_id}`, `GET /me`, `GET /users`, `GET /users/{user_id}`, `PATCH /users/{user_id}`, `DELETE /users/{user_id}`, `GET /health` |

### 📡 WebSocket

| Path | รายละเอียด |
|:---|:---|
| `ws://localhost:8000/api/v1/ws?room=default` | รับ event แบบ broadcast; ส่ง `ping` จะได้ `{"type": "pong"}` (`api/ws.py`) |
| `ws://localhost:8000/ws?client_id=<id>` | ต้องระบุ `client_id`; ส่ง `{"action": "subscribe"/"unsubscribe"/"ping"/"get_status"}` ได้ (`api/websocket.py`) |
| `GET /ws/status` | จำนวน client ที่เชื่อมต่อและรายการ event ที่มี |

## 🔧 Environment variables

อ่านผ่าน `app/config.py` (pydantic-settings, ไฟล์ `.env`, ชื่อ case-sensitive) — ตัวอย่างอยู่ใน `.env.example`

| ตัวแปร | Default | ความหมาย |
|:---|:---|:---|
| `APP_NAME` / `APP_VERSION` | `POS-MOBILE API` / `1.0.0` | ชื่อและเวอร์ชันที่แสดงใน API |
| `DEBUG` | `True` | `True` = uvicorn reload (`docker-compose.yml` และ `Dockerfile` ที่ root ตั้งเป็น `false`; `backend/Dockerfile` ไม่ได้ตั้ง) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./pos_mobile.db` | SQLAlchemy async URL |
| `DATABASE_ECHO` | `False` | แสดง SQL log |
| `CORS_ORIGINS` | `["http://localhost:8000","http://127.0.0.1:8000","file://","null"]` | JSON list ของ origin ที่อนุญาต |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | ที่อยู่/พอร์ตของเซิร์ฟเวอร์ |
| `DATA_DIR` | `~/pos-mobile-data` (`Path.home()`) | โฟลเดอร์ข้อมูล (`run.py` สร้างให้ตอนเริ่ม) |
| `AUTH_ENABLED` | `False` | `False` = ข้ามการยืนยันตัวตน (ใช้/สร้าง user `dev@local` อัตโนมัติ); `True` = ต้องใช้ JWT Bearer หรือ `X-API-Key` |
| `JWT_SECRET` | (ว่าง) | จำเป็นเมื่อ `AUTH_ENABLED=true` (ไม่ตั้งจะ raise `ValueError`); ถ้าปิด auth จะใช้ค่า dev ภายใน — อ่านจาก environment ใน `app/auth.py` |
| `JWT_ALGORITHM` | `HS256` | อัลกอริทึม JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | อายุ access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | อายุ refresh token |
| `API_KEY` | (ว่าง) | มีใน `Settings` แต่ไม่พบการใช้งานในโค้ด |

## 🛠 Technologies

FastAPI 0.118.0 · Uvicorn 0.38.0 · SQLAlchemy 2.0.36 (async) + aiosqlite 0.20.0 · Alembic 1.13.2 · Pydantic 2 + pydantic-settings 2.13.0 · PyJWT 2.10.1 · passlib + bcrypt · websockets · pytest / pytest-asyncio / pytest-cov (เวอร์ชันตาม `requirements.txt`)

## 🐳 Docker

ดูวิธีรันทั้งระบบด้วย `docker compose` ได้ที่ [README หลัก](../README.md#-รันด้วย-docker-compose)

---

ดู [`../LICENSE`](../LICENSE) สำหรับ license ของโปรเจกต์
