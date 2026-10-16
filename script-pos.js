// ═══════════════════════════════════════════════
// DATA STORE
// ══════════════
let _storageWarned = false;
const DB = {
  get: (k, d=[]) => { try { return JSON.parse(localStorage.getItem('qpos_'+k)) ?? d; } catch { return d; } },
  set: (k, v) => {
    try { localStorage.setItem('qpos_'+k, JSON.stringify(v)); return true; }
    catch (err) {
      if (!_storageWarned) {
        _storageWarned = true;
        console.error('บันทึกข้อมูลลงเครื่องไม่สำเร็จ:', err);
        if (typeof toast === 'function') toast('บันทึกข้อมูลไม่สำเร็จ — พื้นที่จัดเก็บเต็มหรือถูกปิดกั้น', 'error');
      }
      return false;
    }
  },
};

let products = DB.get('products', []);
let sales    = DB.get('sales', []);
let purchases= DB.get('purchases', []);
let debts    = DB.get('debts', []);
let expenses = DB.get('expenses', []);
let settings = DB.get('settings', {
  storeName:'Quick POS', storeAddr:'', storePhone:'',
  taxId:'', lowStock:5, expiryDays:30, vat:'no'
});
let holdBills = DB.get('holdBills', []);
let hiddenMappingPrefixes = DB.get('hiddenMappingPrefixes', []);
let billCounter = DB.get('billCounter', 1);

// ── CATEGORY MAPPING ──────────────────────────
// ── OFFICIAL CATEGORY CODE TABLE (CP All) ──────
// รหัสหมวดหมู่ทางการ ถาวร ลบไม่ได้ (locked:true)
const OFFICIAL_CATEGORY_MAPPING = [
  { prefix:'01', name:'แซนวิชเย็น', locked:true },
  { prefix:'02', name:'APPETIZER', locked:true },
  { prefix:'03', name:'ผลไม้&ขนมหวาน', locked:true },
  { prefix:'05', name:'COUNTER DRINK', locked:true },
  { prefix:'06', name:'FOOD PLACE', locked:true },
  { prefix:'07', name:'แซนวิชอบร้อน', locked:true },
  { prefix:'08', name:'BUGGER', locked:true },
  { prefix:'09', name:'บัตร7-11', locked:true },
  { prefix:'10', name:'BEER & RTD ALCOHOL', locked:true },
  { prefix:'11', name:'LIQUOR', locked:true },
  { prefix:'12', name:'บุหรี่นอก', locked:true },
  { prefix:'13', name:'บัตรโทรศัพท์ภายใน/ต่างประเทศ', locked:true },
  { prefix:'14', name:'HEALTH CARE', locked:true },
  { prefix:'15', name:'COUNT COSTOMER', locked:true },
  { prefix:'16', name:'SALAD', locked:true },
  { prefix:'18', name:'MEDICINE', locked:true },
  { prefix:'19', name:'ข้าวกล่องแดง 3D แช่เย็น', locked:true },
  { prefix:'20', name:'ข้าวกล่องขาว 6M แช่แข็ง', locked:true },
  { prefix:'21', name:'SAUSAGE', locked:true },
  { prefix:'22', name:'ข้าวกล่องดำ 7D แช่เย็น', locked:true },
  { prefix:'23', name:'ไส้กรอกกริลล์', locked:true },
  { prefix:'24', name:'ขนมจีบ&ซาลาเปา', locked:true },
  { prefix:'25', name:'HOT PASTY', locked:true },
  { prefix:'26', name:'บัตรโทรศัพท์ระหว่างประเทศ', locked:true },
  { prefix:'27', name:'บัตรเติมเกมส์', locked:true },
  { prefix:'28', name:'BOOKS', locked:true },
  { prefix:'29', name:'UHT MILK', locked:true },
  { prefix:'30', name:'นมพาสเจอร์ไรส์ (ขวด)', locked:true },
  { prefix:'31', name:'PASTEURIZED DRINK', locked:true },
  { prefix:'32', name:'เครื่องปรุง', locked:true },
  { prefix:'33', name:'บะหมี่กึ่งสำเร็จรูป', locked:true },
  { prefix:'34', name:'เครื่องชง', locked:true },
  { prefix:'35', name:'SPECIAL ITEM', locked:true },
  { prefix:'36', name:'CHILLED CAKE CP RAM', locked:true },
  { prefix:'37', name:'STAMP', locked:true },
  { prefix:'38', name:'NON - CABONATED SOFT DRINK', locked:true },
  { prefix:'39', name:'ENTERTAINMENT', locked:true },
  { prefix:'40', name:'ลูกอม ช็อคโกแลต', locked:true },
  { prefix:'41', name:'SNACKS', locked:true },
  { prefix:'42', name:'CABONATED SOFT DRINK', locked:true },
  { prefix:'43', name:'IT DEVICES', locked:true },
  { prefix:'44', name:'ICE CREAM', locked:true },
  { prefix:'45', name:'ICE', locked:true },
  { prefix:'46', name:'7-SERVICE (บริการส่งพัสดุ SPEED D)', locked:true },
  { prefix:'47', name:'7-SERVICE (บรรจุภัณฑ์ SPEED D)', locked:true },
  { prefix:'48', name:'HEALTH AND WELLNESS', locked:true },
  { prefix:'49', name:'ENERGY & SPORT DRINK', locked:true },
  { prefix:'50', name:'PERSONAL CARE', locked:true },
  { prefix:'51', name:'HOUSEWARE', locked:true },
  { prefix:'52', name:'STATIONARY', locked:true },
  { prefix:'53', name:'DRUG & HEALTH CARE', locked:true },
  { prefix:'54', name:'SANITARY', locked:true },
  { prefix:'55', name:'HOUSEHOLD', locked:true },
  { prefix:'56', name:'ELECTRONIC', locked:true },
  { prefix:'58', name:'ซิมการ์ด', locked:true },
  { prefix:'59', name:'HERBAL PERSONAL CARE', locked:true },
  { prefix:'60', name:'BAKERY', locked:true },
  { prefix:'61', name:'ฟาร์มเฮาท์', locked:true },
  { prefix:'62', name:'FRESH BAKERY', locked:true },
  { prefix:'63', name:'THAI SNACKS', locked:true },
  { prefix:'65', name:'พ.ร.บ.', locked:true },
  { prefix:'67', name:'เกมโกะ', locked:true },
  { prefix:'68', name:'สินค้าเทศกาล', locked:true },
  { prefix:'69', name:'CPG SYNERGY', locked:true },
  { prefix:'70', name:'เติมเงินออนไลน์ (คอมมิชชั่น)', locked:true },
  { prefix:'71', name:'7 TOP UP CASH', locked:true },
  { prefix:'72', name:'บุหรี่ไทย', locked:true },
  { prefix:'73', name:'BELLINEE BAKERY', locked:true },
  { prefix:'74', name:'สินค้าการกุศล', locked:true },
  { prefix:'75', name:'BELLINEE PACKAGARE BAKERY', locked:true },
  { prefix:'76', name:'KUDSAN SUPPLY USE', locked:true },
  { prefix:'77', name:'24 CATALOG', locked:true },
  { prefix:'78', name:'กระเช้าผลไม้', locked:true },
  { prefix:'79', name:'BELLINEE BAKERY', locked:true },
  { prefix:'80', name:'KUDSAN BAKERY', locked:true },
  { prefix:'83', name:'CP FRESHMART', locked:true },
  { prefix:'84', name:'VEGETABLE', locked:true },
  { prefix:'85', name:'สินค้าโครงการ RTC', locked:true },
  { prefix:'86', name:'MAGAZINE', locked:true },
  { prefix:'87', name:'KUDSAN BEVERAGE', locked:true },
  { prefix:'88', name:'จิตรลัดดา', locked:true },
  { prefix:'89', name:'CATALOG ON SHELL', locked:true },
  { prefix:'90', name:'PROMOTION PREMIUM', locked:true },
  { prefix:'96', name:'HOT SERVE', locked:true },
  { prefix:'97', name:'เสื้อพนักงาน', locked:true },
  { prefix:'98', name:'P.O.P.สื่อภายในร้าน', locked:true },
  { prefix:'99', name:'ลังเบรค', locked:true },
];

// ── ประเภทสินค้า (Type) ──────────────────────────
// รายการประเภทแบบเลือกเอง ไม่ผูกกับรหัสสินค้า/prefix (ต่างจากหมวดหมู่ด้านบน)
const PRODUCT_TYPES = [
  'ขนมและชอคโกแลต',
  'อาหารพร้อมทาน',
  'เครื่องดื่ม',
  'นมและโยเกิร์ต',
  'เบเกอรี่และขนมหวาน',
  'ของใช้ส่วนตัว',
  'อาหารพร้อมปรุง',
  'ผักและผลไม้',
  'ยาและอุปกรณ์การแพทย์',
  'True wallet',
  'True move',
];
function populateProductTypeSelect(selectId, placeholder) {
  const el = document.getElementById(selectId);
  if (!el) return;
  const current = el.value;
  el.innerHTML = `<option value="">${esc(placeholder || '-- เลือกประเภท --')}</option>` +
    PRODUCT_TYPES.map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join('');
  if (current) el.value = current;
}

let categoryMapping = DB.get('categoryMapping', null);
if (!categoryMapping) {
  categoryMapping = OFFICIAL_CATEGORY_MAPPING.map(m => ({...m}));
} else {
  // เผื่อมีข้อมูลเก่าอยู่แล้ว: รวมตารางทางการเข้าไป โดยไม่ลบ mapping ที่ผู้ใช้เพิ่มเองซึ่งไม่ใช่รหัสทางการ
  let mappingChanged = false;
  OFFICIAL_CATEGORY_MAPPING.forEach(off => {
    const existing = categoryMapping.find(m => m.prefix === off.prefix);
    if (existing) {
      if (existing.name !== off.name || !existing.locked) mappingChanged = true;
      existing.name = off.name; existing.locked = true;
    } else { categoryMapping.push({...off}); mappingChanged = true; }
  });
  if (mappingChanged) {
    DB.set('categoryMapping', categoryMapping);
    // เฉพาะสินค้าที่ยังไม่เคยตั้งหมวดหมู่เอง ไม่แตะสินค้าที่ผู้ใช้แก้ไขหมวดหมู่เองแล้ว
    products.forEach(p => { if (!p.category) p.category = getCategoryFromProductId(p.product_id); });
    DB.set('products', products);
  }
}

let cart = DB.get('cart', []);
let currentPayType = 'เงินสด';
let payReceived = '';
let editingProductId = null;
let editingDebtId = null;
let currentDebtId = null;
let creditSaleMode = false;
let adjChanges = {};
let salesChartInst = null, purChartInst = null, categoryChartInst = null, compareChartInst = null;
let currentPage = 'pos';
let posCurrentCat = '';

