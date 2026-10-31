#!/usr/bin/env node
/*
 * End-to-end browser tests for POS-MOBILE (index.html + script-pos.js).
 *
 * Plain Node script — no test framework. Needs only Node Playwright with a
 * Chromium build (`require('playwright')`), npm (to fetch SheetJS/Chart.js once
 * into a cache dir) and a static server serving the repo root (see run.sh).
 *
 *   E2E_BASE_URL   app URL (default http://127.0.0.1:${E2E_PORT:-8801}/)
 *   E2E_CACHE_DIR  where the vendored CDN libraries are cached
 *                  (default: $TMPDIR/pos-e2e-cache)
 *   E2E_ONLY       run only tests whose name contains this substring
 *   E2E_HEADED=1   show the browser
 *
 * CDN handling: cdnjs is not reachable from CI/sandbox, so every request to
 * https://cdnjs.cloudflare.com/** is answered from the npm packages
 * xlsx@0.18.5 / chart.js@4.4.0. SheetJS from npm is byte-identical to the
 * cdnjs file (its SRI hash matches index.html — asserted below). The cdnjs
 * Chart.js file "chart.umd.min.js" is a cdnjs re-minification that does not
 * exist in the npm package, so its bytes differ and Chromium's SRI check would
 * block it. For that script only, the served index.html is rewritten so the
 * integrity attribute holds the sha512 of the file we actually serve — SRI
 * stays enforced, nothing else in the document is touched.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const PORT = process.env.E2E_PORT || '8801';
const BASE = (process.env.E2E_BASE_URL || `http://127.0.0.1:${PORT}/`).replace(/\/?$/, '/');
const FILE_URL = 'file://' + path.join(ROOT, 'index.html');
const CACHE = process.env.E2E_CACHE_DIR || path.join(os.tmpdir(), 'pos-e2e-cache');
const OUT = path.join(CACHE, 'run-' + process.pid);
const ONLY = process.env.E2E_ONLY || '';

// ─────────────────────────────────────────────────────────────
// Vendored CDN libraries
// ─────────────────────────────────────────────────────────────
const VENDOR = [
  { cdn: 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js', pkg: 'xlsx', ver: '0.18.5', file: 'dist/xlsx.full.min.js' },
  { cdn: 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js', pkg: 'chart.js', ver: '4.4.0', file: 'dist/chart.umd.js' },
];

function ensureVendor() {
  fs.mkdirSync(CACHE, { recursive: true });
  for (const v of VENDOR) {
    const dir = path.join(CACHE, `${v.pkg}-${v.ver}`);
    v.dir = path.join(dir, 'package');
    v.path = path.join(v.dir, v.file);
    if (!fs.existsSync(v.path)) {
        console.log(`[vendor] fetching ${v.pkg}@${v.ver} with npm pack → ${dir}`);
      fs.mkdirSync(dir, { recursive: true });
      const out = execFileSync('npm', ['pack', `${v.pkg}@${v.ver}`, '--silent', '--pack-destination', dir], { encoding: 'utf8' });
      const tgz = path.join(dir, out.trim().split('\n').pop());
      execFileSync('tar', ['xzf', tgz, '-C', dir]);
    }
    v.body = fs.readFileSync(v.path);
    v.sri = 'sha512-' + crypto.createHash('sha512').update(v.body).digest('base64');
  }
}

const sriInHtml = (html, url) => {
  const m = html.match(new RegExp(`<script[^>]*src="${url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[^>]*>`));
  if (!m) return null;
  const i = m[0].match(/integrity="([^"]+)"/);
  return i ? i[1] : '';
};

// index.html as served to the browser: only integrity values of vendored
// scripts whose bytes differ from the pinned CDN file are replaced.
function rewriteHtml(html) {
  for (const v of VENDOR) {
    const want = sriInHtml(html, v.cdn);
    if (want && want !== v.sri) html = html.split(`integrity="${want}"`).join(`integrity="${v.sri}"`);
  }
  return html;
}

async function routeContext(ctx) {
  // NB: Playwright matches the most recently registered route first.
  await ctx.route('https://cdnjs.cloudflare.com/**', r => r.abort()); // anything else on cdnjs is unexpected
  for (const v of VENDOR) {
    await ctx.route(v.cdn, r => r.fulfill({
      status: 200, body: v.body,
      headers: { 'content-type': 'application/javascript; charset=utf-8', 'access-control-allow-origin': '*' },
    }));
  }
  // Webfonts are cosmetic; keep the run hermetic.
  await ctx.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r =>
    r.fulfill({ status: 200, body: '', headers: { 'content-type': 'text/css', 'access-control-allow-origin': '*' } }));
  const isIndex = u => (u.href.startsWith(BASE) && (u.pathname === new URL(BASE).pathname || u.pathname.endsWith('/index.html')))
    || u.href === FILE_URL;
  // E2E_APP_SCRIPT=/path/to/other-script-pos.js runs the suite against another build of
  // the app script (e.g. `git show HEAD:script-pos.js`) to check that tests catch regressions.
  if (process.env.E2E_APP_SCRIPT) {
    await ctx.route(u => u.pathname.endsWith('/script-pos.js'), r => r.fulfill({
      status: 200, body: fs.readFileSync(process.env.E2E_APP_SCRIPT), headers: { 'content-type': 'application/javascript; charset=utf-8' },
    }));
  }
  await ctx.route(isIndex, async r => {
    const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
    await r.fulfill({ status: 200, body: rewriteHtml(html), headers: { 'content-type': 'text/html; charset=utf-8' } });
  });
}

// SheetJS in Node (same build as the page uses)
let XLSX;
const nodeXLSX = () => (XLSX ||= require(path.join(VENDOR[0].dir, 'xlsx.js')));

// ─────────────────────────────────────────────────────────────
// Mini test harness
// ─────────────────────────────────────────────────────────────
const tests = [];
const test = (name, fn) => tests.push({ name, fn });
test.skip = (name, reason) => tests.push({ name, skip: reason });

let browser;
const results = [];

// Barcode detector stub: Linux Chromium has no BarcodeDetector. detect()
// returns whatever the test puts into window.__barcodeValue (once).
const INIT_SCRIPT = () => {
  class FakeBarcodeDetector {
    constructor(opts) { this.opts = opts; }
    static async getSupportedFormats() { return ['ean_13', 'code_128', 'qr_code']; }
    async detect(source) {
      window.__detectCalls = (window.__detectCalls || 0) + 1;
      window.__lastDetectSource = source && source.constructor && source.constructor.name;
      const v = window.__barcodeValue;
      if (v == null) return [];
      window.__barcodeValue = null;
      return [{ rawValue: String(v), format: 'ean_13', boundingBox: {}, cornerPoints: [] }];
    }
  }
  window.BarcodeDetector = FakeBarcodeDetector;
  window.__printCalls = 0;
  window.print = () => { window.__printCalls++; };
};

class Session {
  constructor() { this.contexts = []; this.pageErrors = []; this.consoleErrors = []; this.dialogs = []; this.dialogPlan = []; }

  async context(opts = {}) {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 }, isMobile: false, hasTouch: false,
      serviceWorkers: 'block', acceptDownloads: true, permissions: ['camera'],
      timezoneId: 'Asia/Bangkok', locale: 'th-TH', ...opts,
    });
    ctx.setDefaultTimeout(10000);
    await ctx.addInitScript(INIT_SCRIPT);
    await routeContext(ctx);
    this.contexts.push(ctx);
    return ctx;
  }

  watch(page) {
    page.on('pageerror', e => this.pageErrors.push(`${page.url()}: ${e.message}`));
    page.on('console', m => {
      if (process.env.E2E_DEBUG) console.log(`      [console.${m.type()}] ${m.text()}`);
      if (m.type() !== 'error') return;
      const loc = (m.location() && m.location().url) || '';
      if (/\/api\/v1\/sync\/health/.test(loc)) return; // static server has no backend: expected 404
      if (/favicon\.ico/.test(loc)) return;
      this.consoleErrors.push(`${m.text()} @ ${loc}`);
    });
    // Dialogs: tests queue answers with expectDialog(); otherwise accept.
    page.on('dialog', async d => {
      const plan = this.dialogPlan.shift();
      this.dialogs.push({ type: d.type(), message: d.message() });
      try {
        if (plan && plan.accept === false) await d.dismiss();
        else await d.accept(plan && plan.text != null ? plan.text : undefined);
      } catch { /* page navigated */ }
    });
    return page;
  }

  expectDialog(accept = true, text) { this.dialogPlan.push({ accept, text }); }

  async open(opts = {}) {
    const ctx = opts.context || await this.context();
    const page = this.watch(await ctx.newPage());
    await page.goto(opts.url || BASE);
    await ready(page);
    return page;
  }

  async close() { for (const c of this.contexts) await c.close().catch(() => {}); }
}

async function ready(page) {
  await page.waitForFunction(() => window.XLSX && window.Chart && document.readyState === 'complete' && typeof products !== 'undefined');
  await page.waitForFunction(() => document.querySelector('#pos-product-grid').children.length > 0);
}

// ─────────────────────────────────────────────────────────────
// Page helpers
// ─────────────────────────────────────────────────────────────
const g = (page, expr) => page.evaluate(expr);
const isOpen = (page, id) => page.evaluate(i => document.getElementById(i).classList.contains('open'), id);

