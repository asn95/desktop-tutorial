
// ── Lokasi kunjungan & antrean offline ──────────────────────────────
//
// Dua masalah lapangan yang nyata. Pertama, tidak ada cara membuktikan petugas
// benar-benar mendatangi alamatnya — EXIF foto tidak bisa dipakai karena Telegram
// menghapus blok GPS-nya (diperiksa pada foto produksi: nol tag GPS), jadi
// koordinat diambil dari perangkat saat mengirim. Kedua, petugas bekerja di data
// seluler: kalau pengiriman gagal, laporan DAN fotonya hilang begitu saja.

function getPosition(timeoutMs = 8000) {
    // Selalu resolve, tidak pernah reject: izin lokasi boleh ditolak dan laporannya
    // tetap harus bisa dikirim. Yang tanpa koordinat tampil sebagai "lokasi tidak
    // dibagikan" di sisi manajer, bukan sebagai kunjungan palsu.
    return new Promise(resolve => {
        if (!navigator.geolocation) return resolve(null);
        let done = false;
        const finish = v => { if (!done) { done = true; resolve(v); } };
        navigator.geolocation.getCurrentPosition(
            p => finish({ lat: p.coords.latitude, lon: p.coords.longitude }),
            () => finish(null),
            { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60000 }
        );
        setTimeout(() => finish(null), timeoutMs + 500);   // jaga-jaga callback tak pernah datang
    });
}

// Antrean di IndexedDB, bukan localStorage: fotonya 1–3 MB dan localStorage hanya
// menyimpan string (base64 membengkak ~33% dan kuotanya ±5 MB untuk seluruh origin).
const OUTBOX_DB = 'c3mr-outbox', OUTBOX_STORE = 'reports';

function outbox() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(OUTBOX_DB, 1);
        req.onupgradeneeded = () => req.result.createObjectStore(OUTBOX_STORE, { keyPath: 'id', autoIncrement: true });
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

function outboxTx(mode, fn) {
    return outbox().then(db => new Promise((resolve, reject) => {
        const tx = db.transaction(OUTBOX_STORE, mode);
        const req = fn(tx.objectStore(OUTBOX_STORE));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    }));
}

const outboxAdd = rec => outboxTx('readwrite', st => st.add(rec));
const outboxAll = () => outboxTx('readonly', st => st.getAll());
const outboxDel = id => outboxTx('readwrite', st => st.delete(id));

async function postReport(rec) {
    const fd = new FormData();
    fd.append("target_id", rec.target_id);
    fd.append("payment_status", rec.payment_status);
    fd.append("notes", rec.notes || "");
    if (rec.lat != null) { fd.append("lat", rec.lat); fd.append("lon", rec.lon); }
    fd.append("photo", rec.photo, rec.photo_name || "bukti.jpg");
    const res = await fetch(`${API_BASE}/officer/report`, {
        method: 'POST',
        headers: { "X-Telegram-Auth": initDataString },
        body: fd
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res;
}

async function flushOutbox() {
    let queued;
    try { queued = await outboxAll(); } catch { return 0; }
    let sent = 0;
    for (const rec of queued) {
        try {
            await postReport(rec);
            await outboxDel(rec.id);
            sent++;
        } catch {
            break;   // masih offline — sisanya biarkan, urutannya dipertahankan
        }
    }
    if (sent) {
        const badge = document.getElementById('outbox-badge');
        if (badge) badge.style.display = 'none';
        try { localStorage.removeItem(CACHE_KEY); } catch (e) {}   // paksa muat ulang dari server
    }
    return sent;
}

async function showOutboxBadge() {
    let n = 0;
    try { n = (await outboxAll()).length; } catch { return; }
    const badge = document.getElementById('outbox-badge');
    if (!badge) return;
    badge.textContent = `${n} laporan menunggu terkirim`;
    badge.style.display = n ? 'block' : 'none';
}

window.addEventListener('online', () => flushOutbox().then(showOutboxBadge));

const tg = window.Telegram.WebApp;
const API_BASE = window.location.origin + "/api";

let initDataString = "";
let currentTasks = [];
let selectedTask = null;
let selectedTag = null;
let selectedPeriod = null; // batch bulanan "YYYY-MM" yang sedang ditampilkan
let searchQuery = "";      // pencarian nama nasabah / alamat, huruf kecil
let loginAttempts = 0;
const MAX_LOGIN_ATTEMPTS = 5;

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

const CACHE_KEY = 'c3mr_tasks_cache';
const CACHE_CMT_PREFIX = 'c3mr_cmt_';

function cacheSet(key, data) {
    try { localStorage.setItem(key, JSON.stringify({ ts: Date.now(), data })); } catch {}
}

function cacheGet(key, maxAgeMs) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        const { ts, data } = JSON.parse(raw);
        if (maxAgeMs && Date.now() - ts > maxAgeMs) return null;
        return data;
    } catch { return null; }
}

