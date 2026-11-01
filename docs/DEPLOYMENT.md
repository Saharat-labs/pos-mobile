# 🚀 POS-MOBILE - คู่มือ Deploy ขึ้นใช้งานจริง (Production)

> คู่มือนี้สำหรับผู้ดูแลระบบที่จะนำ POS-MOBILE (frontend static + backend FastAPI/SQLite) ขึ้นเซิร์ฟเวอร์จริง
> ทุกค่าที่อ้างถึงอ้างอิงจากไฟล์ใน repo โดยตรง — ถ้าต้องการวิธีติดตั้งเพื่อลองใช้งาน/พัฒนาในเครื่อง ดู [USER_GUIDE.md → การติดตั้งและเริ่มต้น](../USER_GUIDE.md#-การติดตั้งและเริ่มต้น) และ [backend/README.md](../backend/README.md)

---

## 📋 สารบัญ

1. [ภาพรวมทางเลือกการ Deploy](#1-ภาพรวมทางเลือกการ-deploy)
2. [Docker Compose](#2-docker-compose)
3. [การตั้งค่า (Configuration)](#3-การตั้งค่า-configuration)
4. [HTTPS และ Reverse Proxy](#4-https-และ-reverse-proxy)
5. [Database Migrations และผู้ใช้ admin คนแรก](#5-database-migrations-และผู้ใช้-admin-คนแรก)
6. [systemd และ Termux](#6-systemd-และ-termux)
7. [Backup และ Restore](#7-backup-และ-restore)
8. [ออกเวอร์ชันใหม่ของ Frontend (Service Worker)](#8-ออกเวอร์ชันใหม่ของ-frontend-service-worker)
9. [CI/CD (GitHub Actions)](#9-cicd-github-actions)
10. [Checklist ก่อน Deploy และการแก้ไขปัญหา](#10-checklist-ก่อน-deploy-และการแก้ไขปัญหา)

---

## 🎯 ก่อนเริ่ม: ข้อมูลอยู่ที่ไหน?

สิ่งสำคัญที่สุดที่ต้องเข้าใจก่อน deploy:

```
┌──────────────────────────────┐            ┌──────────────────────────────┐
│ Frontend (เบราว์เซอร์)        │            │ Backend (FastAPI + SQLite)   │
│ index.html / script-pos.js   │  HEAD      │ /api/v1/...                  │
│ ข้อมูลขาย/สินค้า → localStorage│ ─────────► │ /api/v1/sync/health          │
│ (แยกตามร้าน: qpos_, qpos_s2_) │  health    │ pos_mobile.db                │
└──────────────────────────────┘  เท่านั้น   └──────────────────────────────┘
```

- **ข้อมูลการขายทั้งหมดของ frontend อยู่ใน `localStorage` ของเบราว์เซอร์แต่ละเครื่อง** (`script-pos.js` บรรทัด 1–30: prefix `qpos_` สำหรับร้าน 1, `qpos_s<id>_` สำหรับร้านอื่น)
- `script-pos.js` เวอร์ชันปัจจุบันเรียก backend **เพียงจุดเดียว** คือ `HEAD /api/v1/sync/health` (บรรทัด ~1991) เพื่อแสดงแถบสถานะการเชื่อมต่อ — **ไม่มีการ sync ข้อมูลขึ้นเซิร์ฟเวอร์อัตโนมัติ**
- ดังนั้นการ backup เซิร์ฟเวอร์ **ไม่ได้** ปกป้องข้อมูลที่อยู่ในมือถือ/แท็บเล็ต ต้องสำรองฝั่งเบราว์เซอร์ด้วย (ดู [หัวข้อ 7](#7-backup-และ-restore))

---

## 1. ภาพรวมทางเลือกการ Deploy

| วิธี | ไฟล์ที่ใช้ | เหมาะกับ | ข้อดี | ข้อจำกัด |
|------|-----------|---------|------|---------|
| **Docker Compose** (แนะนำ) | `docker-compose.yml`, `backend/Dockerfile`, `nginx.conf` | VPS / เซิร์ฟเวอร์ในร้าน / NAS ที่มี Docker | รัน migration อัตโนมัติ, มี healthcheck, มี volume เก็บ DB, มี profile `backup` | ไม่มี TLS ในตัว ต้องวาง reverse proxy ข้างหน้าเอง |
| **systemd บน Linux** | `backend/pos-mobile.service` (ต้องแก้ path) | เซิร์ฟเวอร์ที่ไม่อยากใช้ Docker | เบา, restart อัตโนมัติ, log ใน journald | ต้องรัน `alembic upgrade head` เอง, ต้องตั้ง web server สำหรับ frontend เอง, ไฟล์ตัวอย่างใช้ path Termux |
| **Termux บน Android** | `backend/start_termux.sh` | ร้านเล็กที่ใช้มือถือเครื่องเดียวเป็นทั้ง POS และเซิร์ฟเวอร์ | ไม่ต้องมีคอมพิวเตอร์ | path ถูก hardcode, ไม่ได้รัน alembic, เครื่องอื่นในร้านเข้าผ่าน `http://<IP>` จะใช้กล้อง/PWA ไม่ได้ (ไม่ใช่ secure context) |
| **GitHub Pages / static host** (frontend อย่างเดียว) | `index.html`, `script-pos.js`, `style-pos.css`, `sw.js`, `manifest.json`, `icons/` | ไม่ต้องการ backend เลย | ได้ HTTPS ฟรี, ไม่ต้องดูแลเซิร์ฟเวอร์ | ไม่มี backend — health check จะได้ 404 ซึ่ง frontend ถือว่า "ไม่ทราบสถานะ" (ไม่แสดงว่าล่ม) |

---

## 2. Docker Compose

> วิธีสั่งรันแบบเร็ว ๆ มีอยู่แล้วใน [README.md → รันด้วย docker compose](../README.md#-รันด้วย-docker-compose) หัวข้อนี้เน้นเรื่องที่ต้องรู้สำหรับ production

### 2.1 Services

| Service | Build / Image | Port (host:container) | Volume | Healthcheck |
|---------|---------------|-----------------------|--------|-------------|
| `backend` | build `./backend` ด้วย `backend/Dockerfile` (python:3.12-slim, รันเป็น user `posuser`) | `8000:8000` | `backend-data` → `/data` | `curl -f http://localhost:8000/api/v1/sync/health` ทุก 30s |
| `frontend` | build จาก root ของ repo (context `.`) ด้วย `nginx.Dockerfile` (nginx:alpine) — copy เข้า image **เฉพาะ** `index.html`, `script-pos.js`, `style-pos.css`, `manifest.json`, `sw.js`, `icons/`, `LICENSE`, `README.md`, `USER_GUIDE.md` และ `nginx.conf` | `8080:80` | ไม่มี volume (ไม่ mount repo) | `wget --spider http://localhost/health` ทุก 30s (`HEALTHCHECK` ใน `nginx.Dockerfile`) |
| `backup` | build เหมือน `backend` | — | `backend-data` → `/data`, bind `./backup` → `/backup` | — (อยู่ใน profile `backup`, `restart: "no"`) |

ที่มา: `docker-compose.yml` บรรทัด 5–55, `nginx.Dockerfile`

> 🔒 container `frontend` เสิร์ฟเฉพาะไฟล์ที่ copy เข้า image — `.git/`, `backend/` (รวม `backend/.env`), ไฟล์ `.db` และ `backup/` **ไม่อยู่ใน image จึงไม่ถูกเสิร์ฟ** นอกจากนี้ `nginx.conf` ยังตอบ 404 ให้ path ที่ขึ้นต้นด้วยจุด (`location ~ /\.`, บรรทัด 16) และ `/backend`, `/backup`, `/tests`, `/docs`, `/.github` (บรรทัด 20) เป็นชั้นป้องกันซ้อน
>
> ⚠️ checkout ที่เก่ากว่า commit `8eb6ef5` ใช้ `image: nginx:alpine` + bind mount `./:/usr/share/nginx/html` ซึ่ง **เปิดให้ดาวน์โหลดทั้ง repo** (`.git/`, `backend/.env`, `backup/`) — ถ้า deploy ไว้แบบนั้น ให้ `git pull` แล้ว `docker compose up -d --build` ทันที และตรวจด้วย `curl -I http://localhost:8080/.git/config` (ต้องได้ 404) ถ้าเคยเปิดสู่สาธารณะ ให้ถือว่า `JWT_SECRET` และไฟล์ backup รั่วไหลแล้ว และเปลี่ยน secret ใหม่

**ขั้นตอนตอน container `backend` เริ่ม** (`backend/Dockerfile` บรรทัด 56):

```sh
alembic upgrade head && exec python run.py
```

1. `alembic upgrade head` — สร้าง/อัปเกรดตาราง + สร้างร้านเริ่มต้น `STORE001` (revision 003) โดยอ่าน `DATABASE_URL` จาก environment (`backend/alembic/env.py` บรรทัด 24–26)
2. `python run.py` — สร้าง `DATA_DIR` แล้วรัน uvicorn ที่ `HOST:PORT` (`reload=DEBUG`)
3. ตอน startup `init_db()` จะ `create_all` อีกรอบ (ไม่มีผลถ้าตารางมีอยู่แล้ว) และสร้างร้าน id=1 เฉพาะเมื่อตาราง `stores` ว่าง (ซึ่งไม่เกิดหลัง alembic เพราะ revision 003 สร้างไว้แล้ว)

### 2.2 ฐานข้อมูล SQLite อยู่ที่ไหน

- `DATABASE_URL=sqlite+aiosqlite:////data/pos_mobile.db` (สังเกต `////` = absolute path) → ไฟล์ `/data/pos_mobile.db` ใน container
- `/data` คือ named volume `backend-data` ซึ่ง Docker ตั้งชื่อจริงเป็น `<ชื่อโปรเจค>_backend-data` — ถ้า clone ไว้ในโฟลเดอร์ `pos-mobile` จะได้ **`pos-mobile_backend-data`** (ยืนยันด้วย `docker compose config`)
- ข้อมูลจะคงอยู่ข้าม `docker compose down` / `up --build` แต่ **จะหายถ้าสั่ง `docker compose down -v`** ⚠️

```bash
docker volume ls | grep backend-data
docker volume inspect pos-mobile_backend-data   # ดู Mountpoint บน host
```

### 2.3 คำสั่งที่ใช้บ่อย

```bash
cd /path/to/pos-mobile

docker compose up -d --build          # เริ่ม (build backend + frontend ใหม่ถ้าไฟล์เปลี่ยน)
docker compose build frontend         # build เฉพาะ frontend หลังแก้ไฟล์ static หรือ nginx.conf
docker compose ps                     # ดูสถานะ + health
docker compose logs -f backend        # log backend (alembic + uvicorn)
docker compose logs -f frontend       # access/error log ของ nginx
docker compose restart backend
docker compose down                   # หยุด (ข้อมูลยังอยู่ใน volume)
```

### 2.4 อัปเดตเป็นเวอร์ชันใหม่

`docker-compose.yml` **build ทั้งสอง image เองจากโค้ดในเครื่อง** (ไม่ได้ดึง image จาก GHCR) — ไฟล์ frontend และ `nginx.conf` ถูก copy เข้า image ตอน build ดังนั้น `git pull` อย่างเดียว **ยังไม่เปลี่ยนหน้าเว็บ** ต้อง build ใหม่ทุกครั้ง:

```bash
# 0. สำรองก่อนเสมอ (ดูหัวข้อ 7)
docker compose --profile backup run --rm backup

# 1. ดึงโค้ดใหม่
git pull

# 2. build + recreate ทั้ง backend และ frontend
#    migration (alembic upgrade head) รันเองตอน container backend เริ่ม
docker compose up -d --build

# 3. ตรวจว่า migration ผ่านและ healthy
docker compose logs --tail=50 backend
docker compose ps
curl -f http://localhost:8080/api/v1/sync/health
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/.git/config   # ต้องได้ 404
```

> ⚠️ ถ้าไฟล์ frontend เปลี่ยน อย่าลืม bump `CACHE_NAME` ใน `sw.js` ก่อน commit (ดู [หัวข้อ 8](#8-ออกเวอร์ชันใหม่ของ-frontend-service-worker))

### 2.5 Backup profile

```bash
mkdir -p backup                                    # ดูหมายเหตุเรื่องสิทธิ์ด้านล่าง
docker compose --profile backup run --rm backup
```

- รัน `python scripts/backup_db.py` (`docker-compose.yml` บรรทัด 55)
- อ่าน DB แบบ read-only (`mode=ro`) จาก `DB_PATH` (default `/data/pos_mobile.db`) — ถ้าไม่มีไฟล์ DB จะ error แทนการสร้าง DB เปล่า
- เขียนไฟล์ `pos_mobile_backup_<YYYYMMDD_HHMMSS>.json` (เวลา **UTC**) ลง `BACKUP_DIR` (default `/backup`) = โฟลเดอร์ `./backup` บน host
- ปรับได้ด้วย env `DB_PATH`, `BACKUP_DIR` (`backend/scripts/backup_db.py` บรรทัด 12–13) — ตัวแปร `DATABASE_URL` ที่ compose ส่งให้ service นี้ **ไม่ถูกใช้** โดยสคริปต์
- **ไม่มีระบบ retention / ลบไฟล์เก่า** — ต้องจัดการเอง เช่น cron บน host:

```cron
# สำรองทุกวัน 23:30 และเก็บไว้ 30 วัน (ตัวอย่าง — ปรับ path ตามจริง)
30 23 * * * cd /path/to/pos-mobile && docker compose --profile backup run --rm backup && find ./backup -name 'pos_mobile_backup_*.json' -mtime +30 -delete
```

> 🔒 **เก็บไฟล์ backup ไว้นอก web root เสมอ** — ไฟล์ JSON มีข้อมูลขาย/ลูกหนี้ทั้งหมด และไฟล์ SQLite ทั้งไฟล์ (7.2) มีตาราง `users` (password hash) และ `api_keys` ด้วย ใน compose ปัจจุบัน `./backup` ไม่ถูกเสิร์ฟ (ไม่อยู่ใน image frontend และ `nginx.conf` ตอบ 404 ให้ `/backup`) แต่ถ้ามีใครเสิร์ฟโฟลเดอร์ repo ด้วยวิธีอื่น (checkout เก่าที่ bind mount ทั้ง repo, nginx บน host ที่ `root` ชี้ไปที่ repo, `python -m http.server`, Live Server ฯลฯ) ไฟล์ใน `./backup` จะดาวน์โหลดได้ทันที — แนะนำให้ย้ายปลายทางออกนอก repo ด้วย override เช่น:
>
> ```yaml
> # docker-compose.override.yml
> services:
>   backup:
>     volumes: !override
>       - backend-data:/data
>       - /var/backups/pos-mobile:/backup
> ```
>
> แล้วปรับ path ใน `find` ของ cron ให้ตรงกัน (`!override` ต้องใช้ Compose v2.24+) และจำกัดสิทธิ์โฟลเดอร์ (`chmod 700`)

ข้อจำกัดของ backup profile ที่ต้องรู้:

| เรื่อง | รายละเอียด |
|--------|-----------|
| ตารางที่ dump | `products, sales, sale_items, purchases, purchase_items, debts, debt_payments, expenses, stock_movements, hold_bills, settings, category_mappings` (บรรทัด 15–17) — **ไม่รวม** `stores`, `users`, `api_keys`, `refresh_tokens` |
| รูปแบบไฟล์ | `{"timestamp", "version", "data": {<ตาราง>: [แถวดิบ]}}` — เป็นแถวดิบของตาราง (เช่น `sale_items` แยกจาก `sales`) **ไม่ได้ออกแบบมาให้ใช้กับ `POST /api/v1/sync/restore`** (endpoint นั้นคาดรูปแบบของ `GET /api/v1/sync/backup`) อย่าส่งเข้า `/restore` และไม่มีสคริปต์ restore ให้ ใช้เป็น archive/ตรวจสอบเท่านั้น |
| สิทธิ์เขียน | image รันเป็น `posuser` (non-root, `backend/Dockerfile` บรรทัด 43) แต่ `./backup` ที่ Docker สร้างให้อัตโนมัติจะเป็นของ root → อาจได้ `PermissionError` ดูวิธีแก้ใน [หัวข้อ 10](#102-การแก้ไขปัญหา) |

> 💡 สำหรับ disaster recovery ที่กู้คืนได้ครบ แนะนำให้สำรอง **ไฟล์ SQLite ทั้งไฟล์** เพิ่มด้วย (ดู [7.2](#72-สำรองไฟล์-sqlite-ทั้งไฟล์-แนะนำสำหรับ-disaster-recovery))

---

## 3. การตั้งค่า (Configuration)

ค่าทั้งหมดอยู่ใน `backend/app/config.py` (pydantic-settings, `case_sensitive = True`, `env_file = ".env"`) — ชื่อตัวแปรต้องเป็นตัวพิมพ์ใหญ่ตรงตามตาราง

> ⚠️ **ไม่มี `SECRET_KEY`** ในโปรเจคนี้ — secret ที่ใช้เซ็น JWT คือ `JWT_SECRET`

### 3.1 ตารางค่าทั้งหมด

ค่า default ด้านล่างได้จากการรัน `python3 -c "from app.config import settings; ..."` ใน `backend/`

| ตัวแปร | Default | ความหมาย | คำแนะนำ Production |
|--------|---------|---------|-------------------|
| `APP_NAME` | `POS-MOBILE API` | ชื่อที่แสดงใน `/`, `/health`, `/docs` | ปล่อยตามเดิมได้ |
| `APP_VERSION` | `1.0.0` | เวอร์ชันที่แสดงใน API/Swagger | ตั้งให้ตรงกับ release |
| `DEBUG` | `True` | ส่งเป็น `reload=` ให้ uvicorn (`run.py` บรรทัด 34) — `True` = auto-reload เมื่อไฟล์เปลี่ยน | **`false` เสมอ** (compose ตั้งให้แล้ว; `backend/.env.example` ตั้ง `true`) — หมายเหตุ: `/docs`, `/redoc`, `/openapi.json` เปิดอยู่เสมอไม่ขึ้นกับค่านี้ |
| `DATABASE_URL` | `sqlite+aiosqlite:///./pos_mobile.db` | ที่อยู่ DB — `///./` = relative กับ **working directory** ตอนรัน | ใช้ absolute path เช่น `sqlite+aiosqlite:////data/pos_mobile.db` (compose) หรือ `sqlite+aiosqlite:////var/lib/pos-mobile/pos_mobile.db` |
| `DATABASE_ECHO` | `False` | log SQL ทุกคำสั่ง | `false` |
| `CORS_ORIGINS` | `["http://localhost:8000","http://127.0.0.1:8000","file://","null"]` | JSON list ของ origin ที่อนุญาต (`allow_credentials=True`, ทุก method/header — `app/main.py` บรรทัด 39–45) | ถ้า frontend กับ API อยู่ origin เดียวกันผ่าน nginx (`/api/`) ไม่จำเป็นต้องใช้ CORS — ตั้งเป็น origin จริงเท่านั้น เช่น `["https://pos.example.com"]` และ **เอา `"null"` / `"file://"` ออก** |
| `HOST` | `0.0.0.0` | address ที่ uvicorn bind | ใน Docker ต้องเป็น `0.0.0.0`; systemd หลัง reverse proxy ใช้ `127.0.0.1` |
| `PORT` | `8000` | พอร์ต uvicorn | ถ้าเปลี่ยน ต้องแก้ `nginx.conf` (`proxy_pass http://backend:8000`), ports และ healthcheck ใน compose/Dockerfile ด้วย |
| `AUTH_ENABLED` | `False` | `False` = ข้ามการยืนยันตัวตนทั้งหมด (ใช้ user แรกในระบบ หรือสร้าง `dev@local` / `devpass` ให้อัตโนมัติ — `app/auth.py` บรรทัด 344–350) | **`true`** ถ้า API เข้าถึงได้จากเครือข่าย — อ่านคำเตือนใน [5.3](#53-สร้างผู้ใช้-admin-คนแรก) ก่อนเปิด |
| `API_KEY` | `""` | ประกาศไว้ใน config แต่ **ไม่มีโค้ดส่วนไหนใช้** (API key จริงสร้างผ่าน `/api/v1/auth/api-keys` และเก็บใน DB) | ไม่ต้องตั้ง |
| `JWT_SECRET` | `""` | secret เซ็น JWT — ถ้า `AUTH_ENABLED=true` แต่ไม่ตั้ง จะ `ValueError` ตอน import; ถ้าปิด auth ใช้ค่า dev `dev-secret-change-in-production` | **บังคับ** — สุ่มยาว ๆ เช่น `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ALGORITHM` | `HS256` | อัลกอริทึม JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | อายุ access token (นาที) | ตามนโยบาย (15–60) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | อายุ refresh token (วัน) | ตามนโยบาย |
| `DATA_DIR` | `~/pos-mobile-data` (`Path.home()`) | `run.py` แค่ `mkdir` โฟลเดอร์นี้ตอนเริ่ม — **ไม่ได้กำหนดตำแหน่ง DB** (DB ดูจาก `DATABASE_URL`) | ตั้งให้เป็นโฟลเดอร์เดียวกับ DB เพื่อไม่ให้สับสน (compose: `/data`) |

ตัวแปรที่ไม่ได้อยู่ใน `config.py` แต่เกี่ยวข้อง:

| ตัวแปร | อ่านโดย | ความหมาย |
|--------|--------|---------|
| `DB_PATH`, `BACKUP_DIR` | `backend/scripts/backup_db.py` | ตำแหน่ง DB / โฟลเดอร์ปลายทางของ backup |
| `FORWARDED_ALLOW_IPS` | uvicorn (`requirements.txt`: `uvicorn==0.38.0`; `uvicorn/config.py` ใช้ `os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")` เมื่อไม่ได้ส่ง `forwarded_allow_ips` — ซึ่ง `run.py` ไม่ได้ส่ง) | IP ของ proxy ที่เชื่อถือ header `X-Forwarded-*` — หลัง nginx ใน compose ถ้าไม่ตั้ง IP ลูกค้าที่บันทึกใน `refresh_tokens.ip_address` จะเป็น IP ของ container nginx |

> ⚠️ **`JWT_*` ถูกอ่านจาก `os.environ` โดยตรงใน `app/auth.py` (บรรทัด 73–82) ไม่ได้อ่านจาก `settings`** — ถ้าใส่ไว้ใน `backend/.env` ต้องเริ่มด้วย `python run.py` (ซึ่ง `load_dotenv` ไฟล์ `.env` เข้า environment ให้) ถ้ารัน `uvicorn app.main:app` ตรง ๆ ค่า `JWT_SECRET` จาก `.env` จะไม่ถูกเห็น

### 3.2 วิธีตั้งค่า

**ก) ไฟล์ `backend/.env`** (systemd / Termux / รันมือ)

```bash
cd backend
cp .env.example .env
chmod 600 .env
```

แก้อย่างน้อย:

```dotenv
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:////var/lib/pos-mobile/pos_mobile.db
DATA_DIR=/var/lib/pos-mobile
CORS_ORIGINS=["https://pos.example.com"]
AUTH_ENABLED=true
JWT_SECRET=<ค่าสุ่มยาว>
```

ทั้ง `run.py` (โหลด `backend/.env` เสมอ) และ pydantic-settings (โหลด `.env` ใน working directory) จะอ่านไฟล์นี้ `.gitignore` ignore `.env` ไว้แล้ว

**ข) Docker Compose** — `docker-compose.yml` ส่งค่าผ่าน `environment:` เท่านั้น (ไม่มี `env_file:`) แนะนำสร้าง `docker-compose.override.yml` (compose โหลดให้อัตโนมัติ) เพื่อไม่ต้องแก้ไฟล์หลัก:

```yaml
# docker-compose.override.yml (ตัวอย่าง — อย่า commit ไฟล์ที่มี secret)
services:
  backend:
    ports: !override
      - "127.0.0.1:8000:8000"     # ไม่เปิด API ตรงออกเน็ต ให้ผ่าน nginx
    environment:
      - CORS_ORIGINS=["https://pos.example.com"]
      - AUTH_ENABLED=true
      - JWT_SECRET=${JWT_SECRET}  # อ่านจาก shell หรือไฟล์ .env ข้าง docker-compose.yml
  frontend:
    ports: !override
      - "127.0.0.1:8080:80"       # ให้ reverse proxy TLS บน host (หัวข้อ 4.3) เป็นทางเข้าเดียว
```

> `!override` ต้องใช้ Docker Compose v2.24 ขึ้นไป ถ้าเวอร์ชันเก่ากว่าให้แก้ `ports` ใน `docker-compose.yml` โดยตรง
> ไฟล์ `.env` ข้าง `docker-compose.yml` (ที่ compose ใช้แทนค่า `${JWT_SECRET}`) ไม่ถูกเสิร์ฟทางเว็บ เพราะ image frontend copy เฉพาะไฟล์ที่ระบุใน `nginx.Dockerfile` — แต่ควร `chmod 600` และไม่ commit (`.gitignore` ignore `.env` อยู่แล้ว)
> อย่าสร้าง `backend/.env` ก่อน `docker compose build` — `backend/` ไม่มี `.dockerignore` ไฟล์ `.env` จะถูก `COPY . .` เข้า **image backend** (ไม่ถูกเสิร์ฟทางเว็บ แต่ติดไปกับ image ทุกที่ที่ image ถูก push/copy)

**ค) systemd** — ใช้ `EnvironmentFile=` ชี้ไปไฟล์ที่ chmod 600 (ตัวอย่างใน [หัวข้อ 6.1](#61-systemd-บน-linux-server)) หรือพึ่ง `backend/.env` ที่ `run.py` โหลดให้ก็ได้

---

## 4. HTTPS และ Reverse Proxy

### 4.1 ทำไมต้อง HTTPS

| ฟีเจอร์ | ต้องการ secure context | ที่มา |
|--------|------------------------|------|
| สแกนบาร์โค้ดด้วยกล้อง | ✅ `navigator.mediaDevices.getUserMedia` + `BarcodeDetector` | `script-pos.js` บรรทัด ~1795–1831 |
| ติดตั้งเป็นแอป (PWA) / ทำงานออฟไลน์ | ✅ `navigator.serviceWorker.register('./sw.js')` | `index.html` บรรทัด 13–14 |

secure context = `https://` หรือ `http://localhost` / `127.0.0.1` เท่านั้น — **เข้าผ่าน `http://192.168.x.x:8080` จากมือถือเครื่องอื่นในร้าน กล้องและ service worker จะไม่ทำงาน**

### 4.2 สิ่งที่ `nginx.conf` ทำอยู่ตอนนี้

| Location | พฤติกรรม |
|----------|----------|
| `listen 80` | HTTP อย่างเดียว ไม่มี TLS |
| `~ /\.` (บรรทัด 16) | `deny all` + 404 ให้ทุก path ที่มีส่วนขึ้นต้นด้วยจุด (`.git`, `.env`, `.well-known` ฯลฯ) |
| `~ ^/(backend\|backup\|tests\|docs\|\.github)(/\|$)` (บรรทัด 20) | 404 — ชั้นป้องกันซ้อน เผื่อไฟล์เหล่านี้หลุดเข้า web root |
| `= /sw.js` | exact match (ชนะ regex location ทุกตัว) → `Cache-Control: no-cache, no-store, must-revalidate` + `Pragma: no-cache` + `Expires: 0` — เบราว์เซอร์ตรวจ `sw.js` ใหม่ทุกครั้ง |
| `~* \.(js\|css)$` | `Cache-Control: no-cache` — เก็บ cache ได้แต่ต้อง revalidate ทุกครั้ง (ได้ `304` ถ้าไฟล์ไม่เปลี่ยน ผ่าน `ETag`/`Last-Modified`) จึงไม่มี `script-pos.js`/`style-pos.css` อายุ 1 ปีค้างใน HTTP cache |
| `~* \.(png\|jpg\|...\|woff2)$` | รูป/ฟอนต์: `expires 1y` + `Cache-Control: public, immutable` |
| `/manifest.json` | cache 1 วัน |
| `/api/` | `proxy_pass http://backend:8000` + `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, timeout 60s — **ไม่มี header `Upgrade`/`Connection`** จึงใช้ WebSocket `/api/v1/ws` ผ่าน nginx ไม่ได้ |
| `/ws` | **ไม่ได้ proxy** — ตกไปที่ SPA fallback (`index.html`) |
| `/health` | ตอบ `200 healthy` จาก nginx เอง (ไม่ได้เช็ค backend) |
| `/` | `try_files $uri $uri/ /index.html` |
| security headers | `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy` (ระดับ server — หายไปใน location ที่มี `add_header` ของตัวเอง ตามกฎการสืบทอดของ nginx) |

### 4.3 วาง TLS ไว้ข้างหน้า (แนะนำ)

วิธีที่แก้ไฟล์ใน repo น้อยที่สุด: ให้ compose ฟังเฉพาะ localhost แล้วใช้ nginx (หรือ reverse proxy อื่น) บน host ทำ TLS แล้วส่งต่อไปที่ `127.0.0.1:8080` — container `frontend` เสิร์ฟเฉพาะไฟล์ใน image และปฏิเสธ path ที่ซ่อน/ไม่ใช่ frontend อยู่แล้ว (4.2) จึงเปิดผ่าน TLS ได้โดยไม่เผย repo

> 💡 container ตอบ 404 ให้ `/.well-known/...` (กฎ `~ /\.`) — ถ้าใช้ Let's Encrypt แบบ HTTP-01 ให้ nginx บน host ตอบ `/.well-known/acme-challenge/` เองจากโฟลเดอร์ webroot นอก repo (หรือใช้ `certbot --nginx`) อย่า proxy ไป container

```nginx
# /etc/nginx/sites-available/pos-mobile  (nginx บน host — ตัวอย่าง)
server {
    listen 443 ssl http2;
    server_name pos.example.com;

    ssl_certificate     /etc/letsencrypt/live/pos.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pos.example.com/privkey.pem;

    # frontend + /api/ → container frontend (nginx.conf ส่ง /api/ ต่อให้ backend)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # WebSocket — nginx.conf ใน container ไม่รองรับ จึงส่งตรงไป backend
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    location /api/v1/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}

server {
    listen 80;
    server_name pos.example.com;
    return 301 https://$host$request_uri;
}
```

และเปลี่ยน port mapping ของ compose ให้ไม่เปิดออกภายนอก (ผ่าน override ตาม [3.2](#32-วิธีตั้งค่า)): `frontend` → `"127.0.0.1:8080:80"`, `backend` → `"127.0.0.1:8000:8000"`

WebSocket endpoint ที่มีจริง (ดู `backend/README.md` หัวข้อ WebSocket):
- `/api/v1/ws?room=default` (`app/api/ws.py`)
- `/ws?client_id=<id>` (`app/api/websocket.py`)

> 💡 frontend ปัจจุบันยังไม่ได้เปิด WebSocket — ถ้าไม่มี client อื่นใช้ จะข้ามสอง location นี้ก็ได้
> 💡 ร้านที่ไม่มีโดเมน/อยู่ใน LAN อย่างเดียว: ต้องใช้ certificate ที่อุปกรณ์ทุกเครื่องเชื่อถือ (เช่น CA ภายในที่ติดตั้งลงมือถือ) ไม่เช่นนั้นเบราว์เซอร์จะไม่ถือว่าเป็น secure context

---

## 5. Database Migrations และผู้ใช้ admin คนแรก

### 5.1 Alembic

มี 3 revision ใน `backend/alembic/versions/`: `001` (ตารางหลัก) → `002` (users, api_keys, refresh_tokens) → `003` (stores + `store_id` ทุกตาราง + ร้านเริ่มต้น `STORE001` id=1)

```bash
cd backend
source venv/bin/activate

# ระบุ DB ด้วย env — alembic/env.py อ่าน DATABASE_URL จาก os.environ เท่านั้น (ไม่อ่าน .env)
export DATABASE_URL=sqlite+aiosqlite:////var/lib/pos-mobile/pos_mobile.db

alembic current          # ดู revision ปัจจุบัน
alembic upgrade head     # อัปเกรดเป็นล่าสุด
alembic history          # ดูรายการ revision
alembic downgrade -1     # ย้อน 1 revision (สำรอง DB ก่อน!)
```

> ⚠️ ถ้าไม่ตั้ง `DATABASE_URL` alembic จะใช้ `sqlalchemy.url` ใน `alembic.ini` = `./pos_mobile.db` (relative กับโฟลเดอร์ที่รันคำสั่ง) ซึ่งอาจเป็นคนละไฟล์กับที่แอปใช้

**ใน Docker:** `backend/Dockerfile` รัน `alembic upgrade head` ทุกครั้งที่ container เริ่ม โดยใช้ `DATABASE_URL` จาก compose — ไม่ต้องสั่งเอง ถ้าต้องการรันมือ:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

### 5.2 ทำไม `alembic upgrade head` สำคัญ

`init_db()` (`app/database.py` บรรทัด 34–49) ใช้ `create_all` สร้างตาราง และสร้างร้าน `STORE001` (id=1) ให้เมื่อตาราง `stores` ยังว่าง — แต่ **ไม่บันทึก `alembic_version`** ผลคือ ถ้าเริ่มเซิร์ฟเวอร์บน DB ใหม่โดยไม่รัน alembic ก่อน แอปจะใช้งานได้ แต่รัน `alembic upgrade head` ทีหลังจะล้มด้วย `table ... already exists` และ migration ในอนาคตจะใช้ไม่ได้จนกว่าจะ `alembic stamp head` (ดู [10.2](#102-การแก้ไขปัญหา))

ดังนั้นให้รัน `alembic upgrade head` **ก่อน** เริ่มเซิร์ฟเวอร์ครั้งแรกเสมอ (Docker ทำให้อัตโนมัติ)

> ℹ️ ก่อน commit `7ab1281` `init_db()` ไม่สร้างร้าน — DB ที่สร้างจาก `run.py`/`start_termux.sh` ด้วยโค้ดเก่าจะตอบ `404 Store not found for current user` ทุก endpoint ที่ผูกกับร้าน การรันโค้ดปัจจุบันหนึ่งครั้งจะเติมร้าน id=1 ให้ (ถ้าตาราง `stores` ว่าง)

### 5.3 สร้างผู้ใช้ admin คนแรก

กฎใน `app/api/auth.py` บรรทัด 121–139 (`POST /api/v1/auth/register`):

| `AUTH_ENABLED` | ใครสมัครได้ |
|----------------|-------------|
| `false` | ทุกคน ทุก role (ไม่มีการตรวจสอบ) |
| `true` | ได้ **เฉพาะเมื่อยังไม่มี user ในระบบเลย** — มี user แล้วจะได้ `403 Registration requires admin privileges` |

ข้อควรระวัง:
- role ของ user แรก **มาจาก request** (default `staff`) และ `is_superuser` เป็น `false` เสมอ → ต้องส่ง `"role": "admin"` เอง
- ถ้าเคยรันด้วย `AUTH_ENABLED=false` แล้วมีการเรียก endpoint ใดก็ตามที่ต้องการ user ระบบจะสร้าง **`dev@local` / `devpass` (admin + superuser)** ให้อัตโนมัติ — หลังเปิด auth แล้วจะสมัคร admin ใหม่ไม่ได้ และบัญชี dev นี้ล็อกอินด้วยรหัสที่ทุกคนรู้ได้ ⚠️

ขั้นตอนที่แนะนำ (DB ใหม่):

```bash
# 1. ตั้ง AUTH_ENABLED=true + JWT_SECRET ก่อนเริ่ม backend ครั้งแรก
# 2. สมัคร admin คนแรกทันที
curl -X POST https://pos.example.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","username":"owner","password":"<รหัสอย่างน้อย 8 ตัว>","full_name":"เจ้าของร้าน","role":"admin"}'

# 3. ล็อกอินเพื่อรับ token
curl -X POST https://pos.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"owner","password":"<รหัส>"}'
```

ถ้า DB เคยรันแบบปิด auth มาก่อน: ตรวจว่ามี user `dev@local` หรือไม่ (`GET /api/v1/auth/users` ด้วย token admin) แล้วปิดใช้งาน/เปลี่ยนรหัสก่อนเปิดให้เข้าจากเครือข่าย

---

## 6. systemd และ Termux

### 6.1 systemd บน Linux server

`backend/pos-mobile.service` เป็น **ตัวอย่างที่ใช้ path ของ Termux** (`User=termux`, `/data/data/com.termux/...`) — Termux ไม่มี systemd จึงใช้ไฟล์นี้ตรง ๆ ไม่ได้ทั้งบน Android และ Linux ให้คัดลอกไปแก้ path:

```bash
# ตัวอย่างโครงสร้างบนเซิร์ฟเวอร์
sudo useradd -r -s /usr/sbin/nologin posmobile
sudo mkdir -p /opt/pos-mobile /var/lib/pos-mobile
sudo git clone https://github.com/saharatyokthuan/pos-mobile.git /opt/pos-mobile
cd /opt/pos-mobile/backend
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo chown -R posmobile:posmobile /var/lib/pos-mobile

# migration ครั้งแรก
sudo -u posmobile env DATABASE_URL=sqlite+aiosqlite:////var/lib/pos-mobile/pos_mobile.db \
  venv/bin/alembic upgrade head
```

```ini
# /etc/systemd/system/pos-mobile.service — ดัดแปลงจาก backend/pos-mobile.service
[Unit]
Description=POS-MOBILE Backend API
After=network.target

[Service]
Type=simple
User=posmobile
WorkingDirectory=/opt/pos-mobile/backend
EnvironmentFile=/etc/pos-mobile.env
Environment=PATH=/opt/pos-mobile/backend/venv/bin:/usr/bin:/bin
ExecStartPre=/opt/pos-mobile/backend/venv/bin/alembic upgrade head
ExecStart=/opt/pos-mobile/backend/venv/bin/python run.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

`/etc/pos-mobile.env` (chmod 600) ใส่ค่าตาม [3.2](#32-วิธีตั้งค่า) โดยให้ `HOST=127.0.0.1`, `DEBUG=false` และ `DATABASE_URL` เป็น absolute path — `ExecStartPre` จะได้ `DATABASE_URL` เดียวกันจาก `EnvironmentFile`

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pos-mobile
journalctl -u pos-mobile -f
```

frontend: ให้ nginx บน host เสิร์ฟ **เฉพาะไฟล์ frontend** (`index.html`, `script-pos.js`, `style-pos.css`, `sw.js`, `manifest.json`, `icons/`) โดยคัดลอกไปไว้ในโฟลเดอร์แยก เช่น `/var/www/pos-mobile` — **อย่าตั้ง `root` ไปที่ `/opt/pos-mobile`** (จะเผย `.git/`, `backend/.env`, `backup/`; กฎ deny ใน `nginx.conf` เป็นแค่ชั้นป้องกันซ้อน) และ proxy `/api/` ไป `127.0.0.1:8000` — ใช้ `nginx.conf` เป็นแม่แบบได้ (เปลี่ยน `proxy_pass` เป็น `http://127.0.0.1:8000` และเพิ่ม TLS ตาม [4.3](#43-วาง-tls-ไว้ข้างหน้า-แนะนำ))

### 6.2 Termux บน Android

ขั้นตอนติดตั้ง Termux อยู่ใน [USER_GUIDE.md → วิธีที่ 2](../USER_GUIDE.md#วิธีที่-2-รันในเครื่อง-termuxandroid---แนะนำสำหรับการใช้งานจริง) ข้อควรรู้เพิ่มเติมก่อนใช้จริง:

| เรื่อง | รายละเอียด | ทางแก้ |
|--------|-----------|-------|
| path ถูก hardcode | `start_termux.sh` บรรทัด 6: `BACKEND_DIR="/data/data/com.termux/files/home/projects/pos-mobile/backend"` — แต่ USER_GUIDE ให้ clone ไว้ที่ `~/pos-mobile` | clone ไว้ที่ `~/projects/pos-mobile` หรือแก้ `BACKEND_DIR` ในสำเนาของสคริปต์ |
| ไม่ได้รัน alembic | สคริปต์เรียก `init_db()` (บรรทัด 48–52) แทน `alembic upgrade head` → แอปใช้งานได้ (`init_db()` สร้างร้าน id=1 ให้) แต่ DB ไม่มี `alembic_version` ทำให้ `alembic upgrade head` ภายหลังล้มด้วย `table ... already exists` | รัน `alembic upgrade head` เองหนึ่งครั้งใน `backend/` ก่อนรันสคริปต์ครั้งแรก |
| `.env` จาก example | ถ้าไม่มี `.env` จะ `cp .env.example .env` (บรรทัด 41–44) ซึ่งมี `DEBUG=true` และ DB ที่ `./pos_mobile.db` | แก้ `.env` เป็น `DEBUG=false` |
| ติดตั้ง dependency ทุกครั้ง | `pip install -r requirements.txt` ทุกครั้งที่เริ่ม (ต้องมีเน็ต/ช้า) | รับได้ หรือสร้างสคริปต์เริ่มแบบสั้นที่ `source venv/bin/activate && exec python run.py` |
| ระบบปิด process เบื้องหลัง | Android อาจ kill Termux | `termux-wake-lock`, ปิด battery optimization ให้ Termux |
| เครื่องอื่นในร้าน | เข้า `http://<IP มือถือ>:8000` ได้ แต่ไม่ใช่ secure context | ใช้บนเครื่องเดียวกันผ่าน `localhost` หรือทำ TLS ตาม [หัวข้อ 4](#4-https-และ-reverse-proxy) |

---

## 7. Backup และ Restore

มีข้อมูล **3 แหล่ง** ที่ต้องสำรองแยกกัน และรูปแบบไฟล์ **ใช้แทนกันไม่ได้**:

| แหล่ง | วิธีสำรอง | รูปแบบ | กู้คืนด้วย |
|------|----------|--------|-----------|
| SQLite บนเซิร์ฟเวอร์ (ทั้งไฟล์) | คัดลอกไฟล์ `pos_mobile.db` (7.2) | SQLite | วางไฟล์คืน |
| SQLite บนเซิร์ฟเวอร์ (JSON ดิบ) | `docker compose --profile backup run --rm backup` (2.5) | `{timestamp, version, data:{<ตาราง>:[...]}}` | ไม่มีเครื่องมือ restore |
| ข้อมูลร้าน 1 ร้านบนเซิร์ฟเวอร์ | `GET /api/v1/sync/backup` (7.3) | `{timestamp, version, data:{products, sales, ...}}` (snake_case) | `POST /api/v1/sync/restore` (ทั้งไฟล์หรือเฉพาะ `data`) |
| ข้อมูลในเบราว์เซอร์ (ร้านที่เลือกอยู่) | ตั้งค่า → "สำรองข้อมูลทั้งหมด" (7.4) | `{products, sales, holdBills, billCounter, categoryMapping, ...}` (camelCase) | ตั้งค่า → "กู้คืนข้อมูล" |

### 7.1 Compose backup profile

ดู [2.5](#25-backup-profile)

### 7.2 สำรองไฟล์ SQLite ทั้งไฟล์ (แนะนำสำหรับ disaster recovery)

ได้ครบทุกตารางรวม `stores`, `users`, `api_keys` — ใช้ backup API ของ `sqlite3` ใน Python (มีใน image อยู่แล้ว) เพื่อให้ได้สำเนาที่สอดคล้องกันแม้ backend กำลังทำงาน

> 🔒 ไฟล์นี้มี **password hash ของผู้ใช้ทุกคน, hash ของ API key และ refresh token** — เก็บไว้ **นอก repo และนอก web root ใด ๆ** (ตัวอย่างใช้ `/var/backups/pos-mobile` สิทธิ์ `700`) ห้ามวางไว้ใน `./backup` หรือโฟลเดอร์ที่มีการเสิร์ฟผ่านเว็บ ถ้าส่งออกนอกเครื่องควรเข้ารหัส

```bash
sudo install -d -m 700 /var/backups/pos-mobile
docker compose exec backend python -c "import sqlite3; s=sqlite3.connect('/data/pos_mobile.db'); d=sqlite3.connect('/data/pos_mobile.snapshot.db'); s.backup(d); d.close(); s.close()"
sudo docker compose cp backend:/data/pos_mobile.snapshot.db /var/backups/pos-mobile/pos_mobile_$(date +%Y%m%d_%H%M%S).db
docker compose exec backend rm /data/pos_mobile.snapshot.db
```

กู้คืน:

```bash
docker compose stop backend
sudo docker compose cp /var/backups/pos-mobile/pos_mobile_YYYYMMDD_HHMMSS.db backend:/data/pos_mobile.db
docker compose start backend     # alembic upgrade head จะรันให้อัตโนมัติถ้าไฟล์เป็น revision เก่า
```

### 7.3 API `/api/v1/sync/backup` และ `/restore`

ทั้งสอง endpoint ทำงาน **เฉพาะร้านของผู้ใช้ปัจจุบัน** (`get_current_store`) — ถ้า `AUTH_ENABLED=true` ต้องแนบ `Authorization: Bearer <token>` หรือ `X-API-Key`

```bash
# สำรอง
curl -H "Authorization: Bearer $TOKEN" \
  https://pos.example.com/api/v1/sync/backup > store_backup_$(date +%Y%m%d).json

# กู้คืน — ส่งเฉพาะ object "data" (ต้องมี jq)
jq '.data' store_backup_20261030.json | \
  curl -X POST https://pos.example.com/api/v1/sync/restore \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @-
```

`/restore` รับได้ทั้งไฟล์จาก `GET /api/v1/sync/backup` ทั้งก้อน (`{timestamp, version, data:{...}}` — โค้ดจะแกะ `data` ให้) และ object `data` ด้านในโดยตรง ถ้า payload ไม่มี section ของ backup เลย (เช่น `{}` หรือไฟล์ผิดชนิด) จะตอบ **400 และไม่ลบข้อมูล** (`app/services/sync_service.py`, `restore_backup`)

> ⚠️ ตัวอย่าง restore ใน [USER_GUIDE.md](../USER_GUIDE.md#restore-กู้คืนข้อมูล) ใช้ `curl ... -d @backup_20240115.json` ซึ่ง **ส่งไฟล์ทั้งก้อน** — ใช้ได้กับโค้ดปัจจุบัน แต่เซิร์ฟเวอร์ที่ยังรันโค้ดก่อน commit `7ab1281` จะข้าม key `timestamp`/`version`/`data` แล้วมองทุกรายการเป็นลิสต์ว่าง ผลคือ **ลบข้อมูลของร้านทิ้งทั้งหมดแล้วไม่กู้อะไรกลับมา** ถ้าไม่แน่ใจว่าเซิร์ฟเวอร์เป็นเวอร์ชันไหน ให้ส่ง `.data` ตามตัวอย่างข้างบน ซึ่งปลอดภัยทุกเวอร์ชัน

พฤติกรรม `/restore`: validate ก่อน → snapshot ข้อมูลเดิม → ลบข้อมูลของร้านนั้น → เขียนใหม่ (คงเลขบิลเดิมถ้ายังว่าง) → ถ้าล้มกลางทางจะย้อน snapshot กลับ (400 = ไฟล์ผิดรูป ข้อมูลเดิมไม่ถูกแตะ)

### 7.4 สำรองข้อมูลในเบราว์เซอร์ (frontend JSON)

- ปุ่ม "สำรองข้อมูลทั้งหมด" (`exportBackupJSON` ใน `script-pos.js` บรรทัด ~1759) **ดาวน์โหลดไฟล์ลงเครื่อง** `qpos-backup-<ชื่อร้าน>-<วันที่>.json` — ไม่ได้ส่งขึ้นเซิร์ฟเวอร์
- สำรองเฉพาะ **ร้านที่เลือกอยู่** — ถ้ามีหลายร้านในเครื่อง ต้องสลับร้านแล้วกดสำรองทีละร้าน
- "กู้คืนข้อมูล" (`importBackupJSON`) แทนที่ข้อมูลของร้านปัจจุบันในเครื่องทั้งหมด
- รูปแบบเป็น camelCase (`holdBills`, `categoryMapping`, `billCounter`) **ใช้กับ `/api/v1/sync/restore` ไม่ได้** และกลับกันก็ไม่ได้
- การล้างข้อมูลเบราว์เซอร์ / ถอนการติดตั้ง PWA / เปลี่ยนโดเมน (origin ใหม่ = localStorage ใหม่) ทำให้ข้อมูลหาย → **ย้ายโดเมน/พอร์ตตอน deploy ต้องให้ร้านสำรอง JSON จาก origin เดิมก่อน แล้วกู้คืนที่ origin ใหม่**

---

## 8. ออกเวอร์ชันใหม่ของ Frontend (Service Worker)

`sw.js` ใช้กลยุทธ์ **cache-first** สำหรับไฟล์ static ทุกตัว (ยกเว้น `/api/`) และ precache `./`, `index.html`, `script-pos.js`, `style-pos.css`, `manifest.json` ภายใต้ชื่อ `CACHE_NAME` (ปัจจุบัน `pos-mobile-v3`)

ผลคือ: **ถ้าไม่เปลี่ยน `CACHE_NAME` เครื่องที่ติดตั้งแล้วจะใช้ไฟล์เก่าตลอดไป** แม้เซิร์ฟเวอร์มีไฟล์ใหม่

ทุกครั้งที่แก้ `index.html`, `script-pos.js`, `style-pos.css`, `manifest.json` หรือไฟล์ใน `icons/`:

```js
// sw.js
const CACHE_NAME = 'pos-mobile-v4';   // ← เพิ่มเลขทุก release ที่มีไฟล์ frontend เปลี่ยน
```

แล้ว build image frontend ใหม่บนเซิร์ฟเวอร์ (ไฟล์ถูก copy เข้า image ตอน build ไม่ได้ mount จาก repo):

```bash
git pull
docker compose build frontend && docker compose up -d frontend
```

> ถ้าเพิ่มไฟล์ frontend ใหม่ (เช่นไฟล์ JS/CSS ใหม่) ต้องเพิ่มบรรทัด `COPY` ใน `nginx.Dockerfile` ด้วย ไม่เช่นนั้นไฟล์จะไม่อยู่ใน image (และถ้าต้องการให้ใช้ออฟไลน์ ให้เพิ่มใน `ASSETS` ของ `sw.js`)

เมื่อผู้ใช้เปิดแอปครั้งถัดไป เบราว์เซอร์จะเห็น `sw.js` เปลี่ยน → `install` cache ใหม่ (`skipWaiting`) → `activate` ลบ cache เก่าและ `clients.claim()` → **โหลดหน้าใหม่อีกครั้ง** ถึงจะเห็นเวอร์ชันใหม่

ทำไมไฟล์ที่ได้จึงเป็นชุดเดียวกันเสมอ (ไม่มี `index.html` ใหม่คู่กับ `script-pos.js` เก่า):

- `nginx.conf` ส่ง `sw.js` ด้วย `location = /sw.js` (exact match) แบบ `no-cache, no-store` → เบราว์เซอร์เห็น `CACHE_NAME` ใหม่ทันที
- `.js`/`.css` ได้ `Cache-Control: no-cache` (revalidate ทุกครั้ง) แทน cache 1 ปี (ดู [4.2](#42-สิ่งที่-nginxconf-ทำอยู่ตอนนี้))
- ตอน `install` `sw.js` precache ด้วย `new Request(url, { cache: 'reload' })` ซึ่งข้าม HTTP cache ของเบราว์เซอร์ → cache ชุดใหม่ถูกเติมด้วยไฟล์ที่อยู่บนเซิร์ฟเวอร์ขณะนั้นเสมอ

แต่ service worker ยังเป็น **cache-first** — การ revalidate ข้างบนไม่ได้ทำให้เครื่องที่ติดตั้งแล้วโหลดไฟล์ใหม่เอง **ยังต้อง bump `CACHE_NAME` ทุก release ที่ไฟล์ frontend เปลี่ยน** ไม่เช่นนั้นเครื่องเดิมจะใช้ชุดเก่าใน cache ต่อไป

> ⚠️ อย่าแนะนำให้ผู้ใช้ "ล้างข้อมูลเว็บไซต์" เพื่อแก้หน้าเก่า — ข้อมูลร้านทั้งหมด (สินค้า, การขาย, ลูกหนี้) อยู่ใน `localStorage` ของเบราว์เซอร์นั้นเท่านั้น การล้างข้อมูลเว็บไซต์จะลบข้อมูลทิ้งด้วย ถ้าผู้ใช้ยังเห็นหน้าเก่า ให้ตรวจว่า bump `CACHE_NAME` แล้วและ image frontend ถูก build ใหม่ ([10.2](#102-การแก้ไขปัญหา)) จากนั้นให้ปิดแท็บ/แอปทั้งหมดแล้วเปิดใหม่ (หรือโหลดหน้าใหม่สองครั้ง)

---

## 9. CI/CD (GitHub Actions)

ไฟล์: `.github/workflows/ci-cd.yml` — ทำงานเมื่อ push ไป `main`/`develop`, เปิด PR เข้า `main`, หรือสั่งเอง (`workflow_dispatch`)

| Job | เงื่อนไข | ทำอะไร |
|-----|---------|-------|
| `test-backend` | ทุก event | Python 3.12, `pip install -r requirements.txt` + pytest, รัน `pytest tests/ --cov=app` ใน `backend/` (DB ทดสอบเป็น in-memory ใน `tests/conftest.py`), อัปโหลด coverage ไป Codecov (`fail_ci_if_error: false`) |
| `lint-frontend` | ทุก event | `node --check script-pos.js`; `tidy` และ `stylelint` จะถูกข้ามถ้าไม่มีใน runner (ปกติไม่มี) |
| `build` | push / workflow_dispatch (ไม่รันบน PR) | build + push 2 image ไป GHCR: `ghcr.io/<owner>/<repo>-backend` (context `./backend` → `backend/Dockerfile`) และ `ghcr.io/<owner>/<repo>-frontend` (`nginx.Dockerfile`), tag ตาม branch, `<branch>-<sha>`, และ `latest` บน default branch |
| `deploy-staging` | branch `develop`, environment `staging` | **มีแค่ `echo`** — ยังไม่ได้ deploy จริง |
| `deploy-production` | branch `main`, environment `production` | **มีแค่ `echo`** — ยังไม่ได้ deploy จริง |

Secrets / การตั้งค่าที่ต้องมี:

| รายการ | จำเป็น | หมายเหตุ |
|--------|-------|---------|
| `GITHUB_TOKEN` | ✅ (อัตโนมัติ) | ใช้ login GHCR, job `build` ขอ `packages: write` แล้ว |
| GitHub Environments `staging`, `production` | ✅ | สร้างใน Settings → Environments; ใส่ required reviewers ให้ `production` เพื่อให้ต้องอนุมัติก่อน |
| `CODECOV_TOKEN` | ไม่บังคับ | workflow ไม่ได้ส่ง token ให้ codecov-action — repo private อาจอัปโหลดไม่สำเร็จ (แต่ไม่ทำให้ CI ล้ม) |
| secret สำหรับ deploy (เช่น SSH key/host) | เมื่อจะเติม step deploy | ยังไม่มีการอ้างถึงใน workflow |

ข้อควรรู้:
- `docker-compose.yml` **ไม่ได้ใช้ image จาก GHCR** (ทั้ง backend และ frontend ใช้ `build:` — frontend build จาก `nginx.Dockerfile` ตัวเดียวกับที่ CI ใช้) ถ้าจะ deploy ด้วย image ที่ CI build ต้องมี compose/override ที่ใช้ `image: ghcr.io/...` เอง
- image frontend จาก `nginx.Dockerfile` ใช้ `nginx.conf` ที่ `proxy_pass http://backend:8000` — ต้องรันใน network เดียวกับ container ที่ชื่อ/alias `backend` ไม่เช่นนั้น nginx จะไม่ start (`host not found in upstream`)
- `Dockerfile` ที่ root (python:3.11, รันเป็น root, ไม่รัน alembic) **ไม่ได้ถูกใช้** ทั้งใน compose และ CI

---

## 10. Checklist ก่อน Deploy และการแก้ไขปัญหา

### 10.1 Checklist ก่อน Deploy

**ความปลอดภัย**
- [ ] `AUTH_ENABLED=true` และตั้ง `JWT_SECRET` แบบสุ่ม (ไม่ใช่ `dev-secret-change-in-production`)
- [ ] สมัคร admin คนแรกด้วย `"role":"admin"` ทันทีหลังเปิดระบบ และไม่มีบัญชี `dev@local` ค้างอยู่
- [ ] `DEBUG=false`
- [ ] `CORS_ORIGINS` มีเฉพาะ origin จริง (ไม่มี `"null"`, `"file://"`)
- [ ] พอร์ต `8000` ไม่เปิดออกอินเทอร์เน็ต (bind `127.0.0.1` หรือ firewall)
- [ ] ใช้ `docker-compose.yml` ตั้งแต่ commit `8eb6ef5` ขึ้นไป (frontend build จาก `nginx.Dockerfile` ไม่มี bind mount) — ตรวจว่า repo ไม่ถูกเสิร์ฟ: `curl -s -o /dev/null -w '%{http_code}\n' https://pos.example.com/.git/config` และ `.../backend/.env` ต้องได้ `404`
- [ ] ไฟล์ backup (JSON และ `.db`) อยู่นอก repo/นอก web root และสิทธิ์ `700` ([2.5](#25-backup-profile), [7.2](#72-สำรองไฟล์-sqlite-ทั้งไฟล์-แนะนำสำหรับ-disaster-recovery))
- [ ] ไม่มี `backend/.env` หรือไฟล์ `.db` อยู่ใน `backend/` ตอน build image

**ข้อมูล**
- [ ] `DATABASE_URL` เป็น absolute path อยู่บน volume/ดิสก์ที่ถาวร
- [ ] `alembic upgrade head` สำเร็จ (`alembic current` = `003 (head)`)
- [ ] ตั้ง backup อัตโนมัติ + retention และ **ลองกู้คืนจริง** อย่างน้อยหนึ่งครั้ง
- [ ] ถ้าย้ายโดเมน/พอร์ต: แจ้งทุกร้านให้สำรอง JSON จากเบราว์เซอร์ก่อน

**Frontend / HTTPS**
- [ ] เข้าผ่าน `https://` ได้ certificate ถูกต้อง
- [ ] bump `CACHE_NAME` ใน `sw.js` ถ้าไฟล์ frontend เปลี่ยน
- [ ] `curl -f https://pos.example.com/api/v1/sync/health` ได้ `{"status":"healthy",...}`
- [ ] ทดสอบสแกนบาร์โค้ดด้วยกล้องบนมือถือจริง และติดตั้ง PWA ได้

### 10.2 การแก้ไขปัญหา

| อาการ | สาเหตุ | วิธีแก้ |
|-------|--------|--------|
| `404 Store not found for current user` | ไม่มีร้านที่ตรงกับ `store_id` ของผู้ใช้ (เช่น DB ที่สร้างด้วยโค้ดก่อน `7ab1281` ซึ่ง `init_db()` ไม่สร้างร้าน หรือร้านถูกลบ) | อัปเดตโค้ดแล้วรีสตาร์ท (`init_db()` จะสร้างร้าน id=1 ถ้าตาราง `stores` ว่าง); ถ้ามีร้านอื่นอยู่แต่ไม่มี id ที่ผู้ใช้อ้างถึง ให้แก้ `store_id` ของ user ผ่าน API/DB |
| `alembic upgrade head` ล้ม `table products already exists` | DB ถูกสร้างด้วย `init_db()` (`create_all`) มาก่อน ไม่มีตาราง `alembic_version` | สำรอง DB ก่อน แล้ว `alembic stamp head` (ถ้า schema ตรงกับ model ปัจจุบัน) |
| `git pull` แล้วหน้าเว็บไม่เปลี่ยน | ไฟล์ frontend และ `nginx.conf` ถูก copy เข้า image ตอน build | `docker compose build frontend && docker compose up -d frontend` (และ bump `CACHE_NAME`) |
| ไฟล์ frontend ใหม่ตอบ 404 / หน้า index แทน | ไฟล์ไม่ได้อยู่ในรายการ `COPY` ของ `nginx.Dockerfile` | เพิ่ม `COPY` แล้ว build ใหม่ |
| backend ไม่ start: `ValueError: JWT_SECRET must be set when AUTH_ENABLED=true` | เปิด auth แต่ไม่มี `JWT_SECRET` ใน **environment** | ตั้งใน compose `environment:`, `EnvironmentFile`, หรือ `backend/.env` + เริ่มด้วย `python run.py` (ไม่ใช่ `uvicorn` ตรง ๆ) |
| `403 Registration requires admin privileges` ตอนสมัครคนแรก | มี user อยู่แล้ว (มักเป็น `dev@local` ที่ถูกสร้างตอนปิด auth) | ล็อกอินด้วยบัญชีนั้นแล้วสร้าง/ปรับ user ผ่าน `/api/v1/auth/users`, เปลี่ยนรหัส/ปิดบัญชี dev |
| `docker compose --profile backup run --rm backup` → `PermissionError: '/backup/...'` | image รันเป็น `posuser` แต่ `./backup` เป็นของ root | สร้างโฟลเดอร์ปลายทางก่อน (แนะนำนอก repo ตาม [2.5](#25-backup-profile)) แล้ว `sudo chown $(docker compose run --rm --no-deps backup id -u) <โฟลเดอร์>` หรือเพิ่ม `user: "0"` ให้ service `backup` ใน override |
| backup → `sqlite3.OperationalError: unable to open database file` | ยังไม่มี `/data/pos_mobile.db` (backend ยังไม่เคยเริ่ม) หรือ `DB_PATH` ผิด | เริ่ม `backend` ก่อนหนึ่งครั้ง / ตั้ง `DB_PATH` |
| backup → `no such table: ...` | DB ยังไม่ถูก migrate ครบ | `docker compose exec backend alembic upgrade head` |
| หลัง `/restore` ข้อมูลร้านหายหมด | เซิร์ฟเวอร์รันโค้ดก่อน `7ab1281` และส่งไฟล์จาก `/backup` ทั้งก้อน (เหมือนตัวอย่างใน USER_GUIDE.md) แทนที่จะส่ง `.data` | กู้จากไฟล์ SQLite/สำรองอื่น — ครั้งต่อไปใช้ `jq '.data'` ตาม [7.3](#73-api-apiv1syncbackup-และ-restore) |
| แถบสถานะขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" | `HEAD /api/v1/sync/health` ได้ 5xx หรือ network error (nginx ส่งต่อไม่ถึง backend) | `docker compose ps`, `docker compose logs backend`, `curl -I http://localhost:8080/api/v1/sync/health` |
| กล้องสแกนไม่ทำงาน / ติดตั้ง PWA ไม่ได้ | เข้าผ่าน `http://<IP>` ไม่ใช่ secure context | ใช้ HTTPS ตาม [หัวข้อ 4](#4-https-และ-reverse-proxy) |
| deploy แล้วผู้ใช้ยังเห็นหน้าเก่า | ไม่ได้ bump `CACHE_NAME` (service worker เป็น cache-first) หรือไม่ได้ build image frontend ใหม่ | bump `CACHE_NAME` ใน `sw.js` แล้ว `docker compose build frontend && docker compose up -d frontend`; ตรวจด้วย `curl -sI https://pos.example.com/sw.js` ว่าได้ `Cache-Control: no-cache, no-store, must-revalidate` และ `/script-pos.js` ได้ `Cache-Control: no-cache` จากนั้นให้ผู้ใช้ปิดแอปทุกแท็บแล้วเปิดใหม่ — **ห้ามล้างข้อมูลเว็บไซต์** (ข้อมูลร้านอยู่ใน `localStorage`, ดู [8](#8-ออกเวอร์ชันใหม่ของ-frontend-service-worker)) |
| WebSocket ต่อไม่ติดผ่านพอร์ต 8080 | `nginx.conf` ไม่ส่ง `Upgrade`/`Connection` และไม่ proxy `/ws` | ต่อพอร์ต 8000 ตรง หรือเพิ่ม location ตาม [4.3](#43-วาง-tls-ไว้ข้างหน้า-แนะนำ) |
| CORS error ในเบราว์เซอร์ | origin ของหน้าเว็บไม่อยู่ใน `CORS_ORIGINS` | ใช้ origin เดียวกันผ่าน nginx `/api/` (ไม่ต้อง CORS) หรือเพิ่ม origin |
| `database is locked` | มีหลาย process เขียน SQLite พร้อมกัน (เช่น รัน backend ซ้อนสองตัว) | รัน backend instance เดียวต่อไฟล์ DB, หยุด process ที่ค้าง |
| nginx (image จาก `nginx.Dockerfile`) ไม่ start: `host not found in upstream "backend"` | ไม่มี container ชื่อ `backend` ใน network เดียวกัน | รันร่วมกับ backend ใน network เดียวกัน (ตั้ง alias `backend`) |
| `start_termux.sh` → `Backend directory not found` | path hardcode `~/projects/pos-mobile/backend` | ย้าย clone หรือแก้ `BACKEND_DIR` ([6.2](#62-termux-บน-android)) |
| `docker compose` เตือน `the attribute version is obsolete` | `version: '3.8'` ใน `docker-compose.yml` | ไม่มีผลต่อการทำงาน (เอาบรรทัดออกได้) |

---

## 📚 เอกสารที่เกี่ยวข้อง

- [README.md](../README.md) — ภาพรวม, โครงสร้างไฟล์, docker compose แบบเร็ว
- [USER_GUIDE.md](../USER_GUIDE.md) — คู่มือการใช้งานหน้าร้าน, ติดตั้ง Termux
- [backend/README.md](../backend/README.md) — endpoints, WebSocket, environment variables, การรันเทสต์