async function checkIcons(page, where) {
  const bad = await page.evaluate(() => [...document.querySelectorAll('use')]
    .map(u => u.getAttribute('href') || u.getAttribute('xlink:href') || '')
    .filter(h => {
      if (!h.startsWith('#')) return true;
      const el = document.getElementById(h.slice(1));
      return !el || el.tagName.toLowerCase() !== 'symbol';
    }));
  assert.equal(bad.length, 0, `${where}: unresolved SVG <use> href(s): ${[...new Set(bad)].join(', ')}`);
}

async function assertVisibleOpen(page, id, where) {
  assert.ok(await isOpen(page, id), `${where}: #${id} should have class "open"`);
  assert.ok(await page.locator('#' + id).isVisible(), `${where}: #${id} should be visible`);
}
async function assertClosed(page, id, where) {
  assert.ok(!(await isOpen(page, id)), `${where}: #${id} should be closed`);
  assert.ok(!(await page.locator('#' + id).isVisible()), `${where}: #${id} should be hidden`);
}

async function lastToast(page) {
  return page.evaluate(() => { const t = [...document.querySelectorAll('#toast-container .toast')].pop(); return t ? t.textContent.trim() : ''; });
}
async function waitToast(page, re) {
  await page.waitForFunction(src => [...document.querySelectorAll('#toast-container .toast')].some(t => new RegExp(src).test(t.textContent)), re.source);
}

// sets stock of products by barcode directly (setup only; the stock-adjust UI is tested separately)
async function setStock(page, map) {
  await page.evaluate(m => {
    for (const [bc, s] of Object.entries(m)) { const p = products.find(x => x.barcode === bc); p.stock = s; }
    save(); renderPosProducts();
  }, map);
}

const P1 = { barcode: '8859733221136', name: 'ไอโอร่าบิสกิตรสนมกระเป๋าหูรูดToyStory16ก.', price: 25 };
const P2 = { barcode: '6942712001293', name: 'เอมอสกัมมี่สติชรสพีชและบลูเบอร์รี่ 34 ก.(ด.)', price: 30 };
const P3 = { barcode: '8850389122761', name: 'น้ำวิตามินบลูบับเบิลกัม 500 มล.', price: 35 };

const card = (page, p) => page.locator('#pos-product-grid .product-card', { has: page.locator('.pc-barcode', { hasText: p.barcode }) });
const prod = (page, bc) => page.evaluate(b => products.find(x => x.barcode === b), bc);

async function gotoPage(page, name) {
  if (await page.locator('#nav-' + name).count()) await page.click('#nav-' + name);
  else { await page.click('#hamburger-btn'); await page.click(`#sidebar .sidebar-link[onclick="navigateFromMenu('${name}')"]`); }
  await page.waitForFunction(n => document.getElementById('page-' + n).classList.contains('active'), name);
}
async function sidebar(page, text) {
  await page.click('#hamburger-btn');
  await page.locator('#sidebar .sidebar-link', { hasText: text }).click();
}

async function cashSale(page, items, receivedKeys) {
  for (const [p, n] of items) for (let i = 0; i < n; i++) await card(page, p).click();
  await page.click('#cart-fab');
  await page.click('#cart-sheet button:has-text("ชำระเงิน")');
  await assertVisibleOpen(page, 'modal-payment', 'cashSale');
  for (const k of receivedKeys) await page.click(`#modal-payment .key-btn:text-is("${k}")`);
  await page.click('#pay-cash-section button:has-text("ชำระ")');
  await assertVisibleOpen(page, 'modal-receipt', 'cashSale');
}

async function downloadFrom(page, clickFn) {
  const [dl] = await Promise.all([page.waitForEvent('download'), clickFn()]);
  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, `${Date.now()}-${dl.suggestedFilename()}`);
  await dl.saveAs(file);
  return { file, name: dl.suggestedFilename() };
}

function readXlsx(file) {
  const buf = fs.readFileSync(file);
  assert.equal(buf.subarray(0, 2).toString('latin1'), 'PK', `${path.basename(file)} is not a zip/xlsx`);
  const wb = nodeXLSX().read(buf, { type: 'buffer' });
  const sheets = {};
  for (const n of wb.SheetNames) sheets[n] = nodeXLSX().utils.sheet_to_json(wb.Sheets[n], { header: 1 });
  return { names: wb.SheetNames, sheets };
}

function writeXlsx(rows, name, opts = {}) {
  const X = nodeXLSX();
  const ws = X.utils.aoa_to_sheet(rows, opts);
  const wb = X.utils.book_new();
  X.utils.book_append_sheet(wb, ws, 'Sheet1');
  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, name);
  X.writeFile(wb, file);
  return file;
}

// ─────────────────────────────────────────────────────────────
// TESTS
// ─────────────────────────────────────────────────────────────

test('vendored SheetJS matches index.html SRI; every script/icon reference is resolvable', async () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  assert.equal(sriInHtml(html, VENDOR[0].cdn), VENDOR[0].sri, 'npm xlsx@0.18.5 should be byte-identical to the cdnjs file pinned in index.html');
  assert.ok(sriInHtml(html, VENDOR[1].cdn), 'Chart.js tag keeps an integrity attribute');
  // static check: icon names used from JS exist as <symbol id="i-NAME">
  const js = fs.readFileSync(path.join(ROOT, 'script-pos.js'), 'utf8');
  const symbols = new Set([...html.matchAll(/<symbol[^>]*id="i-([\w-]+)"/g)].map(m => m[1]));
  const used = new Set();
  for (const m of js.matchAll(/icon\(\s*'([\w-]+)'\s*\)/g)) used.add(m[1]);
  for (const m of js.matchAll(/icon\([^)]*?\?\s*'([\w-]+)'\s*:\s*'([\w-]+)'\s*\)/g)) { used.add(m[1]); used.add(m[2]); }
  const toastIcons = js.match(/TOAST_ICONS\s*=\s*\{([^}]*)\}/);
  for (const m of toastIcons[1].matchAll(/'([\w-]+)'/g)) used.add(m[1]);
  const missing = [...used].filter(n => !symbols.has(n));
  assert.deepEqual(missing, [], 'icon() names without a matching <symbol>');
});

test('every page renders without page errors and all SVG icons resolve', async (s) => {
  const page = await s.open();
  await checkIcons(page, 'pos');
  for (const name of ['products', 'purchase', 'debt', 'reports', 'more', 'pos']) {
    await gotoPage(page, name);
    const active = await page.evaluate(() => [...document.querySelectorAll('.page.active')].map(p => p.id));
    assert.deepEqual(active, ['page-' + name], 'exactly one active page');
    assert.ok(await page.locator('#page-' + name).isVisible());
    await checkIcons(page, name);
  }
  // reports tabs + compare + charts
  await gotoPage(page, 'reports');
  for (const [i, tab] of ['sales', 'stock', 'expense'].entries()) {
    await page.locator('#report-tabs .tab-btn').nth(i).click();
    assert.ok(await page.locator('#rtab-' + tab).isVisible(), `report tab ${tab} visible`);
    await checkIcons(page, 'reports/' + tab);
  }
  await page.locator('#report-tabs .tab-btn').nth(0).click();
  await page.click('button:has-text("เดือนนี้ vs เดือนก่อน")');
  await page.click('button:has-text("7วันนี้ vs 7วันก่อน")');
  assert.ok(await g(page, () => !!(salesChartInst && compareChartInst)), 'charts were created');
  // more page: open the category-mapping card and the sidebar
  await gotoPage(page, 'more');
  await page.click('.mapping-card-header');
  assert.ok(await page.locator('#mapping-list .mapping-row').first().isVisible());
  await checkIcons(page, 'more/mapping');
  await page.click('#hamburger-btn');
  assert.ok(await page.locator('#sidebar').evaluate(e => e.classList.contains('open')));
  await checkIcons(page, 'sidebar');
  await page.keyboard.press('Escape');
  assert.ok(!(await page.locator('#sidebar').evaluate(e => e.classList.contains('open'))), 'Esc closes sidebar');
});