const loading = document.getElementById('loading-view');
const loginView = document.getElementById('login-view');
const listView = document.getElementById('list-view');
const detailView = document.getElementById('detail-view');
const taskContainer = document.getElementById('task-container');

window.onload = async () => {
    tg.ready();
    tg.expand();
    initDataString = tg.initData || "";
    const user = tg.initDataUnsafe?.user;
    if (user?.id && initDataString) {
        await loginSecure();
    } else {
        showView('login');
    }
};

async function loginSecure() {
    showView('loading');
    try {
        const response = await fetch(`${API_BASE}/officer/tasks`, {
            headers: { "X-Telegram-Auth": initDataString }
        });
        if (!response.ok) throw new Error();
        currentTasks = await response.json();
        cacheSet(CACHE_KEY, currentTasks);

        const user = tg.initDataUnsafe?.user;
        if (user) {
            const name = user.first_name || 'Petugas';
            document.getElementById('officer-id').textContent =
                name.toUpperCase().slice(0, 4) + '-' + String(user.id).slice(-3);
        }

        const now = new Date();
        document.getElementById('sync-time').textContent =
            now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');

        renderTasks();
        showView('list');
    } catch (err) {
        // Try loading cached data when offline
        const cached = cacheGet(CACHE_KEY, 24 * 60 * 60 * 1000); // 24hr max
        if (cached && cached.length > 0) {
            currentTasks = cached;
            renderTasks();
            showView('list');
            document.getElementById('sync-time').textContent = 'LURING';
        } else {
            alert("Akses ditolak: validasi kriptografi gagal atau petugas belum terdaftar.");
            showView('login');
        }
    }
}

function manualLogin() {
    if (loginAttempts >= MAX_LOGIN_ATTEMPTS) {
        alert("Terlalu banyak percobaan login. Coba lagi dalam 5 menit.");
        return;
    }
    const tid = document.getElementById('manual-tid').value;
    if (tid) {
        loginAttempts++;
        initDataString = `user={"id":${tid},"first_name":"Petugas"}&hash=dummy_hash`;
        loginSecure();
    }
}

function showView(viewId) {
    [loading, loginView, listView, detailView].forEach(el => {
        if (el) el.classList.add('hidden');
    });
    document.getElementById(viewId + '-view').classList.remove('hidden');

    const webBtn = document.getElementById('web-submit-btn');
    if (viewId === 'detail') {
        if (tg.initData) {
            // Inside Telegram: use native MainButton, hide HTML button
            tg.BackButton.show();
            tg.MainButton.setText("KIRIM LAPORAN");
            tg.MainButton.color = "#E81E28";
            tg.MainButton.show();
            if (webBtn) webBtn.classList.add('hidden');
        } else {
            // Outside Telegram: show HTML button only
            if (webBtn) webBtn.classList.remove('hidden');
        }
    } else {
        tg.BackButton.hide();
        tg.MainButton.hide();
        if (webBtn) webBtn.classList.add('hidden');
    }
}

document.getElementById('back-btn').addEventListener('click', () => showView('list'));
tg.BackButton.onClick(() => showView('list'));

