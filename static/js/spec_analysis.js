/**
 * QC-Check 02 — Design Spec Analysis
 * Handles spec capture, analysis request, and cost estimation display.
 */

// State
let currentComponents = [];

// Open Analysis Modal
async function openSpecAnalysis() {
    const overlay = document.getElementById('spec-analysis-overlay');
    if (overlay) {
        overlay.classList.add('active');
        // Reset state
        document.getElementById('spec-results').style.display = 'none';
        document.getElementById('spec-capture-preview').src = '';
        currentComponents = [];
    }
}

function closeSpecAnalysis() {
    const overlay = document.getElementById('spec-analysis-overlay');
    if (overlay) overlay.classList.remove('active');
}

// 1. Capture Spec Image (from main camera or file upload)
async function captureSpecImage() {
    const btn = document.getElementById('btn-capture-spec');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-mini"></span> 解析中...';
    }

    try {
        // Reuse main camera canvas if available
        const video = document.getElementById('live-preview');
        const canvas = document.createElement('canvas'); // temporary canvas
        if (video && video.readyState === 4) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const imageData = canvas.toDataURL('image/jpeg', 0.95);

            // Display preview
            const preview = document.getElementById('spec-capture-preview');
            if (preview) preview.src = imageData;

            // Send to Analyze API
            await analyzeSpec(imageData);
        } else {
            alert("カメラが準備できていません");
        }
    } catch (e) {
        console.error(e);
        alert("エラーが発生しました: " + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '📷 撮影・解析';
        }
    }
}

// 1.5 Handle File Upload
async function handleSpecFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Reset input so the same file can be selected again if needed
    event.target.value = '';

    const btnBtn = document.getElementById('spec-file-upload').nextElementSibling;
    if (btnBtn) {
        btnBtn.disabled = true;
        btnBtn.innerHTML = '<span class="spinner-mini"></span> 解析中...';
    }

    try {
        const reader = new FileReader();
        reader.onload = async (e) => {
            const imageData = e.target.result; // Base64 Data URL

            // Display preview
            const preview = document.getElementById('spec-capture-preview');
            if (preview) preview.src = imageData;

            // Send to Analyze API
            await analyzeSpec(imageData);

            if (btnBtn) {
                btnBtn.disabled = false;
                btnBtn.innerHTML = '📁 画像をアップロード';
            }
        };
        reader.onerror = () => {
            alert("ファイルの読み込みに失敗しました");
            if (btnBtn) {
                btnBtn.disabled = false;
                btnBtn.innerHTML = '📁 画像をアップロード';
            }
        }
        reader.readAsDataURL(file);
    } catch (e) {
        console.error(e);
        alert("エラーが発生しました: " + e.message);
        if (btnBtn) {
            btnBtn.disabled = false;
            btnBtn.innerHTML = '📁 画像をアップロード';
        }
    }
}

// 2. Analyze API Call
async function analyzeSpec(imageData) {
    try {
        const res = await fetch('/api/analyze-spec', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const data = await res.json();

        if (data.error) {
            alert("解析エラー: " + data.error);
            return;
        }

        if (data.warning) {
            // Show warning toast if mock data
            if (window.showToast) window.showToast("⚠️ " + data.warning, 'info');
        }

        currentComponents = data.components || [];
        renderComponents(currentComponents);
        document.getElementById('spec-results').style.display = 'block';

        // Auto-calculate cost
        calculateCost(currentComponents);

    } catch (e) {
        console.error(e);
        alert("通信エラー");
    }
}

// 3. Render Components List
function renderComponents(components) {
    const tbody = document.getElementById('spec-components-body');
    if (!tbody) return;

    tbody.innerHTML = components.map((c, i) => `
        <tr>
            <td>
                <input type="text" value="${c.part_number || ''}" placeholder="P/N" class="spec-input" style="width:100px; color:var(--text-accent);" onchange="updateComponent(${i}, 'part_number', this.value)">
            </td>
            <td>
                <input type="text" value="${c.name || ''}" class="spec-input" onchange="updateComponent(${i}, 'name', this.value)">
            </td>
            <td>
                <input type="text" value="${c.details || ''}" class="spec-input" onchange="updateComponent(${i}, 'details', this.value)">
            </td>
            <td>
                <input type="number" value="${c.count}" class="spec-input" style="width:60px;" onchange="updateComponent(${i}, 'count', this.value)">
            </td>
        </tr>
    `).join('');
}

function updateComponent(index, field, value) {
    if (currentComponents[index]) {
        currentComponents[index][field] = value;
        // Recalculate cost
        calculateCost(currentComponents);
    }
}

// 4. Estimate Cost API Call
async function calculateCost(components) {
    try {
        const res = await fetch('/api/estimate-cost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ components })
        });
        const data = await res.json();

        if (data.error) {
            alert("試算エラー: " + data.error);
            return;
        }

        const totalEl = document.getElementById('spec-total-cost');
        if (totalEl) {
            totalEl.textContent = `${data.currency} ${data.total_cost}`;
        }

    } catch (e) {
        console.error(e);
    }
}