test('every modal opens and closes (Esc closes the top one; backdrop click closes)', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 10 });
  await card(page, P1).click();
  const debtId = await page.evaluate(() => {
    debts.push({ id: 'd1', customer: 'ทดสอบ', phone: '', billNo: '-', amount: 100, paid: 0, date: today(), note: '', status: 'ค้าง', payments: [] });
    save(); return 'd1';
  });
  const openers = {
    'cart-sheet': () => page.click('#cart-fab'),
    'modal-payment': () => g(page, () => openPayment()),
    'modal-receipt': () => g(page, () => showReceipt({ billNo: 'B99999', date: new Date().toISOString(), items: [{ name: 'x', qty: 1, subtotal: 1 }], subtotal: 1, discount: 0, vat: 0, total: 1, received: 1, change: 0, payType: 'เงินสด' })),
    'modal-hold': () => g(page, () => openHoldBillsPage()),
    'modal-product': () => g(page, () => openProductModal()),
    'modal-master-search': () => g(page, () => openMasterSearch()),
    'modal-stock-adjust': () => g(page, () => showSubPage('stock-adjust')),
    'modal-purchase': () => g(page, () => openPurchaseModal()),
    'modal-debt': () => g(page, () => openDebtModal()),
    'modal-pay-debt': () => page.evaluate(id => openPayDebt(id), debtId),
    'modal-expense': () => g(page, () => openExpense()),
    'modal-stores': () => g(page, () => openStoresModal()),
    'modal-shortcuts': () => g(page, () => openModal('modal-shortcuts')),
    'modal-scanner': async () => { await page.click('#pos-scan-btn'); await page.waitForFunction(() => _scan && _scan.raf); },
  };
  const ids = await page.evaluate(() => ['cart-sheet', ...[...document.querySelectorAll('.modal-overlay')].map(m => m.id)]);
  const noOpener = ids.filter(id => !openers[id]);
  assert.deepEqual(noOpener, [], 'modal(s) in index.html not covered by this test');

  for (const id of ids) {
    await openers[id]();
    await assertVisibleOpen(page, id, id);
    await checkIcons(page, id);
    await page.keyboard.press('Escape');
    await assertClosed(page, id, id + ' after Esc');
    // backdrop click (top-left corner is outside the bottom-sheet panel)
    await openers[id]();
    await assertVisibleOpen(page, id, id + ' (2nd)');
    await page.mouse.click(5, 5);
    await assertClosed(page, id, id + ' after backdrop click');
    if (id === 'modal-scanner') assert.equal(await g(page, () => _scan), null, 'camera stream released after closing scanner');
    if (id === 'modal-receipt') { await card(page, P1).click(); } // receipt backdrop = newBill() → cart cleared; refill
  }

  // stacking: cart → payment, Esc closes only the payment first
  await page.click('#cart-fab');
  await page.click('#cart-sheet button:has-text("ชำระเงิน")');
  await page.keyboard.press('Escape');
  await assertClosed(page, 'modal-payment', 'stacked');
  await assertVisibleOpen(page, 'cart-sheet', 'stacked: cart stays');
  await page.keyboard.press('Escape');
  await assertClosed(page, 'cart-sheet', 'stacked');
  // product form → scanner on top: Esc closes scanner, product form stays
  await g(page, () => openProductModal());
  await page.click('#modal-product button[title^="สแกนบาร์โค้ด"]');
  await page.waitForFunction(() => document.getElementById('modal-scanner').classList.contains('open'));
  await page.keyboard.press('Escape');
  await assertClosed(page, 'modal-scanner', 'scanner over product');
  await assertVisibleOpen(page, 'modal-product', 'product under scanner');
  await page.keyboard.press('Escape');
  await assertClosed(page, 'modal-product', 'product');
});

test('cash sale end-to-end (cash keypad, transfer, card) → receipt, stock, sales, bill number', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 10, [P2.barcode]: 5 });
  const bc0 = await g(page, () => billCounter);
  assert.equal(await page.textContent('#pos-bill-no'), 'บิล #B' + String(bc0).padStart(5, '0'));

  // cart: 2 × P1 + 1 × P2 = 80
  await card(page, P1).click(); await card(page, P1).click(); await card(page, P2).click();
  assert.equal(await page.textContent('#cart-count-badge'), '3');
  await page.click('#cart-fab');
  assert.match(await page.textContent('#cs-total'), /80\.00/);
  await page.click('#cart-sheet button:has-text("ชำระเงิน")');
  assert.match(await page.textContent('#pay-total-display'), /80\.00/);
  // not enough cash → rejected
  await page.click('#modal-payment .key-btn:text-is("5")');
  await page.click('#modal-payment .key-btn:text-is("0")');
  await page.click('#pay-cash-section button:has-text("ชำระ")');
  await waitToast(page, /รับเงินไม่พอ/);
  assert.equal(await g(page, () => sales.length), 0);
  await assertVisibleOpen(page, 'modal-payment', 'after insufficient cash');
  // C, then 100 via keypad
  await page.click('#modal-payment .key-btn:text-is("C")');
  for (const k of ['1', '00']) await page.click(`#modal-payment .key-btn:text-is("${k}")`);
  assert.equal(await page.textContent('#pay-received-display'), '100');
  assert.match(await page.textContent('#pay-change-display'), /20\.00/);
  await page.click('#pay-cash-section button:has-text("ชำระ")');
  await assertVisibleOpen(page, 'modal-receipt', 'receipt');
  const receipt = await page.textContent('#receipt-content');
  const bill1 = 'B' + String(bc0).padStart(5, '0');
  assert.ok(receipt.includes(bill1), 'receipt shows bill no');
  assert.ok(receipt.includes(P1.name) && receipt.includes(P2.name), 'receipt lists items');
  assert.match(receipt, /ทอน\s*20\.00/);
  await checkIcons(page, 'receipt');

  assert.equal((await prod(page, P1.barcode)).stock, 8);
  assert.equal((await prod(page, P2.barcode)).stock, 4);
  const sale = await g(page, () => sales[sales.length - 1]);
  assert.equal(await g(page, () => sales.length), 1);
  assert.deepEqual([sale.billNo, sale.total, sale.received, sale.change, sale.payType], [bill1, 80, 100, 20, 'เงินสด']);
  assert.equal(await g(page, () => billCounter), bc0 + 1);
  assert.equal(JSON.parse(await g(page, () => localStorage.getItem('qpos_sales'))).length, 1, 'persisted');

  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  await assertClosed(page, 'modal-receipt', 'new bill');
  assert.equal(await g(page, () => cart.length), 0);
  assert.equal(await page.textContent('#pos-bill-no'), 'บิล #B' + String(bc0 + 1).padStart(5, '0'));
  assert.ok(!(await page.locator('#cart-count-badge').isVisible()), 'cart badge hidden');

  // transfer + card
  for (const [btn, type] of [['#pay-transfer-btn', 'โอน'], ['#pay-card-btn', 'บัตร']]) {
    await card(page, P1).click();
    await page.click('#cart-fab');
    await page.click('#cart-sheet button:has-text("ชำระเงิน")');
    await page.click(btn);
    assert.ok(await page.locator('#pay-transfer-section').isVisible());
    assert.ok(!(await page.locator('#pay-cash-section').isVisible()));
    await page.click('#pay-transfer-section button:has-text("ยืนยันการชำระ")');
    await assertVisibleOpen(page, 'modal-receipt', type);
    assert.ok((await page.textContent('#receipt-content')).includes(`รับ (${type})`));
    await page.click('#modal-receipt button:has-text("บิลใหม่")');
  }
  const all = await g(page, () => sales.map(x => [x.billNo, x.payType]));
  assert.deepEqual(all.map(x => x[1]), ['เงินสด', 'โอน', 'บัตร']);
  assert.deepEqual(all.map(x => x[0]), [0, 1, 2].map(i => 'B' + String(bc0 + i).padStart(5, '0')), 'bill numbers increment');
  assert.equal((await prod(page, P1.barcode)).stock, 6);

  // out-of-stock product cannot be added (card has pointer-events:none, so dispatch the click)
  await card(page, P3).dispatchEvent('click');
  assert.equal(await g(page, () => cart.length), 0, 'P3 has stock 0');
  // data survives reload
  await page.reload(); await ready(page);
  assert.equal(await g(page, () => sales.length), 3);
  assert.equal(await page.textContent('#pos-bill-no'), 'บิล #B' + String(bc0 + 3).padStart(5, '0'));
});

test('credit sale → debt created → partial payment reduces outstanding → full payment', async (s) => {
  const page = await s.open();
  await setStock(page, { [P2.barcode]: 5 });
  const bc0 = await g(page, () => billCounter);
  await card(page, P2).click(); await card(page, P2).click(); // 60
  await page.click('#cart-fab');
  await page.fill('#cs-discount-val', '10'); // 60 - 10 = 50
  await page.click('#cart-sheet button:has-text("เชื่อ")');
  await assertVisibleOpen(page, 'modal-debt', 'credit sale');
  assert.equal(await page.inputValue('#dm-amount'), '50.00');
  assert.ok(await page.locator('#dm-amount').evaluate(e => e.readOnly), 'amount locked for credit sale');
  await page.fill('#dm-name', 'สมชาย ใจดี');
  await page.fill('#dm-phone', '0812345678');
  await page.click('#modal-debt button:has-text("บันทึก")');
  await assertClosed(page, 'modal-debt', 'credit sale saved');
  await assertClosed(page, 'cart-sheet', 'credit sale saved');

  const st = await g(page, () => ({ debts, sales, cart, billCounter }));
  assert.equal(st.debts.length, 1);
  assert.deepEqual([st.debts[0].customer, st.debts[0].amount, st.debts[0].paid, st.debts[0].status], ['สมชาย ใจดี', 50, 0, 'ค้าง']);
  assert.equal(st.sales.length, 1);
  assert.equal(st.sales[0].payType, 'เชื่อ');
  assert.equal(st.debts[0].billNo, st.sales[0].billNo);
  assert.equal(st.cart.length, 0);
  assert.equal(st.billCounter, bc0 + 1);
  assert.equal((await prod(page, P2.barcode)).stock, 3);
  assert.equal(await page.textContent('#pos-bill-no'), 'บิล #B' + String(bc0 + 1).padStart(5, '0'),
    'POS header bill number must advance after a credit sale');
  assert.equal(await page.locator('#dm-amount').evaluate(e => e.readOnly), false, 'debt amount field unlocked again');
  assert.equal(await page.inputValue('#cs-discount-val'), '0', 'discount reset for the next bill');

  await gotoPage(page, 'debt');
  assert.match(await page.textContent('#debt-outstanding'), /50\.00/);
  assert.equal(await page.textContent('#debt-bill-count'), '1');
  await page.click('#debt-list button:has-text("รับชำระ")');
  await assertVisibleOpen(page, 'modal-pay-debt', 'pay debt');
  assert.equal(await page.inputValue('#pd-outstanding'), '50');
  await page.fill('#pd-pay-amt', '25');
  await page.click('#modal-pay-debt button:has-text("รับชำระ")');
  await assertClosed(page, 'modal-pay-debt', 'partial pay');
  let d = await g(page, () => debts[0]);
  assert.deepEqual([d.paid, d.status, d.payments.length], [25, 'ค้าง', 1]);
  assert.match(await page.textContent('#debt-outstanding'), /25\.00/);
  assert.match(await page.textContent('#debt-list .debt-amount'), /25\.00/);

  await page.click('#debt-list button:has-text("รับชำระ")');
  assert.equal(await page.inputValue('#pd-pay-amt'), '25');
  await page.click('#modal-pay-debt button:has-text("รับชำระ")');
  d = await g(page, () => debts[0]);
  assert.deepEqual([d.paid, d.status], [50, 'ชำระแล้ว']);
  assert.match(await page.textContent('#debt-outstanding'), /0\.00/);
  assert.equal(await page.textContent('#debt-bill-count'), '0');
  assert.equal(await page.locator('#debt-list button:has-text("รับชำระ")').count(), 0);
  await checkIcons(page, 'debt list');
});