tg.MainButton.onClick(async () => {
    const photo = document.getElementById('photo-input').files[0];
    if (!photo) { tg.showAlert("Bukti foto wajib dilampirkan."); return; }

    tg.MainButton.showProgress();
    const pos = await getPosition();
    const rec = {
        target_id: selectedTask.id,
        payment_status: document.getElementById('payment-status').value,
        notes: document.getElementById('notes').value,
        lat: pos ? pos.lat : null,
        lon: pos ? pos.lon : null,
        photo: photo,
        photo_name: photo.name,
    };

    try {
        await postReport(rec);
        tg.HapticFeedback.notificationOccurred('success');
        tg.showAlert("Laporan berhasil dikirim!", () => loginSecure());
    } catch (err) {
        // Jangan buang laporannya. Petugas sudah mendatangi alamatnya dan memotret;
        // memintanya mengulang karena sinyal buruk adalah cara tercepat kehilangan
        // bukti kunjungan yang tidak bisa diambil ulang.
        try {
            await outboxAdd(rec);
            await showOutboxBadge();
            tg.HapticFeedback.notificationOccurred('warning');
            tg.showAlert("Sinyal bermasalah. Laporan disimpan dan akan terkirim otomatis saat jaringan kembali.",
                         () => showView('list'));
        } catch {
            tg.showAlert("Pengiriman gagal dan laporan tidak bisa disimpan. Coba lagi.");
        }
    } finally {
        tg.MainButton.hideProgress();
    }
});

// Periode bulanan, selaras dengan pemilih periode di dashboard web.

const MONTHS_ID = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];

function periodLabel(p) {
    if (!p) return 'Lainnya';
    const [y, m] = p.split('-');
    return (MONTHS_ID[parseInt(m, 10) - 1] || p) + ' ' + y;
}

function renderPeriodOptions() {
    const bar = document.querySelector('.period-bar');
    const sel = document.getElementById('period-select');
    const counts = {};
    currentTasks.filter(t => t.status !== 'completed').forEach(t => {
        const p = t.period || '';
        counts[p] = (counts[p] || 0) + 1;
    });
    const periods = Object.keys(counts).sort().reverse(); // terbaru dulu

    bar.style.display = periods.length ? 'flex' : 'none';
    // Default = batch terbaru; pilihan pengguna dipertahankan bila masih valid.
    if (selectedPeriod !== 'all' && !periods.includes(selectedPeriod)) {
        selectedPeriod = periods[0] ?? null;
    }

    sel.innerHTML = '';
    periods.forEach(p => {
        const o = document.createElement('option');
        o.value = p;
        o.textContent = periodLabel(p) + ' (' + counts[p] + ')';
        sel.appendChild(o);
    });
    if (periods.length > 1) {
        const all = document.createElement('option');
        all.value = 'all';
        all.textContent = 'Semua Periode (' + Object.values(counts).reduce((a, b) => a + b, 0) + ')';
        sel.appendChild(all);
    }
    sel.value = selectedPeriod ?? '';
}

document.getElementById('period-select').addEventListener('change', (e) => {
    selectedPeriod = e.target.value;
    renderTasks();
});

document.getElementById('task-search').addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    renderTasks();
});

