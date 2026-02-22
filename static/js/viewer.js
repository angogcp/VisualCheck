/**
 * QC-Check 02 — 共通画像ビューア (Viewer Modal)
 * main.js と gallery.js から利用可能
 * AI判定機能を追加
 */

let viewerCurrentIndex = -1;
let viewerIsOpen = false;
// window.galleryImages は main.js / gallery.js で定義・更新されることを想定

// ビューアを開く
function openViewer(filepath) {
    // ギャラリー画像からインデックスを検索
    // window.galleryImages が未定義の場合は空配列として扱う
    const images = window.galleryImages || [];

    const normalizedPath = filepath.replace(/\\\\/g, '\\');
    const index = images.findIndex(img => {
        const imgPath = img.filepath.replace(/\\\\/g, '\\');
        return imgPath === normalizedPath;
    });

    if (index === -1) {
        // ギャラリーにない場合は直接表示 (単体表示モード)
        viewerCurrentIndex = -1;
        showViewerImage(filepath, '', '', 0, 0);
    } else {
        viewerCurrentIndex = index;
        const img = images[index];
        showViewerImage(
            img.filepath,
            img.label,
            img.filename,
            index + 1,
            images.length
        );
    }

    const overlay = document.getElementById('viewer-overlay');
    if (overlay) {
        overlay.classList.add('active');
        viewerIsOpen = true;
        document.body.style.overflow = 'hidden';
    }
}

// ビューア閉じる
function closeViewer() {
    const overlay = document.getElementById('viewer-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        viewerIsOpen = false;
        document.body.style.overflow = '';

        // AI結果をリセット
        const aiResult = document.getElementById('ai-result-container');
        if (aiResult) aiResult.style.display = 'none';
    }
}

// 画像表示更新
function showViewerImage(filepath, label, filename, current, total) {
    const viewerImg = document.getElementById('viewer-image');
    const viewerLabel = document.getElementById('viewer-label');
    const viewerFilename = document.getElementById('viewer-filename');
    const viewerCounter = document.getElementById('viewer-counter');
    const btnAnalyze = document.getElementById('btn-analyze');

    if (!viewerImg) return;

    viewerImg.src = `/image?path=${encodeURIComponent(filepath)}`;
    viewerImg.dataset.filepath = filepath;

    // AI結果をリセット
    const aiResult = document.getElementById('ai-result-container');
    if (aiResult) aiResult.style.display = 'none';

    // 分析ボタン有効化
    if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.onclick = () => analyzeImage(filepath);
    }

    // ラベル表示
    if (viewerLabel) {
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
            viewerLabel.style.border = 'none';
            viewerLabel.style.background = 'transparent';
        }
    }

    if (viewerFilename) viewerFilename.textContent = filename || '';
    if (viewerCounter) viewerCounter.textContent = total > 0 ? `${current} / ${total}` : '';
}

// ナビゲーション
function viewerNavigate(direction) {
    const images = window.galleryImages || [];
    if (images.length === 0) return;
    if (viewerCurrentIndex === -1 && images.length > 0) viewerCurrentIndex = 0;

    viewerCurrentIndex += direction;
    if (viewerCurrentIndex < 0) viewerCurrentIndex = images.length - 1;
    if (viewerCurrentIndex >= images.length) viewerCurrentIndex = 0;

    const img = images[viewerCurrentIndex];
    showViewerImage(
        img.filepath,
        img.label,
        img.filename,
        viewerCurrentIndex + 1,
        images.length
    );
}

// ラベル付け (判定)
async function viewerLabel(label) {
    const viewerImg = document.getElementById('viewer-image');
    if (!viewerImg) return;

    const filepath = viewerImg.dataset.filepath;
    if (!filepath) return;

    // main.js / gallery.js の labelImage は使わず、ここで実装するか、
    // window.labelImage があるならそれを使う（統一のため）
    // ここでは汎用的に実装する

    try {
        const response = await fetch('/label', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath, label }),
        });
        const data = await response.json();

        if (data.success) {
            // トースト通知 (window.showToast があると仮定)
            if (window.showToast) {
                const labelJa = label === 'ok' ? 'OK' : 'NG';
                window.showToast(`✓ ${labelJa} に分類しました`, label === 'ok' ? 'success' : 'error');
            }

            // グローバルデータを更新
            const images = window.galleryImages || [];
            if (viewerCurrentIndex >= 0 && viewerCurrentIndex < images.length) {
                images[viewerCurrentIndex].label = label;
                images[viewerCurrentIndex].filepath = data.new_filepath;
            }

            // リフレッシュ (window.refreshGallery などがあれば呼ぶ)
            if (window.refreshGallery) window.refreshGallery();
            if (window.refreshStats) window.refreshStats();

            // ビューア更新
            showViewerImage(
                data.new_filepath,
                label,
                images[viewerCurrentIndex]?.filename || '',
                viewerCurrentIndex + 1,
                images.length
            );

            // パス更新
            viewerImg.dataset.filepath = data.new_filepath;

        } else {
            if (window.showToast) window.showToast(`✗ 失敗: ${data.error}`, 'error');
        }
    } catch (err) {
        console.error(err);
        if (window.showToast) window.showToast(`✗ エラー: ${err.message}`, 'error');
    }
}