test('hold bill then resume (and delete a held bill)', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 5, [P2.barcode]: 5 });
  await card(page, P1).click(); await card(page, P1).click();
  await page.click('#cart-fab');
  await page.click('#cart-sheet button:has-text("พัก")');
  let st = await g(page, () => ({ holdBills, cart }));
  assert.equal(st.holdBills.length, 1);
  assert.equal(st.cart.length, 0);
  assert.deepEqual(st.holdBills[0].cart.map(c => [c.name, c.qty]), [[P1.name, 2]]);
  await assertClosed(page, 'cart-sheet', 'after hold');

  // a different cart is in progress; resuming asks to replace it
  await card(page, P2).click();
  await sidebar(page, 'บิลพัก');
  await assertVisibleOpen(page, 'modal-hold', 'hold list');
  assert.ok((await page.textContent('#hold-bills-list')).includes('บิล 1'));
  s.expectDialog(true);
  await page.click('#hold-bills-list button:has-text("เรียก")');
  assert.equal(s.dialogs.at(-1).message, 'แทนที่รายการปัจจุบัน?');
  st = await g(page, () => ({ holdBills, cart }));
  assert.equal(st.holdBills.length, 0);
  assert.deepEqual(st.cart.map(c => [c.name, c.qty]), [[P1.name, 2]]);
  await assertVisibleOpen(page, 'cart-sheet', 'resumed cart shown');
  assert.match(await page.textContent('#cs-total'), /50\.00/);
  // resumed bill can be paid normally
  await page.click('#cart-sheet button:has-text("ชำระเงิน")');
  await page.click('#modal-payment .quick-cash-btn:text-is("+50")');
  await page.click('#pay-cash-section button:has-text("ชำระ")');
  await assertVisibleOpen(page, 'modal-receipt', 'resumed bill paid');
  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  assert.equal((await prod(page, P1.barcode)).stock, 3);

  // delete
  await card(page, P2).click();
  await g(page, () => holdCurrentCart());
  await g(page, () => openHoldBillsPage());
  await page.click('#hold-bills-list button:has-text("ลบ")');
  assert.equal(await g(page, () => holdBills.length), 0);
  assert.ok((await page.textContent('#hold-bills-list')).includes('ไม่มีบิลพัก'));
  // persisted
  await page.reload(); await ready(page);
  assert.equal(await g(page, () => holdBills.length), 0);
});

test('purchase saved increases stock; empty purchase rejected', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 2, [P2.barcode]: 0 });
  const ids = await g(page, () => products.map(p => [p.barcode, p.id]));
  const idOf = Object.fromEntries(ids);
  await gotoPage(page, 'purchase');
  await page.click('#topbar-action');
  await assertVisibleOpen(page, 'modal-purchase', 'purchase');
  // empty row → rejected
  await page.click('#modal-purchase button:has-text("บันทึก")');
  await waitToast(page, /ไม่มีรายการสินค้า/);
  assert.equal(await g(page, () => purchases.length), 0);

  const rows = page.locator('#pur-items-list .pur-item-row');
  await rows.nth(0).locator('.pr-prod').selectOption(idOf[P1.barcode]);
  await rows.nth(0).locator('.pr-qty').fill('12');
  await rows.nth(0).locator('.pr-price').fill('10');
  await page.click('#modal-purchase button:has-text("เพิ่มรายการสินค้า")');
  await rows.nth(1).locator('.pr-prod').selectOption(idOf[P2.barcode]);
  await rows.nth(1).locator('.pr-qty').fill('3');
  await rows.nth(1).locator('.pr-price').fill('20.5');
  await page.fill('#pur-supplier', 'ซีพี');
  await page.click('#modal-purchase button:has-text("บันทึก")');
  await assertClosed(page, 'modal-purchase', 'purchase saved');
  assert.equal((await prod(page, P1.barcode)).stock, 14);
  assert.equal((await prod(page, P2.barcode)).stock, 3);
  const pur = await g(page, () => purchases);
  assert.equal(pur.length, 1);
  assert.equal(pur[0].supplier, 'ซีพี');
  assert.deepEqual(pur[0].items.map(i => [i.qty, i.price, i.total]), [[12, 10, 120], [3, 20.5, 61.5]]);
  const listTxt = await page.textContent('#pur-list');
  assert.ok(listTxt.includes('ซีพี') && /181\.50/.test(listTxt), 'purchase list shows supplier and total');
  await checkIcons(page, 'purchase list');
  // POS grid reflects new stock
  await gotoPage(page, 'pos');
  assert.match(await card(page, P2).textContent(), /\b3\b/);
});

test('stock adjust works (search, set, no-change)', async (s) => {
  const page = await s.open();
  await gotoPage(page, 'more');
  await page.click('#page-more button:has-text("ปรับสต๊อก")');
  await assertVisibleOpen(page, 'modal-stock-adjust', 'adjust');
  assert.equal(await page.locator('#adj-list .adj-row').count(), 4);
  await page.click('#modal-stock-adjust button:has-text("บันทึก")');
  await waitToast(page, /ไม่มีการเปลี่ยนแปลง/);
  await assertVisibleOpen(page, 'modal-stock-adjust', 'no change keeps modal');
  await page.fill('#adj-search', 'น้ำวิตามิน');
  assert.equal(await page.locator('#adj-list .adj-row').count(), 1);
  await page.locator('#adj-list .adj-input').fill('17');
  await page.fill('#adj-search', '');
  await page.dispatchEvent('#adj-search', 'input');
  assert.equal(await page.locator('#adj-list .adj-row').count(), 4);
  const p1 = await prod(page, P1.barcode);
  await page.fill(`#adj-${p1.id}`, '9');
  await page.click('#modal-stock-adjust button:has-text("บันทึก")');
  await assertClosed(page, 'modal-stock-adjust', 'adjust saved');
  assert.equal((await prod(page, P3.barcode)).stock, 17, 'value entered before re-filtering is kept');
  assert.equal((await prod(page, P1.barcode)).stock, 9);
  assert.equal((await prod(page, P2.barcode)).stock, 0, 'untouched');
  await page.reload(); await ready(page);
  assert.equal((await prod(page, P1.barcode)).stock, 9, 'persisted');
});