function renderTasks() {
    renderPeriodOptions();
    taskContainer.innerHTML = '';
    const inPeriod = (selectedPeriod && selectedPeriod !== 'all')
        ? currentTasks.filter(t => (t.period || '') === selectedPeriod)
        : currentTasks;
    const activeTasks = inPeriod.filter(t => t.status !== 'completed');
    // Hitungan di info-bar tetap beban kerja SEBENARNYA, tidak ikut menyusut saat
    // mengetik — kalau tidak, petugas mengira tugasnya berkurang.
    document.getElementById('active-cases').textContent = activeTasks.length;

    const shown = searchQuery
        ? activeTasks.filter(t =>
            (t.customerName || '').toLowerCase().includes(searchQuery) ||
            (t.address || '').toLowerCase().includes(searchQuery))
        : activeTasks;

    // Terbaru dulu. Backend sudah mengurutkan, tapi cache localStorage bisa
    // menyajikan data lama yang belum terurut sampai 24 jam (lihat cacheGet).
    // .filter() mengembalikan array baru, jadi .sort() tidak merusak currentTasks.
    shown.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    if (shown.length === 0) {
        taskContainer.innerHTML = searchQuery
            ? '<p style="text-align:center;color:#9ca3af;padding:40px 16px;font-size:13px;">Tidak ada tugas yang cocok dengan pencarian.</p>'
            : '<p style="text-align:center;color:#9ca3af;padding:40px 16px;font-size:13px;">Tidak ada tugas tertunda pada periode ini.</p>';
        return;
    }

    shown.forEach((task, i) => {
        const caseNum = '2025-' + String(8394 - i * 3012).replace('-','');

        const div = document.createElement('div');
        div.className = 'tcard';
        div.innerHTML =
            '<div class="tcard-case">Kasus #' + esc(caseNum) + '</div>' +
            '<div class="tcard-name">' + esc(task.customerName) + '</div>' +
            '<div class="tcard-addr">' + esc(task.address) + '</div>' +
            '<div class="tcard-bottom">' +
                '<span class="tcard-amt">Rp ' + task.amountDue.toLocaleString('id-ID') + '</span>' +
                '<button class="tcard-btn">Proses Laporan &rarr;</button>' +
            '</div>';

        div.querySelector('.tcard-btn').addEventListener('click', () => showDetail(task));
        div.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON') showDetail(task);
        });
        taskContainer.appendChild(div);
    });
}

function showDetail(task) {
    selectedTask = task;
    selectedTag = null;
    document.getElementById('target-name').textContent = task.customerName;
    document.getElementById('target-address').textContent = task.address;
    // Koordinat hasil geocoding lebih akurat; alamat teks sebagai cadangan.
    document.getElementById('target-maps').href =
        'https://www.google.com/maps/search/?api=1&query=' +
        (task.latitude != null && task.longitude != null
            ? task.latitude + ',' + task.longitude
            : encodeURIComponent(task.address));
    document.getElementById('target-amount').textContent = 'Saldo: Rp ' + task.amountDue.toLocaleString('id-ID');
    document.getElementById('report-form').reset();
    document.getElementById('photo-area').className = 'upbox';
    document.getElementById('photo-preview').innerHTML = '<p class="upbox-ph">Ketuk untuk mengambil bukti foto</p>';
    document.getElementById('cmt-input').value = '';
    document.querySelectorAll('.cmt-tag').forEach(t => t.classList.remove('active'));
    loadComments(task.id);
    showView('detail');
}

// "Buka di Maps": webview Telegram menelan klik <a target="_blank"> biasa,
// jadi link eksternal harus dibuka lewat API resmi Telegram (openLink).
document.addEventListener('click', (e) => {
    const a = e.target.closest('#target-maps');
    if (!a || !a.href) return;
    e.preventDefault();
    try {
        if (initDataString && tg.openLink) tg.openLink(a.href);
        else window.open(a.href, '_blank');
    } catch {
        window.open(a.href, '_blank');
    }
});


document.addEventListener('click', (e) => {
    if (e.target.classList.contains('cmt-tag')) {
        const tag = e.target.dataset.tag;
        document.querySelectorAll('.cmt-tag').forEach(t => t.classList.remove('active'));
        if (selectedTag === tag) {
            selectedTag = null;
        } else {
            selectedTag = tag;
            e.target.classList.add('active');
        }
    }
});

