# 🛒 POS-MOBILE

### ระบบขายหน้าร้าน (Point of Sale) สำหรับมือถือ — frontend ทำงานในเบราว์เซอร์ และมี backend (FastAPI) เสริมให้เลือกรัน

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI_(ไม่บังคับ)-009688?style=flat-square&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

🔗 **ใช้งานจริง:** https://saharatyokthuan.github.io/pos-mobile/

> ⚠️ หน้าเว็บ (`script-pos.js`) ยังเก็บข้อมูลไว้ใน `localStorage` ของเบราว์เซอร์เครื่องนั้น ๆ เท่านั้น — **ยังไม่ได้เรียก backend API เพื่อบันทึก/ดึงข้อมูล** (ดู [สถาปัตยกรรม](#-สถาปัตยกรรม)) ส่วน `backend/` เป็น API ที่รันแยกได้

---

## 📁 โครงสร้างไฟล์

```
📦 POS-MOBILE
├── 🌐 index.html          → หน้าเว็บทั้งหมดแบบ single-page (header, sidebar, ทุกหน้า, ทุก modal)
├── 🎨 style-pos.css       → ธีมสี, เลย์เอาต์, responsive, สไตล์การพิมพ์ใบเสร็จ
├── ⚙️ script-pos.js       → ลอจิกทั้งหมด: จัดการข้อมูล, render, คำนวณ, นำทางระหว่างหน้า
├── 📱 manifest.json, sw.js, icons/ → PWA (manifest, service worker, ไอคอน)
├── 🖥️ backend/            → FastAPI + SQLAlchemy + Alembic (ดู backend/README.md)
├── 🐳 docker-compose.yml  → รัน backend + frontend (nginx) พร้อมกัน
├── 🐳 Dockerfile          → ไฟล์แยกจาก `backend/Dockerfile` (ใช้ python:3.11-slim, build จาก root, copy backend/) — `docker-compose.yml` ไม่ได้ใช้ไฟล์นี้
├── 🐳 nginx.Dockerfile    → image ของ frontend (nginx:alpine)
├── 🔧 nginx.conf          → config nginx: static, /api/ → backend, /health
├── 📘 PROJECT.md, USER_GUIDE.md, TASKS.md → เอกสารโปรเจกต์
├── 📄 LICENSE             → MIT
└── 🧪 .github/workflows/ci-cd.yml → CI/CD
```

ทุกหน้าอยู่ใน `index.html` ไฟล์เดียว สลับหน้าด้วย JavaScript (`showPage()`) ไม่มีการโหลดหน้าใหม่

### 📋 รายการสินค้ากลาง (ไม่บังคับ)

ปุ่ม "เพิ่มจากรายการสินค้ากลาง" และการ auto-fill ชื่อ/หมวดหมู่จากรหัสสินค้า ต้องใช้ไฟล์ `master-products.js`
ที่ประกาศค่าตัวแปร `MASTER_PRODUCTS` (อาร์เรย์รายการสินค้า) **ไฟล์นี้ไม่ได้รวมอยู่ใน repo**

ถ้าต้องการเปิดใช้ ให้วางไฟล์ `master-products.js` ไว้ข้าง ๆ `index.html` แล้วเพิ่มบรรทัดนี้ก่อน `script-pos.js`:

```html
<script src="master-products.js"></script>
```

ถ้าไม่มีไฟล์ ระบบจะซ่อนปุ่มดังกล่าวให้อัตโนมัติ (แอปยังใช้งานส่วนอื่นได้ครบถ้วน)

## 🏗️ สถาปัตยกรรม

- **Frontend** (`index.html` + `script-pos.js`): อ่าน/เขียนข้อมูลผ่าน `localStorage` (key ขึ้นต้น `qpos_`) ทั้งหมด
- **Backend** (`backend/`): REST API + WebSocket บน FastAPI/SQLite มี endpoint ครบสำหรับสินค้า ขาย สั่งซื้อ ลูกหนี้ รายจ่าย ฯลฯ รวมถึง `/api/v1/sync` สำหรับรับข้อมูลจาก localStorage (แต่ schema ยังไม่ตรงกับไฟล์ export ของ frontend — ส่งตรง ๆ จะได้ 422, ดู Known Issues ใน [TASKS.md](TASKS.md))
- **ที่ตรวจพบในโค้ด:** `script-pos.js` เรียก backend เพียงจุดเดียว คือ `fetch('/api/v1/sync/health', { method: 'HEAD' })` ทุก 30 วินาทีเพื่อตรวจสถานะออนไลน์ (`initOnlineDetection`) — ไม่มีการซิงก์หรือโหลดข้อมูลจาก API ดังนั้นการใช้งานจริงตอนนี้ยังเป็นแบบ localStorage ล้วน และ backend ยังไม่ได้ต่อกับหน้าเว็บ

## ✨ ฟีเจอร์หลัก

| หน้า | รายละเอียด |
|:---|:---|
| 🛒 **ขายสินค้า** | ค้นหาสินค้า/สแกนบาร์โค้ด (กล้องสด หรือถ่ายรูป), ตะกร้าสินค้า, ส่วนลด, VAT 7%, ชำระเงินสด/โอน/บัตร, คีย์แพดคำนวณเงินทอน, พักบิล/เรียกบิล, ขายเชื่อ |
| 📦 **สินค้า** | เพิ่ม/แก้ไขสินค้า, ค้นหา/กรองตามหมวดหมู่และสต๊อก, auto-fill ชื่อ+หมวดหมู่จากรหัส/บาร์โค้ด, ปรับสต๊อก, แจ้งเตือนสต๊อกต่ำ/ใกล้หมดอายุ |
| 🚚 **สั่งซื้อ** | บันทึกรายการสั่งซื้อจากผู้จำหน่าย, ค้นหาตามช่วงวันที่, export Excel |
| 💳 **ลูกหนี้** | บันทึกยอดขายเชื่อ, ติดตามยอดค้างชำระ, รับชำระหนี้บางส่วน/เต็มจำนวน |
| 📊 **รายงาน** | ยอดขาย (กราฟแท่ง+โดนัทตามหมวดหมู่, สินค้าขายดี, เปรียบเทียบช่วงเวลา), สต๊อก, รายจ่าย — export Excel ทุกแท็บ |
| ⚙️ **เพิ่มเติม/ตั้งค่า** | บันทึกรายจ่าย, ปรับสต๊อกด่วน, บิลพัก, นำเข้า/ส่งออก Excel, สำรอง/กู้คืนข้อมูล JSON, จัดการ mapping หมวดหมู่สินค้าตามรหัส, ข้อมูลร้าน/ตั้งค่าระบบ |

## 🔄 นำเข้า / ส่งออกข้อมูล

- ⬇️ ส่งออกสินค้า, ยอดขาย, สต๊อก, สั่งซื้อ, รายจ่าย เป็น **Excel (.xlsx)**
- ⬆️ นำเข้า Excel Master Product และไฟล์อัปเดตชื่อ+หมวดหมู่
- 🗄️ สำรอง/กู้คืนข้อมูลทั้งหมดเป็นไฟล์ JSON

## 💾 การเก็บข้อมูล

ข้อมูลทั้งหมดที่หน้าเว็บใช้เก็บใน `localStorage` ของเบราว์เซอร์ — หน้าเว็บไม่ได้ส่งข้อมูลขึ้น backend ข้อมูลอยู่เฉพาะในเครื่อง/เบราว์เซอร์นั้น ๆ
แนะนำให้สำรองข้อมูล (JSON) เป็นประจำ เพราะการล้างข้อมูลเบราว์เซอร์จะลบข้อมูลทั้งหมด

## 🚀 วิธีใช้งาน

- **ออนไลน์:** เปิด https://saharatyokthuan.github.io/pos-mobile/
- **ในเครื่อง:** เปิดไฟล์ `index.html` ในเบราว์เซอร์ได้ทันที — ไม่ต้อง build ไม่ต้อง install
- **รัน backend (ไม่บังคับ):** ดู [backend/README.md](backend/README.md) หรือหัวข้อ docker compose ด้านล่าง

> ฟีเจอร์สแกนบาร์โค้ดด้วยกล้องต้องเปิดผ่าน `https://` หรือ `localhost` เท่านั้น (ข้อกำหนดด้านความปลอดภัยของเบราว์เซอร์)

## 🐳 รันด้วย docker compose

`docker-compose.yml` มี service ดังนี้:

| Service | Image / build | Port | หน้าที่ |
|:---|:---|:---|:---|
| `backend` | build จาก `./backend` (`backend/Dockerfile`) | `8000:8000` | FastAPI API, เก็บ SQLite ที่ volume `backend-data` (`/data/pos_mobile.db`), healthcheck `/api/v1/sync/health`; ตอนเริ่ม container จะรัน `alembic upgrade head` (สร้างตาราง + ร้านเริ่มต้น) แล้วจึงรัน `python run.py` |
| `frontend` | build จาก `nginx.Dockerfile` (`nginx:alpine`) | `8080:80` | เสิร์ฟเฉพาะไฟล์ frontend ที่ copy เข้า image ตอน build (ไม่ mount repo — แก้ไฟล์แล้วต้อง `docker compose build frontend`) ใช้ `nginx.conf`, ส่ง `/api/` ต่อไปที่ `backend:8000`, มี `/health` |
| `backup` | build จาก `./backend` | - | ทำ backup ตาราง SQLite เป็น JSON ไปที่ `./backup` — เปิดเฉพาะเมื่อใช้ profile `backup` |

```bash
docker compose up --build              # เริ่ม backend + frontend
# หน้าเว็บ:   http://localhost:8080
# API docs:   http://localhost:8000/docs   (หรือผ่าน nginx ที่ http://localhost:8080/api/v1/...)

docker compose --profile backup run --rm backup   # สำรองข้อมูลเป็น JSON ลง ./backup
docker compose down                    # หยุด (ข้อมูลอยู่ใน volume backend-data)
```

หมายเหตุที่ตรวจจากไฟล์ตั้งค่า:
- `nginx.conf` proxy เฉพาะ `/api/` — path WebSocket (`/ws`) ไม่ได้ถูก proxy ต้องต่อที่พอร์ต 8000 ตรง ๆ
- ฐานข้อมูลของ backend อยู่ที่ `/data/pos_mobile.db` ใน volume `backend-data` เท่านั้น (ไม่มีการ mount ไฟล์ DB จาก host)
- `nginx.conf` ส่ง `sw.js` แบบ `no-cache, no-store` และ `.js`/`.css` แบบ `Cache-Control: no-cache` (revalidate ทุกครั้ง) — ออก release frontend ใหม่ต้อง bump `CACHE_NAME` ใน `sw.js` ([docs/DEPLOYMENT.md §8](docs/DEPLOYMENT.md#8-ออกเวอร์ชันใหม่ของ-frontend-service-worker))

## 📚 เอกสาร / การทดสอบ

| เอกสาร | เนื้อหา |
|:---|:---|
| [USER_GUIDE.md](USER_GUIDE.md) | คู่มือใช้งานหน้าร้าน, ติดตั้งบน Termux/คอมพิวเตอร์ |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | สถาปัตยกรรม, internals ของ frontend/backend, เพิ่มโมดูล/หน้าใหม่, API docs |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deploy production: docker compose, config, HTTPS, migration, backup, ออก release frontend |
| [backend/README.md](backend/README.md) | endpoints, environment variables, การรัน backend |
| [tests/e2e/README.md](tests/e2e/README.md) | ชุดทดสอบเบราว์เซอร์ (Playwright) |

```bash
tests/e2e/run.sh                         # E2E ของ frontend ใน Chromium (ต้องมี node + playwright, python3)
cd backend && python3 -m pytest -q       # unit/API tests ของ backend
python3 backend/scripts/smoke_test.py --base-url http://localhost:8000   # smoke test กับ backend ที่รันอยู่ (ใช้ DB ทดลองเท่านั้น — ขั้น restore จะแทนที่ข้อมูลร้าน)
```

## 📦 Dependencies (โหลดผ่าน CDN + ตรวจสอบ SRI)

| ไลบรารี | ใช้ทำอะไร |
|:---|:---|
| [SheetJS (xlsx.js) 0.18.5](https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js) | นำเข้า/ส่งออกไฟล์ Excel |
| [Chart.js 4.4.0](https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js) | กราฟในหน้ารายงาน |

Backend: FastAPI, SQLAlchemy (async) + SQLite, Alembic, Pydantic, PyJWT, Uvicorn — รายละเอียดใน [backend/README.md](backend/README.md#-technologies)

## 📄 License

เผยแพร่ภายใต้ [MIT License](LICENSE)

---

made in Thailand 🇹🇭