test('Excel: every export button downloads a valid xlsx with the right content', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 10 });
  await page.evaluate(() => {
    const p = products[0];
    purchases.push({ id: 'pu1', date: today(), supplier: 'ผู้ขายA', items: [{ productId: p.id, name: p.name, qty: 2, price: 5, total: 10 }], createdAt: Date.now() });
    expenses.push({ id: 'e1', name: 'ค่าไฟ', amount: 300, date: today(), note: 'บิลเดือนนี้', createdAt: Date.now() });
    save();
  });
  await cashSale(page, [[P1, 2]], ['1', '00']);
  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  const nProducts = await g(page, () => products.length);

  const exports = [];
  // More page: products
  await gotoPage(page, 'more');
  exports.push(['products', await downloadFrom(page, () => page.click('#page-more button:has-text("Export สินค้า")'))]);
  // Purchase page
  await gotoPage(page, 'purchase');
  exports.push(['purchase', await downloadFrom(page, () => page.click('#page-purchase button:has-text("Excel")'))]);
  // Reports
  await gotoPage(page, 'reports');
  exports.push(['sales', await downloadFrom(page, () => page.click('#rtab-sales button[onclick="exportSalesExcel()"]'))]);
  await page.click('button:has-text("เดือนนี้ vs เดือนก่อน")');
  exports.push(['compare', await downloadFrom(page, () => page.click('#rtab-sales button[onclick="exportCompareExcel()"]'))]);
  await page.locator('#report-tabs .tab-btn').nth(1).click();
  exports.push(['stock', await downloadFrom(page, () => page.click('#rtab-stock button[onclick="exportStockExcel()"]'))]);
  await page.locator('#report-tabs .tab-btn').nth(2).click();
  exports.push(['expense', await downloadFrom(page, () => page.click('#rtab-expense button[onclick="exportPurchaseRptExcel()"]'))]);

  // every export button in the DOM is covered
  const btns = await page.evaluate(() => [...document.querySelectorAll('button[onclick*="Excel()"]')].map(b => b.getAttribute('onclick')));
  const covered = ['exportProductsExcel()', 'exportPurchaseExcel()', 'exportSalesExcel()', 'exportCompareExcel()', 'exportStockExcel()', 'exportPurchaseRptExcel()'];
  assert.deepEqual([...new Set(btns)].filter(b => !covered.includes(b)), [], 'export buttons not covered');

  const x = Object.fromEntries(exports.map(([k, v]) => [k, { ...v, ...readXlsx(v.file) }]));
  assert.equal(x.products.name, 'products.xlsx');
  assert.deepEqual(x.products.sheets['สินค้า'][0], ['รหัสสินค้า', 'บาร์โค้ด', 'ชื่อสินค้า', 'หมวดหมู่', 'ราคาขาย', 'ต้นทุน', 'สต๊อก', 'วันหมดอายุ']);
  assert.equal(x.products.sheets['สินค้า'].length, nProducts + 1);
  const p1row = x.products.sheets['สินค้า'].find(r => String(r[1]) === P1.barcode);
  assert.deepEqual([p1row[2], p1row[4], p1row[6]], [P1.name, 25, 8]);

  assert.equal(x.purchase.name, 'purchase.xlsx');
  assert.deepEqual(x.purchase.sheets['สั่งซื้อ'].slice(1).map(r => [r[1], r[3], r[5]]), [['ผู้ขายA', 2, 10]]);

  assert.equal(x.sales.name, 'sales.xlsx');
  assert.deepEqual(x.sales.names, ['ยอดขาย', 'แยกตามหมวดหมู่']);
  assert.equal(x.sales.sheets['ยอดขาย'].length, 2, 'header + 1 sale');
  assert.equal(x.sales.sheets['ยอดขาย'][1][3], 50);

  assert.equal(x.compare.name, 'compare_report.xlsx');
  assert.deepEqual(x.compare.names, ['สรุปเปรียบเทียบ', 'ช่วง A', 'ช่วง B']);
  assert.equal(x.compare.sheets['สรุปเปรียบเทียบ'][1][1], 50, 'this month total');

  assert.equal(x.stock.name, 'stock.xlsx');
  assert.equal(x.stock.sheets['สต๊อก'].length, nProducts + 1);

  assert.equal(x.expense.name, 'expense.xlsx');
  const exRows = x.expense.sheets['รายจ่าย'].slice(1).map(r => [r[1], r[2], r[5]]);
  assert.deepEqual(exRows, [['ซื้อสินค้า', P1.name, 10], ['รายจ่าย', 'ค่าไฟ', 300]]);
});

test('Excel import: generated xlsx adds new and updates existing products; master update', async (s) => {
  const page = await s.open();
  const before = await g(page, () => products.length);
  const file = writeXlsx([
    ['รหัสสินค้า', 'บาร์โค้ด', 'ชื่อสินค้า', 'หมวดหมู่', 'ราคาขาย', 'ต้นทุน', 'สต๊อก', 'วันหมดอายุ'],
    ['4111505', P1.barcode, 'ไอโอร่า (ชื่อใหม่)', '', 27, 18, 40, ''],           // update by id/barcode
    ['4199999', '1234567890123', 'สินค้านำเข้าใหม่', '', 15, 10, 7, '2027-01-31'], // new, category from prefix 41
    ['', '5555555555555', 'ไม่มีรหัสแต่มีบาร์โค้ด', 'หมวดเอง', 9, 0, '', ''],       // new, custom category, no stock col
    ['1234', '', 'ไม่มีบาร์โค้ด', '', 5, 1, 1, ''],                                  // skipped (no barcode)
  ], 'import.xlsx');
  await gotoPage(page, 'more');
  await page.setInputFiles('#excelInput', file);
  await waitToast(page, /นำเข้าแล้ว 2 รายการ \(อัปเดต 1 รายการ\)/);
  assert.equal(await g(page, () => products.length), before + 2);
  const up = await prod(page, P1.barcode);
  assert.deepEqual([up.name, up.price, up.cost, up.stock], ['ไอโอร่า (ชื่อใหม่)', 27, 18, 40]);
  const nw = await prod(page, '1234567890123');
  assert.deepEqual([nw.product_id, nw.name, nw.category, nw.price, nw.cost, nw.stock, nw.expiry], ['4199999', 'สินค้านำเข้าใหม่', 'SNACKS', 15, 10, 7, '2027-01-31']);
  const nw2 = await prod(page, '5555555555555');
  assert.deepEqual([nw2.product_id, nw2.category, nw2.stock], ['', 'หมวดเอง', 0]);
  assert.equal(await page.inputValue('#excelInput'), '', 'file input reset so the same file can be re-imported');
  // persisted + visible in product list
  await gotoPage(page, 'products');
  assert.ok((await page.textContent('#prod-list')).includes('สินค้านำเข้าใหม่'));

  // round trip: export → re-import changes nothing and adds nothing
  const snapshot = await g(page, () => JSON.stringify(products.map(({ createdAt, ...p }) => p)));
  await gotoPage(page, 'more');
  const exp = await downloadFrom(page, () => page.click('#page-more button:has-text("Export สินค้า")'));
  await page.setInputFiles('#excelInput', exp.file);
  await waitToast(page, new RegExp(`นำเข้าแล้ว 0 รายการ \\(อัปเดต ${before + 2} รายการ\\)`));
  assert.equal(await g(page, () => JSON.stringify(products.map(({ createdAt, ...p }) => p))), snapshot, 'export→import round trip is lossless');

  // master update: only name + category change; price/stock untouched
  const mfile = writeXlsx([
    ['Master Product ID', 'Barcode', 'ชื่อสินค้า', 'Category'],
    ['4199999', '', 'ชื่อจากมาสเตอร์', 'หมวดมาสเตอร์'],
    ['0000000', '0000000000000', 'ไม่มีในร้าน', ''],
  ], 'master.xlsx');
  await page.setInputFiles('#masterUpdateInput', mfile);
  await waitToast(page, /อัปเดตชื่อ\+หมวดหมู่แล้ว 1 รายการ \(ไม่พบสินค้า 1 รายการ\)/);
  const m = await prod(page, '1234567890123');
  assert.deepEqual([m.name, m.category, m.price, m.stock], ['ชื่อจากมาสเตอร์', 'หมวดมาสเตอร์', 15, 7]);
});

test('Excel import: expiry given as a real Excel date cell is imported as that date', async (s) => {
  const page = await s.open();
  const file = writeXlsx([
    ['รหัสสินค้า', 'บาร์โค้ด', 'ชื่อสินค้า', 'ราคาขาย', 'สต๊อก', 'วันหมดอายุ'],
    ['4100001', '2000000000001', 'วันที่เป็นเซลล์วันที่', 10, 1, new Date(Date.UTC(2027, 2, 15))],
    ['4100002', '2000000000002', 'วันที่เป็นข้อความ', 10, 1, '2027-03-15'],
  ], 'dates.xlsx', { cellDates: false });
  await gotoPage(page, 'more');
  await page.setInputFiles('#excelInput', file);
  await waitToast(page, /นำเข้าแล้ว 2 รายการ/);
  assert.equal((await prod(page, '2000000000002')).expiry, '2027-03-15', 'text date');
  assert.equal((await prod(page, '2000000000001')).expiry, '2027-03-15', 'date cell (Excel serial number)');
});

