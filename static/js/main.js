/**
 * QC-Check 02 — メインインタラクション
 * WebRTC camera capture + Flask API interaction + Image Viewer
 */

// ── カメラ初期化 (WebRTC) ──

let videoStream = null;
const video = document.getElementById('live-preview');
const canvas = document.getElementById('capture-canvas');
const ctx = canvas.getContext('2d');

async function initCamera() {
    const statusEl = document.getElementById('camera-status');
    const statusText = document.getElementById('status-text');
    const fallback = document.getElementById('camera-fallback');

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment'
            },
            audio: false
        });

        video.srcObject = stream;
        videoStream = stream;

        statusEl.className = 'camera-status status-live';
        statusText.textContent = 'カメラ接続中';
        video.style.display = 'block';
        fallback.style.display = 'none';

    } catch (err) {
        console.warn('Camera not available:', err);
        statusEl.className = 'camera-status status-mock';
        statusText.textContent = 'カメラ未接続';
        video.style.display = 'none';
        fallback.style.display = 'flex';
    }
}

// ── トースト通知 ──

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ── 撮影 ──

async function captureImage() {
    const btn = document.getElementById('capture-btn');
    const flash = document.getElementById('capture-flash');
    const cableId = document.getElementById('cable-id').value.trim();

    if (!videoStream) {
        showToast('✗ カメラが接続されていません', 'error');
        return;
    }

    btn.classList.add('capturing');
    btn.disabled = true;
    flash.classList.add('flash');

    try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);

        const imageData = canvas.toDataURL('image/jpeg', 0.95);

        const response = await fetch('/capture', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: imageData,
                cable_id: cableId,
            }),
        });

        const data = await response.json();

        if (data.success) {
            showToast(`✓ 撮影完了: ${data.filename}`, 'success');
            refreshGallery();
            refreshStats();
        } else {
            showToast(`✗ 撮影失敗: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast(`✗ エラー: ${err.message}`, 'error');
    }

    setTimeout(() => {
        btn.classList.remove('capturing');
        btn.disabled = false;
        flash.classList.remove('flash');
    }, 500);
}

// ── ラベル付け ──

async function labelImage(filepath, label) {
    try {
        const response = await fetch('/label', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath, label }),
        });

        const data = await response.json();

        if (data.success) {
            const labelJa = label === 'ok' ? 'OK' : 'NG';
            showToast(`✓ ${labelJa} に分類しました`, label === 'ok' ? 'success' : 'error');
            refreshGallery();
            refreshStats();
        } else {
            showToast(`✗ ラベル変更失敗: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast(`✗ エラー: ${err.message}`, 'error');
    }
}

// ── ギャラリー更新 ──

// ── ギャラリー更新 ──

// グローバル: ギャラリーの画像データを保持 (viewer.js と共有)
window.galleryImages = [];

async function refreshGallery() {
    // キャプチャページのみギャラリー(最近の撮影)がある
    const grid = document.getElementById('gallery-grid');
    if (!grid) return;

    try {
        const response = await fetch('/gallery?n=24');
        window.galleryImages = await response.json();

        if (window.galleryImages.length === 0) {
            grid.innerHTML = `
                <div class="gallery-empty">
                    <p>まだ撮影がありません</p>
                    <p>「撮影」ボタンで画像をキャプチャしてください</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = window.galleryImages.map((img, index) => {
            const imgSrc = `/image?path=${encodeURIComponent(img.filepath)}`;
            // view.js の openViewer を使用
            // エスケープ不要、dataset経由で渡す (HTML側で修正済み)
            return `
                <div class="gallery-item" data-filepath="${img.filepath}"
                     onclick="openViewer(this.dataset.filepath)">
                    <img src="${imgSrc}" alt="${img.filename}" loading="lazy">
                    <div class="gallery-label label-${img.label}">${img.label.toUpperCase()}</div>
                    <div class="gallery-actions">
                        <button class="btn-label btn-ok"
                                onclick="event.stopPropagation(); labelImage(this.closest('.gallery-item').dataset.filepath, 'ok')"
                                title="OK判定">✓</button>
                        <button class="btn-label btn-ng"
                                onclick="event.stopPropagation(); labelImage(this.closest('.gallery-item').dataset.filepath, 'ng')"
                                title="NG判定">✗</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Gallery refresh failed:', err);
    }
}

// ── 統計更新 ──

async function refreshStats() {
    try {
        const response = await fetch('/stats');
        const stats = await response.json();

        const ids = ['stat-ok', 'stat-ng', 'stat-unlabeled', 'stat-total'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = stats[id.replace('stat-', '')];
        });
    } catch (err) {
        console.error('Stats refresh failed:', err);
    }
}

// ── キーボードショートカット (撮影のみ) ──

document.addEventListener('keydown', (e) => {
    // ビューアが開いているときは何もしない (viewer.js が処理)
    if (document.body.style.overflow === 'hidden') return;

    if (e.code === 'Space' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        captureImage();
    }
});

// ── 初期化 ──

document.addEventListener('DOMContentLoaded', () => {
    // カメラ要素がある場合のみ初期化
    if (document.getElementById('live-preview')) {
        initCamera();
    }
    refreshGallery();
    setInterval(refreshStats, 30000);
});
