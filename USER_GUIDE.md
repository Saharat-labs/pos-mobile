# 📖 POS-MOBILE - คู่มือการใช้งานฉบับสมบูรณ์

> ระบบขายหน้าร้าน (Point of Sale) สำหรับมือถือ — ทำงานในเบราว์เซอร์ 100% + Backend API สำหรับซิงค์ข้อมูล

---

## 📋 สารบัญ

1. [ภาพรวมระบบ](#ภาพรวมระบบ)
2. [การติดตั้งและเริ่มต้น](#การติดตั้งและเริ่มต้น)
3. [Frontend (POS บนเบราว์เซอร์)](#frontend-pos-บนเบราว์เซอร์)
4. [Backend API (ฐานข้อมูลกลาง)](#backend-api-ฐานข้อมูลกลาง)
5. [การซิงค์ข้อมูล (Sync/Backup)](#การซิงค์ข้อมูล-syncbackup)
6. [หน้าจอหลักและฟีเจอร์](#หน้าจอหลักและฟีเจอร์)
7. [คีย์บอร์ดและปุ่มลัด](#คีย์บอร์ดและปุ่มลัด)
8. [การแก้ไขปัญหา](#การแก้ไขปัญหา)

---

## 🎯 ภาพรวมระบบ

```
┌─────────────────────────────────────────────────────────────┐
│                    POS-MOBILE SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (เบราว์เซอร์)          Backend (Termux/Server)    │
│  ┌─────────────────────┐         ┌─────────────────────┐   │
│  │ index.html          │ ◄─────► │ FastAPI + SQLite    │   │
│  │ script-pos.js       │  Sync   │ Port 8000           │   │
│  │ style-pos.css       │         │ pos_mobile.db       │   │
│  └─────────────────────┘         └─────────────────────┘   │
│         ▲                                  ▲                │
│         │ localStorage                     │                │
│         │ (Offline-first)                  │                │
│         ▼                                  ▼                │
│  📱 ใช้งานบนมือถือ/แท็บเล็ต         💾 เก็บข้อมูลถาวร      │
└─────────────────────────────────────────────────────────────┘
```

**จุดเด่น:**
- ✅ **Offline-first** - ใช้งานได้โดยไม่ต้องอินเทอร์เน็ต
- ✅ **Mobile-first** - UI ปรับตัวสำหรับมือถือ
- ✅ **No backend required** - Frontend ทำงานได้เอง
- ✅ **Sync เมื่อต้องการ** - สำรอง/กู้คืนข้อมูลได้ทุกเมื่อ
- ✅ **ฟรี 100%** - ไม่มีค่าใช้จ่ายรายเดือน

---

## 🚀 การติดตั้งและเริ่มต้น

### วิธีที่ 1: ใช้งานออนไลน์ (ง่ายที่สุด)
```
🌐 เปิด: https://saharatyokthuan.github.io/pos-mobile/
```
*ไม่ต้องติดตั้งอะไร ใช้งานได้ทันที*

---

### วิธีที่ 2: รันในเครื่อง (Termux/Android) - แนะนำสำหรับการใช้งานจริง

#### ข้อกำหนดเบื้องต้น
- Android 7.0+
- Termux app (จาก F-Droid หรือ GitHub)
- พื้นที่ว่าง ~500MB

#### ขั้นตอนติดตั้ง

```bash
# 1. ติดตั้ง Termux จาก F-Droid (แนะนำ) หรือ GitHub Releases
# ไม่ใช้ Play Store version (เก่าเกินไป)

# 2. อัปเดตแพ็กเกจ
pkg update && pkg upgrade -y

# 3. ติดตั้ง dependencies
pkg install -y git python nodejs-lts nginx

# 4. Clone โปรเจค
cd ~
git clone https://github.com/saharatyokthuan/pos-mobile.git
cd pos-mobile

# 5. เริ่ม Backend (รันค้างพื้นหลัง)
cd backend
chmod +x start_termux.sh
./start_termux.sh &
# หรือรันใน tmux/screen เพื่อให้ค้างอยู่

# 6. เปิด Frontend
# วิธี A: เปิดไฟล์โดยตรง
termux-open index.html

# วิธี B: ผ่าน nginx (แนะนำสำหรับ barcode scanner)
# ตั้งค่า nginx ให้ serve โฟลเดอร์ pos-mobile
```

#### ตั้งค่า Nginx (สำหรับ Barcode Scanner HTTPS)
```nginx
# ~/.termux/files/usr/etc/nginx/nginx.conf
server {
    listen 8080;
    server_name localhost;
    root /data/data/com.termux/files/home/pos-mobile;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
}
```
```bash
nginx -c ~/.termux/files/usr/etc/nginx/nginx.conf
# เปิด http://localhost:8080
```

---

### วิธีที่ 3: รันบนคอมพิวเตอร์ (Windows/Mac/Linux)

```bash
# 1. Clone
git clone https://github.com/saharatyokthuan/pos-mobile.git
cd pos-mobile

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py

# 3. Frontend - เปิด index.html ในเบราว์เซอร์
# หรือใช้ VS Code Live Server extension
```

---

## 📱 Frontend (POS บนเบราว์เซอร์)

### 🏠 เมนูหลัก (Sidebar)
กดปุ่ม **☰** มุมซ้ายบน เพื่อเปิดเมนู

| เมนู | ไอคอน | คำอธิบาย |
|-----|-------|----------|
| **ขายสินค้า** | 🛒 | หน้าขายหลัก - สแกน/ค้นหา/เพิ่มตะกร้า/ชำระเงิน |
| **สินค้า** | 📦 | จัดการสินค้า - เพิ่ม/แก้ไข/ค้นหา/สต๊อก |
| **สั่งซื้อ** | 🚚 | สั่งซื้อจากผู้จำหน่าย - PO/รับเข้า |
| **ลูกหนี้** | 💳 | จัดการลูกค้าซื้อเชื่อ - บันทึก/รับชำระ |
| **รายงาน** | 📊 | ยอดขาย/สต๊อก/รายจ่าย - กราฟ/Export Excel |
| **เพิ่มเติม/ตั้งค่า** | ⚙️ | ตั้งค่าร้าน/สำรองข้อมูล/นำเข้า-ส่งออก |

---

### 🛒 หน้าขายสินค้า (POS)

#### ค้นหาสินค้า
```
1. พิมพ์ชื่อ/รหัส/บาร์โค้ด ในช่องค้นหา
2. กด Enter หรือกดปุ่ม 📷 สแกนบาร์โค้ด
3. สินค้าจะปรากายในกริดด้านล่าง
```

#### เพิ่มสินค้าลงตะกร้า
```
- กดที่สินค้า 1 ครั้ง = เพิ่ม 1 ชิ้น
- กดค้าง (Long press) = เลือกจำนวน/ราคา/ส่วนลด
- สินค้าในตะกร้าจะแสดงด้านขวา/ล่าง
```

#### การชำระเงิน
```
1. ตรวจสอบตะกร้า ให้ถูกต้อง
2. กดปุ่ม "ชำระเงิน" (สีเขียว)
3. เลือกวิธีชำระ:
   💵 เงินสด - พิมพ์จำนวนเงินได้ → คำนวณเงินทอนอัตโนมัติ
   🏦 โอนเงิน - ใส่เลขที่อ้างอิง
   💳 บัตร - ใส่เลขที่อ้างอิง
   📝 เชื่อ - ลูกค้าจะเป็นลูกหนี้
4. กด "ยืนยันชำระ" → พิมพ์ใบเสร็จ/บันทึก
```

#### ฟีเจอร์พิเศษ
| ฟีเจอร์ | วิธีใช้ |
|---------|--------|
| **พักบิล** | กด "พักบิล" → ใส่ชื่อบิล → เรียกคืนได้จากเมนู "บิลพัก" |
| **ขายเชื่อ** | เลือกชำระ "เชื่อ" → ระบบสร้างลูกหนี้อัตโนมัติ |
| **ส่วนลด** | กดที่สินค้าในตะกร้า → ใส่ % หรือ จำนวนเงิน |
| **VAT 7%** | เปิด/ปิดได้ในหน้าตั้งค่า |
| **คีย์แพดเงินทอน** | หน้าชำระเงินสดมีคีย์แพดคำนวณเงินทอน |

---

### 📦 หน้าจัดการสินค้า

#### เพิ่มสินค้าใหม่
```
1. กดปุ่ม "+" หรือ "เพิ่มสินค้า"
2. กรอกข้อมูล:
   - รหัสสินค้า * (บังคับ, ซ้ำไม่ได้)
   - บาร์โค้ด (สแกนได้)
   - ชื่อสินค้า *
   - หมวดหมู่
   - หน่วย (ชิ้น/กล่อง/กก./ลิตร)
   - ราคาขาย *
   - ต้นทุน
   - สต๊อกเริ่มต้น
   - สต๊อกขั้นต่ำ (เตือนเมื่อใกล้หมด)
   - วันหมดอายุ (ถ้ามี)
3. กด "บันทึก"
```

#### แก้ไขสินค้า
```
- กดที่แถวสินค้า → เลือก "แก้ไข"
- หรือกดค้าง → เมนู context menu
```

#### ค้นหา/กรอง
```
- ช่องค้นหา: ชื่อ/รหัส/บาร์โค้ด
- ตัวกรองหมวดหมู่: เลือกหมวด
- ตัวกรองสต๊อก: ทุกประเภท / มีสต๊อก / ใกล้หมด / หมดแล้ว
```

#### เพิ่มจากรายการสินค้ากลาง (Master Products)
```
1. กด "📋 เพิ่มจากรายการสินค้ากลาง"
2. ค้นหาจากรายการที่เตรียมไว้
3. กดเลือก → ข้อมูลจะ auto-fill (ชื่อ, หมวดหมู่, ราคา)
4. แก้ไขรหัส/ราคาตามต้องการ → บันทึก
```
> ⚠️ ต้องมีไฟล์ `master-products.js` วางข้าง `index.html` (ไม่รวมใน repo)

#### นำเข้า/ส่งออก Excel
```
📥 นำเข้า: กด "นำเข้าสินค้า" → เลือกไฟล์ .xlsx
📤 ส่งออก: กด "ส่งออกสินค้า" → ได้ไฟล์ .xlsx
```

---

### 🚚 หน้าสั่งซื้อ (Purchase Orders)

```
1. กด "+ สั่งซื้อใหม่"
2. เลือก/เพิ่มผู้จำหน่าย
3. เพิ่มรายการสินค้า (ค้นหาจากฐานข้อมูล)
4. กด "บันทึก PO" → สถานะ "รอรับเข้า"
5. เมื่อสินค้ามา: เปิด PO → กด "รับเข้า" → ใส่จำนวนจริง → สต๊อกเพิ่มอัตโนมัติ
4. ส่งออก Excel: กด "Export Excel"
```

---

### 💳 หน้าลูกหนี้ (Debtors)

```
รายการลูกหนี้:
- แสดง: ชื่อ, โทรศัพท์, ยอดค้าง, สถานะ (เปิด/บางส่วน/ชำระแล้ว)

รับชำระหนี้:
1. กดที่ลูกค้า → "รับชำระ"
2. ใส่จำนวนเงิน (บางส่วน/เต็มจำนวน)
3. เลือกวิธีชำระ
4. บันทึก → ยอดค้างอัปเดตอัตโนมัติ
```

---

### 📊 หน้ารายงาน (Reports)

| แท็บ | เนื้อหา |
|------|---------|
| **ยอดขาย** | กราฟแท่งรายวัน, โดนัทตามหมวดหมู่, สินค้าขายดี, เปรียบเทียบช่วงเวลา |
| **สต๊อก** | สินค้าทั้งหมด, สต๊อกต่ำ, ใกล้หมดอายุ, มูลค่าสต๊อก |
| **รายจ่าย** | ตารางรายจ่าย, สรุปตามหมวดหมู่/เดือน |
| **ทั้งหมด** | Export Excel ทุกแท็บได้ |

#### ตัวกรองวันที่
```
- วันนี้ / สัปดาห์นี้ / เดือนนี้ / ปีนี้
- ช่วงวันที่กำหนดเอง
```

---

### ⚙️ หน้าตั้งค่า (Settings)

#### 📂 นำเข้า/ส่งออกข้อมูล
```
📤 ส่งออก Excel:
  - สินค้า, ยอดขาย, สต๊อก, สั่งซื้อ, รายจ่าย

📥 นำเข้า Excel:
  - Master Product (ชื่อ+หมวดหมู่+ราคา)
  - อัปเดตชื่อ/หมวดหมู่จากรหัส

💾 สำรอง/กู้คืน JSON:
  - "สำรองข้อมูลทั้งหมด" → ดาวน์โหลดไฟล์ .json
  - "กู้คืนข้อมูล" → เลือกไฟล์ .json → ยืนยัน (จะทับข้อมูลเดิม!)
```

#### 🏪 ข้อมูลร้าน/ตั้งค่าระบบ
```
- ชื่อร้าน, ที่อยู่, โทรศัพท์, ภาษี
- เปิด/ปิด VAT 7%
- เปิด/ปิดบาร์โค้ดสแกน
- ตั้งค่าพิมพ์ใบเสร็จ
- Mapping หมวดหมู่ตามรหัสสินค้า
```

---

## 🖥️ Backend API (ฐานข้อมูลกลาง)

### เริ่มต้น Backend

```bash
cd /root/projects/pos-mobile/backend
./start_termux.sh
```

**ค่าที่ได้:**
- API Server: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Database: `pos_mobile.db` (SQLite)

---

### API Endpoints สำคัญ

#### Products
```bash
# รายการสินค้า
GET  /api/v1/products?page=1&page_size=50&search=coffee&category=beverage

# สินค้าตัวเดียว
GET  /api/v1/products/1
GET  /api/v1/products/code/TEST001
GET  /api/v1/products/barcode/1234567890123

# สินค้าสต๊อกต่ำ
GET  /api/v1/products/low-stock

# สร้างสินค้า
POST /api/v1/products
{
  "code": "COF001",
  "name": "กาแฟอาราบิก้า",
  "category": "เครื่องดื่ม",
  "price": 45,
  "stock": 100
}

# ปรับสต๊อก
POST /api/v1/products/1/stock?quantity=10&movement_type=in&reference_type=purchase
```

#### Sales
```bash
# สร้างการขาย
POST /api/v1/sales
{
  "customer_name": "สมชาย ใจดี",
  "payment_method": "cash",
  "paid_amount": 500,
  "items": [
    {"product_id": 1, "product_code": "COF001", "product_name": "กาแฟ", "quantity": 2, "unit_price": 45, "line_total": 90}
  ]
}

# รายการขาย
GET /api/v1/sales?start_date=2024-01-01&end_date=2024-01-31

# สรุปยอดขายวันนี้
GET /api/v1/sales/summary/daily

# สินค้าขายดี
GET /api/v1/sales/summary/top-products?start_date=2024-01-01&end_date=2024-01-31
```

#### Sync/Backup (สำคัญ!)
```bash
# Sync จาก Frontend (localStorage) → Backend
POST /api/v1/sync
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

# Backup ทั้งหมด (ดาวน์โหลด JSON)
GET /api/v1/sync/backup

# Restore จาก backup
POST /api/v1/sync/restore
{ "data": { ...backup data... } }
```

---

## 🔄 การซิงค์ข้อมูล (Sync/Backup)

### ทำไมต้อง Sync?
- Frontend เก็บข้อมูลใน **localStorage** (อยู่ในเบราว์เซอร์)
- ถ้าล้าง cache/เปลี่ยนเบราว์เซอร์/โทรศัพท์เสีย → **ข้อมูลหายหมด**
- Backend ให้ **ฐานข้อมูลถาวร** + **Backup/Restore**

---

### วิธี Sync จาก Frontend

#### วิธีที่ 1: ผ่านหน้าตั้งค่า (GUI)
```
1. เปิดเมนู ☰ → "เพิ่มเติม/ตั้งค่า" (⚙️)
2. เลื่อนลงหา "💾 สำรองข้อมูลทั้งหมด"
3. กดปุ่ม → ระบบจะ POST ไป /api/v1/sync
4. รอผลสำเร็จ → ข้อมูลอยู่ใน Backend แล้ว
```

#### วิธีที่ 2: ผ่าน JavaScript Console (สำหรับนักพัฒนา)
```javascript
// เปิด Developer Tools (F12) → Console → วางโค้ดนี้:

async function syncAllData() {
    const data = {
        products: JSON.parse(localStorage.getItem('products') || '[]'),
        sales: JSON.parse(localStorage.getItem('sales') || '[]'),
        purchases: JSON.parse(localStorage.getItem('purchases') || '[]'),
        debts: JSON.parse(localStorage.getItem('debts') || '[]'),
        expenses: JSON.parse(localStorage.getItem('expenses') || '[]'),
        stockMovements: JSON.parse(localStorage.getItem('stockMovements') || '[]'),
        holdBills: JSON.parse(localStorage.getItem('holdBills') || '[]'),
        settings: JSON.parse(localStorage.getItem('settings') || '[]'),
        categoryMappings: JSON.parse(localStorage.getItem('categoryMappings') || '[]'),
    };
    
    const res = await fetch('http://localhost:8000/api/v1/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const result = await res.json();
    console.log('✅ Sync result:', result);
    alert(`Synced: ${JSON.stringify(result.counts)}`);
}

syncAllData();
```

---

### วิธี Backup/Restore

#### Backup (สำรองข้อมูล)
```bash
# ผ่าน API
curl http://localhost:8000/api/v1/sync/backup > backup_$(date +%Y%m%d).json

# ผ่านเบราว์เซอร์
# เปิด http://localhost:8000/api/v1/sync/backup → Save As .json
```

#### Restore (กู้คืนข้อมูล)
```bash
# ผ่าน API
curl -X POST http://localhost:8000/api/v1/sync/restore \
  -H "Content-Type: application/json" \
  -d @backup_20240115.json

# ⚠️ จะทับข้อมูลเดิมทั้งหมด!
```

---

## ⌨️ คีย์บอร์ดและปุ่มลัด

### Frontend (เบราว์เซอร์)
| ปุ่ม | ฟังก์ชัน |
|-----|----------|
| `Enter` | ค้นหา/ยืนยัน/เพิ่มสินค้า |
| `Escape` | ปิด Modal/Sidebar |
| `Ctrl+S` | บันทึก (ในฟอร์ม) |
| `F11` | โหมดเต็มจอ |
| `📷` | สแกนบาร์โค้ด (กล้อง) |
| `🖼️` | เลือกรูปบาร์โค้ด |

### Backend (Terminal)
| คำสั่ง | ฟังก์ชัน |
|--------|----------|
| `./start_termux.sh` | เริ่ม Backend (Termux) |
| `python run.py` | เริ่ม Backend (ทั่วไป) |
| `Ctrl+C` | หยุด Server |
| `tail -f uvicorn.log` | ดู Log |

---

## 🛠️ การพัฒนา/ปรับแต่ง (For Developers)

### โครงสร้างโปรเจค
```
pos-mobile/
├── index.html           # Frontend: หน้าเว็บหลัก (single-page)
├── script-pos.js        # Frontend: Logic ทั้งหมด (~1800 บรรทัด)
├── style-pos.css        # Frontend: Theme, responsive, print
├── backend/
│   ├── app/
│   │   ├── main.py      # FastAPI entry point
│   │   ├── config.py    # Settings
│   │   ├── database.py  # SQLite + SQLAlchemy
│   │   ├── models/      # 13 Database models
│   │   ├── schemas/     # Pydantic validation
│   │   ├── services/    # 9 Business logic services
│   │   └── api/         # 9 REST API routers
│   ├── start_termux.sh  # Termux startup script
│   ├── run.py           # Python run script
│   └── requirements.txt # Dependencies
└── .gitignore
```

### เพิ่มฟีเจอร์ใหม่
```bash
# 1. Model: backend/app/models/__init__.py
# 2. Schema: backend/app/schemas.py
# 3. Service: backend/app/services/xxx_service.py
# 4. Router: backend/app/api/xxx.py
# 5. Register: backend/app/api/__init__.py
# 6. Test: curl /api/v1/xxx
# 7. Commit & Push
```

### รันเทสต์
```bash
cd /root/projects/pos-mobile/backend
python -m pytest tests/ -v
```

---

## 🔧 การแก้ไขปัญหา (Troubleshooting)

### Frontend Issues

| ปัญหา | สาเหตุ | วิธีแก้ |
|--------|--------|---------|
| **Barcode scanner ไม่ทำงาน** | ต้องเป็น HTTPS หรือ localhost | ใช้ nginx + SSL หรือเข้าผ่าน localhost:8080 |
| **ข้อมูลหายหลังรีโหลด** | localStorage ถูกล้าง | Sync ก่อนรีโหลด / ตั้งค่าเบราว์เซอร์ไม่ล้างข้อมูล |
| **UI แสดงผิดบนมือถือ** | Viewport/CSS | ตรวจสอบ `style-pos.css` media queries |
| **ไม่สามารถพิมพ์ใบเสร็จ** | Print CSS | ตรวจสอบ `@media print` ใน CSS |

### Backend Issues

| ปัญหา | สาเหตุ | วิธีแก้ |
|--------|--------|---------|
| **Port 8000 ถูกใช้งาน** | Process ค้าง | `pkill -f uvicorn` แล้วรันใหม่ |
| **ModuleNotFoundError** | ไม่ได้ activate venv / path ผิด | `source venv/bin/activate` หรือตั้ง `PYTHONPATH` |
| **Pydantic version conflict** | pip vs apt package | ใช้ `apt install python3-*` แทน pip |
| **Database locked** | Process อื่นใช้ DB | หยุด process อื่น / reboot |
| **CORS Error** | Frontend เรียกจาก origin ต่างกัน | เพิ่ม origin ใน `CORS_ORIGINS` config |

### Termux/Android Issues

| ปัญหา | วิธีแก้ |
|--------|---------|
| **Permission denied** | `termux-setup-storage` ให้สิทธิ์ storage |
| **Python version เก่า** | `pkg install python` (ต้อง 3.10+) |
| **Out of memory** | ปิด app อื่น / เพิ่ม swap |
| **Wake lock** | `termux-wake-lock` ไว้รันพื้นหลัง |

---

## 📞 การขอความช่วยเหลือ

- **GitHub Issues**: https://github.com/saharatyokthuan/pos-mobile/issues
- **Email**: saharatyokthuan@gmail.com

---

## 📄 License

MIT License - ใช้งานได้อย่างอิสระ แก้ไขได้ แจกจ่ายได้

---

## 🙏 Credits

- **Frontend**: Vanilla HTML5/CSS3/JavaScript (ES6+)
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Charts**: Chart.js (CDN)
- **Excel**: SheetJS/xlsx.js (CDN)
- **Icons**: Unicode Emoji (ไม่ต้องโหลด font)

---

> **ทำในประเทศไทย 🇹🇭** ด้วย ❤️ สำหรับร้านค้าขนาดเล็ก-กลาง