/**
 * QC-Check 02 — レポートページ
 * 日別統計、合格率バー、最近のNG画像
 */

// ── 本日サマリーの更新 ──

async function loadTodaySummary() {
    try {
        const response = await fetch('/api/daily-stats?days=1');
        const data = await response.json();

        let todayOk = 0, todayNg = 0, todayUnlabeled = 0, todayTotal = 0;

        if (data.length > 0) {
            const today = data[0];
            todayOk = today.ok || 0;
            todayNg = today.ng || 0;
            todayUnlabeled = today.unlabeled || 0;
            todayTotal = today.total || 0;
        }

        document.getElementById('today-total').textContent = todayTotal;
        document.getElementById('today-ok').textContent = todayOk;
        document.getElementById('today-ng').textContent = todayNg;

        // 合格率
        const inspected = todayOk + todayNg;
        const rate = inspected > 0 ? ((todayOk / inspected) * 100).toFixed(1) + '%' : '—';
        document.getElementById('today-rate').textContent = rate;

        // 合格率バー
        updatePassRateBar(todayOk, todayNg);

    } catch (err) {
        console.error('Failed to load today summary:', err);
    }
}

// ── 合格率バー ──

function updatePassRateBar(ok, ng) {
    const total = ok + ng;
    const fill = document.getElementById('pass-rate-fill');
    const okCount = document.getElementById('rate-ok-count');
    const ngCount = document.getElementById('rate-ng-count');

    okCount.textContent = ok;
    ngCount.textContent = ng;

    if (total === 0) {
        fill.style.width = '0%';
        fill.style.background = 'var(--text-muted)';
        return;
    }

    const percentage = (ok / total) * 100;
    fill.style.width = `${percentage}%`;

    // 合格率に応じたカラー
    if (percentage >= 90) {
        fill.style.background = 'linear-gradient(90deg, #00e676, #69f0ae)';
    } else if (percentage >= 70) {
        fill.style.background = 'linear-gradient(90deg, #ffc107, #ffca28)';
    } else {
        fill.style.background = 'linear-gradient(90deg, #ff5252, #ff8a80)';
    }
}

// ── 最近のNG画像 ──

async function loadRecentNG() {
    const grid = document.getElementById('recent-ng-grid');

    try {
        const response = await fetch('/gallery?label=ng&n=8&offset=0');
        const data = await response.json();

        let images = Array.isArray(data) ? data : (data.images || []);

        if (images.length === 0) {
            grid.innerHTML = '<p class="no-ng-text">NG画像はありません 👍</p>';
            return;
        }

        grid.innerHTML = images.map(img => {
            const imgSrc = `/image?path=${encodeURIComponent(img.filepath)}`;
            return `
                <div class="ng-thumb">
                    <img src="${imgSrc}" alt="${img.filename}" loading="lazy">
                    <span class="ng-thumb-name">${img.filename}</span>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error('Failed to load recent NG:', err);
        grid.innerHTML = '<p class="no-ng-text">読み込みに失敗しました</p>';
    }
}

// ── 初期化 ──

document.addEventListener('DOMContentLoaded', () => {
    loadTodaySummary();
    loadRecentNG();
});