test('JSON backup download → modify data → restore from that file → data matches backup', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 10, [P2.barcode]: 10 });
  await cashSale(page, [[P1, 1]], ['1', '00']);
  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  await page.evaluate(() => {
    debts.push({ id: 'd1', customer: 'ก', phone: '', billNo: '-', amount: 99, paid: 10, date: today(), note: '', status: 'ค้าง', payments: [{ amount: 10, date: today() }] });
    expenses.push({ id: 'e1', name: 'ค่าน้ำ', amount: 120, date: today(), note: '', createdAt: 1 });
    categoryMapping.push({ prefix: '0099', name: 'หมวดสำรอง' });
    settings.storeName = 'ร้านก่อนสำรอง';
    save();
  });
  await card(page, P2).click();
  await g(page, () => holdCurrentCart());

  await gotoPage(page, 'more');
  const dl = await downloadFrom(page, () => page.click('#page-more button:has-text("สำรองข้อมูลทั้งหมด")'));
  assert.match(dl.name, /^qpos-backup-.+-\d{4}-\d{2}-\d{2}\.json$/);
  const backup = JSON.parse(fs.readFileSync(dl.file, 'utf8'));
  const KEYS = ['products', 'sales', 'purchases', 'debts', 'expenses', 'settings', 'holdBills', 'billCounter', 'categoryMapping'];
  const state = () => page.evaluate(keys => JSON.parse(JSON.stringify(Object.fromEntries(keys.map(k => [k, eval(k)])))), KEYS);
  const orig = await state();
  for (const k of KEYS) assert.deepEqual(backup[k], orig[k], `backup.${k} equals app state`);

  // modify: wipe everything, then add something new
  s.expectDialog(true);
  await page.click('#page-more button:has-text("ล้างข้อมูลทั้งหมด")');
  await page.evaluate(() => { products.push({ id: 'new', product_id: '9', barcode: '9', name: 'หลังสำรอง', price: 1, stock: 1 }); settings.storeName = 'เปลี่ยนแล้ว'; save(); });
  assert.equal(await g(page, () => sales.length), 0);

  // cancelled restore changes nothing
  await gotoPage(page, 'more');
  s.expectDialog(false);
  await page.setInputFiles('#backupInput', dl.file);
  await page.waitForFunction(() => document.getElementById('backupInput').value === '');
  assert.equal(await g(page, () => products.length), 1);

  s.expectDialog(true);
  await page.setInputFiles('#backupInput', dl.file);
  await waitToast(page, /กู้คืนข้อมูลแล้ว/);
  assert.match(s.dialogs.at(-1).message, /กู้คืน/);
  assert.deepEqual(await state(), orig, 'restored state equals the backup');
  assert.equal(await page.inputValue('#set-store-name'), 'ร้านก่อนสำรอง', 'settings form refreshed');
  await page.reload(); await ready(page);
  assert.deepEqual(await state(), orig, 'restored state persisted across reload');

  // invalid file
  fs.writeFileSync(path.join(OUT, 'bad.json'), '{not json');
  await gotoPage(page, 'more');
  await page.setInputFiles('#backupInput', path.join(OUT, 'bad.json'));
  await waitToast(page, /ไฟล์ไม่ถูกต้อง/);
  assert.deepEqual(await state(), orig);
});

test('category mapping add / hide / show / delete (+ locked rows, duplicates)', async (s) => {
  const page = await s.open();
  const prefix = await g(page, () => { for (let i = 0; i < 100; i++) { const p = String(i).padStart(2, '0'); if (!categoryMapping.some(m => p.startsWith(m.prefix) || m.prefix.startsWith(p))) return p; } });
  assert.ok(prefix, 'free 2-digit prefix');
  await page.evaluate(pre => { products.push({ id: 'mp', product_id: pre + '12345', barcode: '7000000000001', name: 'สินค้าทดสอบหมวด', category: getCategoryFromProductId(pre + '12345'), price: 5, cost: 0, stock: 3 }); save(); }, prefix);
  assert.equal((await prod(page, '7000000000001')).category, 'อื่นๆ');
  await gotoPage(page, 'more');
  await page.click('.mapping-card-header');
  const row = () => page.locator('#mapping-list .mapping-row', { has: page.locator('.m-prefix', { hasText: new RegExp('^' + prefix + '$') }) });

  // add
  await page.fill('#mapping-prefix', prefix);
  await page.fill('#mapping-cat', 'หมวดทดสอบ E2E');
  await page.click('.mapping-add-row button:has-text("เพิ่ม")');
  await waitToast(page, /อัปเดตสินค้า 1 รายการ/);
  assert.equal(await row().count(), 1);
  assert.equal((await prod(page, '7000000000001')).category, 'หมวดทดสอบ E2E');
  assert.equal(await page.inputValue('#mapping-prefix'), '');
  await checkIcons(page, 'mapping after add');
  // duplicate
  await page.fill('#mapping-prefix', prefix);
  await page.fill('#mapping-cat', 'ซ้ำ');
  await page.click('.mapping-add-row button:has-text("เพิ่ม")');
  await waitToast(page, /มีรหัสนี้อยู่แล้ว/);
  assert.equal(await g(page, () => categoryMapping.filter(m => m.prefix === document.getElementById('mapping-prefix').value).length), 1);
  // POS category chip exists
  assert.ok((await page.textContent('#pos-cat-scroll')).includes('หมวดทดสอบ E2E'));

  // hide
  await row().locator('[data-action="toggle-hide"]').click();
  assert.equal(await row().count(), 0, 'hidden row not listed');
  assert.deepEqual(await g(page, () => hiddenMappingPrefixes), [prefix]);
  const bar = page.locator('#mapping-list .mapping-hidden-bar');
  assert.match(await bar.textContent(), /แสดงรายการที่ซ่อนไว้ \(1\)/);
  await checkIcons(page, 'mapping hidden');
  // show hidden rows, then un-hide
  await bar.click();
  assert.equal(await row().count(), 1);
  assert.ok(await row().evaluate(e => e.classList.contains('mapping-row-hidden')));
  await row().locator('[data-action="toggle-hide"]').click();
  assert.deepEqual(await g(page, () => hiddenMappingPrefixes), []);
  assert.equal(await page.locator('#mapping-list .mapping-hidden-bar').count(), 0);
  assert.ok(!(await row().evaluate(e => e.classList.contains('mapping-row-hidden'))));

  // persisted across reload
  await page.reload(); await ready(page);
  assert.ok(await g(page, () => categoryMapping.some(m => m.name === 'หมวดทดสอบ E2E')));
  await gotoPage(page, 'more');
  await page.click('.mapping-card-header');

  // locked official rows cannot be deleted
  const locked = page.locator('#mapping-list .mapping-row').first();
  assert.equal(await locked.locator('[data-action="delete-mapping"]').count(), 0, 'official row has no delete button');
  const nBefore = await g(page, () => categoryMapping.length);
  await g(page, () => deleteMapping(0));
  assert.equal(await g(page, () => categoryMapping.length), nBefore);

  // delete (cancel first, then confirm)
  s.expectDialog(false);
  await row().locator('[data-action="delete-mapping"]').click();
  assert.equal(await row().count(), 1, 'cancelled delete keeps row');
  s.expectDialog(true);
  await row().locator('[data-action="delete-mapping"]').click();
  assert.equal(s.dialogs.at(-1).message, 'ลบการแม็พนี้?');
  assert.equal(await row().count(), 0);
  assert.ok(!(await g(page, () => categoryMapping.some(m => m.name === 'หมวดทดสอบ E2E'))));
  assert.equal((await prod(page, '7000000000001')).category, 'อื่นๆ', 'product category recomputed after delete');
});

test('print button calls window.print', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 1 });
  await cashSale(page, [[P1, 1]], ['5', '0']);
  assert.equal(await g(page, () => window.__printCalls), 0);
  await page.click('#modal-receipt button:has-text("พิมพ์")');
  assert.equal(await g(page, () => window.__printCalls), 1);
  await assertVisibleOpen(page, 'modal-receipt', 'receipt stays open after print');
  // @media print hides the app chrome and shows the receipt
  await page.emulateMedia({ media: 'print' });
  assert.ok(await page.locator('#receipt-content').isVisible(), 'receipt visible in print media');
  assert.ok(!(await page.locator('#bottom-nav').isVisible()), 'bottom nav hidden in print media');
  await page.emulateMedia({ media: 'screen' });
});

