# 🛒 POS-MOBILE

### ระบบขายหน้าร้าน (Point of Sale) สำหรับมือถือ — ทำงานในเบราว์เซอร์ 100%

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![No Backend](https://img.shields.io/badge/Backend-ไม่ต้องมี-brightgreen?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

🔗 **ใช้งานจริง:** https://saharatyokthuan.github.io/pos-mobile/

> ⚠️ ข้อมูลของแอปเก็บไว้ใน `localStorage` ของเบราว์เซอร์เครื่องนั้น ๆ เท่านั้น ไม่มีการส่งขึ้นเซิร์ฟเวอร์

---

## 📁 โครงสร้างไฟล์

```
📦 POS-MOBILE
├── 🌐 index.html          → หน้าเว็บทั้งหมดแบบ single-page (header, sidebar, ทุกหน้า, ทุก modal)
├── 🎨 style-pos.css       → ธีมสี, เลย์เอาต์, responsive, สไตล์การพิมพ์ใบเสร็จ
└── ⚙️ script-pos.js       → ลอจิกทั้งหมด: จัดการข้อมูล, render, คำนวณ, นำทางระหว่างหน้า
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

ข้อมูลทั้งหมดเก็บใน `localStorage` ของเบราว์เซอร์ — ไม่มีการส่งขึ้นเซิร์ฟเวอร์ ข้อมูลอยู่เฉพาะในเครื่อง/เบราว์เซอร์นั้น ๆ
แนะนำให้สำรองข้อมูล (JSON) เป็นประจำ เพราะการล้างข้อมูลเบราว์เซอร์จะลบข้อมูลทั้งหมด

## 🚀 วิธีใช้งาน

- **ออนไลน์:** เปิด https://saharatyokthuan.github.io/pos-mobile/
- **ในเครื่อง:** เปิดไฟล์ `index.html` ในเบราว์เซอร์ได้ทันที — ไม่ต้อง build ไม่ต้อง install

> ฟีเจอร์สแกนบาร์โค้ดด้วยกล้องต้องเปิดผ่าน `https://` หรือ `localhost` เท่านั้น (ข้อกำหนดด้านความปลอดภัยของเบราว์เซอร์)

## 📦 Dependencies (โหลดผ่าน CDN + ตรวจสอบ SRI)

| ไลบรารี | ใช้ทำอะไร |
|:---|:---|
| [SheetJS (xlsx.js) 0.18.5](https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js) | นำเข้า/ส่งออกไฟล์ Excel |
| [Chart.js 4.4.0](https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js) | กราฟในหน้ารายงาน |

## 📄 License

เผยแพร่ภายใต้ [MIT License](LICENSE)

---

made in Thailand 🇹🇭
