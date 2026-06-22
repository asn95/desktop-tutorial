const tg = window.Telegram.WebApp;
const API_BASE = window.location.origin + "/api";

let initDataString = "";
let currentTasks = [];
let selectedTask = null;
let selectedTag = null;
let loginAttempts = 0;
const MAX_LOGIN_ATTEMPTS = 5;

// --- HTML Escaping ---
function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// --- Offline Cache ---
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
        tg.HapticFeedback.notificationOccurred('success');
        tg.showAlert("Laporan berhasil dikirim!", () => loginSecure());
    } catch (err) {
        tg.showAlert("Pengiriman gagal.");
    } finally {
        tg.MainButton.hideProgress();
    }
});

function renderTasks() {
    taskContainer.innerHTML = '';
    const active = currentTasks.filter(t => t.status !== 'completed').length;
    document.getElementById('active-cases').textContent = active;

    if (active === 0) {
        taskContainer.innerHTML = '<p style="text-align:center;color:#9ca3af;padding:40px 16px;font-size:13px;">Tidak ada tugas tertunda.</p>';
        return;
    }

    const activeTasks = currentTasks.filter(t => t.status !== 'completed');
    activeTasks.forEach((task, i) => {
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
    document.getElementById('target-amount').textContent = 'Saldo: Rp ' + task.amountDue.toLocaleString('id-ID');
    document.getElementById('report-form').reset();
    document.getElementById('photo-area').className = 'upbox';
    document.getElementById('photo-preview').innerHTML = '<p class="upbox-ph">Ketuk untuk mengambil bukti foto</p>';
    document.getElementById('cmt-input').value = '';
    document.querySelectorAll('.cmt-tag').forEach(t => t.classList.remove('active'));
    loadComments(task.id);
    showView('detail');
}

// --- Comment Functions ---

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