test('store switcher: add store, data isolated, switch back, rename, delete store', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 4 });
  await card(page, P1).click(); // cart in store 1 (kept with store 1)
  await sidebar(page, 'สลับ / จัดการร้าน');
  await assertVisibleOpen(page, 'modal-stores', 'stores');
  assert.equal(await page.locator('#store-list .store-row').count(), 1);

  s.expectDialog(true, 'สาขาสอง');  // prompt: name
  s.expectDialog(true);              // confirm: switch now?
  s.expectDialog(true);              // confirm: cart will stay with current store
  await Promise.all([page.waitForEvent('load'), page.click('#modal-stores button:has-text("เพิ่มร้าน")')]);
  await ready(page).catch(() => {});
  await page.waitForFunction(() => window.XLSX && window.Chart && typeof currentStoreId !== 'undefined');
  assert.deepEqual(s.dialogs.slice(-3).map(d => d.type), ['prompt', 'confirm', 'confirm']);
  let st = await g(page, () => ({ currentStoreId, stores, n: products.length, sales: sales.length, cart: cart.length, name: settings.storeName }));
  assert.equal(st.currentStoreId, 2);
  assert.deepEqual(st.stores.map(x => x.name), ['ร้านหลัก', 'สาขาสอง']);
  assert.deepEqual([st.n, st.sales, st.cart], [0, 0, 0], 'new store starts empty (no demo seed, no cart)');
  assert.equal(st.name, 'สาขาสอง');
  assert.ok((await page.textContent('#header-subtitle')).includes('สาขาสอง'));
  await checkIcons(page, 'store 2 header');

  // add a product in store 2 through the product form
  await gotoPage(page, 'products');
  await page.click('#topbar-action');
  await page.fill('#pm-product_id', '4100077');
  await page.dispatchEvent('#pm-product_id', 'input');
  assert.equal(await page.inputValue('#pm-category'), 'SNACKS', 'category auto-filled from prefix');
  await page.fill('#pm-barcode', '8800000000077');
  await page.fill('#pm-name', 'สินค้าเฉพาะสาขาสอง');
  await page.fill('#pm-price', '12');
  await page.fill('#pm-stock', '6');
  await page.click('#modal-product button:has-text("บันทึก")');
  await assertClosed(page, 'modal-product', 'product saved');
  assert.equal(await g(page, () => products.length), 1);
  const ls = await g(page, () => ({ s2: JSON.parse(localStorage.getItem('qpos_s2_products')), s1: JSON.parse(localStorage.getItem('qpos_products')) }));
  assert.deepEqual(ls.s2.map(p => p.name), ['สินค้าเฉพาะสาขาสอง']);
  assert.equal(ls.s1.length, 4);
  assert.ok(!ls.s1.some(p => p.name === 'สินค้าเฉพาะสาขาสอง'), 'store 1 data untouched');

  // switch back via header subtitle (visible when >1 store)
  await page.click('#header-subtitle');
  await assertVisibleOpen(page, 'modal-stores', 'stores via header');
  await Promise.all([page.waitForEvent('load'), page.locator('#store-list .store-row', { hasText: 'ร้านหลัก' }).locator('button:has-text("สลับ")').click()]);
  await ready(page);
  st = await g(page, () => ({ currentStoreId, names: products.map(p => p.name), cart: cart.map(c => c.name) }));
  assert.equal(st.currentStoreId, 1);
  assert.equal(st.names.length, 4);
  assert.ok(!st.names.includes('สินค้าเฉพาะสาขาสอง'));
  assert.deepEqual(st.cart, [P1.name], 'store 1 cart restored');

  // rename store 2
  await g(page, () => openStoresModal());
  s.expectDialog(true, 'สาขาสอง (ใหม่)');
  await page.locator('#store-list .store-row', { hasText: 'สาขาสอง' }).locator('button[title="เปลี่ยนชื่อ"]').click();
  assert.ok((await page.textContent('#store-list')).includes('สาขาสอง (ใหม่)'));
  // active store (1) can't be deleted
  assert.equal(await page.locator('#store-list .store-row', { hasText: 'ร้านหลัก' }).locator('button[title="ลบร้าน"]').count(), 0);
  // delete store 2 (cancel, then confirm)
  s.expectDialog(false);
  await page.locator('#store-list .store-row', { hasText: 'สาขาสอง' }).locator('button[title="ลบร้าน"]').click();
  assert.equal(await g(page, () => stores.length), 2);
  s.expectDialog(true);
  await page.locator('#store-list .store-row', { hasText: 'สาขาสอง' }).locator('button[title="ลบร้าน"]').click();
  st = await g(page, () => ({ stores, keys: Object.keys(localStorage).filter(k => k.startsWith('qpos_s2_')), g: JSON.parse(localStorage.getItem('qpos_stores')) }));
  assert.deepEqual(st.stores.map(x => x.id), [1]);
  assert.deepEqual(st.g.map(x => x.id), [1]);
  assert.deepEqual(st.keys, [], 'all store-2 keys removed');
  assert.equal(await g(page, () => products.length), 4, 'store 1 data still there');
  await page.reload(); await ready(page);
  assert.equal(await g(page, () => stores.length), 1);
});

test('keyboard shortcuts: F2, /, ?, F4, F8, F9, Esc', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 5 });
  const active = () => g(page, () => document.activeElement && document.activeElement.id);
  await page.keyboard.press('F2');
  assert.equal(await active(), 'pos-search-input');
  // F2 from another page jumps back to POS
  await gotoPage(page, 'products');
  await page.keyboard.press('F2');
  assert.equal(await g(page, () => currentPage), 'pos');
  assert.equal(await active(), 'pos-search-input');
  // '?' while typing is just text
  await page.keyboard.type('?');
  assert.ok(!(await isOpen(page, 'modal-shortcuts')));
  assert.equal(await page.inputValue('#pos-search-input'), '?');
  await page.fill('#pos-search-input', '');
  await page.dispatchEvent('#pos-search-input', 'input');
  await g(page, () => document.activeElement.blur());
  // '/' focuses search when not typing; '?' opens help
  await page.keyboard.press('/');
  assert.equal(await active(), 'pos-search-input');
  assert.equal(await page.inputValue('#pos-search-input'), '', '"/" is not typed into the box');
  await g(page, () => document.activeElement.blur());
  await page.keyboard.press('?');
  await assertVisibleOpen(page, 'modal-shortcuts', '?');
  await checkIcons(page, 'shortcuts');
  await page.keyboard.press('Escape');
  await assertClosed(page, 'modal-shortcuts', 'Esc');
  // F8 with empty cart → warning, no modal
  await page.keyboard.press('F8');
  await waitToast(page, /ยังไม่มีสินค้า/);
  assert.ok(!(await isOpen(page, 'modal-payment')));
  // Enter in search adds first match (barcode)
  await page.keyboard.press('F2');
  await page.keyboard.type(P1.barcode);
  await page.keyboard.press('Enter');
  assert.deepEqual(await g(page, () => cart.map(c => [c.name, c.qty])), [[P1.name, 1]]);
  assert.equal(await page.inputValue('#pos-search-input'), '');
  // F4 cart, Esc
  await page.keyboard.press('F4');
  await assertVisibleOpen(page, 'cart-sheet', 'F4');
  await page.keyboard.press('Escape');
  await assertClosed(page, 'cart-sheet', 'Esc cart');
  // F8 payment (works while focus is in the search box)
  await page.focus('#pos-search-input');
  await page.keyboard.press('F8');
  await assertVisibleOpen(page, 'modal-payment', 'F8');
  assert.match(await page.textContent('#pay-total-display'), /25\.00/);
  await page.keyboard.press('Escape');
  await assertClosed(page, 'modal-payment', 'Esc payment');
  // F9 hold
  await page.keyboard.press('F9');
  assert.equal(await g(page, () => holdBills.length), 1);
  assert.equal(await g(page, () => cart.length), 0);
  // modifier keys are ignored
  await page.keyboard.press('Control+F4');
  assert.ok(!(await isOpen(page, 'cart-sheet')));
});

test('camera scanner (stubbed BarcodeDetector): fills POS search / adds item, fills product barcode field, photo scan', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 3 });
  // known in-stock barcode → added to cart, search cleared
  await page.click('#pos-scan-btn');
  await page.waitForFunction(() => _scan && document.getElementById('scanner-video').readyState >= 2);
  await assertVisibleOpen(page, 'modal-scanner', 'scanner');
  assert.ok(await g(page, () => _scan.track.readyState === 'live'), 'fake camera track live');
  await page.waitForFunction(() => window.__detectCalls > 0);
  const track = await page.evaluateHandle(() => _scan.track);
  await g(page, () => { window.__barcodeValue = '8859733221136'; });
  await page.waitForFunction(() => !document.getElementById('modal-scanner').classList.contains('open'));
  assert.equal(await track.evaluate(t => t.readyState), 'ended', 'camera stopped after a hit');
  assert.equal(await g(page, () => window.__lastDetectSource), 'HTMLVideoElement');
  assert.deepEqual(await g(page, () => cart.map(c => [c.name, c.qty])), [[P1.name, 1]]);
  await waitToast(page, /พบ Barcode: 8859733221136/);

  // unknown barcode → stays in the search box (filtered grid shows nothing)
  await page.click('#pos-scan-btn');
  await page.waitForFunction(() => _scan && window.__detectCalls > 0);
  await g(page, () => { window.__barcodeValue = '0000000000017'; });
  await page.waitForFunction(() => !document.getElementById('modal-scanner').classList.contains('open'));
  assert.equal(await page.inputValue('#pos-search-input'), '0000000000017');
  assert.equal(await g(page, () => cart.length), 1);

  // product form: camera → barcode field
  await g(page, () => openProductModal());
  await page.click('#modal-product button[title^="สแกนบาร์โค้ด"]');
  await page.waitForFunction(() => _scan && window.__detectCalls > 0);
  await g(page, () => { window.__barcodeValue = '8851234567890'; });
  await page.waitForFunction(() => !document.getElementById('modal-scanner').classList.contains('open'));
  assert.equal(await page.inputValue('#pm-barcode'), '8851234567890');
  await assertVisibleOpen(page, 'modal-product', 'product form kept');
  await page.keyboard.press('Escape');

  // photo scan (file input → createImageBitmap → detector)
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');
  await g(page, () => { window.__barcodeValue = '6942712001293'; }); // P2 has no stock → stays in box, "สินค้าหมด"
  await page.setInputFiles('#pos-photo-input', { name: 'code.png', mimeType: 'image/png', buffer: png });
  await waitToast(page, /พบ Barcode: 6942712001293/);
  assert.equal(await page.inputValue('#pos-search-input'), '6942712001293');
  assert.equal(await g(page, () => window.__lastDetectSource), 'ImageBitmap');
  await g(page, () => openProductModal());
  await g(page, () => { window.__barcodeValue = '1112223334445'; });
  await page.setInputFiles('#pm-photo-input', { name: 'code.png', mimeType: 'image/png', buffer: png });
  await page.waitForFunction(() => document.getElementById('pm-barcode').value === '1112223334445');
  // photo with no barcode
  await page.setInputFiles('#pm-photo-input', { name: 'code.png', mimeType: 'image/png', buffer: png });
  await waitToast(page, /ไม่พบบาร์โค้ดในภาพ/);
});

