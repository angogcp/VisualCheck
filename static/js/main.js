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

// グローバル: ギャラリーの画像データを保持
let galleryImages = [];

async function refreshGallery() {
    try {
        const response = await fetch('/gallery?n=24');
        galleryImages = await response.json();
        const grid = document.getElementById('gallery-grid');

        if (galleryImages.length === 0) {
            grid.innerHTML = `
                <div class="gallery-empty">
                    <p>まだ撮影がありません</p>
                    <p>「撮影」ボタンで画像をキャプチャしてください</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = galleryImages.map((img, index) => {
            const imgSrc = `/image?path=${encodeURIComponent(img.filepath)}`;
            const escapedPath = img.filepath.replace(/\\/g, '\\\\');
            return `
                <div class="gallery-item" data-filepath="${img.filepath}"
                     onclick="openViewer('${escapedPath}')">
                    <img src="${imgSrc}" alt="${img.filename}" loading="lazy">
                    <div class="gallery-label label-${img.label}">${img.label.toUpperCase()}</div>
                    <div class="gallery-actions">
                        <button class="btn-label btn-ok"
                                onclick="event.stopPropagation(); labelImage('${escapedPath}', 'ok')"
                                title="OK判定">✓</button>
                        <button class="btn-label btn-ng"
                                onclick="event.stopPropagation(); labelImage('${escapedPath}', 'ng')"
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

        document.getElementById('stat-ok').textContent = stats.ok;
        document.getElementById('stat-ng').textContent = stats.ng;
        document.getElementById('stat-unlabeled').textContent = stats.unlabeled;
        document.getElementById('stat-total').textContent = stats.total;
    } catch (err) {
        console.error('Stats refresh failed:', err);
    }
}

// ── 画像ビューア ──

let viewerCurrentIndex = -1;
let viewerIsOpen = false;

function openViewer(filepath) {
    // ギャラリー画像からインデックスを検索
    const normalizedPath = filepath.replace(/\\\\/g, '\\');
    const index = galleryImages.findIndex(img => {
        const imgPath = img.filepath.replace(/\\\\/g, '\\');
        return imgPath === normalizedPath;
    });

    if (index === -1) {
        // ギャラリーにない場合は直接表示
        showViewerImage(filepath, '', '', 0, 0);
    } else {
        viewerCurrentIndex = index;
        const img = galleryImages[index];
        showViewerImage(
            img.filepath,
            img.label,
            img.filename,
            index + 1,
            galleryImages.length
        );
    }

    const overlay = document.getElementById('viewer-overlay');
    overlay.classList.add('active');
    viewerIsOpen = true;
    document.body.style.overflow = 'hidden';
}

function showViewerImage(filepath, label, filename, current, total) {
    const viewerImg = document.getElementById('viewer-image');
    const viewerLabel = document.getElementById('viewer-label');
    const viewerFilename = document.getElementById('viewer-filename');
    const viewerCounter = document.getElementById('viewer-counter');

    viewerImg.src = `/image?path=${encodeURIComponent(filepath)}`;
    viewerImg.dataset.filepath = filepath;

    // ラベル表示
    if (label) {
        viewerLabel.textContent = label.toUpperCase();
        viewerLabel.className = 'viewer-label';
        if (label === 'ok') {
            viewerLabel.style.background = 'rgba(0, 230, 118, 0.1)';
            viewerLabel.style.color = '#00e676';
            viewerLabel.style.border = '1px solid rgba(0, 230, 118, 0.3)';
        } else if (label === 'ng') {
            viewerLabel.style.background = 'rgba(255, 82, 82, 0.1)';
            viewerLabel.style.color = '#ff5252';
            viewerLabel.style.border = '1px solid rgba(255, 82, 82, 0.3)';
        } else {
            viewerLabel.style.background = 'rgba(255, 193, 7, 0.1)';
            viewerLabel.style.color = '#ffc107';
            viewerLabel.style.border = '1px solid rgba(255, 193, 7, 0.3)';
        }
    } else {
        viewerLabel.textContent = '';
    }

    viewerFilename.textContent = filename || '';
    viewerCounter.textContent = total > 0 ? `${current} / ${total}` : '';
}

function closeViewer() {
    const overlay = document.getElementById('viewer-overlay');
    overlay.classList.remove('active');
    viewerIsOpen = false;
    document.body.style.overflow = '';
}

function viewerNavigate(direction) {
    if (galleryImages.length === 0) return;

    viewerCurrentIndex += direction;
    if (viewerCurrentIndex < 0) viewerCurrentIndex = galleryImages.length - 1;
    if (viewerCurrentIndex >= galleryImages.length) viewerCurrentIndex = 0;

    const img = galleryImages[viewerCurrentIndex];
    showViewerImage(
        img.filepath,
        img.label,
        img.filename,
        viewerCurrentIndex + 1,
        galleryImages.length
    );
}

async function viewerLabel(label) {
    const viewerImg = document.getElementById('viewer-image');
    const filepath = viewerImg.dataset.filepath;
    if (!filepath) return;

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

            // ギャラリーデータを更新
            if (viewerCurrentIndex >= 0 && viewerCurrentIndex < galleryImages.length) {
                galleryImages[viewerCurrentIndex].label = label;
                galleryImages[viewerCurrentIndex].filepath = data.new_filepath;
            }

            // ビューア表示を更新
            showViewerImage(
                data.new_filepath,
                label,
                galleryImages[viewerCurrentIndex]?.filename || '',
                viewerCurrentIndex + 1,
                galleryImages.length
            );

            viewerImg.dataset.filepath = data.new_filepath;

            // ギャラリーと統計も更新
            refreshGallery();
            refreshStats();
        } else {
            showToast(`✗ ラベル変更失敗: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast(`✗ エラー: ${err.message}`, 'error');
    }
}

// ── キーボードショートカット ──

document.addEventListener('keydown', (e) => {
    if (viewerIsOpen) {
        if (e.code === 'Escape') {
            closeViewer();
        } else if (e.code === 'ArrowLeft') {
            e.preventDefault();
            viewerNavigate(-1);
        } else if (e.code === 'ArrowRight') {
            e.preventDefault();
            viewerNavigate(1);
        }
        return;
    }

    if (e.code === 'Space' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        captureImage();
    }
});

// ── 初期化 ──

document.addEventListener('DOMContentLoaded', () => {
    initCamera();
    refreshGallery();
    setInterval(refreshStats, 30000);
});
