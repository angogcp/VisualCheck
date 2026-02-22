/**
 * QC-Check 02 — Model Management
 * Handles model selection, versioning, and training triggers.
 */

function openModelSettings() {
    const overlay = document.getElementById('model-settings-overlay');
    if (overlay) {
        overlay.classList.add('active');
        loadModelList();
    }
}

function closeModelSettings() {
    const overlay = document.getElementById('model-settings-overlay');
    if (overlay) overlay.classList.remove('active');
}

// Check for "M" key to open settings (shortcut)
document.addEventListener('keydown', (e) => {
    if (e.key === 'm' && !e.ctrlKey && !e.metaKey && document.body.style.overflow !== 'hidden') {
        openModelSettings();
    }
});

async function loadModelList() {
    try {
        const res = await fetch('/api/models');
        const models = await res.json();

        // Populate Select
        const select = document.getElementById('model-select');
        // Keep existing options but select the active one
        // Or rebuild options if needed. For now just set value.

        const activeModel = models.find(m => m.active);
        if (activeModel && select) {
            select.value = activeModel.type;
            loadVersionList(activeModel.type);
        }
    } catch (e) {
        console.error("Failed to load models", e);
    }
}

async function loadVersionList(modelType) {
    const listEl = document.getElementById('version-list');
    const badgeEl = document.getElementById('current-version-badge');

    if (!listEl) return;

    listEl.innerHTML = '<div style="text-align:center; color:var(--text-muted);">読み込み中...</div>';

    try {
        const res = await fetch(`/api/versions?model_type=${modelType}`);
        const data = await res.json();

        if (badgeEl) badgeEl.textContent = data.current || 'v0';

        if (!data.versions || data.versions.length === 0) {
            listEl.innerHTML = '<div style="text-align:center; color:var(--text-muted);">学習済みモデルがありません</div>';
            return;
        }

        listEl.innerHTML = data.versions.map(v => {
            const isCurrent = v.version === data.current;
            const dateStr = ''; // Timestamp not currently available in simple API

            return `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:8px; border-bottom:1px solid var(--border-glass); background:${isCurrent ? 'rgba(68, 138, 255, 0.05)' : 'transparent'};">
                    <div>
                        <span style="font-weight:bold; color:var(--text-primary);">${v.version}</span>
                        ${isCurrent ? '<span style="font-size:0.75rem; color:var(--accent-ok); margin-left:8px;">(現在)</span>' : ''}
                    </div>
                    ${!isCurrent ? `<button onclick="rollbackTo('${v.version}', '${modelType}')" style="background:transparent; border:1px solid var(--text-muted); color:var(--text-muted); padding:2px 8px; border-radius:4px; cursor:pointer; font-size:0.8rem;">戻す</button>` : ''}
                </div>
            `;
        }).join('');

    } catch (e) {
        console.error("Failed to load versions", e);
        listEl.innerHTML = '<div style="text-align:center; color:var(--accent-ng);">エラーが発生しました</div>';
    }
}

async function rollbackTo(version, modelType) {
    if (!confirm(`${modelType} を ${version} に戻しますか？`)) return;

    try {
        const res = await fetch('/api/rollback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version, model_type: modelType })
        });
        const data = await res.json();

        if (data.success) {
            if (window.showToast) window.showToast(`✓ ${version} に戻しました`, 'success');
            loadVersionList(modelType); // Refresh
        } else {
            alert(data.error || '失敗しました');
        }
    } catch (e) {
        alert('通信エラー');
    }
}

async function startTraining() {
    const select = document.getElementById('model-select');
    const modelType = select ? select.value : 'patchcore';

    if (!confirm(`${modelType} の学習を開始しますか？\n(時間がかかる場合があります)`)) return;

    try {
        const res = await fetch('/api/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_type: modelType })
        });
        const data = await res.json();

        if (data.status === 'started') {
            if (window.showToast) window.showToast('学習を開始しました (バックグラウンド)', 'info');
            closeModelSettings();
        } else {
            alert(data.message || '開始できませんでした');
        }
    } catch (e) {
        alert('通信エラー');
    }
}