test('closing the scanner while the camera is still starting is not reported as an error', async (s) => {
  const page = await s.open();
  for (let i = 0; i < 5; i++) {
    await page.click('#pos-scan-btn');
    await page.waitForFunction(() => document.getElementById('modal-scanner').classList.contains('open'));
    await page.keyboard.press('Escape'); // before video.play() resolves
    await page.waitForTimeout(300);
    assert.ok(!(await isOpen(page, 'modal-scanner')), 'scanner stays closed');
    assert.equal(await g(page, () => _scan), null);
  }
  const toasts = await page.evaluate(() => [...document.querySelectorAll('#toast-container .toast-error')].map(t => t.textContent));
  assert.deepEqual(toasts, [], 'no error toast');
});

test('scanner without BarcodeDetector shows a warning instead of failing', async (s) => {
  const ctx = await s.context();
  await ctx.addInitScript(() => { delete window.BarcodeDetector; });
  const page = await s.open({ context: ctx });
  assert.equal(await g(page, () => 'BarcodeDetector' in window), false);
  await page.click('#pos-scan-btn');
  await waitToast(page, /ไม่รองรับกล้องสด/);
  assert.ok(!(await isOpen(page, 'modal-scanner')));
});

test('offline banner appears when the network drops and hides when it returns', async (s) => {
  const ctx = await s.context();
  const page = await s.open({ context: ctx });
  await page.waitForTimeout(300); // health check against the static server (404 → "unknown", no banner)
  assert.ok(await page.locator('#offline-indicator').evaluate(e => e.classList.contains('hidden')));
  await ctx.setOffline(true);
  await page.waitForFunction(() => !document.getElementById('offline-indicator').classList.contains('hidden'));
  assert.match(await page.textContent('#offline-indicator'), /ออฟไลน์/);
  await checkIcons(page, 'offline banner');
  await ctx.setOffline(false);
  await page.waitForFunction(() => document.getElementById('offline-indicator').classList.contains('hidden'));
  await waitToast(page, /กลับมาออนไลน์แล้ว/);
});

test('sales report counts a sale made shortly after midnight (Asia/Bangkok) as today', async (s) => {
  const ctx = await s.context();
  const page = await ctx.newPage();
  s.watch(page);
  // 01:30 local on the 30th = 18:30 UTC on the 29th
  await page.clock.setFixedTime(new Date('2026-10-30T01:30:00+07:00'));
  await page.goto(BASE); await ready(page);
  await setStock(page, { [P1.barcode]: 2 });
  await cashSale(page, [[P1, 1]], ['5', '0']);
  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  await gotoPage(page, 'reports');
  await page.click('#rtab-sales button:has-text("วันนี้")');
  assert.equal(await page.inputValue('#rep-sale-from'), '2026-10-30');
  assert.equal(await page.textContent('#rs-bills'), '1', 'sale at 01:30 belongs to today');
  assert.deepEqual(await g(page, () => salesChartInst.data.labels), ['2026-10-30'], 'chart groups by local day');
  await page.click('button:has-text("7วันนี้ vs 7วันก่อน")');
  assert.equal(await g(page, () => periodSummary(today(), today()).bills), 1, 'compare report uses local day');
});

test('a sale with a malformed date does not break the reports', async (s) => {
  const page = await s.open();
  await setStock(page, { [P1.barcode]: 2 });
  await cashSale(page, [[P1, 1]], ['5', '0']);
  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  // one corrupted record (long, unparsable date) next to a good one
  await page.evaluate(() => { sales.push({ ...sales[0], id: 'bad', billNo: 'BBAD01', date: 'not-a-real-date-value' }); save(); });
  await page.reload(); await ready(page);
  await gotoPage(page, 'reports');
  await page.click('#rtab-sales button:has-text("วันนี้")');
  assert.equal(await page.textContent('#rs-bills'), '1', 'the valid sale is still counted');
  assert.deepEqual(await g(page, () => salesChartInst.data.labels), [await g(page, () => today())]);
  await page.click('button:has-text("7วันนี้ vs 7วันก่อน")');
  assert.equal(await g(page, () => periodSummary(today(), today()).bills), 1);
  assert.equal(await g(page, () => localDay('not-a-real-date-value')), 'not-a-real', 'falls back to the first 10 chars');
});

test('store list edits from a stale second tab do not drop stores added in another tab', async (s) => {
  const ctx = await s.context();
  const a = await s.open({ context: ctx });
  const b = await s.open({ context: ctx });           // both tabs loaded stores = [ร้านหลัก]
  const saved = () => g(a, () => JSON.parse(localStorage.getItem('qpos_stores')).map(x => `${x.id}:${x.name}`));

  s.expectDialog(true, 'แท็บเอ'); s.expectDialog(false); // prompt name, decline "switch now?"
  await g(a, () => addStore());
  s.expectDialog(true, 'แท็บบี'); s.expectDialog(false);
  await g(b, () => addStore());                          // b still holds the old list in memory
  assert.deepEqual(await saved(), ['1:ร้านหลัก', '2:แท็บเอ', '3:แท็บบี'], 'b must not overwrite a\'s store or reuse its id');

  s.expectDialog(true, 'แท็บเอ ใหม่');
  await g(a, () => renameStore(2));                      // a does not know store 3 yet
  assert.deepEqual(await saved(), ['1:ร้านหลัก', '2:แท็บเอ ใหม่', '3:แท็บบี']);

  s.expectDialog(true);
  await g(b, () => deleteStore(2));                      // b still has the old name in memory
  assert.deepEqual(await saved(), ['1:ร้านหลัก', '3:แท็บบี']);

  await g(a, () => switchStore(2));                      // deleted in the other tab: no reload, warning
  await waitToast(a, /ไม่พบร้านนี้แล้ว/);
  assert.equal(await g(a, () => currentStoreId), 1);
  assert.deepEqual(await saved(), ['1:ร้านหลัก', '3:แท็บบี'], 'switching must not resurrect the deleted store');
});

test('file:// — index.html opened from disk loads and works without page errors', async (s) => {
  const ctx = await s.context({ permissions: [] });
  const page = await s.open({ context: ctx, url: FILE_URL });
  assert.equal(await g(page, () => location.protocol), 'file:');
  await checkIcons(page, 'file:// pos');
  for (const name of ['products', 'purchase', 'debt', 'reports', 'more', 'pos']) {
    await gotoPage(page, name);
    await checkIcons(page, 'file:// ' + name);
  }
  // modals except the camera scanner
  for (const fn of ['openHoldBillsPage()', 'openProductModal()', "showSubPage('stock-adjust')", 'openPurchaseModal()', 'openDebtModal()', 'openExpense()', 'openStoresModal()', "openModal('modal-shortcuts')"]) {
    await page.evaluate(fn);
    await checkIcons(page, 'file:// ' + fn);
    await page.keyboard.press('Escape');
  }
  assert.equal(await g(page, () => document.querySelectorAll('.modal-overlay.open').length), 0);
  // localStorage works on file:// — a sale persists across reload
  await setStock(page, { [P1.barcode]: 2 });
  await cashSale(page, [[P1, 1]], ['5', '0']);
  await page.click('#modal-receipt button:has-text("บิลใหม่")');
  await page.reload(); await ready(page);
  assert.equal(await g(page, () => sales.length), 1);
  assert.ok(await page.locator('#offline-indicator').evaluate(e => e.classList.contains('hidden')), 'no server banner on file://');
});

// ─────────────────────────────────────────────────────────────
// Runner
// ─────────────────────────────────────────────────────────────
(async () => {
  ensureVendor();
  browser = await chromium.launch({
    headless: !process.env.E2E_HEADED,
    args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
    // Without a UTF-8 locale, Linux Chromium replaces non-ASCII download names
    // (e.g. the Thai store name in the backup file) with "download".
    env: { ...process.env, LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
  });
  let failed = 0, passed = 0, skipped = 0;
  for (const t of tests) {
    if (ONLY && !t.name.includes(ONLY)) continue;
    if (t.skip) { skipped++; console.log(`SKIP  ${t.name}\n      ${t.skip}`); continue; }
    const s = new Session();
    const t0 = Date.now();
    let err = null;
    let timer = null;
    try {
      await Promise.race([
        t.fn(s),
        new Promise((_, rej) => { timer = setTimeout(() => rej(new Error('test timed out after 90s')), 90000); }),
      ]);
      if (s.pageErrors.length) throw new Error('uncaught page error(s):\n        ' + s.pageErrors.join('\n        '));
      if (s.consoleErrors.length) throw new Error('console error(s):\n        ' + s.consoleErrors.join('\n        '));
      if (s.dialogPlan.length) throw new Error(`${s.dialogPlan.length} expected dialog(s) never appeared`);
    } catch (e) { err = e; } finally { clearTimeout(timer); }
    await s.close();
    const ms = Date.now() - t0;
    if (err) { failed++; console.log(`FAIL  ${t.name} (${ms}ms)\n      ${(err.stack || String(err)).split('\n').slice(0, 6).join('\n      ')}`); }
    else { passed++; console.log(`PASS  ${t.name} (${ms}ms)`); }
  }
  await browser.close();
  fs.rmSync(OUT, { recursive: true, force: true });
  console.log(`\n${passed} passed, ${failed} failed, ${skipped} skipped`);
  process.exitCode = failed ? 1 : 0;
})().catch(e => { console.error(e); process.exitCode = 2; if (browser) browser.close(); });
