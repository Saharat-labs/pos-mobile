# 🛠️ POS-MOBILE — คู่มือนักพัฒนา (Developer Guide)

> เขียนจากการอ่านโค้ดจริงใน repo — **ไม่ได้เดา** ถ้าโค้ดเปลี่ยน ให้ยึดโค้ดเป็นหลัก
> อ้างอิงด้วยชื่อไฟล์ + ชื่อฟังก์ชัน (เลขบรรทัดเปลี่ยนบ่อย จึงใส่เฉพาะที่จำเป็น)

---

## 📋 สารบัญ

1. [ภาพรวมและสถาปัตยกรรม](#1-ภาพรวมและสถาปัตยกรรม)
2. [Frontend internals (`script-pos.js`)](#2-frontend-internals-script-posjs)
3. [Backend internals (`backend/app`)](#3-backend-internals-backendapp)
4. [เพิ่มโมดูลใหม่ฝั่ง Backend ทีละขั้น](#4-เพิ่มโมดูลใหม่ฝั่ง-backend-ทีละขั้น)
5. [เพิ่มหน้า/Modal ใหม่ฝั่ง Frontend ทีละขั้น](#5-เพิ่มหน้าmodal-ใหม่ฝั่ง-frontend-ทีละขั้น)
6. [การรันและทดสอบ + API documentation](#6-การรันและทดสอบ--api-documentation)
7. [Conventions](#7-conventions)
8. [ข้อควรระวัง (Gotchas)](#8-ข้อควรระวัง-gotchas)

---

## 1. ภาพรวมและสถาปัตยกรรม

Repo นี้มี 2 ส่วนที่ **แยกกันอิสระ**:

| ส่วน | ไฟล์ | เก็บข้อมูลที่ |
|------|------|--------------|
| Frontend SPA (PWA) | `index.html`, `script-pos.js`, `style-pos.css`, `sw.js`, `manifest.json`, `icons/` | `localStorage` ของเบราว์เซอร์ |
| Backend API | `backend/` (FastAPI + SQLAlchemy async + SQLite) | ไฟล์ SQLite (`DATABASE_URL`) |

### Frontend เรียก Backend ตรงไหนบ้าง?

**ปัจจุบันมีจุดเดียว** — health check ใน `initOnlineDetection()` (`script-pos.js`):

```js
fetch('/api/v1/sync/health', { method: 'HEAD', cache: 'no-store' })
```

- ใช้แค่เพื่อแสดงแถบสถานะ (`#offline-indicator`) — ไม่ได้ส่ง/ดึงข้อมูลใด ๆ
- ไม่มีโค้ดเรียก `/api/v1/sync`, `/sync/backup`, `/sync/restore` หรือ WebSocket จาก frontend
- Backup/Restore ใน frontend (`exportBackupJSON` / `importBackupJSON`) เป็นไฟล์ JSON ในเครื่องล้วน ๆ
- ร้านหลายร้านใน frontend (store switcher) **ไม่ผูก** กับ `stores` ของ backend

ดังนั้น frontend ทำงานได้ 100% แบบ offline; backend เป็นบริการแยกที่พร้อมให้ client อื่น (หรือการเชื่อมในอนาคต) ใช้

```
┌──────────────────────────── Browser ────────────────────────────┐
│ index.html ── script-pos.js ── style-pos.css                    │
│      │              │                                           │
│      │              ├── localStorage  (qpos_* / qpos_s<id>_*)   │
│      │              └── HEAD /api/v1/sync/health ทุก 30 วิ ─────┼──┐
│      └── sw.js (cache-first static, ข้าม /api/)                  │  │
│  CDN: SheetJS 0.18.5, Chart.js 4.4.0 (cdnjs)                     │  │
└──────────────────────────────────────────────────────────────────┘  │
                                                                      ▼
┌────────────────────── backend/ (FastAPI :8000) ──────────────────────┐
│ app/main.py ─► app/api/* (routers)  ─► app/services/* ─► app/models  │
│                    │  Depends(get_db, get_current_store, require_*)   │
│                    ▼                                                  │
│              app/database.py (AsyncSession) ──► SQLite (aiosqlite)    │
│ WebSocket: /api/v1/ws (app/websocket.py) และ /ws (websocket_manager)  │
└───────────────────────────────────────────────────────────────────────┘
```

Deployment (อ่านจาก `docker-compose.yml` / `nginx.conf`): nginx เสิร์ฟไฟล์ static ที่พอร์ต 8080 และ proxy เฉพาะ `/api/` ไปที่ `backend:8000`

---

## 2. Frontend internals (`script-pos.js`)

ไฟล์เดียว ไม่มี build step ไม่มี module — ทุกอย่างเป็น global และถูกเรียกจาก inline handler ใน `index.html` (`onclick="..."`)

### 2.1 Global state และการโหลดข้อมูล

ส่วน `DATA STORE` บนสุดของไฟล์:

| ชื่อ | หน้าที่ |
|------|---------|
| `storePrefix(id)` | ร้าน 1 → `'qpos_'` (prefix เดิม ไม่ต้อง migrate), ร้านอื่น → `` `qpos_s${id}_` `` |
| `getGlobal(k, d)` / `setGlobal(k, v)` | อ่าน/เขียนค่าที่ **ใช้ร่วมทุกร้าน** ด้วย prefix `qpos_` เสมอ |
| `stores` | รายการร้าน `[{id, name}]` (global key `qpos_stores`) |
| `currentStoreId` | ร้านที่ใช้อยู่ (global key `qpos_currentStore`), ถ้าไม่อยู่ใน `stores` จะกลับเป็น 1 |
| `STORE_PREFIX` | `const` = `storePrefix(currentStoreId)` คำนวณครั้งเดียวตอนโหลดหน้า |
| `DB.get(k, d)` / `DB.set(k, v)` | อ่าน/เขียนข้อมูล **ของร้านปัจจุบัน** (`STORE_PREFIX + k`, JSON) — `DB.set` คืน `false` และ `toast` เตือนครั้งเดียวเมื่อ quota เต็ม |

ตัวแปรข้อมูลหลัก (โหลดด้วย `DB.get` ตอน parse script): `products`, `sales`, `purchases`, `debts`, `expenses`, `settings`, `holdBills`, `hiddenMappingPrefixes`, `billCounter`, `categoryMapping`, `cart`

ตัวแปร UI state: `currentPage`, `posCurrentCat`, `editingProductId`, `editingDebtId`, `currentDebtId`, `creditSaleMode`, `adjChanges`, chart instances (`salesChartInst` ฯลฯ)

> ⚠️ เพราะ `STORE_PREFIX` เป็น `const` การสลับร้าน (`switchStore`) จึง `save()` → `setGlobal('currentStore', id)` → `location.reload()` — อย่าพยายามสลับร้านโดยไม่ reload

### 2.2 `save()`

`save()` เขียนตัวแปรทั้งหมดกลับ `localStorage` ในครั้งเดียว:

```js
const save = ()=>{
  DB.set('products',products); DB.set('sales',sales);
  DB.set('purchases',purchases); DB.set('debts',debts);
  DB.set('expenses',expenses); DB.set('holdBills',holdBills);
  DB.set('billCounter',billCounter); DB.set('settings',settings);
  DB.set('categoryMapping', categoryMapping);
  DB.set('hiddenMappingPrefixes', hiddenMappingPrefixes);
  DB.set('cart', cart);
};
```

แพทเทิร์นคือ: แก้ตัวแปรใน memory → เรียก `save()` → render ใหม่ (ดู `saveExpense()` เป็นตัวอย่างสั้นที่สุด)

### 2.3 Navigation

ทุก "หน้า" อยู่ใน `index.html` เป็น `<div class="page" id="page-<name>">` และแสดงด้วย `.page.active` (`style-pos.css`)

| ฟังก์ชัน | หน้าที่ |
|----------|---------|
| `showPage(name)` | ปิดเมนู, สลับ `.active` จาก `page-<currentPage>` → `page-<name>`, ตั้ง `currentPage`, เรียก `setActiveNav` + `runPageInit` |
| `setActiveNav(name)` | ไฮไลต์ `#nav-<name>` ใน bottom nav, แสดง `#cart-fab` เฉพาะหน้า `pos`, ตั้ง `#topbar-title` จาก map `titles` |
| `runPageInit(name)` | ซ่อน `#topbar-action`/`#pos-bill-no` ก่อน แล้วทำ setup ของแต่ละหน้า (render, ตั้งปุ่ม action บน topbar) |
| `navigateFromMenu(name)` | ใช้จาก sidebar: `closeMenu()` + `showPage()` |
| `showSubPage('stock-adjust')` | เปิด modal ปรับสต๊อก (ไม่ใช่หน้า) |

หน้าที่มีตอนนี้: `pos`, `products`, `purchase`, `debt`, `reports`, `more` — bottom nav (`#bottom-nav`) มี 5 ปุ่ม (ไม่มี `purchase`; เข้าได้จาก sidebar)

ตอนเริ่ม (`DOMContentLoaded` ท้ายไฟล์): `seedDemoData()` → `updateHeaderSubtitle()` → `setActiveNav(currentPage)` → `runPageInit(currentPage)` → `initOnlineDetection()` → `initKeyboardShortcuts()` → นับ alert สต๊อก/วันหมดอายุ

### 2.4 Modal pattern

```html
<div class="modal-overlay" id="modal-xxx" onclick="if(event.target===this)closeModal('modal-xxx')">
  <div class="modal">
    <div class="modal-handle"></div>
    <div class="modal-title"><svg class="icon" aria-hidden="true"><use href="#i-wallet"/></svg> หัวข้อ</div>
    ...
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-xxx')">ยกเลิก</button>
      <button class="btn btn-primary" onclick="saveXxx()">บันทึก</button>
    </div>
  </div>
</div>
```

- `openModal(id)` / `closeModal(id)` แค่เพิ่ม/ลบ class `open` (`.modal-overlay.open { display:flex }`)
- คลิกพื้นหลัง = ปิด (เช็ค `event.target===this`)
- `Esc` เรียก `closeTopModal()` ซึ่งปิด modal `.open` ตัวล่าสุดใน DOM; `modal-scanner` ถูกจัดการพิเศษด้วย `stopScanner()` (ต้องปิดกล้อง)
- ตะกร้า (`#cart-sheet`) ใช้ `openCartSheet()`/`closeCartSheet()` — `openCartSheet()` เรียก `renderCart()` แล้ว `openModal('cart-sheet')` (และ `closeCartSheet()` เรียก `closeModal('cart-sheet')`) จึงเปิด/ปิดด้วย class `open` แบบเดียวกับ modal อื่น
- แพทเทิร์นเปิด modal: ฟังก์ชัน `openXxx()` reset ค่าในฟอร์มก่อนแล้วค่อย `openModal` (ดู `openExpense()`)

### 2.5 ไอคอน: SVG sprite + `icon(name)`

- Sprite อยู่ต้น `<body>` ใน `index.html` ใต้คอมเมนต์ `Lucide v0.460.0 (ISC License)` — แต่ละไอคอนเป็น `<symbol id="i-<name>" viewBox="0 0 24 24">`
- ใน HTML: `<svg class="icon" aria-hidden="true"><use href="#i-camera"/></svg>`
- ใน JS: `icon('camera')` คืน string เดียวกัน (ใช้ใน template literal / `innerHTML`)
- สไตล์ (stroke/size) มาจาก `.icon` ใน `style-pos.css` ดังนั้น `<symbol>` ใส่แค่ path

**เพิ่มไอคอนใหม่:**
1. เปิดไอคอนจาก Lucide **v0.460.0** (ให้ตรงเวอร์ชันเดิม) แล้วคัดลอกเฉพาะ element ข้างใน `<svg>` (`<path>`, `<circle>`, …)
2. เพิ่ม `<symbol id="i-<lucide-name>" viewBox="0 0 24 24">…</symbol>` ใน sprite — เรียงตามตัวอักษรแบบที่มีอยู่
3. ใช้ `icon('<lucide-name>')` หรือ `<use href="#i-<lucide-name>"/>`
4. bump `CACHE_NAME` ใน `sw.js` (ดู 2.10)

> ถ้าอ้างชื่อที่ไม่มีใน sprite จะไม่ error — แค่แสดงช่องว่าง ตรวจด้วยตาทุกครั้ง

### 2.6 XSS helpers: `esc` / `escJs`

ข้อมูลที่ผู้ใช้กรอก (ชื่อสินค้า ลูกค้า ร้าน ฯลฯ) ถูกแทรกลง `innerHTML` บ่อย ต้อง escape เสมอ:

| ใช้เมื่อ | ฟังก์ชัน | ตัวอย่าง |
|----------|----------|----------|
| แทรกเป็นข้อความ/attribute ใน HTML | `esc(s)` | `` `<div>${esc(p.name)}</div>` `` |
| แทรกเป็น **JS string** ใน inline handler | `escJs(s)` | `` `onclick="setCatFilter(${escJs(cat)})"` `` |

`escJs` = `esc(JSON.stringify(String(s)))` — ได้ string พร้อมเครื่องหมายคำพูดแล้ว **ไม่ต้องครอบ `'...'` เพิ่ม** เหตุผล (คอมเมนต์ในโค้ด): เบราว์เซอร์ถอด `&#39;` กลับเป็น `'` ก่อน parse JS ดังนั้น `esc()` อย่างเดียวไม่พอใน handler

ค่าตัวเลข/ID ที่ระบบสร้างเอง (เช่น `s.id` ใน `renderStores`) ใส่ตรงได้ แต่ถ้าไม่แน่ใจให้ใช้ `escJs`

### 2.7 `toast(msg, type)`

```js
toast('บันทึกแล้ว');                      // success (default)
toast('กรอกรายการและจำนวนเงิน','error');   // success | error | warning | info
```

ใส่ไอคอนจาก `TOAST_ICONS` และต่อข้อความด้วย `append` (เป็น text node — ไม่ต้อง escape) หายไปเองใน 2.8 วิ ถ้าไม่มี `#toast-container` จะ `console.warn`

### 2.8 Barcode scanner

ใช้ `BarcodeDetector` API ของเบราว์เซอร์ (ไม่มี library) — ถ้าไม่รองรับจะ `toast` แนะนำให้กรอกเอง

| ฟังก์ชัน | หน้าที่ |
|----------|---------|
| `openLiveScanner(onCode)` | เปิดกล้องหลัง (`facingMode: 'environment'`) ใน `#modal-scanner`, loop `requestAnimationFrame` ตรวจทุก ≥150ms, เจอโค้ดแล้ว `vibrate` → `stopScanner()` → `onCode(code)` |
| `stopScanner()` | หยุด track ทั้งหมด + ปิด modal (state อยู่ใน `_scan`) |
| `toggleTorch()` / `setScannerZoom(v)` | แสดงเฉพาะเมื่อ `track.getCapabilities()` มี `torch`/`zoom` |
| `scanBarcode()` / `scanBarcodeToProductForm()` | ตัวเรียกใช้: ใส่ผลลง `#pos-search-input` + `addFirstResult()` / ลง `#pm-barcode` |
| `scanBarcodeFromPhoto(e)` / `scanBarcodeFromPhotoToProductForm(e)` | fallback อ่านจากรูป (`<input type="file" capture>`) |

ใช้สแกนในที่ใหม่: `openLiveScanner(code => { /* ใช้ code */ })`

### 2.9 Keyboard shortcuts & offline indicator

`initKeyboardShortcuts()` — listener เดียวบน `document`:

| ปุ่ม | Action | ทำงานขณะพิมพ์ในช่อง input? |
|------|--------|---------------------------|
| `F2`, `/` | `focusPosSearch()` | F2 ได้, `/` ไม่ได้ |
| `F4` | `openCartSheet()` | ได้ |
| `F8` | `openPayment()` | ได้ |
| `F9` | `holdCurrentCart()` | ได้ |
| `Esc` | `closeTopModal()` | ได้ |
| `?` | `openModal('modal-shortcuts')` | ไม่ได้ |

ข้ามทุกปุ่มเมื่อกด Ctrl/Meta/Alt — เพิ่ม shortcut ใหม่ใน object `actions` และ **อัปเดตตารางใน `#modal-shortcuts`** ด้วย

`initOnlineDetection()` — สถานะ `serverReachable`: `true` / `false` / `null` (ไม่รู้)
- `navigator.onLine === false` → แถบแดง "ออฟไลน์"
- health check ได้สถานะอื่นที่ไม่ใช่ ok และไม่ใช่ 404/405/501, หรือ fetch ล้มหลังเคยรู้สถานะ → แถบเหลือง (`.warn`) "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้"
- `file://` หรือ static host ที่ตอบ 404/405/501 → `null` ไม่แจ้งเตือน
- ตรวจซ้ำทุก 30 วิ + event `online`/`offline`; เพิ่ม class `body.offline-active`

### 2.10 Service worker (`sw.js`)

- `CACHE_NAME = 'pos-mobile-v3'` (ค่าปัจจุบัน), precache `ASSETS` = `./`, `index.html`, `script-pos.js`, `style-pos.css`, `manifest.json`
- `install` precache ด้วย `cache.addAll(ASSETS.map(u => new Request(u, { cache: 'reload' })))` — `cache: 'reload'` ข้าม HTTP cache ของเบราว์เซอร์ จึงได้ไฟล์ล่าสุดจากเซิร์ฟเวอร์ทุกตัว (ไม่มี `index.html` ใหม่คู่กับ `script-pos.js` เก่า) แล้ว `skipWaiting()`
- ฝั่งเซิร์ฟเวอร์ `nginx.conf` ส่ง `location = /sw.js` แบบ `no-cache, no-store, must-revalidate` และ `.js`/`.css` แบบ `Cache-Control: no-cache` (revalidate ทุกครั้ง) — รูป/ฟอนต์ยัง cache 1 ปี (ดู [DEPLOYMENT.md §8](DEPLOYMENT.md#8-ออกเวอร์ชันใหม่ของ-frontend-service-worker))
- `activate` ลบ cache ทุกตัวที่ชื่อไม่ตรง `CACHE_NAME`
- `fetch`: path ขึ้นต้น `/api/` → ไม่แตะ (ไป network); อย่างอื่น **cache-first** และ cache GET ที่ ok เพิ่ม (รวมไฟล์ CDN); navigation ที่ล้มจะ fallback เป็น `index.html`
- ลงทะเบียนใน `<head>` ของ `index.html` (`navigator.serviceWorker.register('./sw.js')`)

> ✅ **กฎ:** แก้ `index.html` / `script-pos.js` / `style-pos.css` / `manifest.json` เมื่อไหร่ ให้ bump `CACHE_NAME` (เช่น `v3` → `v4`) ใน commit เดียวกัน — `cache: 'reload'` และ header ของ nginx แค่รับประกันว่า cache ชุดใหม่ได้ไฟล์ล่าสุด แต่ `fetch` ยังเป็น cache-first ถ้าไม่ bump ผู้ใช้ที่เคยเปิดแอปจะได้ไฟล์เก่าจาก cache ตลอดไป (ดู commit `de10195` เป็นตัวอย่าง)
> ไฟล์ใหม่ที่ต้องใช้ offline ตั้งแต่ครั้งแรก ให้เพิ่มใน `ASSETS` ด้วย

### 2.11 CDN libraries

โหลดด้วย `<script defer>` จาก cdnjs พร้อม `integrity` (SRI) ใน `<head>`:

| Library | เวอร์ชัน | Global | ใช้ที่ |
|---------|----------|--------|--------|
| SheetJS | 0.18.5 | `XLSX` | `exportXLSX`, `exportXLSXMulti`, `importExcel`, `importMasterUpdate` |
| Chart.js | 4.4.0 | `Chart` | รายงาน (`renderSalesReport`, `renderCompareReport`, …) |

เปลี่ยนเวอร์ชันต้องอัปเดต `integrity` hash ด้วย

`MASTER_PRODUCTS` (รายการสินค้ากลาง) ถูกอ้างถึงแบบ optional (`typeof MASTER_PRODUCTS === 'undefined'`) — ถ้าไม่มี ปุ่ม `#btn-master-search` จะถูกซ่อน ปัจจุบัน `index.html` ไม่ได้โหลดไฟล์ `master-products.js`

---

## 3. Backend internals (`backend/app`)

### 3.1 โครงสร้างเลเยอร์

```
backend/
├── run.py                 # โหลด .env → os.environ, สร้าง DATA_DIR, uvicorn app.main:app
├── alembic/ + alembic.ini # migrations (001 → 002 → 003)
├── app/
│   ├── main.py            # FastAPI app, CORS, lifespan(init_db/close_db), include routers, / และ /health
│   ├── config.py          # Settings (pydantic-settings) อ่าน .env
│   ├── database.py        # engine, AsyncSessionLocal, get_db, init_db (create_all), close_db
│   ├── base.py            # DeclarativeBase
│   ├── models/__init__.py # SQLAlchemy models ทั้งหมด (ไฟล์เดียว)
│   ├── schemas.py         # Pydantic schemas ทั้งหมด (ไฟล์เดียว)
│   ├── auth.py            # JWT, API key, password, get_current_user/store, require_*
│   ├── websocket.py / websocket_manager.py  # WS managers (2 ชุด — ดู 3.7)
│   ├── api/               # routers (HTTP layer) + validation.py
│   └── services/          # business logic: class XxxService(db)
└── tests/                 # pytest + conftest.py
```

กติกาการแบ่งงาน (ดู `app/api/expenses.py` + `app/services/expense_service.py`):

- **api/** — parse/validate input, ดึง dependency (`get_db`, `get_current_store`), แปลง `None` → `HTTPException(404)`, กำหนด `response_model`/`status_code`
- **services/** — query/commit ด้วย `AsyncSession`, รับ `store_id: int = 1`, คืน ORM object หรือ `(items, total)`; ไม่รู้จัก HTTP (ยกเว้นบาง service ที่ raise ค่า error ของตัวเอง)
- **models/** — ตาราง + relationship + index

### 3.2 `app/config.py`

`Settings(BaseSettings)` — `env_file=".env"`, `case_sensitive=True`

| Key | Default | หมายเหตุ |
|-----|---------|---------|
| `APP_NAME` / `APP_VERSION` | `POS-MOBILE API` / `1.0.0` | |
| `DEBUG` | `True` | ใช้เป็น `reload=` ของ uvicorn ใน `run.py` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./pos_mobile.db` | relative กับ working dir |
| `DATABASE_ECHO` | `False` | log SQL |
| `CORS_ORIGINS` | localhost:8000, 127.0.0.1:8000, `file://`, `null` | |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | |
| `AUTH_ENABLED` | `False` | dev mode (ดู 3.5) |
| `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | `""`, `HS256`, `15`, `7` | ⚠️ `auth.py` อ่านค่าเหล่านี้จาก `os.environ` ไม่ใช่จาก `settings` |
| `API_KEY` | `""` | ไม่พบการใช้งานในโค้ด |
| `DATA_DIR` | `~/pos-mobile-data` | `run.py` สร้างโฟลเดอร์ให้ |

### 3.3 `app/database.py`

- `engine = create_async_engine(settings.DATABASE_URL, ...)` (+ `check_same_thread=False` สำหรับ SQLite)
- `get_db()` — dependency ที่ yield `AsyncSession` (tests override ตัวนี้)
- `init_db()` — ถูกเรียกใน `lifespan` ของ `main.py` ทุกครั้งที่ start: `Base.metadata.create_all` และสร้างร้านเริ่มต้น `id=1` / `STORE001` (`ร้านค้าเริ่มต้น`) เมื่อตาราง `stores` ยังว่าง (ตั้งแต่ commit `7ab1281`) — แต่ **ไม่** บันทึก `alembic_version` ถ้า DB ถูกสร้างด้วย `init_db()` ต้อง `alembic stamp head` ก่อนรัน migration ถัดไป — เพราะ user ทุกคน (รวม dev user) ผูกกับ `store_id=1`

### 3.4 `app/schemas.py`

แพทเทิร์นต่อโมดูล: `XxxBase` → `XxxCreate(XxxBase)` → `XxxUpdate(BaseModel)` (ทุก field `Optional`) → `XxxResponse(XxxBase)` (+ `id`, timestamps) → `XxxListResponse` (`items, total, page, page_size`)

- ทุก class มี `class Config: from_attributes = True`
- `store_id: Optional[int] = None` ใน Base — ค่าจริงมาจาก `get_current_store` ไม่ใช่จาก body
- เงินใช้ `Decimal` + `Field(gt=0)`; enum ใช้ `Field(pattern="^(a|b)$")`
- Update ใช้ `data.model_dump(exclude_unset=True)` ใน service

### 3.5 Auth (`app/auth.py`, routes ใน `app/api/auth.py`)

| ส่วน | รายละเอียด |
|------|-----------|
| Password | `passlib` bcrypt — `hash_password`, `verify_password` |
| JWT | PyJWT, `create_access_token` (`type: access`), `create_refresh_token` (`type: refresh` + `jti`); refresh token เก็บเป็น SHA-256 ใน `RefreshToken` (`store_refresh_token`, `validate_refresh_token`, `revoke_*`) |
| API Key | header `X-API-Key`, รูปแบบ `pos_<urlsafe>`, เก็บ bcrypt hash + `key_prefix`; `validate_api_key` ไล่ verify ทุก key ที่ active |
| `get_current_user` | ลอง Bearer JWT ก่อน แล้ว API key; ไม่ผ่าน → 401, user ปิด → 403 |
| `get_current_store` | `Store` ของ `current_user.store_id`; ไม่มี → 404, inactive → 403 |
| Roles | `require_roles(*roles)`; `require_admin` = admin, `require_manager` = admin+manager, `require_staff` = ทุก role; `is_superuser` ผ่านเสมอ |
| Scopes | `require_scopes(...)` ตรวจ scope ของ API key |

**Dev mode (`AUTH_ENABLED=False`, ค่า default):** `get_current_user` คืน user แรกในตาราง หรือสร้าง `dev@local` / `devpass` (role `admin`, superuser, `store_id=1`) ให้อัตโนมัติ — จึงเรียก API ได้โดยไม่ต้อง login และ tests ใช้ได้เลย
เมื่อ `AUTH_ENABLED=true` ต้องตั้ง `JWT_SECRET` ใน environment ไม่งั้น import `app.auth` จะ `ValueError`

ปัจจุบัน `require_admin` ใช้ใน `/auth/users*` และ `/stores` (POST/PUT/DELETE); router ข้อมูลอื่นพึ่ง `get_current_store` (ซึ่งต้อง auth เมื่อเปิด) แต่ไม่ได้จำกัด role

### 3.6 Multi-store

- ทุก model ข้อมูลร้านมี `store_id` FK → `stores.id` (`ondelete="CASCADE"`, `index=True`): `Product`, `Sale`, `Purchase`, `Debt`, `Expense`, `StockMovement`, `HoldBill`, `Setting`, `User` — ยกเว้น `CategoryMapping` (global)
- Router ใส่ `current_store: Store = Depends(get_current_store)` แล้วส่ง `current_store.id` เข้า service
- Service **ต้อง** filter `Model.store_id == store_id` ทุก query รวมถึง `get()` ที่ใช้ใน update/delete (กันข้ามร้าน)
- Migration `003_add_multi_store.py` สร้างตาราง `stores` และ INSERT ร้านเริ่มต้น (`STORE001`, `is_default=1`)

### 3.7 WebSocket

มี **2 ชุดแยกกัน** ที่ใช้ manager คนละตัว:

| Endpoint | ไฟล์ | Manager | ใครส่ง event |
|----------|------|---------|-------------|
| `ws://host:8000/api/v1/ws?room=default` | `app/api/ws.py` | `app/websocket.py` (`manager`, `notify_data_change(entity, action, detail)`) | ไม่มี service ไหนเรียก `notify_data_change` (มีแค่ใน test) |
| `ws://host:8000/ws?client_id=<id>` | `app/api/websocket.py` (include ตรงใน `main.py`) | `app/websocket_manager.py` (`manager`, `broadcast_event`, `send_event_to_client`) | `ProductService` (`product_created`, `stock_updated`), `SaleService` (`sale_created`) |
| `GET /ws/status` | `app/api/websocket.py` | — | จำนวน client + `available_events` |

ส่ง event จาก service ใหม่ (ชุดที่ใช้งานจริง):

```python
from app.websocket_manager import broadcast_event
await broadcast_event("expense_created", {"id": expense.id, "amount": float(expense.amount)})
```

ชื่อ event ควรอยู่ใน `ConnectionManager.event_types` (client subscribe ได้เฉพาะชื่อในชุดนี้; client ที่ไม่ subscribe อะไรเลยจะได้ทุก event)

### 3.8 Validation helpers (`app/api/validation.py`)

| ชื่อ | ใช้ทำอะไร |
|------|-----------|
| `MAX_PAGE_SIZE = 100`, `DEFAULT_PAGE_SIZE = 50`, `MAX_BULK_ITEMS = 1000` | ค่าคงที่ |
| `validate_page_params(page, page_size)` | คืน tuple (เรียกตรงหลังใช้ `Query(ge=1, le=MAX_PAGE_SIZE)` ใน signature) |
| `validate_date_range(start, end)` | 400 ถ้า `start > end` |
| `validate_payment_method`, `validate_*_status`, `validate_stock_movement_type`, `validate_positive_*` | 400 พร้อมข้อความ |
| `get_pagination`, `get_date_range` | dependency แบบ Pydantic model (`PaginationParams`, `DateRangeParams`) |

แพทเทิร์นที่ list endpoint ใช้ (กำหนด bound ใน `Query` เพื่อให้ FastAPI ตอบ 422 เอง):

```python
page: int = Query(1, ge=1),
page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
```

### 3.9 Alembic (`backend/alembic`)

- `env.py` ใช้ `app.models.Base.metadata`, รันแบบ async, `render_as_batch=True` บน SQLite (จำเป็นสำหรับ ALTER ที่ SQLite ไม่รองรับ)
- `DATABASE_URL` ใน environment override `sqlalchemy.url` ของ `alembic.ini` (`sqlite+aiosqlite:///./pos_mobile.db`)
- Revisions ตั้งชื่อเป็นเลข: `001_initial_schema.py` (`revision='001'`) → `002_add_auth_tables.py` → `003_add_multi_store.py` (head)
- Docker (`backend/Dockerfile`): `alembic upgrade head && exec python run.py`

```bash
cd backend
alembic upgrade head          # สร้าง/อัปเดต schema + ร้านเริ่มต้น
alembic current               # ดู revision ปัจจุบัน
alembic downgrade -1          # ย้อน 1 ขั้น
```

---

## 4. เพิ่มโมดูลใหม่ฝั่ง Backend ทีละขั้น

ตัวอย่าง: โมดูล **Suppliers** (ผู้ขาย) ทำตามแบบ `expenses` ซึ่งเป็นโมดูล CRUD ที่ง่ายที่สุด

### ขั้นที่ 1 — Model (`app/models/__init__.py`)

```python
class Supplier(Base):
    """Supplier model."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store: Mapped["Store"] = relationship("Store", back_populates="suppliers")
```

และเพิ่มใน `Store`:

```python
suppliers: Mapped[list["Supplier"]] = relationship("Supplier", back_populates="store")
```

### ขั้นที่ 2 — Alembic migration

สร้างไฟล์ `alembic/versions/004_add_suppliers.py` (ตั้งเลขต่อจาก head; ใช้ `alembic revision --autogenerate -m "add suppliers"` เป็นจุดเริ่มก็ได้ แต่ให้แก้ `revision`/ชื่อไฟล์ให้เป็นเลขตามแบบเดิมและตรวจทุกบรรทัด):

```python
"""Add suppliers

Revision ID: 004
Revises: 003
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_suppliers_store_id'), 'suppliers', ['store_id'])
    op.create_index(op.f('ix_suppliers_name'), 'suppliers', ['name'])


def downgrade() -> None:
    op.drop_index(op.f('ix_suppliers_name'), table_name='suppliers')
    op.drop_index(op.f('ix_suppliers_store_id'), table_name='suppliers')
    op.drop_table('suppliers')
```

ทดสอบ: `alembic upgrade head` แล้ว `alembic downgrade -1` แล้ว `upgrade head` อีกรอบบน DB ทดลอง (ตั้ง `DATABASE_URL` ชี้ไฟล์ชั่วคราว)

> ถ้าต้อง ALTER ตารางเดิมบน SQLite ให้ใช้ `with op.batch_alter_table('x') as batch:` (ดูคอมเมนต์ใน `003_add_multi_store.py`)

### ขั้นที่ 3 — Schemas (`app/schemas.py`)

```python
# ==================== Supplier Schemas ====================

class SupplierBase(BaseModel):
    store_id: Optional[int] = None
    name: str = Field(..., max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    items: List[SupplierResponse]
    total: int
    page: int
    page_size: int
```

### ขั้นที่ 4 — Service (`app/services/supplier_service.py`)

```python
"""Supplier service - business logic for suppliers."""

from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Supplier
from app.schemas import SupplierCreate, SupplierUpdate


class SupplierService:
    """Supplier business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: SupplierCreate, store_id: int = 1) -> Supplier:
        supplier = Supplier(store_id=store_id, name=data.name, phone=data.phone, notes=data.notes)
        self.db.add(supplier)
        await self.db.commit()
        await self.db.refresh(supplier)
        return supplier

    async def get(self, supplier_id: int, store_id: int = 1) -> Optional[Supplier]:
        result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_id, Supplier.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, page_size: int = 50, store_id: int = 1) -> tuple[List[Supplier], int]:
        query = select(Supplier).where(Supplier.store_id == store_id)
        total = await self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        query = query.order_by(Supplier.name).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def update(self, supplier_id: int, data: SupplierUpdate, store_id: int = 1) -> Optional[Supplier]:
        supplier = await self.get(supplier_id, store_id)
        if not supplier:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(supplier, field, value)
        await self.db.commit()
        await self.db.refresh(supplier)
        return supplier

    async def delete(self, supplier_id: int, store_id: int = 1) -> bool:
        supplier = await self.get(supplier_id, store_id)
        if not supplier:
            return False
        await self.db.delete(supplier)
        await self.db.commit()
        return True
```

### ขั้นที่ 5 — Router (`app/api/suppliers.py`)

```python
"""Suppliers API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.supplier_service import SupplierService
from app.schemas import SupplierCreate, SupplierUpdate, SupplierResponse, SupplierListResponse
from app.api.validation import validate_page_params, MAX_PAGE_SIZE
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


def get_service(db: AsyncSession = Depends(get_db)) -> SupplierService:
    return SupplierService(db)


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    service: SupplierService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Create new supplier."""
    return await service.create(data, current_store.id)


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    service: SupplierService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """List suppliers."""
    page, page_size = validate_page_params(page, page_size)
    items, total = await service.list(page, page_size, current_store.id)
    return SupplierListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    service: SupplierService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get supplier by ID."""
    supplier = await service.get(supplier_id, current_store.id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    service: SupplierService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Update supplier."""
    supplier = await service.update(supplier_id, data, current_store.id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: int,
    service: SupplierService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Delete supplier."""
    if not await service.delete(supplier_id, current_store.id):
        raise HTTPException(status_code=404, detail="Supplier not found")
```

> **ลำดับ route สำคัญ:** path คงที่ (`/categories`, `/summary/...`) ต้องประกาศ **ก่อน** `/{id}` — ดู `expenses.py`, `products.py` และกรณี `settings.mappings_router` ที่ต้อง register ก่อน `settings.router` ใน `app/api/__init__.py`
> ถ้าต้องการจำกัด role ให้เพิ่ม `current_user: User = Depends(require_manager)` (ดู `app/api/stores.py`)

### ขั้นที่ 6 — Register router

Router ข้อมูลทั้งหมด register ผ่าน `api_router` (prefix `/api/v1`) ใน **`app/api/__init__.py`** ซึ่ง `app/main.py` include อีกที — ไม่ต้องแก้ `main.py`:

```python
from app.api import auth, products, ..., stores, suppliers
...
api_router.include_router(suppliers.router)
```

`main.py` include ตรงเฉพาะ `ws.router` จาก `app/api/websocket.py` (ไม่มี `/api/v1`)

### ขั้นที่ 7 — Tests (`backend/tests/test_api_suppliers.py`)

Fixture `client` ใน `tests/conftest.py`: SQLite in-memory ใหม่ทุก test (`test_engine`), ขึ้นกับ fixture `test_session` ซึ่งเป็นตัวสร้าง `Store(id=1)` ให้, override `get_db`, ใช้ `httpx.AsyncClient` + `ASGITransport` (AUTH_ENABLED=False จึงได้ dev user อัตโนมัติ)

```python
"""Tests for Suppliers API."""
import pytest
from httpx import AsyncClient


class TestSuppliersAPI:
    """Test Suppliers API endpoints."""

    @pytest.mark.asyncio
    async def test_create_and_get_supplier(self, client: AsyncClient):
        resp = await client.post("/api/v1/suppliers", json={"name": "ซีพี ออลล์", "phone": "021234567"})
        assert resp.status_code == 201
        sid = resp.json()["id"]

        resp = await client.get(f"/api/v1/suppliers/{sid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "ซีพี ออลล์"

    @pytest.mark.asyncio
    async def test_page_size_bound(self, client: AsyncClient):
        resp = await client.get("/api/v1/suppliers", params={"page_size": 101})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_missing_returns_404(self, client: AsyncClient):
        resp = await client.delete("/api/v1/suppliers/999")
        assert resp.status_code == 404
```

Service test ใช้ fixture `test_session` ตรง ๆ (ดู `tests/test_expense_service.py`) ถ้าต้องทดสอบข้ามร้าน ให้ `test_session.add(Store(id=2, ...))` แล้วเรียก service ด้วย `store_id=2`

Checklist: model ✔ migration ✔ schemas ✔ service ✔ router ✔ register ✔ tests ✔ → `python3 -m pytest -q` เขียวทั้งหมด

---

## 5. เพิ่มหน้า/Modal ใหม่ฝั่ง Frontend ทีละขั้น

ตัวอย่าง: หน้า **ผู้ขาย** (`suppliers`) ที่เก็บข้อมูลใน `localStorage`

### ขั้นที่ 1 — HTML ของหน้า (`index.html` ใน `#page-container`)

```html
<div class="page" id="page-suppliers">
  <div class="page-body">
    <input type="text" id="sup-search" placeholder="ค้นหา..." oninput="renderSuppliers()">
    <div id="sup-list"></div>
  </div>
</div>
```

### ขั้นที่ 2 — ทางเข้า (nav)

- Sidebar (`<aside id="sidebar">`): `<button class="sidebar-link" onclick="navigateFromMenu('suppliers')"><svg class="icon" aria-hidden="true"><use href="#i-truck"/></svg> ผู้ขาย</button>`
- ถ้าจะใส่ bottom nav ให้ใช้ `id="nav-suppliers"` เพื่อให้ `setActiveNav` ไฮไลต์ได้ (ตอนนี้มี 5 ปุ่ม จอมือถือแคบ — พิจารณาให้ดี)
- เพิ่ม title ใน map `titles` ของ `setActiveNav()`: `suppliers: icon('truck')+' ผู้ขาย'`

### ขั้นที่ 3 — `runPageInit`

```js
if (name === 'suppliers') {
  if (topAction) {
    topAction.style.display = 'inline-flex';
    topAction.innerHTML = icon('plus') + ' เพิ่มผู้ขาย';
    topAction.onclick = ()=>openSupplierModal();
  }
  renderSuppliers();
}
```

### ขั้นที่ 4 — ข้อมูลใน `DB`

ส่วน `DATA STORE` บนสุด:

```js
let suppliers = DB.get('suppliers', []);
```

เพิ่มใน `save()`:

```js
DB.set('suppliers', suppliers);
```

### ขั้นที่ 5 — Modal + logic

HTML ตามแพทเทิร์นใน 2.4 (`id="modal-supplier"`) แล้ว JS:

```js
// ═══════════════════════════════════════════════
// SUPPLIERS
// ═══════════════════════════════════════════════
function openSupplierModal(){
  document.getElementById('sup-name').value='';
  document.getElementById('sup-phone').value='';
  openModal('modal-supplier');
}
function saveSupplier(){
  const name=document.getElementById('sup-name').value.trim();
  if(!name){toast('กรอกชื่อผู้ขาย','error');return;}
  suppliers.push({id:uid(),name,phone:document.getElementById('sup-phone').value.trim(),createdAt:Date.now()});
  save(); closeModal('modal-supplier'); renderSuppliers(); toast('บันทึกผู้ขายแล้ว');
}
function deleteSupplier(id){
  if(!confirm('ลบผู้ขายนี้?')) return;
  suppliers=suppliers.filter(s=>s.id!==id); save(); renderSuppliers();
}
function renderSuppliers(){
  const q=(document.getElementById('sup-search').value||'').toLowerCase();
  const list=suppliers.filter(s=>s.name.toLowerCase().includes(q));
  document.getElementById('sup-list').innerHTML=list.map(s=>`
    <div class="card">
      <div>${esc(s.name)} <span class="text-muted">${esc(s.phone)}</span></div>
      <button class="btn-icon" onclick="deleteSupplier(${escJs(s.id)})">${icon('trash-2')}</button>
    </div>`).join('') || '<p class="text-muted">ยังไม่มีข้อมูล</p>';
}
```

- ID ใช้ `uid()`, วันที่ใช้ `today()`/`ymd()`, เงินแสดงด้วย `fmt()`
- ทุกค่าที่ผู้ใช้กรอก → `esc()`; ทุกค่าใน inline handler → `escJs()`

### ขั้นที่ 6 — Backup / Restore / ล้างข้อมูล

ถ้าข้อมูลต้องอยู่รอดการสำรอง ต้องแก้ **3 จุด**:

```js
// exportBackupJSON()
const backup={products,sales,...,categoryMapping,suppliers,exportedAt:...,version:1};
// importBackupJSON()
suppliers=data.suppliers||[];
// clearAllData()
...;suppliers=[];
```

(ถ้ามีหน้าที่เปิดอยู่ให้ render ใหม่หลัง restore ด้วย)

### ขั้นที่ 7 — ปิดท้าย

- ไอคอนใหม่? เพิ่ม `<symbol>` (2.5)
- เพิ่ม shortcut? อัปเดต `actions` + `#modal-shortcuts`
- **bump `CACHE_NAME` ใน `sw.js`**
- ทดสอบใน 2 ร้าน (สลับร้านผ่าน `#modal-stores`) ว่าข้อมูลแยกกันจริง

---

## 6. การรันและทดสอบ + API documentation

### 6.1 Backend

```bash
cd backend
pip install -r requirements.txt     # CI ใช้ Python 3.12
alembic upgrade head                 # ⚠️ ทำก่อน start ครั้งแรก (ดู Gotchas)
python3 run.py                       # http://0.0.0.0:8000, reload ตาม DEBUG
```

ทดสอบ:

```bash
cd backend
python3 -m pytest -q                 # ล่าสุด: 176 passed
python3 -m pytest tests/test_api_expenses.py -q
python3 -m pytest -q --cov=app       # แบบ CI (.github/workflows/ci-cd.yml)
```

### 6.2 API documentation (Swagger)

| URL | เนื้อหา |
|-----|---------|
| `http://localhost:8000/docs` | Swagger UI (ลองยิง API ได้) |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | OpenAPI schema (ใช้ generate client ได้) |
| `GET /` | ข้อมูลแอป + ลิงก์ docs |
| `GET /health` | health ของแอป |

Routers (prefix รวม `/api/v1` จาก `app/api/__init__.py`):

| Prefix | ไฟล์ | Tag | จุดเด่น |
|--------|------|-----|---------|
| `/api/v1/auth` | `api/auth.py` | Auth | register, login, refresh, logout(-all), change-password, api-keys, me, users (admin), health |
| `/api/v1/ws` (WebSocket) | `api/ws.py` | WebSocket | `?room=`; ส่ง `ping` ได้ `pong` |
| `/api/v1/products` | `api/products.py` | Products | CRUD, categories, low-stock, expiring, code/{code}, barcode/{barcode}, bulk, /{id}/stock |
| `/api/v1/sales` | `api/sales.py` | Sales | create/list/get/update, bill/{bill_no}, summary/daily, summary/top-products |
| `/api/v1/purchases` | `api/purchases.py` | Purchases | create/list/get/update, po/{po_no}, /{id}/receive |
| `/api/v1/debts` | `api/debts.py` | Debts | create/list/get/update, summary, customer/{name}, /{id}/payments |
| `/api/v1/expenses` | `api/expenses.py` | Expenses | CRUD, categories, summary/monthly, summary/yearly |
| `/api/v1/stock-movements` | `api/stock_movements.py` | Stock Movements | create, list, product/{id} |
| `/api/v1/hold-bills` | `api/hold_bills.py` | Hold Bills | create/list/get/delete, bill/{bill_no} |
| `/api/v1/settings/mappings` | `api/settings.py` (`mappings_router`) | Category Mappings | CRUD + bulk (register ก่อน `/settings/{key}`) |
| `/api/v1/settings` | `api/settings.py` (`router`) | Settings | list/create, get/put/delete `/{key}` |
| `/api/v1/sync` | `api/sync.py` | Sync/Backup | `POST ""` sync, `GET /backup`, `POST /restore`, `GET/HEAD /health` |
| `/api/v1/stores` | `api/stores.py` | Stores | CRUD (เขียน = admin), default, /{id}/stats |
| `/ws` (WebSocket) + `GET /ws/status` | `api/websocket.py` | WebSocket | include ตรงใน `main.py`, ต้องมี `?client_id=` |

### 6.3 Frontend

ไม่มี build — เสิร์ฟ root ของ repo ด้วย static server ใดก็ได้:

```bash
cd /path/to/pos-mobile
python3 -m http.server 8080          # http://localhost:8080
```

- ต้องเปิดผ่าน `http://localhost` (ไม่ใช่ `file://`) เพื่อให้ service worker และกล้อง (`getUserMedia`) ทำงาน — กล้องบนมือถือต้องเป็น HTTPS หรือ localhost
- Static server ธรรมดาจะตอบ 404 ที่ `/api/v1/sync/health` → indicator ถือว่า "ไม่รู้สถานะ" ไม่แจ้งเตือน
- ทดสอบ frontend + backend พร้อมกัน: `docker compose up` (nginx 8080 → proxy `/api/` ไป backend)
- ระหว่างพัฒนา: DevTools → Application → Service Workers → "Update on reload" หรือ bump `CACHE_NAME` เพื่อไม่ติด cache
- ล้างข้อมูลทดสอบ: DevTools → Application → Local Storage → ลบ key `qpos_*`

### 6.4 Browser E2E

ชุดทดสอบ E2E อยู่ที่ `tests/e2e/frontend.spec.js` — เปิดแอปใน Chromium จริงผ่าน Playwright แล้วกดใช้งานแบบผู้ใช้ (ทุกหน้า, modal, การขาย/ขายเชื่อ/รับชำระหนี้, พักบิล, สั่งซื้อ, Excel, สำรอง/กู้คืน JSON, หลายร้าน, ปุ่มลัด, สแกนบาร์โค้ดด้วยกล้องจำลอง, แบนเนอร์ออฟไลน์, `file://`) รายละเอียดอยู่ใน [tests/e2e/README.md](../tests/e2e/README.md)

```bash
tests/e2e/run.sh        # ต้องมี node + playwright (Chromium), npm, python3 — ไม่ต้อง npm install ในโปรเจกต์
```

`run.sh` เปิด `python3 -m http.server` ที่ root ของ repo (ปิดด้วย PID ตอนจบ) แล้วรัน `node tests/e2e/frontend.spec.js` — exit code 0 เมื่อผ่านทั้งหมด

| ตัวแปร | ความหมาย | ค่าเริ่มต้น |
|---|---|---|
| `E2E_PORT` | พอร์ต static server (ถ้าถูกใช้อยู่ สคริปต์ exit 2) | `8801` |
| `E2E_CACHE_DIR` | แคช SheetJS/Chart.js ที่ดึงด้วย `npm pack` + ไฟล์ชั่วคราว | `$TMPDIR/pos-e2e-cache` |
| `E2E_ONLY` | รันเฉพาะเทสต์ที่ชื่อมีข้อความนี้ | ทั้งหมด |
| `E2E_HEADED=1` / `E2E_DEBUG=1` | เปิดหน้าต่างเบราว์เซอร์ / พิมพ์ console ของหน้า | ปิด |
| `E2E_APP_SCRIPT` | ใช้ `script-pos.js` ไฟล์อื่น (เช่นเวอร์ชันเก่า) เพื่อตรวจว่าเทสต์จับบั๊กได้ | ไฟล์ในโปรเจกต์ |
| `E2E_BASE_URL` | รัน `node tests/e2e/frontend.spec.js` ตรง ๆ กับเซิร์ฟเวอร์ที่เปิดอยู่แล้ว | ตั้งโดย `run.sh` |

ชุดทดสอบดัก `https://cdnjs.cloudflare.com/**` แล้วตอบด้วยไฟล์จาก npm (`xlsx@0.18.5`, `chart.js@4.4.0`) และปิด Service Worker ในแต่ละ context

---

## 7. Conventions

### โค้ด Frontend
- Vanilla JS ไม่มี framework/module/build; ฟังก์ชัน global ที่ HTML เรียกผ่าน `onclick`
- แบ่ง section ด้วยแบนเนอร์ `// ═══…` + ชื่อ section ตัวพิมพ์ใหญ่ และ sub-section `// ── … ──`
- โค้ดเก่าเขียนแบบอัดแน่น (หลาย statement ต่อบรรทัด); โค้ดใหม่ (stores, scanner, shortcuts, online detection) เขียนแบบเว้นวรรค 2 ช่อง อ่านง่ายกว่า — โค้ดใหม่ให้ใช้แบบหลัง
- คอมเมนต์อธิบายเหตุผลเป็นภาษาไทยได้
- ทุก `localStorage` access ห่อด้วย `try/catch` (ดู `DB`, `getGlobal`)
- สีใช้ CSS variables ใน `:root` ของ `style-pos.css` (เช่น `--teal` ซึ่งปัจจุบันเป็นสีส้ม `#FF6600`)

### โค้ด Backend
- Module docstring บรรทัดแรกทุกไฟล์ (`"""Expenses API routes."""`), docstring สั้นทุก endpoint/method
- Type hints + SQLAlchemy 2.0 `Mapped[...]`/`mapped_column`
- Service รับ `store_id: int = 1` เป็นพารามิเตอร์ท้าย
- Error detail ของ API เป็นภาษาอังกฤษ (`"Expense not found"`); คอมเมนต์อธิบายเป็นไทยได้

### UI strings
- ข้อความที่ผู้ใช้เห็นเป็น **ภาษาไทย** ทั้งหมด (`toast`, `confirm`, label, placeholder) — ศัพท์เทคนิคบางคำเป็นอังกฤษได้ (Barcode, VAT)
- Format เงิน/วันที่ด้วย locale `th-TH` (`fmt`, `thDate`, `thDT`)

### Commit messages
Conventional Commits (ดู `git log --oneline`):

```
feat(frontend): live barcode scanner with preview, torch, and zoom
fix(api): bound pagination params on GET /auth/users
fix(backup): utf-8 output, close DB, no utcnow, don't create missing DB
docs: document store switcher, shortcuts, scanner; bump SW cache
chore: ignore docker compose backup output directory
ci: run full test suite (167 tests) + update TASKS.md
```

- type: `feat` / `fix` / `docs` / `chore` / `ci`; scope ที่ใช้: `frontend`, `backend`, `api`, `docker`, `backup`
- ข้อความภาษาอังกฤษ ตัวพิมพ์เล็ก ไม่มีจุดท้าย

---

## 8. ข้อควรระวัง (Gotchas)

| เรื่อง | รายละเอียด | ที่มา |
|--------|-----------|-------|
| ไม่มีร้าน `id=1` | ถ้าตาราง `stores` ว่าง ทุก endpoint ที่ใช้ `get_current_store` ตอบ `404 Store not found for current user` — ร้านเริ่มต้นมาจาก migration 003 หรือจาก `init_db()` (seed ร้าน id=1 เมื่อตาราง `stores` ว่าง) ถ้าเจอ 404 นี้ให้ตรวจตาราง `stores` ก่อน | `app/auth.py` `get_current_store`, `app/database.py`, `alembic/versions/003_add_multi_store.py` |
| ลำดับ Alembic vs create_all | ถ้า start แอปก่อน (create_all สร้างตารางแล้ว) แล้วค่อย `alembic upgrade head` อาจชนว่าตารางมีอยู่แล้ว — รัน migration ก่อนเสมอ | `app/main.py` lifespan |
| JWT config | `auth.py` อ่าน `JWT_*` จาก `os.environ` — `run.py` โหลด `.env` เข้า environ ให้ แต่ถ้ารัน `uvicorn app.main:app` ตรง ๆ ค่าใน `.env` จะไม่ถูกใช้ | `app/auth.py`, `run.py` |
| WebSocket 2 ชุด | event จาก service ไปที่ `/ws` เท่านั้น ไม่ไป `/api/v1/ws` | 3.7 |
| nginx ไม่ proxy WS | `nginx.conf` proxy แค่ `/api/` และไม่มี header `Upgrade`; ต่อ WS ที่พอร์ต 8000 ตรง | `nginx.conf` |
| SW cache-first | ลืม bump `CACHE_NAME` = ผู้ใช้ได้ไฟล์เก่า | `sw.js` |
| Schema frontend ≠ backend | เช่น expense ฝั่ง frontend `{name, amount, date, note}` แต่ backend `{category, description, amount, payment_method, notes}` — ถ้าจะเชื่อม sync ต้องทำ mapping | `saveExpense()`, `ExpenseBase` |
| Route order | path คงที่ก่อน `/{id}` | `app/api/__init__.py` |