async function submitComment() {
    const msg = document.getElementById('cmt-input').value.trim();
    if (!msg) { alert("Tulis komentar terlebih dahulu."); return; }

    const btn = document.getElementById('cmt-send');
    btn.disabled = true;
    btn.textContent = "Mengirim...";

    const fd = new FormData();
    fd.append("target_id", selectedTask.id);
    fd.append("message", msg);
    if (selectedTag) fd.append("tag", selectedTag);

    try {
        const res = await fetch(`${API_BASE}/officer/comment`, {
            method: 'POST',
            headers: { "X-Telegram-Auth": initDataString },
            body: fd
        });
        if (!res.ok) throw new Error();
        document.getElementById('cmt-input').value = '';
        selectedTag = null;
        document.querySelectorAll('.cmt-tag').forEach(t => t.classList.remove('active'));
        loadComments(selectedTask.id);
        if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    } catch (err) {
        alert("Gagal mengirim komentar.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Kirim Komentar";
    }
}

async function loadComments(targetId) {
    const list = document.getElementById('cmt-list');
    try {
        const res = await fetch(`${API_BASE}/officer/comments/${targetId}`, {
            headers: { "X-Telegram-Auth": initDataString }
        });
        if (!res.ok) throw new Error();
        const comments = await res.json();
        cacheSet(CACHE_CMT_PREFIX + targetId, comments);

        if (comments.length === 0) {
            list.innerHTML = '<p class="cmt-empty">Belum ada komentar.</p>';
            return;
        }

        const tagLabels = {
            wrong_address: 'Alamat Salah',
            wrong_phone: 'Nomor Salah',
            customer_moved: 'Customer Pindah',
            not_found: 'Tidak Ditemukan',
            other: 'Lainnya'
        };

        list.innerHTML = comments.map(c => {
            const tagHtml = c.tag ? '<span class="cmt-item-tag">' + esc(tagLabels[c.tag] || c.tag) + '</span>' : '';
            const time = new Date(c.created_at).toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
            return '<div class="cmt-item">' + tagHtml +
                '<div class="cmt-item-msg">' + esc(c.message) + '</div>' +
                '<div class="cmt-item-time">' + esc(time) + '</div></div>';
        }).join('');
    } catch (err) {
        const cached = cacheGet(CACHE_CMT_PREFIX + targetId, 24 * 60 * 60 * 1000);
        if (cached) {
            const tagLabels = {
                wrong_address: 'Alamat Salah', wrong_phone: 'Nomor Salah',
                customer_moved: 'Customer Pindah', not_found: 'Tidak Ditemukan', other: 'Lainnya'
            };
            list.innerHTML = cached.map(c => {
                const tagHtml = c.tag ? '<span class="cmt-item-tag">' + esc(tagLabels[c.tag] || c.tag) + '</span>' : '';
                const time = new Date(c.created_at).toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
                return '<div class="cmt-item">' + tagHtml +
                    '<div class="cmt-item-msg">' + esc(c.message) + '</div>' +
                '<div class="cmt-item-time">' + esc(time) + ' (tersimpan)</div></div>';
            }).join('');
        } else {
            list.innerHTML = '<p class="cmt-empty">Gagal memuat komentar.</p>';
        }
    }
}

async function submitReportWeb() {
    const photo = document.getElementById('photo-input').files[0];
    if (!photo) { alert("Bukti foto wajib dilampirkan."); return; }

    const btn = document.getElementById('web-submit-btn');
    btn.textContent = "Memproses...";
    btn.disabled = true;

    const fd = new FormData();
    fd.append("target_id", selectedTask.id);
    fd.append("payment_status", document.getElementById('payment-status').value);
    fd.append("notes", document.getElementById('notes').value);
    fd.append("photo", photo);

    try {
        const res = await fetch(`${API_BASE}/officer/report`, {
            method: 'POST',
            headers: { "X-Telegram-Auth": initDataString },
            body: fd
        });
        if (!res.ok) throw new Error();
        alert("Laporan berhasil dikirim!");
        loginSecure();
    } catch (err) {
        alert("Pengiriman gagal.");
    } finally {
        btn.textContent = "Kirim Laporan";
        btn.disabled = false;
    }
}

document.getElementById('photo-input').onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
        document.getElementById('photo-area').className = 'upbox attached';
        document.getElementById('photo-preview').innerHTML =
            '<p class="upbox-file">' + file.name.toUpperCase() + '</p>' +
            '<p class="upbox-repl">Ganti Foto</p>';
    }
};


// Saat aplikasi dibuka: coba kirim ulang apa pun yang tertinggal di antrean.
// Petugas sering menutup Mini App begitu keluar dari area bersinyal buruk.
flushOutbox().then(showOutboxBadge).catch(() => {});