// 削除
function viewerDelete() {
    const viewerImg = document.getElementById('viewer-image');
    if (!viewerImg) return;
    const filepath = viewerImg.dataset.filepath;
    if (!filepath) return;

    // 削除確認ダイアログ呼び出し (window.requestDelete)
    if (window.requestDelete) {
        window.requestDelete(filepath.replace(/\\/g, '\\\\'));
        closeViewer();
    } else {
        // main.js にはない機能の場合、簡易実装するか、スキップ
        if (confirm('本当に削除しますか？')) {
            fetch('/image', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filepath }),
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    if (window.showToast) window.showToast('削除しました', 'success');
                    closeViewer();
                    if (window.refreshGallery) window.refreshGallery();
                }
            });
        }
    }
}

// ── AI 分析機能 ──

async function analyzeImage(filepath) {
    const aiContainer = document.getElementById('ai-result-container');
    const aiScoreDiv = document.getElementById('ai-score-value');
    const aiLabelDiv = document.getElementById('ai-label-value');
    const btnAnalyze = document.getElementById('btn-analyze');
    const btnHeatmap = document.getElementById('btn-heatmap');
    const heatmapImg = document.getElementById('viewer-heatmap');

    if (!aiContainer || !btnAnalyze) return;

    btnAnalyze.disabled = true;
    btnAnalyze.innerHTML = '<span class="spinner-mini"></span> 分析中...';
    aiContainer.style.display = 'none';
    if (btnHeatmap) btnHeatmap.style.display = 'none';
    if (heatmapImg) {
        heatmapImg.style.display = 'none';
        heatmapImg.src = '';
    }

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath })
        });
        const data = await response.json();

        if (data.error) {
            if (window.showToast) window.showToast(`AI分析エラー: ${data.error}`, 'error');
        } else {
            // 結果表示
            aiContainer.style.display = 'flex';

            const scorePercent = (data.score * 100).toFixed(1);
            if (aiScoreDiv) {
                aiScoreDiv.textContent = `${scorePercent}%`;
                // 色分け (50%以上でNG警戒色)
                aiScoreDiv.style.color = data.score > 0.5 ? '#ff5252' : '#00e676';
            }

            if (aiLabelDiv) {
                const labelText = data.label === 'ng' ? '異常検知' : '正常';
                aiLabelDiv.textContent = labelText;
                aiLabelDiv.className = `ai-label-pill ${data.label}`;
            }

            // ヒートマップ処理
            if (data.heatmap && heatmapImg && btnHeatmap) {
                heatmapImg.src = data.heatmap;
                btnHeatmap.style.display = 'inline-block';
                // デフォルトで表示しない、ボタンで切り替え
                // heatmapImg.style.display = 'block'; 
            }
        }
    } catch (e) {
        console.error(e);
        if (window.showToast) window.showToast('通信エラーが発生しました', 'error');
    } finally {
        btnAnalyze.disabled = false;
        btnAnalyze.innerHTML = '🤖 AI判定';
    }
}

function toggleHeatmap() {
    const heatmapImg = document.getElementById('viewer-heatmap');
    const btnHeatmap = document.getElementById('btn-heatmap');
    if (heatmapImg && heatmapImg.src) {
        if (heatmapImg.style.display === 'none') {
            heatmapImg.style.display = 'block';
            if (btnHeatmap) {
                btnHeatmap.style.background = '#e57373'; // lighter active state
                btnHeatmap.textContent = '🔥 隠す';
            }
        } else {
            heatmapImg.style.display = 'none';
            if (btnHeatmap) {
                btnHeatmap.style.background = '#ef5350';
                btnHeatmap.textContent = '🔥 ヒートマップ';
            }
        }
    }
}

// キーボードイベント
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
    }
});
