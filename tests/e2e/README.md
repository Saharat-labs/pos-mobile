# ทดสอบ End-to-End (เบราว์เซอร์) — POS-MOBILE

ชุดทดสอบนี้เปิดแอปใน Chromium จริงผ่าน Playwright แล้วกดใช้งานแบบผู้ใช้ ครอบคลุม
หน้าทุกหน้า, modal ทุกตัว, การขายเงินสด/โอน/บัตร, ขายเชื่อ+รับชำระหนี้, พักบิล, สั่งซื้อ,
ปรับสต๊อก, Export/Import Excel, สำรอง/กู้คืน JSON, แม็พหมวดหมู่, พิมพ์ใบเสร็จ,
หลายร้าน, ปุ่มลัดคีย์บอร์ด, สแกนบาร์โค้ด (กล้องจำลอง), แบนเนอร์ออฟไลน์ และการเปิดผ่าน `file://`

## สิ่งที่ต้องมี

- Node.js + แพ็กเกจ `playwright` พร้อม Chromium (`require('playwright')` ต้องใช้ได้)
- `npm` (ใช้ `npm pack` ดาวน์โหลด SheetJS และ Chart.js ครั้งแรก แล้วเก็บแคชไว้)
- `python3` (ใช้เป็น static server)

ไม่ต้อง build และไม่ต้อง `npm install` ในโปรเจกต์

## วิธีรัน

```bash
tests/e2e/run.sh
```

สคริปต์จะเปิด `python3 -m http.server` ที่พอร์ต 8801 รันชุดทดสอบ แล้วปิดเซิร์ฟเวอร์ (ด้วย PID) ให้เอง
ผลลัพธ์แสดงเป็น `PASS` / `FAIL` / `SKIP` ทีละข้อ และ exit code เป็น 0 เมื่อผ่านทั้งหมด

ตัวแปรที่ปรับได้:

| ตัวแปร | ความหมาย | ค่าเริ่มต้น |
|---|---|---|
| `E2E_PORT` | พอร์ตของ static server | `8801` |
| `E2E_CACHE_DIR` | โฟลเดอร์แคชไลบรารีที่โหลดจาก npm และไฟล์ชั่วคราว | `$TMPDIR/pos-e2e-cache` |
| `E2E_ONLY` | รันเฉพาะเทสต์ที่ชื่อมีข้อความนี้ | (ทั้งหมด) |
| `E2E_HEADED=1` | เปิดหน้าต่างเบราว์เซอร์ให้เห็น | ปิด |
| `E2E_DEBUG=1` | พิมพ์ console ของหน้าเว็บออกมาระหว่างรัน | ปิด |
| `E2E_APP_SCRIPT` | ใช้ไฟล์ `script-pos.js` อื่นแทน (เช่นเวอร์ชันเก่าจาก `git show HEAD:script-pos.js`) เพื่อตรวจว่าเทสต์จับบั๊กได้ | (ไฟล์ในโปรเจกต์) |

ตัวอย่าง: `E2E_ONLY="Excel" E2E_PORT=8810 tests/e2e/run.sh`

ถ้ามีเซิร์ฟเวอร์ของแอปรันอยู่แล้ว สามารถรันไฟล์ทดสอบตรง ๆ ได้:
`E2E_BASE_URL=http://127.0.0.1:8801/ node tests/e2e/frontend.spec.js`

## เรื่อง CDN และ SRI

`index.html` โหลด SheetJS และ Chart.js จาก cdnjs ซึ่งอาจเข้าไม่ได้ใน CI ชุดทดสอบจึงดักคำขอ
`https://cdnjs.cloudflare.com/**` แล้วตอบด้วยไฟล์จากแพ็กเกจ npm (`xlsx@0.18.5`, `chart.js@4.4.0`)

- SheetJS จาก npm ตรงกับไฟล์บน cdnjs ทุกไบต์ (เทสต์ตรวจว่า hash ตรงกับ `integrity` ใน `index.html`)
- Chart.js บน cdnjs (`chart.umd.min.js`) เป็นไฟล์ที่ cdnjs ย่อเอง ไม่มีใน npm ไบต์จึงต่างกัน
  ชุดทดสอบจึงแก้เฉพาะค่า `integrity` ของสคริปต์ตัวนี้ใน `index.html` ที่ส่งให้เบราว์เซอร์ เป็น hash ของไฟล์ที่เสิร์ฟจริง
  (เบราว์เซอร์ยังตรวจ SRI อยู่ ไฟล์ `index.html` บนดิสก์ไม่ถูกแก้)

## หมายเหตุ

- แต่ละเทสต์ใช้ browser context ใหม่ (localStorage ว่าง) และปิด Service Worker ไว้ เพื่อไม่ให้แคชค้าง
- กล่องยืนยัน `confirm` / `prompt` ถูกตอบอัตโนมัติในเทสต์
- `window.print` และ `BarcodeDetector` ถูกจำลอง (Chromium บน Linux ไม่มี BarcodeDetector)
- กล้องใช้ `--use-fake-device-for-media-stream`