// ═══════════════════════════════════════════════
// UTILS
// ═══════════════════════════════════════════════
const fmt = n => '฿' + (+n||0).toLocaleString('th-TH',{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtN= n => (+n||0).toLocaleString('th-TH',{minimumFractionDigits:2,maximumFractionDigits:2});
const ymd  = d => { const x=new Date(d); return new Date(x.getTime()-x.getTimezoneOffset()*60000).toISOString().slice(0,10); };
const today= ()=> ymd(new Date());
const uid  = ()=> Date.now().toString(36)+Math.random().toString(36).slice(2,6);
const thDate= d=> d ? new Date(d).toLocaleDateString('th-TH',{year:'numeric',month:'short',day:'numeric'}) : '-';
const thTime= d=> d ? new Date(d).toLocaleTimeString('th-TH',{hour:'2-digit',minute:'2-digit'}) : '';
const thDT  = d=> d ? new Date(d).toLocaleString('th-TH',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '-';
const save = ()=>{
  DB.set('products',products); DB.set('sales',sales);
  DB.set('purchases',purchases); DB.set('debts',debts);
  DB.set('expenses',expenses); DB.set('holdBills',holdBills);
  DB.set('billCounter',billCounter); DB.set('settings',settings);
  DB.set('categoryMapping', categoryMapping);
  DB.set('hiddenMappingPrefixes', hiddenMappingPrefixes);
  DB.set('cart', cart);
};

function toast(msg, type='success') {
  const c = document.getElementById('toast-container');
  if (!c) { console.warn(msg); return; }
  const t = document.createElement('div');
  t.className = `toast toast-${type}`; t.textContent = msg;
  c.appendChild(t);
  setTimeout(()=>t.remove(), 2800);
}

// ── ESCAPE HTML (ป้องกัน XSS จากชื่อสินค้า/ลูกค้า ที่ผู้ใช้กรอกเอง) ──
function esc(s) {
  return String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ── CATEGORY FUNCTIONS ──────────────────────────
function getCategoryFromProductId(productId) {
  if (!productId || typeof productId !== 'string') return 'อื่นๆ';
  for (let m of categoryMapping) {
    if (productId.startsWith(m.prefix)) return m.name;
  }
  return 'อื่นๆ';
}

function getAllCategories() {
  const catSet = new Set();
  products.forEach(p => {
    if (p.category) catSet.add(p.category);
  });
  // Also include mapped categories that may not have products yet
  categoryMapping.forEach(m => catSet.add(m.name));
  return Array.from(catSet).sort();
}

function updateCategorySelects() {
  const cats = getAllCategories();
  // Filter dropdown
  const filterEl = document.getElementById('prod-cat-filter');
  if (filterEl) {
    const current = filterEl.value;
    filterEl.innerHTML = '<option value="">ทุกหมวด</option>';
    cats.forEach(c => filterEl.innerHTML += `<option value="${esc(c)}">${esc(c)}</option>`);
    if (current) filterEl.value = current;
  }
}

// ── CATEGORY VISIBILITY (ซ่อน/แสดงรายการในลิสต์แม็พหมวดหมู่ หน้าเพิ่มเติม) ──
let showHiddenMappings = false;
function renderMapping() {
  const list = document.getElementById('mapping-list');
  const hiddenCount = categoryMapping.filter(m => hiddenMappingPrefixes.includes(m.prefix)).length;
  const visibleMapping = showHiddenMappings ? categoryMapping : categoryMapping.filter(m => !hiddenMappingPrefixes.includes(m.prefix));
  const toggleBar = hiddenCount ? `
    <div class="mapping-hidden-bar" onclick="showHiddenMappings=!showHiddenMappings;renderMapping()">
      ${showHiddenMappings ? `🔽 ซ่อนรายการที่ซ่อนไว้ (${hiddenCount})` : `▶️ แสดงรายการที่ซ่อนไว้ (${hiddenCount})`}
    </div>` : '';
  list.innerHTML = toggleBar + visibleMapping.map((m) => {
    const i = categoryMapping.indexOf(m);
    const isHidden = hiddenMappingPrefixes.includes(m.prefix);
    return `
    <div class="mapping-row ${isHidden?'mapping-row-hidden':''}">
      <span class="m-prefix">${esc(m.prefix)}</span>
      <span class="m-arrow">→</span>
      <span class="m-cat">${esc(m.name)}</span>
      <button class="btn-icon" title="${isHidden?'แสดงรายการนี้':'ซ่อนรายการนี้'}" data-action="toggle-hide" data-prefix="${esc(m.prefix)}">${isHidden?'🙈':'👁️'}</button>
      ${m.locked ? '<span title="หมวดหมู่ทางการ ถาวร ลบไม่ได้" style="opacity:.6">🔒</span>' : `<button class="btn-icon" data-action="delete-mapping" data-index="${i}">✕</button>`}
    </div>`;
  }).join('');
}
if (!window.__mappingListDelegated) {
  window.__mappingListDelegated = true;
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    if (btn.dataset.action === 'toggle-hide') toggleMappingHidden(btn.dataset.prefix);
    else if (btn.dataset.action === 'delete-mapping') deleteMapping(Number(btn.dataset.index));
  });
}
function toggleMappingHidden(prefix) {
  const i = hiddenMappingPrefixes.indexOf(prefix);
  if (i === -1) hiddenMappingPrefixes.push(prefix); else hiddenMappingPrefixes.splice(i,1);
  save();
  renderMapping();
}

function reapplyCategoryForPrefix(prefix) {
  let changed = 0;
  products.forEach(p => {
    if (p.product_id && p.product_id.startsWith(prefix)) {
      p.category = getCategoryFromProductId(p.product_id);
      changed++;
    }
  });
  return changed;
}

function recalculateAllCategories() {
  products.forEach(p => { p.category = getCategoryFromProductId(p.product_id); });
  save();
  renderMapping(); updateCategorySelects(); updateCatChips();
  renderProducts(); renderPosProducts();
  toast(`ปรับปรุงหมวดหมู่สินค้าทั้งหมด ${products.length} รายการแล้ว ✓`);
}

function addMapping() {
  const prefix = document.getElementById('mapping-prefix').value.trim();
  const cat = document.getElementById('mapping-cat').value.trim();
  if (!prefix) { toast('กรุณากรอกรหัส prefix', 'error'); return; }
  if (!cat) { toast('กรุณากรอกชื่อหมวดหมู่', 'error'); return; }
  // Check duplicate
  if (categoryMapping.some(m => m.prefix === prefix)) {
    toast('มีรหัสนี้อยู่แล้ว', 'warning');
    return;
  }
  categoryMapping.push({ prefix, name: cat });
  const updated = reapplyCategoryForPrefix(prefix);
  save();
  renderMapping();
  updateCategorySelects();
  updateCatChips();
  renderProducts();
  renderPosProducts();
  document.getElementById('mapping-prefix').value = '';
  document.getElementById('mapping-cat').value = '';
  toast(updated ? `เพิ่มการแม็พแล้ว ✓ (อัปเดตสินค้า ${updated} รายการ)` : 'เพิ่มการแม็พแล้ว ✓');
}

function deleteMapping(index) {
  const m = categoryMapping[index];
  if (m && m.locked) { toast('หมวดหมู่นี้เป็นหมวดหมู่ทางการ ถาวร ลบไม่ได้', 'error'); return; }
  if (!confirm('ลบการแม็พนี้?')) return;
  const prefix = categoryMapping[index].prefix;
  categoryMapping.splice(index, 1);
  reapplyCategoryForPrefix(prefix);
  save();
  renderMapping();
  updateCategorySelects();
  updateCatChips();
  renderProducts();
  renderPosProducts();
  toast('ลบแล้ว');
}

// ── AUTO-FILL CATEGORY IN PRODUCT MODAL ────────
function autoFillCategory() {
  const pid = document.getElementById('pm-product_id').value.trim();
  if (pid) {
    const cat = getCategoryFromProductId(pid);
    document.getElementById('pm-category').value = cat;
  } else {
    document.getElementById('pm-category').value = '';
  }
}

// ═══════════════════════════════════════════════
// MASTER PRODUCT LIST (from export_product.xlsx)
// รายการอ้างอิงสำหรับค้นหา/auto-fill เท่านั้น — ไม่ใช่สต๊อกร้าน
// ═══════════════════════════════════════════════
let MASTER_BY_ID = null, MASTER_BY_BARCODE = null;
function ensureMasterIndex() {
  if (MASTER_BY_ID || typeof MASTER_PRODUCTS === 'undefined') return;
  MASTER_BY_ID = new Map();
  MASTER_BY_BARCODE = new Map();
  MASTER_PRODUCTS.forEach(m => { MASTER_BY_ID.set(m.i, m); MASTER_BY_BARCODE.set(m.b, m); });
}

// เรียกตอนพิมพ์รหัสสินค้า/บาร์โค้ดในฟอร์มเพิ่ม-แก้ไขสินค้า
// เติมชื่อ+หมวดหมู่ให้อัตโนมัติถ้าเจอในรายการกลาง (เติมเฉพาะช่องที่ยังว่าง)
function autoFillProductInfo(source) {
  autoFillCategory(); // คงพฤติกรรมเดิม: เติมหมวดตาม prefix รหัสสินค้า
  ensureMasterIndex();
  if (!MASTER_BY_ID) return;
  const pid = document.getElementById('pm-product_id').value.trim();
  const barcode = document.getElementById('pm-barcode').value.trim();
  const match = (source === 'barcode' ? MASTER_BY_BARCODE.get(barcode) : MASTER_BY_ID.get(pid))
             || MASTER_BY_ID.get(pid) || MASTER_BY_BARCODE.get(barcode);
  if (!match) return;
  const nameEl = document.getElementById('pm-name');
  if (!nameEl.value.trim()) nameEl.value = match.n;
  if (!document.getElementById('pm-barcode').value.trim()) document.getElementById('pm-barcode').value = match.b;
  if (!document.getElementById('pm-product_id').value.trim()) document.getElementById('pm-product_id').value = match.i;
}

// ── รายการสินค้ากลาง: modal ค้นหา + เลือกเพื่อเพิ่มสินค้า ──
function openMasterSearch() {
  ensureMasterIndex();
  document.getElementById('master-search').value = '';
  renderMasterSearch();
  openModal('modal-master-search');
}
function renderMasterSearch() {
  const q = document.getElementById('master-search').value.trim().toLowerCase();
  const listEl = document.getElementById('master-search-list');
  if (typeof MASTER_PRODUCTS === 'undefined') { listEl.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:20px">ไม่พบไฟล์รายการสินค้ากลาง</p>'; return; }
  if (!q) { listEl.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:20px">พิมพ์เพื่อค้นหา...</p>'; return; }
  const existingIds = new Set(products.map(p => p.product_id));
  const results = MASTER_PRODUCTS.filter(m =>
    m.n.toLowerCase().includes(q) || m.i.includes(q) || m.b.includes(q)
  ).slice(0, 50);
  if (!results.length) { listEl.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:20px">ไม่พบสินค้า</p>'; return; }
  listEl.innerHTML = results.map(m => {
    const added = existingIds.has(m.i);
    return `<div class="prod-list-item" style="cursor:pointer;${added?'opacity:.5':''}" onclick="${added?'':`selectMasterProduct('${m.i}')`}">
      <div class="pli-name">${esc(m.n)}${added ? ' <span style="font-size:11px;color:var(--text-muted)">(มีในร้านแล้ว)</span>' : ''}</div>
      <div class="pli-meta">รหัส: ${esc(m.i)} · Barcode: ${esc(m.b)} · ${esc(m.c)}</div>
    </div>`;
  }).join('');
}
function selectMasterProduct(productId) {
  ensureMasterIndex();
  const m = MASTER_BY_ID.get(productId);
  if (!m) return;
  closeModal('modal-master-search');
  openProductModal(null);
  document.getElementById('pm-product_id').value = m.i;
  document.getElementById('pm-barcode').value = m.b;
  document.getElementById('pm-name').value = m.n;
  autoFillCategory();
  toast('เติมข้อมูลจากรายการกลางแล้ว กรอกราคาขายเพื่อบันทึก', 'success');
}

// ═══════════════════════════════════════════════
// NAVIGATION (single-page app: all "pages" live in one index.html,
// toggled via .page/.page.active — see style-pos.css)
// ═══════════════════════════════════════════════
function showPage(name) {
  closeMenu();
  if (name === currentPage) return;
  const current = document.getElementById('page-' + currentPage);
  if (current) current.classList.remove('active');
  const next = document.getElementById('page-' + name);
  if (next) next.classList.add('active');
  currentPage = name;
  setActiveNav(name);
  runPageInit(name);
}

// All modals now live on every page, so this can open directly.
function showSubPage(name) {
  if (name === 'stock-adjust') {
    adjChanges = {};
    renderAdjList();
    openModal('modal-stock-adjust');
  }
}

function setActiveNav(name) {
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'));
  const navEl = document.getElementById('nav-'+name);
  if (navEl) navEl.classList.add('active');

  const fab = document.getElementById('cart-fab');
  if (fab) fab.style.display = name === 'pos' ? 'flex' : 'none';

  const titles = {
    pos:'🛒 ขายสินค้า', products:'📦 สินค้า',
    purchase:'🚚 สั่งซื้อ', debt:'💳 ลูกหนี้',
    reports:'📊 รายงาน', more:'☰ เมนู'
  };
  const titleEl = document.getElementById('topbar-title');
  if (titleEl) titleEl.textContent = titles[name] || '';
}

// Runs the same per-page setup that showPage() used to run inline, now
// triggered once on DOMContentLoaded for whichever page was loaded.
function runPageInit(name) {
  const topAction = document.getElementById('topbar-action');
  const billBadge = document.getElementById('pos-bill-no');
  if (topAction) topAction.style.display = 'none';
  if (billBadge) billBadge.style.display = 'none';

  if (name === 'pos') {
    if (billBadge) {
      billBadge.style.display = 'inline';
      billBadge.textContent = 'บิล #B'+String(billCounter).padStart(5,'0');
    }
    renderPosProducts(); updateCatChips(); updateCartFab();
  }
  if (name === 'products') {
    if (topAction) {
      topAction.style.display = 'inline-flex';
      topAction.textContent = '+ เพิ่มสินค้า';
      topAction.onclick = ()=>openProductModal();
    }
    updateCategorySelects(); renderProducts();
  }
  if (name === 'purchase') {
    if (topAction) {
      topAction.style.display = 'inline-flex';
      topAction.textContent = '+ บันทึกซื้อ';
      topAction.onclick = ()=>openPurchaseModal();
    }
    renderPurchases();
  }
  if (name === 'debt') {
    if (topAction) {
      topAction.style.display = 'inline-flex';
      topAction.textContent = '+ เพิ่ม';
      topAction.onclick = ()=>openDebtModal();
    }
    renderDebts();
  }
  if (name === 'reports') {
    setDateRange('month','sale');
    renderSalesReport(); renderStockReport();
  }
  if (name === 'more') {
    loadSettings();
    renderMapping();
  }
}

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ═══════════════════════════════════════════════
// SIDE MENU
// ═══════════════════════════════════════════════
function openMenu() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebar-overlay').classList.add('open');
  const btn = document.getElementById('hamburger-btn');
  btn.setAttribute('aria-expanded', 'true');
  btn.textContent = '×';
}
function closeMenu() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('open');
  const btn = document.getElementById('hamburger-btn');
  btn.setAttribute('aria-expanded', 'false');
  btn.textContent = '☰';
}
function navigateFromMenu(name) {
  closeMenu();
  showPage(name);
}

// ═══════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════
function loadSettings() {
  document.getElementById('set-store-code').value = settings.storeCode||'';
  document.getElementById('set-store-name').value = settings.storeName||'';
  document.getElementById('set-store-addr').value = settings.storeAddr||'';
  document.getElementById('set-store-phone').value = settings.storePhone||'';
  document.getElementById('set-tax-id').value = settings.taxId||'';
  document.getElementById('set-low-stock').value = settings.lowStock||5;
  document.getElementById('set-expiry-days').value = settings.expiryDays||30;
  document.getElementById('set-vat').value = settings.vat||'no';
}
function saveSettings() {
  settings.storeCode = document.getElementById('set-store-code').value;
  settings.storeName = document.getElementById('set-store-name').value;
  settings.storeAddr = document.getElementById('set-store-addr').value;
  settings.storePhone = document.getElementById('set-store-phone').value;
  settings.taxId = document.getElementById('set-tax-id').value;
  settings.lowStock = +document.getElementById('set-low-stock').value;
  settings.expiryDays = +document.getElementById('set-expiry-days').value;
  settings.vat = document.getElementById('set-vat').value;
  save(); updateHeaderSubtitle(); toast('บันทึกแล้ว ✓');
}
function updateHeaderSubtitle() {
  const el = document.getElementById('header-subtitle');
  if (!el) return;
  const parts = [settings.storeCode, settings.storeName].filter(Boolean);
  el.textContent = parts.join(' · ');
}
function openSetting() {
  navigateFromMenu('more');
}
function clearAllData() {
  if (!confirm('⚠️ ล้างข้อมูลทั้งหมด?')) return;
  products=[];sales=[];purchases=[];debts=[];expenses=[];holdBills=[];billCounter=1;
  save(); toast('ล้างข้อมูลแล้ว','warning'); showPage('pos');
}

// ═══════════════════════════════════════════════
// PRODUCT MANAGEMENT
// ═══════════════════════════════════════════════
function openProductModal(id=null) {
  editingProductId = id;
  document.getElementById('prod-modal-title').textContent = id ? '✏️ แก้ไขสินค้า' : '+ เพิ่มสินค้า';
  updateCategorySelects();
  populateProductTypeSelect('pm-type');
  if (id) {
    const p = products.find(x=>x.id===id); if(!p) return;
    document.getElementById('pm-product_id').value = p.product_id||'';
    document.getElementById('pm-barcode').value = p.barcode||'';
    document.getElementById('pm-name').value = p.name||'';
    document.getElementById('pm-category').value = p.category||'';
    document.getElementById('pm-type').value = p.type||'';
    document.getElementById('pm-price').value = p.price||0;
    document.getElementById('pm-cost').value = p.cost||0;
    document.getElementById('pm-stock').value = p.stock||0;
    document.getElementById('pm-min-stock').value = p.minStock||settings.lowStock;
    document.getElementById('pm-expiry').value = p.expiry||'';
  } else {
    document.getElementById('pm-product_id').value='';
    document.getElementById('pm-barcode').value='';
    document.getElementById('pm-name').value='';
    document.getElementById('pm-category').value='';
    document.getElementById('pm-type').value='';
    document.getElementById('pm-price').value='';
    document.getElementById('pm-cost').value='';
    document.getElementById('pm-stock').value=0;
    document.getElementById('pm-min-stock').value=settings.lowStock;
    document.getElementById('pm-expiry').value='';
  }
  openModal('modal-product');
}

function saveProduct() {
  const productId = document.getElementById('pm-product_id').value.trim();
  const barcode = document.getElementById('pm-barcode').value.trim();
  const name = document.getElementById('pm-name').value.trim();
  const price = +document.getElementById('pm-price').value || 0;
  const category = document.getElementById('pm-category').value.trim(); // auto-filled, but allow save as-is
  const type = document.getElementById('pm-type').value.trim();
  
  if (!productId) { toast('กรุณากรอกรหัสสินค้า','error'); return; }
  if (!barcode) { toast('กรุณากรอกบาร์โค้ด','error'); return; }
  if (!name) { toast('กรุณากรอกชื่อสินค้า','error'); return; }
  if (price <= 0) { toast('กรุณากรอกราคาขายมากกว่า 0','error'); return; }
  const dup = products.find(x => x.id!==editingProductId && (x.barcode===barcode || x.product_id===productId));
  if (dup) { toast(`รหัสหรือบาร์โค้ดนี้ถูกใช้แล้วกับ "${dup.name}"`,'error'); return; }

  const data = {
    id: editingProductId || uid(),
    product_id: productId,
    barcode: barcode,
    name: name,
    category: category || getCategoryFromProductId(productId),
    type: type,
    price: price,
    cost: +document.getElementById('pm-cost').value || 0,
    stock: +document.getElementById('pm-stock').value || 0,
    minStock: +document.getElementById('pm-min-stock').value || settings.lowStock,
    expiry: document.getElementById('pm-expiry').value,
    createdAt: editingProductId ? (products.find(x=>x.id===editingProductId)?.createdAt||Date.now()) : Date.now(),
  };

  if (editingProductId) {
    const idx=products.findIndex(x=>x.id===editingProductId);
    if(idx!==-1){products[idx]=data;}
  } else products.push(data);
  save(); closeModal('modal-product'); renderProducts(); renderPosProducts();
  toast(editingProductId?'แก้ไขแล้ว ✓':'เพิ่มสินค้าแล้ว ✓');
}
function deleteProduct(id) {
  if (!confirm('ลบสินค้านี้?')) return;
  products=products.filter(x=>x.id!==id);
  save(); renderProducts(); renderPosProducts(); toast('ลบแล้ว','warning');
}

function renderProducts() {
  const q=(document.getElementById('prod-search')?.value||'').toLowerCase();
  const cat=document.getElementById('prod-cat-filter')?.value||'';
  const typ=document.getElementById('prod-type-filter')?.value||'';
  const sf=document.getElementById('prod-stock-filter')?.value||'';
  const expWarn=new Date(); expWarn.setDate(expWarn.getDate()+settings.expiryDays);
  populateProductTypeSelect('prod-type-filter', 'ทุกประเภท');
  document.getElementById('prod-type-filter').value = typ;

  let list=products.filter(p=>{
    if(q&&!p.name.toLowerCase().includes(q)&&!(p.product_id||'').includes(q)&&!(p.barcode||'').includes(q)) return false;
    if(cat&&p.category!==cat) return false;
    if(typ&&p.type!==typ) return false;
    if(sf==='low'&&(p.stock<=0||p.stock>settings.lowStock)) return false;
    if(sf==='out'&&p.stock>0) return false;
    if(sf==='available'&&p.stock<=0) return false;
    return true;
  });
  list.sort((a,b)=>(a.product_id||'').localeCompare(b.product_id||'',undefined,{numeric:true}));

  const alerts=products.filter(p=>p.stock<=settings.lowStock||(p.expiry&&new Date(p.expiry)<=expWarn)).length;
  const nb=document.getElementById('nav-alert-badge');
  nb.textContent=alerts; nb.style.display=alerts?'flex':'none';

  const c=document.getElementById('prod-list'); if(!c) return;
  if(!list.length){c.innerHTML='<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-text">ไม่พบสินค้า</div></div>';return;}

  c.innerHTML=list.map(p=>{
    const stockCls=p.stock<=0?'stock-out':p.stock<=settings.lowStock?'stock-low':'stock-ok';
    const stockLabel=p.stock<=0?'หมด':p.stock<=settings.lowStock?`ต่ำ: ${p.stock}`:`${p.stock}`;
    let expiryTxt='';
    if(p.expiry){
      const exp=new Date(p.expiry);
      const cls=exp<new Date()?'expiry-danger':exp<=expWarn?'expiry-warn':'expiry-ok';
      expiryTxt=`<div class="${cls}" style="font-size:11px;margin-top:3px">📅 ${thDate(p.expiry)}</div>`;
    }
    return `<div class="prod-list-item">
      <div class="pli-info">
        <div class="pli-name">${esc(p.name)}</div>
        <div class="pli-meta">รหัส: <span class="pli-barcode">${esc(p.product_id||'-')}</span> · Barcode: ${esc(p.barcode||'-')} · ${esc(p.category||'-')}${p.type?` · 🏷️ ${esc(p.type)}`:''}</div>
        <div class="pli-price">${fmt(p.price)}</div>
        ${expiryTxt}
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
        <span class="pli-stock ${stockCls}">${stockLabel}</span>
        <div style="display:flex;gap:6px">
          <button class="btn-icon" onclick="openProductModal('${p.id}')">✏️</button>
          <button class="btn-icon" onclick="deleteProduct('${p.id}')">🗑️</button>
        </div>
      </div>
    </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════
// POS
// ═══════════════════════════════════════════════
function renderPosProducts() {
  const q=(document.getElementById('pos-search-input')?.value||'').toLowerCase();
  const cat=posCurrentCat;
  const grid=document.getElementById('pos-product-grid'); if(!grid) return;
  let list=products.filter(p=>{
    if(cat&&p.category!==cat) return false;
    if(!q) return true;
    return p.name.toLowerCase().includes(q)||(p.product_id||'').includes(q)||(p.barcode||'').includes(q);
  });
  list.sort((a,b)=>(a.product_id||'').localeCompare(b.product_id||'',undefined,{numeric:true}));
  if(!list.length){grid.innerHTML='<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🔍</div><div class="empty-text">ไม่พบสินค้า</div></div>';return;}
  grid.innerHTML=list.map(p=>{
    const lowCls=p.stock<=0?'no-stock':p.stock<=settings.lowStock?'low-stock':'';
    return `<div class="product-card ${lowCls}" onclick="clickProduct('${p.id}')">
      <div class="pc-name">${esc(p.name)}</div>
      <div class="pc-product_id">รหัส: ${esc(p.product_id||'-')}</div>
      <div class="pc-barcode">Barcode: ${esc(p.barcode||'-')}</div>
      <div class="pc-price">${fmt(p.price)}</div>
      <div class="pc-stock">${p.stock<=0?'❌ หมด':`📦 ${p.stock}`}</div>
    </div>`;
  }).join('');
}

function updateCatChips() {
  const cats = getAllCategories();
  const c=document.getElementById('pos-cat-scroll'); if(!c) return;
  c.innerHTML=`<button class="cat-chip ${!posCurrentCat?'active':''}" onclick="setCatFilter('')">ทั้งหมด</button>`+
    cats.map(cat=>`<button class="cat-chip ${posCurrentCat===cat?'active':''}" onclick="setCatFilter('${esc(cat)}')">${esc(cat)}</button>`).join('');
}

function setCatFilter(cat) {
  posCurrentCat = cat;
  updateCatChips();
  filterPosProducts();
}
function filterPosProducts() {
  renderPosProducts();
}

function clickProduct(id) {
  const p=products.find(x=>x.id===id); if(!p||p.stock<=0) return;
  addToCart(p, 1);
}

function addToCart(product, qty) {
  const key = product.id;
  const ex = cart.find(c => c.key === key);
  const currentQty = ex ? ex.qty : 0;
  if (currentQty + qty > product.stock) {
    toast(`สต๊อกไม่พอ (เหลือ ${product.stock})`, 'error');
    return;
  }
  if(ex) ex.qty += qty;
  else cart.push({key, productId: product.id, name: product.name, price: product.price, qty: qty});
  updateCartFab();
  renderCart();
  toast(`เพิ่ม ${product.name}`,'success');
}
function addFirstResult() {
  const q=document.getElementById('pos-search-input').value.toLowerCase();
  if(!q) return;
  let p=products.find(x=>x.barcode===q);
  if(!p) p=products.find(x=>x.product_id===q);
  if(!p) p=products.find(x=>x.name.toLowerCase().includes(q));
  if(p&&p.stock>0){
    addToCart(p, 1);
    document.getElementById('pos-search-input').value='';
    renderPosProducts();
  } else if(p&&p.stock<=0){
    toast('สินค้าหมด','error');
  }
}
function updateCartFab() {
  DB.set('cart', cart);
  const total=cart.reduce((s,c)=>s+c.qty,0);
  const badge=document.getElementById('cart-count-badge');
  if(!badge) return;
  badge.style.display=total?'flex':'none';
  badge.textContent=total;
}

function openCartSheet() { renderCart(); openModal('cart-sheet'); }
function closeCartSheet() { closeModal('cart-sheet'); }

function renderCart() {
  const list=document.getElementById('cart-items-list'); if(!list) return;
  const badge=document.getElementById('cart-bill-badge');
  if(badge) badge.textContent='บิล #B'+String(billCounter).padStart(5,'0');
  if(!cart.length){
    list.innerHTML='<div class="empty-state"><div class="empty-icon">🛒</div><div class="empty-text">ยังไม่มีสินค้า</div></div>';
  } else {
    list.innerHTML=cart.map((item,i)=>`
      <div class="cart-item">
        <div class="ci-info">
          <div class="ci-name">${esc(item.name)}</div>
          <div class="ci-unit">× ${fmt(item.price)}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px">
          <div class="ci-qty-row">
            <button class="qty-btn" onclick="changeQty(${i},-1)">−</button>
            <span class="qty-val">${item.qty}</span>
            <button class="qty-btn" onclick="changeQty(${i},1)">+</button>
          </div>
          <div class="ci-subtotal">${fmt(item.qty*item.price)}</div>
        </div>
      </div>`).join('');
  }
  calcCart();
}
function changeQty(i,d){
  const item=cart[i]; if(!item) return;
  if(d>0){
    const p=products.find(x=>x.id===item.productId);
    if(p && item.qty+d>p.stock){ toast(`สต๊อกไม่พอ (เหลือ ${p.stock})`,'error'); return; }
  }
  item.qty+=d;
  if(item.qty<=0)cart.splice(i,1);
  updateCartFab();renderCart();
}
function clearCart(){cart=[];updateCartFab();renderCart();}

function calcCart() {
  const sub=cart.reduce((s,c)=>s+c.qty*c.price,0);
  const discV=+(document.getElementById('cs-discount-val')?.value)||0;
  const discT=document.getElementById('cs-discount-type')?.value||'฿';
  const disc=discT==='%'?sub*discV/100:discV;
  const after=Math.max(0,sub-disc);
  let vat=0;
  if(settings.vat==='exclude') vat=after*0.07;
  if(settings.vat==='include') vat=after-after/1.07;
  const total=after+(settings.vat==='exclude'?vat:0);
  const el=id=>document.getElementById(id);
  if(el('cs-subtotal')) el('cs-subtotal').textContent=fmt(sub);
  if(el('cs-vat')) el('cs-vat').textContent=fmt(vat);
  if(el('cs-total')) el('cs-total').textContent=fmt(total);
}
function getCartTotal(){
  const sub=cart.reduce((s,c)=>s+c.qty*c.price,0);
  const discV=+(document.getElementById('cs-discount-val')?.value)||0;
  const discT=document.getElementById('cs-discount-type')?.value||'฿';
  const disc=discT==='%'?sub*discV/100:discV;
  const after=Math.max(0,sub-disc);
  const vat=settings.vat==='exclude'?after*0.07:settings.vat==='include'?after-after/1.07:0;
  const total=after+(settings.vat==='exclude'?vat:0);
  return {subtotal:sub,discount:disc,vat,total};
}

// ═══════════════════════════════════════════════
// PAYMENT
// ═══════════════════════════════════════════════
function openPayment(){
  if(!cart.length){toast('ยังไม่มีสินค้า','warning');return;}
  payReceived='';
  const{total}=getCartTotal();
  document.getElementById('pay-total-display').textContent=fmt(total);
  document.getElementById('pay-received-display').textContent='0';
  document.getElementById('pay-change-display').textContent='฿0.00';
  setPayType('เงินสด');
  openModal('modal-payment');
}
function setPayType(t){
  currentPayType=t;
  ['cash','transfer','card'].forEach(x=>{
    document.getElementById('pay-'+x+'-btn').classList.toggle('active',
      (x==='cash'&&t==='เงินสด')||(x==='transfer'&&t==='โอน')||(x==='card'&&t==='บัตร'));
  });
  document.getElementById('pay-cash-section').style.display=t==='เงินสด'?'block':'none';
  document.getElementById('pay-transfer-section').style.display=t!=='เงินสด'?'block':'none';
}
function keyPad(k){
  const{total}=getCartTotal();
  if(k==='C') payReceived='';
  else if(k==='BACK') payReceived=payReceived.slice(0,-1);
  else if(k==='.'&&payReceived.includes('.')) return;
  else payReceived+=k;
  const v=+payReceived||0;
  document.getElementById('pay-received-display').textContent=payReceived||'0';
  const change=v-total;
  document.getElementById('pay-change-display').textContent=fmt(Math.max(0,change));
}
function quickCash(amount){
  const{total}=getCartTotal();
  const current=+payReceived||0;
  payReceived=String(current+amount);
  document.getElementById('pay-received-display').textContent=payReceived||'0';
  const change=(+payReceived||0)-total;
  document.getElementById('pay-change-display').textContent=fmt(Math.max(0,change));
}
function confirmPayment(){
  const{subtotal,discount,vat,total}=getCartTotal();
  let received=total,change=0;
  if(currentPayType==='เงินสด'){
    received=+payReceived||0;
    if(received<total){toast('รับเงินไม่พอ','error');return;}
    change=received-total;
  } else {
    received=+(document.getElementById('pay-transfer-amt').value)||total;
    if(received<total){toast('ยอดโอนไม่พอ','error');return;}
  }
  const billNo='B'+String(billCounter).padStart(5,'0'); billCounter++;
  const sale={
    id:uid(),billNo,date:new Date().toISOString(),
    items:cart.map(c=>({
      productId:c.productId,name:c.name,
      qty:c.qty,price:c.price,subtotal:c.qty*c.price,
      cost:(products.find(x=>x.id===c.productId)?.cost||0)
    })),
    subtotal,discount,vat,total,received,change,payType:currentPayType,note:''
  };
  sale.items.forEach(item=>{
    const p=products.find(x=>x.id===item.productId);
    if(p) p.stock=Math.max(0,p.stock-item.qty);
  });
  sales.push(sale); save();
  closeModal('modal-payment'); closeModal('cart-sheet');
  showReceipt(sale);
}
function showReceipt(sale){
  document.getElementById('receipt-content').innerHTML=`<div class="receipt">
    <div class="receipt-header">
      <div style="font-size:14px;font-weight:700">${esc(settings.storeName)}</div>
      ${settings.storeAddr?`<div style="font-size:11px">${esc(settings.storeAddr)}</div>`:''}
      ${settings.storePhone?`<div style="font-size:11px">โทร ${esc(settings.storePhone)}</div>`:''}
      <div style="margin-top:4px;font-size:11px">${thDT(sale.date)}</div>
      <div style="font-size:11px">บิล: ${sale.billNo}</div>
    </div>
    <hr class="receipt-divider">
    ${sale.items.map(i=>`<div class="receipt-row"><span>${esc(i.name)} ×${i.qty}</span><span>${fmtN(i.subtotal)}</span></div>`).join('')}
    <hr class="receipt-divider">
    <div class="receipt-row"><span>รวม</span><span>${fmtN(sale.subtotal)}</span></div>
    ${sale.discount>0?`<div class="receipt-row"><span>ส่วนลด</span><span>-${fmtN(sale.discount)}</span></div>`:''}
    ${sale.vat>0?`<div class="receipt-row"><span>VAT</span><span>${fmtN(sale.vat)}</span></div>`:''}
    <hr class="receipt-divider">
    <div class="receipt-row receipt-total"><span>ยอดรวม</span><span>${fmtN(sale.total)}</span></div>
    <div class="receipt-row"><span>รับ (${sale.payType})</span><span>${fmtN(sale.received)}</span></div>
    ${sale.change>0?`<div class="receipt-row"><span>ทอน</span><span>${fmtN(sale.change)}</span></div>`:''}
    <hr class="receipt-divider">
    <div style="text-align:center;font-size:11px">ขอบคุณที่ใช้บริการ</div>
  </div>`;
  openModal('modal-receipt');
}
function printReceipt(){window.print();}
function newBill(){
  closeModal('modal-receipt'); cart=[]; updateCartFab();
  document.getElementById('cs-discount-val').value=0;
  renderCart(); renderPosProducts();
  document.getElementById('pos-bill-no').textContent='บิล #B'+String(billCounter).padStart(5,'0');
}
function addDebtSale(){
  if(!cart.length){toast('ยังไม่มีสินค้า','warning');return;}
  creditSaleMode = true;
  editingDebtId = null;
  document.getElementById('debt-modal-title').textContent = '💳 ขายเชื่อ';
  document.getElementById('dm-name').value = '';
  document.getElementById('dm-phone').value = '';
  const {total} = getCartTotal();
  document.getElementById('dm-amount').value = total.toFixed(2);
  document.getElementById('dm-amount').readOnly = true;
  document.getElementById('dm-date').value = today();
  document.getElementById('dm-note').value = cart.map(c=>c.name).join(', ');
  openModal('modal-debt');
}
function finalizeCreditSale(name,phone,note){
  const{total}=getCartTotal();
  const billNo='B'+String(billCounter).padStart(5,'0'); billCounter++;
  const sale={
    id:uid(),billNo,date:new Date().toISOString(),
    items:cart.map(c=>({productId:c.productId,name:c.name,qty:c.qty,price:c.price,subtotal:c.qty*c.price,cost:products.find(x=>x.id===c.productId)?.cost||0})),
    subtotal:total,discount:0,vat:0,total,received:0,change:0,payType:'เชื่อ',note:`ลูกค้า: ${name}`
  };
  cart.forEach(c=>{const p=products.find(x=>x.id===c.productId);if(p)p.stock=Math.max(0,p.stock-c.qty);});
  sales.push(sale);
  debts.push({id:uid(),customer:name,phone,billNo,billId:sale.id,amount:total,paid:0,date:today(),note:note||sale.items.map(i=>i.name).join(', '),status:'ค้าง',payments:[]});
  save(); cart=[]; updateCartFab(); closeModal('cart-sheet'); renderPosProducts();
  toast(`ขายเชื่อ ${name} ${fmt(total)}`,'info');
}
function holdCurrentCart(){
  if(!cart.length){toast('ไม่มีสินค้าในรายการ','warning');return;}
  const n=`บิล ${holdBills.length+1}`;
  holdBills.push({id:uid(),name:n,cart:[...cart],time:new Date().toISOString()});
  save(); cart=[]; updateCartFab(); closeModal('cart-sheet'); renderPosProducts();
  toast(`พักบิล "${n}" แล้ว`);
}
function openHoldBillsPage(){
  const list=document.getElementById('hold-bills-list');
  list.innerHTML=holdBills.length?holdBills.map((b,i)=>`
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:12px;margin-bottom:8px">
      <div style="font-weight:600">${esc(b.name)}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">${b.cart.length} รายการ · ${thDT(b.time)}</div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" style="flex:1" onclick="resumeHold(${i})">เรียก</button>
        <button class="btn btn-danger btn-sm" onclick="deleteHold(${i})">ลบ</button>
      </div>
    </div>`).join('') : '<div class="empty-state"><div class="empty-text">ไม่มีบิลพัก</div></div>';
  openModal('modal-hold');
}
function resumeHold(i){
  if(cart.length&&!confirm('แทนที่รายการปัจจุบัน?')) return;
  cart=[...holdBills[i].cart]; holdBills.splice(i,1);
  save(); closeModal('modal-hold'); updateCartFab();
  openCartSheet(); renderCart(); toast('เรียกบิลแล้ว');
}
function deleteHold(i){holdBills.splice(i,1);save();openHoldBillsPage();}

// ═══════════════════════════════════════════════
// PURCHASE
// ═══════════════════════════════════════════════
function openPurchaseModal(){
  document.getElementById('pur-date').value=today();
  document.getElementById('pur-supplier').value='';
  document.getElementById('pur-items-list').innerHTML='';
  addPurItem(); openModal('modal-purchase');
}
function addPurItem(){
  const c=document.getElementById('pur-items-list');
  const id=uid();
  const d=document.createElement('div'); d.className='pur-item-row'; d.id='pr-'+id;
  d.innerHTML=`
    <select class="pr-prod">
      <option value="">เลือกสินค้า...</option>
      ${products.map(p=>`<option value="${p.id}">${esc(p.name)} (${esc(p.barcode)})</option>`).join('')}
    </select>
    <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:8px;align-items:flex-end">
      <div><label style="font-size:11px">จำนวน</label><input type="number" class="pr-qty" value="1" min="1" inputmode="numeric"></div>
      <div><label style="font-size:11px">ราคา/หน่วย</label><input type="number" class="pr-price" value="0" step="0.01" inputmode="decimal"></div>
      <button class="btn-icon" style="margin-bottom:0" onclick="document.getElementById('pr-${id}').remove()">✕</button>
    </div>`;
  c.appendChild(d);
}
function savePurchase(){
  const date=document.getElementById('pur-date').value;
  const supplier=document.getElementById('pur-supplier').value;
  const rows=document.getElementById('pur-items-list').querySelectorAll('.pur-item-row');
  const items=[];
  rows.forEach(r=>{
    const pid=r.querySelector('.pr-prod').value;
    const qty=+r.querySelector('.pr-qty').value||0;
    const price=+r.querySelector('.pr-price').value||0;
    if(!pid||qty<=0) return;
    const p=products.find(x=>x.id===pid); if(!p) return;
    p.stock += qty;
    items.push({productId:pid,name:p.name,product_id:p.product_id||'',barcode:p.barcode||'',qty,price,total:qty*price});
  });
  if(!items.length){toast('ไม่มีรายการสินค้า','error');return;}
  purchases.push({id:uid(),date,supplier,items,createdAt:Date.now()});
  save(); closeModal('modal-purchase'); renderPurchases(); renderPosProducts();
  toast('บันทึกการสั่งซื้อแล้ว');
}
function renderPurchases(){
  const from=document.getElementById('pur-date-from')?.value;
  const to=document.getElementById('pur-date-to')?.value;
  let list=purchases;
  if(from) list=list.filter(x=>x.date>=from);
  if(to) list=list.filter(x=>x.date<=to);
  const c=document.getElementById('pur-list'); if(!c) return;
  if(!list.length){c.innerHTML='<div class="empty-state"><div class="empty-icon">🚚</div><div class="empty-text">ไม่พบการสั่งซื้อ</div></div>';return;}
  c.innerHTML=[...list].reverse().map(p=>{
    const total=p.items.reduce((s,i)=>s+i.total,0);
    return `<div class="pur-list-item">
      <div class="pur-date">${thDate(p.date)} · ${esc(p.supplier||'ไม่ระบุผู้จำหน่าย')}</div>
      <div class="pur-main">${esc(p.items.map(i=>i.name).join(', '))}</div>
      <div class="pur-sub">${p.items.length} รายการ · รวม ${fmt(total)}</div>
    </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════
// STOCK ADJUST
// ═══════════════════════════════════════════════
function renderAdjList(){
  const q=(document.getElementById('adj-search')?.value||'').toLowerCase();
  const list=products.filter(p=>!q||p.name.toLowerCase().includes(q));
  const c=document.getElementById('adj-list'); if(!c) return;
  c.innerHTML=list.map(p=>`
    <div class="adj-row">
      <div class="adj-name">${esc(p.name)}</div>
      <div class="adj-cur">${p.stock}</div>
      <input type="number" class="adj-input" id="adj-${p.id}" placeholder="ใหม่" inputmode="numeric" oninput="if(this.value==='')delete adjChanges['${p.id}'];else adjChanges['${p.id}']=+this.value">
    </div>`).join('');
}
function saveStockAdjust(){
  let count=0;
  Object.entries(adjChanges).forEach(([id,val])=>{
    const p=products.find(x=>x.id===id);
    if(p&&!isNaN(val)){p.stock=val;count++;}
  });
  if(!count){toast('ไม่มีการเปลี่ยนแปลง','info');return;}
  adjChanges={}; save(); closeModal('modal-stock-adjust'); renderPosProducts();
  toast(`ปรับสต๊อก ${count} รายการแล้ว`);
}

// ═══════════════════════════════════════════════
// DEBT
// ═══════════════════════════════════════════════
function openDebtModal(id=null){
  editingDebtId=id;
  creditSaleMode=false;
  document.getElementById('dm-amount').readOnly=false;
  document.getElementById('debt-modal-title').textContent=id?'✏️ แก้ไข':'+ เพิ่มลูกหนี้';
  if(id){
    const d=debts.find(x=>x.id===id); if(!d) return;
    document.getElementById('dm-name').value=d.customer;
    document.getElementById('dm-phone').value=d.phone||'';
    document.getElementById('dm-amount').value=d.amount;
    document.getElementById('dm-date').value=d.date;
    document.getElementById('dm-note').value=d.note||'';
  } else {
    document.getElementById('dm-name').value='';
    document.getElementById('dm-phone').value='';
    document.getElementById('dm-amount').value='';
    document.getElementById('dm-date').value=today();
    document.getElementById('dm-note').value='';
  }
  openModal('modal-debt');
}
function saveDebt(){
  const name=document.getElementById('dm-name').value.trim();
  if(!name){toast('กรุณากรอกชื่อ','error');return;}
  if(creditSaleMode){
    const phone=document.getElementById('dm-phone').value.trim();
    const note=document.getElementById('dm-note').value.trim();
    creditSaleMode=false;
    document.getElementById('dm-amount').readOnly=false;
    closeModal('modal-debt');
    finalizeCreditSale(name,phone,note);
    return;
  }
  const data={
    id:editingDebtId||uid(),customer:name,
    phone:document.getElementById('dm-phone').value,
    billNo:editingDebtId?(debts.find(x=>x.id===editingDebtId)?.billNo||'-'):'-',
    amount:+document.getElementById('dm-amount').value||0,
    paid:editingDebtId?(debts.find(x=>x.id===editingDebtId)?.paid||0):0,
    date:document.getElementById('dm-date').value,
    note:document.getElementById('dm-note').value,
    status:'ค้าง',
    payments:editingDebtId?(debts.find(x=>x.id===editingDebtId)?.payments||[]):[]
  };
  data.status=data.paid>=data.amount?'ชำระแล้ว':'ค้าง';
  if(editingDebtId){const i=debts.findIndex(x=>x.id===editingDebtId);if(i!==-1)debts[i]=data;}
  else debts.push(data);
  save(); closeModal('modal-debt'); renderDebts(); toast('บันทึกแล้ว');
}
function openPayDebt(id){
  currentDebtId=id;
  const d=debts.find(x=>x.id===id);
  document.getElementById('pd-name').value=d.customer;
  document.getElementById('pd-outstanding').value=d.amount-d.paid;
  document.getElementById('pd-pay-amt').value=d.amount-d.paid;
  openModal('modal-pay-debt');
}
function confirmPayDebt(){
  const d=debts.find(x=>x.id===currentDebtId);
  const amt=+document.getElementById('pd-pay-amt').value||0;
  d.paid+=amt; d.payments=d.payments||[];
  d.payments.push({amount:amt,date:today()});
  if(d.paid>=d.amount) d.status='ชำระแล้ว';
  save(); closeModal('modal-pay-debt'); renderDebts(); toast(`รับชำระ ${fmt(amt)}`);
}
function deleteDebt(id){
  if(!confirm('ลบรายการนี้?')) return;
  debts=debts.filter(x=>x.id!==id); save(); renderDebts(); toast('ลบแล้ว','warning');
}
function renderDebts(){
  const outstanding=debts.filter(d=>d.status==='ค้าง').reduce((s,d)=>s+d.amount-d.paid,0);
  document.getElementById('debt-outstanding').textContent=fmt(outstanding);
  document.getElementById('debt-bill-count').textContent=debts.filter(d=>d.status==='ค้าง').length;
  const c=document.getElementById('debt-list'); if(!c) return;
  if(!debts.length){c.innerHTML='<div class="empty-state"><div class="empty-icon">💳</div><div class="empty-text">ไม่มีลูกหนี้</div></div>';return;}
  c.innerHTML=debts.map(d=>{
    const out=d.amount-d.paid;
    const isPaid=d.status==='ชำระแล้ว';
    return `<div class="debt-card">
      <div class="flex-between">
        <div class="debt-name">${esc(d.customer)}</div>
        <span class="badge ${isPaid?'badge-green':'badge-amber'}">${d.status}</span>
      </div>
      <div class="debt-meta">${thDate(d.date)} · ${esc(d.note||d.billNo)}</div>
      <div style="margin-top:8px" class="flex-between">
        <div>
          <div style="font-size:11px;color:var(--text-muted)">ยอด / ชำระแล้ว</div>
          <div style="font-family:var(--mono);font-size:13px">${fmt(d.amount)} / <span class="text-green">${fmt(d.paid)}</span></div>
        </div>
        <div class="debt-amount">${fmt(out)}</div>
      </div>
      <div class="debt-footer">
        ${!isPaid?`<button class="btn btn-amber btn-sm" style="flex:1" onclick="openPayDebt('${d.id}')">💰 รับชำระ</button>`:''}
        <button class="btn-icon" onclick="openDebtModal('${d.id}')">✏️</button>
        <button class="btn-icon" onclick="deleteDebt('${d.id}')">🗑️</button>
      </div>
    </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════
// EXPENSE
// ═══════════════════════════════════════════════
function openExpense(){
  document.getElementById('exp-name').value='';
  document.getElementById('exp-amount').value='';
  document.getElementById('exp-date').value=today();
  document.getElementById('exp-note').value='';
  openModal('modal-expense');
}
function saveExpense(){
  const name=document.getElementById('exp-name').value.trim();
  const amount=+document.getElementById('exp-amount').value||0;
  if(!name||!amount){toast('กรอกรายการและจำนวนเงิน','error');return;}
  expenses.push({id:uid(),name,amount,date:document.getElementById('exp-date').value,note:document.getElementById('exp-note').value,createdAt:Date.now()});
  save(); closeModal('modal-expense'); toast('บันทึกรายจ่ายแล้ว');
}

// ═══════════════════════════════════════════════
// REPORTS
// ═══════════════════════════════════════════════
function switchReportTab(tab){
  ['sales','stock','expense'].forEach(t=>{
    document.getElementById('rtab-'+t).style.display=t===tab?'block':'none';
  });
  document.querySelectorAll('#report-tabs .tab-btn').forEach((b,i)=>{
    b.classList.toggle('active',['sales','stock','expense'][i]===tab);
  });
  if(tab==='stock') renderStockReport();
  if(tab==='expense'){setDateRange('month','pur');renderPurchaseReport();}
}

function setDateRange(range,which){
  let from='',to=today();
  if(range==='today') from=today();
  else if(range==='week'){const d=new Date();d.setDate(d.getDate()-6);from=ymd(d);}
  else if(range==='month') from=today().slice(0,7)+'-01';
  else if(range==='year') from=today().slice(0,4)+'-01-01';
  if(which==='sale'){
    const f=document.getElementById('rep-sale-from');const t2=document.getElementById('rep-sale-to');
    if(f)f.value=from; if(t2)t2.value=to;
    renderSalesReport();
  } else {
    const f=document.getElementById('rep-pur-from');const t2=document.getElementById('rep-pur-to');
    if(f)f.value=from; if(t2)t2.value=to;
    renderPurchaseReport();
  }
}
function filterByDate(list,fromId,toId,df='date'){
  const from=document.getElementById(fromId)?.value;
  const to=document.getElementById(toId)?.value;
  return list.filter(x=>{
    const d=(x[df]||'').slice(0,10);
    if(from&&d<from) return false;
    if(to&&d>to) return false;
    return true;
  });
}

function renderSalesReport(){
  const list=filterByDate(sales,'rep-sale-from','rep-sale-to');
  const total=list.reduce((s,x)=>s+x.total,0);
  const profit=list.reduce((s,x)=>s+x.items.reduce((ss,i)=>ss+(i.subtotal-(i.cost||0)*i.qty),0),0);
  document.getElementById('rs-total').textContent=fmt(total);
  document.getElementById('rs-profit').textContent=fmt(profit);
  document.getElementById('rs-bills').textContent=list.length;
  document.getElementById('rs-avg').textContent=list.length?fmt(total/list.length):'฿0';

  const dayMap={};
  list.forEach(s=>{const d=s.date.slice(0,10);dayMap[d]=(dayMap[d]||0)+s.total;});
  const labels=Object.keys(dayMap).sort();
  const ctx=document.getElementById('salesChart');
  if(salesChartInst) salesChartInst.destroy();
  salesChartInst=new Chart(ctx,{
    type:'bar',
    data:{labels,datasets:[{label:'ยอดขาย',data:labels.map(l=>dayMap[l]),backgroundColor:'rgba(45,212,191,0.4)',borderColor:'#2DD4BF',borderWidth:1.5}]},
    options:{responsive:true,plugins:{legend:{labels:{color:'#94A3B8',boxWidth:12}}},scales:{x:{ticks:{color:'#64748B',maxRotation:45}},y:{ticks:{color:'#64748B',callback:v=>'฿'+v.toLocaleString()}}}}
  });

  const catMap={};
  list.forEach(s=>s.items.forEach(i=>{
    const p=products.find(x=>x.id===i.productId);
    const cat=p?.category||'ไม่ระบุหมวด';
    catMap[cat]=(catMap[cat]||0)+i.subtotal;
  }));
  const catLabels=Object.keys(catMap).sort((a,b)=>catMap[b]-catMap[a]);
  const catColors=['#2DD4BF','#F59E0B','#EF4444','#3B82F6','#A855F7','#22C55E','#EC4899','#F97316','#14B8A6','#6366F1'];
  const catCtx=document.getElementById('categoryChart');
  if(categoryChartInst) categoryChartInst.destroy();
  if(catLabels.length){
    categoryChartInst=new Chart(catCtx,{
      type:'doughnut',
      data:{labels:catLabels,datasets:[{data:catLabels.map(l=>catMap[l]),backgroundColor:catLabels.map((_,i)=>catColors[i%catColors.length])}]},
      options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#94A3B8',boxWidth:12,font:{size:10}}}}}
    });
  }

  const pm={};
  list.forEach(s=>s.items.forEach(i=>{if(!pm[i.name])pm[i.name]={qty:0,total:0,profit:0};pm[i.name].qty+=i.qty;pm[i.name].total+=i.subtotal;pm[i.name].profit+=(i.subtotal-(i.cost||0)*i.qty);}));
  const tops=Object.entries(pm).sort((a,b)=>b[1].total-a[1].total).slice(0,10);
  document.getElementById('rs-top-list').innerHTML=tops.map(([n,v],i)=>`
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
      <div><span style="color:var(--text-muted);font-size:11px">#${i+1}</span> ${esc(n)}</div>
      <div style="text-align:right"><div style="font-family:var(--mono);font-size:13px;font-weight:600">${fmt(v.total)}</div><div style="font-size:10px;color:var(--green)">${v.qty} ชิ้น</div></div>
    </div>`).join('')||'<div class="empty-state" style="padding:20px"><div class="empty-text">ไม่มีข้อมูล</div></div>';

  document.getElementById('rs-detail-list').innerHTML=[...list].reverse().slice(0,30).map(s=>`
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
      <div><div style="font-size:13px;font-weight:600">${s.billNo}</div><div style="font-size:11px;color:var(--text-muted)">${thDT(s.date)} · ${s.payType}</div></div>
      <div style="text-align:right"><div style="font-family:var(--mono);font-size:13px;font-weight:600;color:var(--teal)">${fmt(s.total)}</div></div>
    </div>`).join('')||'<div class="empty-state" style="padding:20px"><div class="empty-text">ไม่มีข้อมูล</div></div>';
}

function setCompareRange(mode){
  const af=document.getElementById('cmp-a-from'),at=document.getElementById('cmp-a-to');
  const bf=document.getElementById('cmp-b-from'),bt=document.getElementById('cmp-b-to');
  if(mode==='mom'){
    at.value=today(); af.value=today().slice(0,7)+'-01';
    const d=new Date(); d.setDate(1); d.setDate(d.getDate()-1);
    bt.value=ymd(d);
    bf.value=bt.value.slice(0,7)+'-01';
  } else if(mode==='wow'){
    at.value=today();
    const d1=new Date(); d1.setDate(d1.getDate()-6); af.value=ymd(d1);
    const d2=new Date(); d2.setDate(d2.getDate()-7); bt.value=ymd(d2);
    const d3=new Date(); d3.setDate(d3.getDate()-13); bf.value=ymd(d3);
  }
  renderCompareReport();
}
function periodSummary(from,to){
  const list=sales.filter(s=>{const d=s.date.slice(0,10); return (!from||d>=from)&&(!to||d<=to);});
  const total=list.reduce((s,x)=>s+x.total,0);
  const profit=list.reduce((s,x)=>s+x.items.reduce((ss,i)=>ss+(i.subtotal-(i.cost||0)*i.qty),0),0);
  return {list,total,profit,bills:list.length,avg:list.length?total/list.length:0};
}
function renderCompareReport(){
  const af=document.getElementById('cmp-a-from')?.value, at=document.getElementById('cmp-a-to')?.value;
  const bf=document.getElementById('cmp-b-from')?.value, bt=document.getElementById('cmp-b-to')?.value;
  const a=periodSummary(af,at), b=periodSummary(bf,bt);
  const pct=(x,y)=>y===0?(x===0?0:null):((x-y)/y*100);
  const c=document.getElementById('cmp-stats'); if(!c) return;
  const mkDiff=v=>{ if(v===null||v===undefined||!isFinite(v)) return '<span style="font-size:11px;color:var(--text-muted)">—</span>'; const n=+v; return `<span style="font-size:11px;color:${n>=0?'var(--green)':'var(--red)'}">${n>=0?'▲':'▼'}${Math.abs(n).toFixed(1)}%</span>`; };
  c.innerHTML=`
    <div class="stat-card"><div class="stat-label">ยอดขาย A</div><div class="stat-value text-teal">${fmt(a.total)}</div>${mkDiff(pct(a.total,b.total))}</div>
    <div class="stat-card"><div class="stat-label">ยอดขาย B</div><div class="stat-value">${fmt(b.total)}</div></div>
    <div class="stat-card"><div class="stat-label">กำไร A</div><div class="stat-value text-green">${fmt(a.profit)}</div>${mkDiff(pct(a.profit,b.profit))}</div>
    <div class="stat-card"><div class="stat-label">กำไร B</div><div class="stat-value">${fmt(b.profit)}</div></div>
    <div class="stat-card"><div class="stat-label">บิล A</div><div class="stat-value">${a.bills}</div></div>
    <div class="stat-card"><div class="stat-label">บิล B</div><div class="stat-value">${b.bills}</div></div>
  `;
  const ctx=document.getElementById('compareChart');
  if(compareChartInst) compareChartInst.destroy();
  compareChartInst=new Chart(ctx,{
    type:'bar',
    data:{labels:['ยอดขาย','กำไร','จำนวนบิล','เฉลี่ย/บิล'],
      datasets:[
        {label:`A (${af||'-'} ถึง ${at||'-'})`,data:[a.total,a.profit,a.bills,a.avg],backgroundColor:'rgba(45,212,191,0.5)',borderColor:'#2DD4BF',borderWidth:1.5},
        {label:`B (${bf||'-'} ถึง ${bt||'-'})`,data:[b.total,b.profit,b.bills,b.avg],backgroundColor:'rgba(245,158,11,0.5)',borderColor:'#F59E0B',borderWidth:1.5}
      ]},
    options:{responsive:true,plugins:{legend:{labels:{color:'#94A3B8',boxWidth:12,font:{size:10}}}},scales:{x:{ticks:{color:'#64748B'}},y:{ticks:{color:'#64748B'}}}}
  });
}
function exportCompareExcel(){
  const af=document.getElementById('cmp-a-from')?.value, at=document.getElementById('cmp-a-to')?.value;
  const bf=document.getElementById('cmp-b-from')?.value, bt=document.getElementById('cmp-b-to')?.value;
  const a=periodSummary(af,at), b=periodSummary(bf,bt);
  const summaryRows=[
    ['รายการ',`ช่วง A (${af||'-'} ถึง ${at||'-'})`,`ช่วง B (${bf||'-'} ถึง ${bt||'-'})`],
    ['ยอดขายรวม',a.total,b.total],
    ['กำไรรวม',a.profit,b.profit],
    ['จำนวนบิล',a.bills,b.bills],
    ['เฉลี่ย/บิล',a.avg,b.avg],
  ];
  const aRows=[['วันที่','บิล','สินค้า','ยอดรวม','ชำระ']];
  a.list.forEach(s=>aRows.push([thDT(s.date),s.billNo,s.items.map(i=>i.name).join(','),s.total,s.payType]));
  const bRows=[['วันที่','บิล','สินค้า','ยอดรวม','ชำระ']];
  b.list.forEach(s=>bRows.push([thDT(s.date),s.billNo,s.items.map(i=>i.name).join(','),s.total,s.payType]));
  exportXLSXMulti([
    {name:'สรุปเปรียบเทียบ',rows:summaryRows},
    {name:'ช่วง A',rows:aRows},
    {name:'ช่วง B',rows:bRows},
  ],'compare_report.xlsx');
  toast('Export แล้ว');
}

function renderStockReport(){
  const expWarn=new Date(); expWarn.setDate(expWarn.getDate()+settings.expiryDays);
  const totalVal=products.reduce((s,p)=>s+p.stock*(p.cost||0),0);
  const lowCount=products.filter(p=>p.stock>0&&p.stock<=settings.lowStock).length;
  const outCount=products.filter(p=>p.stock<=0).length;
  document.getElementById('rst-total').textContent=products.length;
  document.getElementById('rst-value').textContent=fmt(totalVal);
  document.getElementById('rst-low').textContent=lowCount;
  document.getElementById('rst-out').textContent=outCount;
  const c=document.getElementById('rst-list'); if(!c) return;
  c.innerHTML=products.map(p=>{
    const stockCls=p.stock<=0?'stock-out':p.stock<=settings.lowStock?'stock-low':'stock-ok';
    return `<div class="prod-list-item">
      <div class="pli-info">
        <div class="pli-name">${esc(p.name)}</div>
        <div class="pli-meta">รหัส: ${esc(p.product_id||'-')} · Barcode: ${esc(p.barcode||'-')} · ${esc(p.category||'-')}</div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:3px;font-family:var(--mono)">ราคาขาย ${fmt(p.price)} · ทุน ${fmt(p.cost)} · มูลค่า ${fmt(p.stock*(p.cost||0))}</div>
      </div>
      <span class="pli-stock ${stockCls}">${p.stock<=0?'หมด':p.stock<=settings.lowStock?`⚠️${p.stock}`:p.stock}</span>
    </div>`;
  }).join('')||'<div class="empty-state"><div class="empty-text">ไม่มีสินค้า</div></div>';
}

function renderPurchaseReport(){
  const purList=filterByDate(purchases,'rep-pur-from','rep-pur-to');
  const expList=filterByDate(expenses,'rep-pur-from','rep-pur-to');
  const purTotal=purList.reduce((s,p)=>s+p.items.reduce((ss,i)=>ss+i.total,0),0);
  const expTotal=expList.reduce((s,e)=>s+e.amount,0);
  document.getElementById('rp-goods').textContent=fmt(purTotal);
  document.getElementById('rp-expense').textContent=fmt(expTotal);
  document.getElementById('rp-total').textContent=fmt(purTotal+expTotal);

  const dayMap={};
  purList.forEach(p=>{const d=p.date;dayMap[d]=dayMap[d]||{goods:0,exp:0};p.items.forEach(i=>dayMap[d].goods+=i.total);});
  expList.forEach(e=>{const d=e.date;dayMap[d]=dayMap[d]||{goods:0,exp:0};dayMap[d].exp+=e.amount;});
  const labels=Object.keys(dayMap).sort();
  const ctx=document.getElementById('purChart');
  if(purChartInst) purChartInst.destroy();
  purChartInst=new Chart(ctx,{
    type:'bar',
    data:{labels,datasets:[
      {label:'ซื้อสินค้า',data:labels.map(l=>dayMap[l].goods),backgroundColor:'rgba(239,68,68,0.4)',borderColor:'#EF4444',borderWidth:1.5},
      {label:'รายจ่าย',data:labels.map(l=>dayMap[l].exp),backgroundColor:'rgba(245,158,11,0.4)',borderColor:'#F59E0B',borderWidth:1.5}
    ]},
    options:{responsive:true,plugins:{legend:{labels:{color:'#94A3B8',boxWidth:12}}},scales:{x:{ticks:{color:'#64748B',maxRotation:45}},y:{ticks:{color:'#64748B',callback:v=>'฿'+v.toLocaleString()}}}}
  });

  const rows=[];
  purList.forEach(p=>p.items.forEach(i=>rows.push({date:p.date,type:'ซื้อสินค้า',name:i.name,total:i.total,note:p.supplier||''})));
  expList.forEach(e=>rows.push({date:e.date,type:'รายจ่าย',name:e.name,total:e.amount,note:e.note||''}));
  rows.sort((a,b)=>b.date.localeCompare(a.date));
  document.getElementById('rp-list').innerHTML=rows.map(r=>`
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
      <div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">
          <span class="badge ${r.type==='ซื้อสินค้า'?'badge-red':'badge-amber'}" style="font-size:10px">${r.type}</span>
          <span style="font-size:13px;font-weight:600">${esc(r.name)}</span>
        </div>
        <div style="font-size:11px;color:var(--text-muted)">${thDate(r.date)} · ${esc(r.note)}</div>
      </div>
      <div style="font-family:var(--mono);font-size:13px;font-weight:600">${fmt(r.total)}</div>
    </div>`).join('')||'<div class="empty-state" style="padding:20px"><div class="empty-text">ไม่มีข้อมูล</div></div>';
}

// ═══════════════════════════════════════════════
// EXCEL EXPORT & IMPORT
// ═══════════════════════════════════════════════
function exportXLSX(data,sheet,file){
  const ws=XLSX.utils.aoa_to_sheet(data);
  const wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,sheet);
  XLSX.writeFile(wb,file);
}
function exportXLSXMulti(sheets,file){
  const wb=XLSX.utils.book_new();
  sheets.forEach(s=>{
    const ws=XLSX.utils.aoa_to_sheet(s.rows);
    XLSX.utils.book_append_sheet(wb,ws,s.name.slice(0,31));
  });
  XLSX.writeFile(wb,file);
}
function exportProductsExcel(){
  const rows=[['รหัสสินค้า','บาร์โค้ด','ชื่อสินค้า','หมวดหมู่','ราคาขาย','ต้นทุน','สต๊อก','วันหมดอายุ']];
  products.forEach(p=>{
    rows.push([p.product_id||'',p.barcode||'',p.name,p.category||'',p.price||0,p.cost||0,p.stock,p.expiry||'']);
  });
  exportXLSX(rows,'สินค้า','products.xlsx'); toast('Export แล้ว');
}
function exportSalesExcel(){
  const list=filterByDate(sales,'rep-sale-from','rep-sale-to');
  const rows=[['วันที่','บิล','สินค้า','ยอดรวม','ชำระ']];
  list.forEach(s=>rows.push([thDT(s.date),s.billNo,s.items.map(i=>i.name).join(','),s.total,s.payType]));

  const catMap={};
  list.forEach(s=>s.items.forEach(i=>{
    const p=products.find(x=>x.id===i.productId);
    const cat=p?.category||'ไม่ระบุหมวด';
    if(!catMap[cat]) catMap[cat]={qty:0,total:0};
    catMap[cat].qty+=i.qty; catMap[cat].total+=i.subtotal;
  }));
  const catRows=[['หมวดหมู่','จำนวนชิ้น','ยอดขายรวม']];
  Object.entries(catMap).sort((a,b)=>b[1].total-a[1].total).forEach(([cat,v])=>catRows.push([cat,v.qty,v.total]));

  exportXLSXMulti([
    {name:'ยอดขาย',rows},
    {name:'แยกตามหมวดหมู่',rows:catRows},
  ],'sales.xlsx');
  toast('Export แล้ว');
}
function exportStockExcel(){
  const rows=[['รหัสสินค้า','บาร์โค้ด','ชื่อสินค้า','หมวดหมู่','สต๊อก','ต้นทุน','มูลค่า']];
  products.forEach(p=>{
    rows.push([p.product_id||'',p.barcode||'',p.name,p.category||'',p.stock,p.cost||0,p.stock*(p.cost||0)]);
  });
  exportXLSX(rows,'สต๊อก','stock.xlsx'); toast('Export แล้ว');
}
function exportPurchaseExcel(){
  const list=filterByDate(purchases,'pur-date-from','pur-date-to');
  const rows=[['วันที่','ผู้จำหน่าย','สินค้า','จำนวน','ราคา/หน่วย','รวม']];
  list.forEach(p=>p.items.forEach(i=>rows.push([p.date,p.supplier||'',i.name,i.qty,i.price,i.total])));
  exportXLSX(rows,'สั่งซื้อ','purchase.xlsx'); toast('Export แล้ว');
}
function exportPurchaseRptExcel(){
  const purList=filterByDate(purchases,'rep-pur-from','rep-pur-to');
  const expList=filterByDate(expenses,'rep-pur-from','rep-pur-to');
  const rows=[['วันที่','ประเภท','รายการ','จำนวน','ราคา','รวม','หมายเหตุ']];
  purList.forEach(p=>p.items.forEach(i=>rows.push([p.date,'ซื้อสินค้า',i.name,i.qty,i.price,i.total,p.supplier||''])));
  expList.forEach(e=>rows.push([e.date,'รายจ่าย',e.name,1,e.amount,e.amount,e.note||'']));
  exportXLSX(rows,'รายจ่าย','expense.xlsx'); toast('Export แล้ว');
}

// ── IMPORT EXCEL ────────────────────────────────
function importExcel(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: 'array' });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const json = XLSX.utils.sheet_to_json(sheet);
      
      let imported = 0;
      let updated = 0;
      
      json.forEach(row => {
        const productId = (row['Master Product ID'] || row['รหัสสินค้า'] || row['Product ID'] || '').toString().trim();
        const barcode = (row['บาร์โค้ด'] || row['Barcode'] || row['barcode'] || '').toString().trim();
        const name = (row['ชื่อสินค้า'] || row['ชื่อสินค้า EN'] || '').toString().trim();
        const category = (row['หมวดหมู่'] || row['Category'] || '').toString().trim();
        const price = parseFloat(row['ราคาขาย'] || row['Price'] || row['ราคา'] || 0);
        const cost = parseFloat(row['ราคาทุน'] || row['Cost'] || row['ต้นทุน'] || 0);
        const stockRaw = row['สต๊อก'] ?? row['Stock'] ?? row['stock'];
        const stock = (stockRaw!==undefined && stockRaw!=='') ? (parseInt(stockRaw)||0) : null;
        const expiryRaw = row['วันที่เริ่มจำหน่าย'] || row['วันหมดอายุ'] || '';
        let expiry = '';
        if (expiryRaw) {
          const d = new Date(expiryRaw);
          if (!isNaN(d)) expiry = ymd(d);
        }
        
        if (!name || !barcode) return;
        
        let existing = products.find(p => p.product_id === productId || p.barcode === barcode);
        
        if (existing) {
          if (name) existing.name = name;
          if (category) existing.category = category;
          if (price > 0) existing.price = price;
          if (cost > 0) existing.cost = cost;
          if (stock !== null) existing.stock = stock;
          if (expiry) existing.expiry = expiry;
          if (productId) existing.product_id = productId;
          if (barcode) existing.barcode = barcode;
          updated++;
        } else {
          const newProduct = {
            id: uid(),
            product_id: productId || '',
            barcode: barcode,
            name: name,
            category: category || getCategoryFromProductId(productId),
            price: price || 0,
            cost: cost || 0,
            stock: stock !== null ? stock : 0,
            minStock: settings.lowStock || 5,
            expiry: expiry || '',
            createdAt: Date.now()
          };
          products.push(newProduct);
          imported++;
        }
      });
      
      save();
      renderProducts();
      renderPosProducts();
      updateCatChips();
      updateCategorySelects();
      toast(`✅ นำเข้าแล้ว ${imported} รายการ (อัปเดต ${updated} รายการ)`, 'success');
    } catch (err) {
      toast('เกิดข้อผิดพลาดในการอ่านไฟล์: ' + err.message, 'error');
      console.error(err);
    }
    event.target.value = '';
  };
  reader.readAsArrayBuffer(file);
}

// ── MASTER UPDATE: อัพเดทชื่อ+หมวดหมู่ จากไฟล์ Excel เท่านั้น ──
// (ไม่แตะราคา/ทุน/สต๊อก ต่างจาก importExcel ที่อัปเดตทุกฟิลด์)
function importMasterUpdate(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: 'array' });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const json = XLSX.utils.sheet_to_json(sheet);

      let updated = 0;
      let notFound = 0;

      json.forEach(row => {
        const productId = (row['Master Product ID'] || row['รหัสสินค้า'] || row['Product ID'] || '').toString().trim();
        const barcode = (row['บาร์โค้ด'] || row['Barcode'] || row['barcode'] || '').toString().trim();
        const name = (row['ชื่อสินค้า'] || row['ชื่อสินค้า EN'] || '').toString().trim();
        const category = (row['หมวดหมู่'] || row['Category'] || '').toString().trim();

        if (!productId && !barcode) return;

        const existing = products.find(p => (productId && p.product_id === productId) || (barcode && p.barcode === barcode));
        if (!existing) { notFound++; return; }

        if (name) existing.name = name;
        existing.category = category || getCategoryFromProductId(existing.product_id);
        updated++;
      });

      save();
      renderProducts();
      renderPosProducts();
      updateCatChips();
      updateCategorySelects();
      toast(`✅ อัปเดตชื่อ+หมวดหมู่แล้ว ${updated} รายการ${notFound ? ` (ไม่พบสินค้า ${notFound} รายการ)` : ''}`, 'success');
    } catch (err) {
      toast('เกิดข้อผิดพลาดในการอ่านไฟล์: ' + err.message, 'error');
      console.error(err);
    }
    event.target.value = '';
  };
  reader.readAsArrayBuffer(file);
}

// ── FULL DATA BACKUP / RESTORE ───────────────────
function exportBackupJSON(){
  const backup={products,sales,purchases,debts,expenses,settings,holdBills,billCounter,categoryMapping,exportedAt:new Date().toISOString(),version:1};
  const blob=new Blob([JSON.stringify(backup,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download=`qpos-backup-${today()}.json`; a.click();
  URL.revokeObjectURL(url);
  toast('สำรองข้อมูลแล้ว ✓');
}
function importBackupJSON(event){
  const file=event.target.files[0]; if(!file) return;
  const reader=new FileReader();
  reader.onload=e=>{
    try{
      const data=JSON.parse(e.target.result);
      if(!confirm('⚠️ การกู้คืนจะแทนที่ข้อมูลทั้งหมดในเครื่องนี้ ดำเนินการต่อ?')){event.target.value='';return;}
      products=data.products||[]; sales=data.sales||[]; purchases=data.purchases||[];
      debts=data.debts||[]; expenses=data.expenses||[]; settings=data.settings||settings;
      holdBills=data.holdBills||[]; billCounter=data.billCounter||1; categoryMapping=data.categoryMapping||categoryMapping;
      save();
      renderProducts(); renderPosProducts(); updateCatChips(); updateCategorySelects();
      renderMapping(); loadSettings();
      toast('กู้คืนข้อมูลแล้ว ✓');
    }catch(err){
      toast('ไฟล์ไม่ถูกต้อง: '+err.message,'error');
    }
    event.target.value='';
  };
  reader.readAsText(file);
}

// ── SCAN BARCODE FROM PHOTO (ถ่าย/เลือกรูป) ─────
async function scanBarcodeFromPhoto(event) {
  const file = event.target.files[0];
  event.target.value = '';
  if (!file) return;
  try {
    if (!('BarcodeDetector' in window)) {
      toast('เบราว์เซอร์นี้ไม่รองรับการอ่านบาร์โค้ดจากรูป กรุณากรอกรหัสสินค้าเอง', 'warning');
      return;
    }
    const detector = new BarcodeDetector();
    const bitmap = await createImageBitmap(file);
    const barcodes = await detector.detect(bitmap);
    if (barcodes.length > 0) {
      const code = barcodes[0].rawValue;
      document.getElementById('pos-search-input').value = code;
      addFirstResult();
      toast('พบ Barcode: ' + code, 'success');
    } else {
      toast('ไม่พบบาร์โค้ดในภาพ ลองถ่ายให้ใกล้ ชัด และแสงพอ', 'warning');
    }
  } catch (err) {
    toast('อ่านบาร์โค้ดจากภาพไม่สำเร็จ: ' + err.message, 'error');
    console.error(err);
  }
}

// ── SCAN BARCODE ─────────────────────────────────
async function scanBarcode() {
  try {
    if (!('BarcodeDetector' in window)) {
      toast('เบราว์เซอร์นี้ไม่รองรับกล้องสด ลองใช้ปุ่ม 🖼️ ถ่าย/เลือกรูปแทน', 'warning');
      return;
    }
    const detector = new BarcodeDetector();
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    const video = document.createElement('video');
    video.srcObject = stream;
    video.setAttribute('playsinline', '');
    video.style.width = '1px';
    video.style.height = '1px';
    video.style.position = 'absolute';
    video.style.top = '-100px';
    document.body.appendChild(video);
    
    await video.play();
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    stream.getTracks().forEach(t => t.stop());
    video.remove();
    
    const barcodes = await detector.detect(canvas);
    if (barcodes.length > 0) {
      const code = barcodes[0].rawValue;
      document.getElementById('pos-search-input').value = code;
      addFirstResult();
      toast('พบ Barcode: ' + code, 'success');
    } else {
      toast('ไม่พบบาร์โค้ดในภาพ', 'warning');
    }
  } catch (err) {
    toast('เปิดกล้องสดไม่สำเร็จ ลองใช้ปุ่ม 🖼️ ถ่าย/เลือกรูปแทน', 'error');
    console.error(err);
  }
}

// ── SCAN BARCODE → ฟอร์มเพิ่ม/แก้ไขสินค้า ─────────
async function scanBarcodeFromPhotoToProductForm(event) {
  const file = event.target.files[0];
  event.target.value = '';
  if (!file) return;
  try {
    if (!('BarcodeDetector' in window)) {
      toast('เบราว์เซอร์นี้ไม่รองรับการอ่านบาร์โค้ดจากรูป กรุณากรอกรหัสเอง', 'warning');
      return;
    }
    const detector = new BarcodeDetector();
    const bitmap = await createImageBitmap(file);
    const barcodes = await detector.detect(bitmap);
    if (barcodes.length > 0) {
      document.getElementById('pm-barcode').value = barcodes[0].rawValue;
      toast('พบ Barcode: ' + barcodes[0].rawValue, 'success');
    } else {
      toast('ไม่พบบาร์โค้ดในภาพ ลองถ่ายให้ใกล้ ชัด และแสงพอ', 'warning');
    }
  } catch (err) {
    toast('อ่านบาร์โค้ดจากภาพไม่สำเร็จ: ' + err.message, 'error');
    console.error(err);
  }
}

async function scanBarcodeToProductForm() {
  try {
    if (!('BarcodeDetector' in window)) {
      toast('เบราว์เซอร์นี้ไม่รองรับกล้องสด ลองใช้ปุ่ม 🖼️ ถ่าย/เลือกรูปแทน', 'warning');
      return;
    }
    const detector = new BarcodeDetector();
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    const video = document.createElement('video');
    video.srcObject = stream;
    video.setAttribute('playsinline', '');
    video.style.width = '1px';
    video.style.height = '1px';
    video.style.position = 'absolute';
    video.style.top = '-100px';
    document.body.appendChild(video);

    await video.play();

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    stream.getTracks().forEach(t => t.stop());
    video.remove();

    const barcodes = await detector.detect(canvas);
    if (barcodes.length > 0) {
      document.getElementById('pm-barcode').value = barcodes[0].rawValue;
      toast('พบ Barcode: ' + barcodes[0].rawValue, 'success');
    } else {
      toast('ไม่พบบาร์โค้ดในภาพ', 'warning');
    }
  } catch (err) {
    toast('เปิดกล้องสดไม่สำเร็จ ลองใช้ปุ่ม 🖼️ ถ่าย/เลือกรูปแทน', 'error');
    console.error(err);
  }
}

// ═══════════════════════════════════════════════
// SEED DATA
// ═══════════════════════════════════════════════
function seedDemoData(){
  if(products.length || DB.get('seeded', false)) return;
  DB.set('seeded', true);
  const seeds=[
    {product_id:'4111505', barcode:'8859733221136', name:'ไอโอร่าบิสกิตรสนมกระเป๋าหูรูดToyStory16ก.', price:25},
    {product_id:'4007475', barcode:'6942712001293', name:'เอมอสกัมมี่สติชรสพีชและบลูเบอร์รี่ 34 ก.(ด.)', price:30},
    {product_id:'3806366', barcode:'8850389122761', name:'น้ำวิตามินบลูบับเบิลกัม 500 มล.', price:35},
    {product_id:'2101210', barcode:'8858684528127', name:'แฮมพริกขี้หนู', price:45},
  ];
  products=seeds.map(s=>({
    id:uid(), product_id:s.product_id, barcode:s.barcode, name:s.name,
    category:getCategoryFromProductId(s.product_id),
    price:s.price, cost:0, stock:0, minStock:5, expiry:'', createdAt:Date.now()
  }));
  save();
}

// ═══════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════
window.addEventListener('DOMContentLoaded',()=>{
  seedDemoData();
  updateHeaderSubtitle();
  setActiveNav(currentPage);
  runPageInit(currentPage);

  const expWarn=new Date(); expWarn.setDate(expWarn.getDate()+settings.expiryDays);
  const alerts=products.filter(p=>p.stock<=settings.lowStock||(p.expiry&&new Date(p.expiry)<=expWarn));
  const nb=document.getElementById('nav-alert-badge');
  if(nb){ nb.textContent=alerts.length; nb.style.display=alerts.length?'flex':'none'; }
  if(alerts.length) setTimeout(()=>toast(`⚠️ ${alerts.length} รายการต้องตรวจสอบ`,'warning'),800);
});

function toggleMappingCard(){
  const body=document.getElementById('mapping-card-body');
  const chevron=document.getElementById('mapping-card-chevron');
  if(!body) return;
  const isOpen=body.style.display!=='none';
  body.style.display=isOpen?'none':'block';
  if(chevron){ chevron.style.display='inline-block'; chevron.style.transform=isOpen?'':'rotate(180deg)'; }
}
