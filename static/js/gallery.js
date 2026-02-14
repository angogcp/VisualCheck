/**
 * QC-Check 02 — ギャラリーページ
 * フィルタリング、検索、削除、ページネーション
 */

let currentFilter = '';
let currentCableId = '';
let currentOffset = 0;
let galleryImages = [];
let searchTimeout = null;
let pendingDeletePath = '';
const PAGE_SIZE = 40;

// ── フィルタタブ ──

function setFilter(label) {
    currentFilter = label;
    currentOffset = 0;

    // タブのアクティブ状態を更新
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.label === label);
    });

    loadGallery(true);
}

// ── 検索 ──

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentCableId = document.getElementById('search-cable-id').value.trim();
        currentOffset = 0;
        loadGallery(true);
    }, 300);
}

// ── ギャラリー読み込み ──

async function loadGallery(reset = false) {
    const grid = document.getElementById('gallery-full-grid');
    const loading = document.getElementById('gallery-loading');
    const pagination = document.getElementById('pagination');

    if (reset) {
        grid.innerHTML = '';
        galleryImages = [];
        currentOffset = 0;
        grid.appendChild(loading);
        loading.style.display = 'flex';
    }

    const params = new URLSearchParams({
        n: PAGE_SIZE,
        offset: currentOffset,
    });
    if (currentFilter) params.set('label', currentFilter);
    if (currentCableId) params.set('cable_id', currentCableId);

    try {
        const response = await fetch(`/gallery?${params}`);
        const data = await response.json();

        loading.style.display = 'none';

        // API が配列を返す場合（後方互換）とオブジェクトを返す場合
        let images, hasMore, total;
        if (Array.isArray(data)) {
            images = data;
            hasMore = false;
            total = data.length;
        } else {
            images = data.images;
            hasMore = data.has_more;
            total = data.total;
        }

        if (reset) galleryImages = [];
        galleryImages = galleryImages.concat(images);

        if (galleryImages.length === 0 && reset) {
            grid.innerHTML = `
                <div class="gallery-empty-full">
                    <div class="empty-icon">🔍</div>
                    <p>画像が見つかりません</p>
                    <p class="empty-sub">フィルタや検索条件を変更してみてください</p>
                </div>
            `;
            pagination.style.display = 'none';
            return;
        }

        // 画像カードを追加
        const fragment = document.createDocumentFragment();
        images.forEach((img, i) => {
            const index = reset ? i : (galleryImages.length - images.length + i);
            const card = createGalleryCard(img, index);
            fragment.appendChild(card);
        });
        grid.appendChild(fragment);

        // ページネーション
        if (hasMore) {
            pagination.style.display = 'flex';
            document.getElementById('pagination-info').textContent =
                `${galleryImages.length} / ${total} 件表示中`;
            currentOffset += PAGE_SIZE;
        } else {
            pagination.style.display = 'none';
        }

        // 統計更新
        refreshGalleryStats();

    } catch (err) {
        loading.style.display = 'none';
        console.error('Gallery load failed:', err);
        grid.innerHTML = `
            <div class="gallery-empty-full">
                <div class="empty-icon">⚠️</div>
                <p>読み込みに失敗しました</p>
                <p class="empty-sub">${err.message}</p>
            </div>
        `;
    }
}

function createGalleryCard(img, index) {
    const div = document.createElement('div');
    div.className = 'gallery-item-full';
    div.dataset.filepath = img.filepath;
    div.dataset.index = index;

    const escapedPath = img.filepath.replace(/\\/g, '\\\\');
    const imgSrc = `/image?path=${encodeURIComponent(img.filepath)}`;

    div.innerHTML = `
        <div class="gallery-thumb" onclick="openGalleryViewer(${index})">
            <img src="${imgSrc}" alt="${img.filename}" loading="lazy">
            <div class="gallery-label label-${img.label}">${img.label.toUpperCase()}</div>
        </div>
        <div class="gallery-item-footer">
            <span class="gallery-item-name">${img.filename}</span>
            <div class="gallery-item-actions">
                <button class="btn-mini btn-mini-ok" onclick="galleryLabel('${escapedPath}', 'ok', this)" title="OK">✓</button>
                <button class="btn-mini btn-mini-ng" onclick="galleryLabel('${escapedPath}', 'ng', this)" title="NG">✗</button>
                <button class="btn-mini btn-mini-del" onclick="requestDelete('${escapedPath}')" title="削除">🗑</button>
            </div>
        </div>
    `;

    return div;
}

// ── もっと表示 ──

function loadMore() {
    loadGallery(false);
}

// ── ラベル付け ──

async function galleryLabel(filepath, label, btn) {
    try {
        const response = await fetch('/label', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath, label }),
        });
        const data = await response.json();

        if (data.success) {
            showToast(`✓ ${label === 'ok' ? 'OK' : 'NG'} に分類しました`, label === 'ok' ? 'success' : 'error');
            // リロード
            loadGallery(true);
        } else {
            showToast(`✗ ${data.error}`, 'error');
        }
    } catch (err) {
        showToast(`✗ エラー: ${err.message}`, 'error');
    }
}

// ── 削除 ──

function requestDelete(filepath) {
    pendingDeletePath = filepath.replace(/\\\\/g, '\\');
    const filename = pendingDeletePath.split(/[\\/]/).pop();
    document.getElementById('confirm-filename').textContent = filename;
    document.getElementById('confirm-overlay').classList.add('active');
}

function cancelDelete() {
    pendingDeletePath = '';
    document.getElementById('confirm-overlay').classList.remove('active');
}

async function confirmDelete() {
    if (!pendingDeletePath) return;

    try {
        const response = await fetch('/image', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath: pendingDeletePath }),
        });
        const data = await response.json();

        if (data.success) {
            showToast('✓ 画像を削除しました', 'success');
            cancelDelete();
            loadGallery(true);
        } else {
            showToast(`✗ ${data.error}`, 'error');
        }
    } catch (err) {
        showToast(`✗ エラー: ${err.message}`, 'error');
    }
}

// ── ビューア（ギャラリーページ用） ──

function openGalleryViewer(index) {
    if (index < 0 || index >= galleryImages.length) return;

    viewerCurrentIndex = index;
    const img = galleryImages[index];
    showViewerImage(
        img.filepath,
        img.label,
        img.filename,
        index + 1,
        galleryImages.length
    );

    const overlay = document.getElementById('viewer-overlay');
    overlay.classList.add('active');
    viewerIsOpen = true;
    document.body.style.overflow = 'hidden';
}

// ── ビューアから削除 ──

function viewerDelete() {
    const viewerImg = document.getElementById('viewer-image');
    const filepath = viewerImg.dataset.filepath;
    if (!filepath) return;
    requestDelete(filepath.replace(/\\/g, '\\\\'));
    closeViewer();
}

// ── 統計更新 ──

async function refreshGalleryStats() {
    try {
        const response = await fetch('/stats');
        const stats = await response.json();
        const setIfExists = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setIfExists('g-stat-ok', stats.ok);
        setIfExists('g-stat-ng', stats.ng);
        setIfExists('g-stat-unlabeled', stats.unlabeled);
        setIfExists('g-stat-total', stats.total);
    } catch (err) {
        console.error('Stats refresh failed:', err);
    }
}

// ── 初期化 ──

document.addEventListener('DOMContentLoaded', () => {
    loadGallery(true);
});
