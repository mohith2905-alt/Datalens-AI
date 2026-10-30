/* InsightFlow v2 — script.js */

let currentData = null;
let chatOpen = false;
let rawRows = [];
let loaderTimer = null;
let messageCount = 0;

// ======== FILE HANDLING ========

function handleFileSelect() {
    const file = document.getElementById("csvFile").files[0];
    if (file) processFile(file);
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById("uploadZone").classList.remove("dragging");
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
}

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById("uploadZone").classList.add("dragging");
}

function handleDragLeave() {
    document.getElementById("uploadZone").classList.remove("dragging");
}

async function processFile(file) {
    const allowed = [".csv", ".xls", ".xlsx"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showToast("Unsupported file format. Use CSV or Excel.", "error");
        return;
    }

    showLoader();
    document.getElementById("welcome-screen").style.display = "none";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/upload", { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        currentData = data;
        rawRows = data.preview || [];

        updateLoaderStep(3);
        await sleep(300);

        document.getElementById("results-area").style.display = "block";

        // Update file badge
        const badge = document.getElementById("fileBadge");
        document.getElementById("fileNameDisplay").textContent = file.name;
        badge.style.display = "flex";

        // Update status
        const dot = document.getElementById("statusDot");
        dot.classList.add("online");
        document.getElementById("status-tag").textContent = "Data loaded";

        // Show clear button
        document.getElementById("clearBtn").style.display = "flex";

        renderSummary(data.summary);
        renderInsights(data.insights || []);
        renderTable(rawRows);
        renderViz(data.plots, data.summary);

        updateLoaderStep(4);
        await sleep(400);

        scrollToSection("summary-section");
        addBotMessage(`✅ Loaded **${file.name}** — ${data.summary.shape[0].toLocaleString()} rows, ${data.summary.shape[1]} columns. Ask me anything about it!`);

    } catch (err) {
        showToast("❌ " + err.message, "error");
        document.getElementById("welcome-screen").style.display = "flex";
        document.getElementById("results-area").style.display = "none";
    } finally {
        hideLoader();
        if (window.lucide) lucide.createIcons();
    }
}

function clearData() {
    currentData = null;
    rawRows = [];
    document.getElementById("results-area").style.display = "none";
    document.getElementById("welcome-screen").style.display = "flex";
    document.getElementById("fileBadge").style.display = "none";
    document.getElementById("clearBtn").style.display = "none";
    document.getElementById("statusDot").classList.remove("online");
    document.getElementById("status-tag").textContent = "Waiting for data";
    document.getElementById("csvFile").value = "";
    lucide.createIcons();
}

// ======== RENDER FUNCTIONS ========

function renderSummary(summary) {
    const view = document.getElementById("summaryView");
    const rows = summary.shape[0];
    const cols = summary.shape[1];
    const missing = summary.missing;
    const dupes = summary.duplicates || 0;

    const cards = [
        { value: rows.toLocaleString(), label: "Total Records", icon: "📊", color: "var(--primary)" },
        { value: cols, label: "Columns", icon: "🗂️", color: "var(--accent)" },
        { value: missing.toLocaleString(), label: "Missing Values", icon: "⚠️", color: missing > 0 ? "var(--warn)" : "var(--success)" },
        { value: dupes.toLocaleString(), label: "Duplicates", icon: "📋", color: dupes > 0 ? "var(--danger)" : "var(--success)" },
    ];

    view.innerHTML = cards.map(c => `
        <div class="stat-card" style="border-top-color: ${c.color}">
            <div class="stat-card-icon">${c.icon}</div>
            <h3>${c.value}</h3>
            <p>${c.label}</p>
        </div>
    `).join("");

    // Column chips
    const colRow = document.getElementById("colInfoRow");
    const numCols = summary.numeric_cols || [];
    const catCols = summary.categorical_cols || [];

    colRow.innerHTML = `
        <span class="col-chip" style="font-weight:700;">Columns:</span>
        ${numCols.map(c => `<span class="col-chip numeric">📈 ${c}</span>`).join("")}
        ${catCols.map(c => `<span class="col-chip categorical">🏷️ ${c}</span>`).join("")}
    `;

    document.getElementById("rowCountBadge").textContent = `${rows.toLocaleString()} rows`;
}

function renderInsights(insights) {
    const view = document.getElementById("insightsView");
    if (!insights || insights.length === 0) {
        view.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">No insights generated.</p>`;
        return;
    }

    view.innerHTML = insights.map((text, i) => {
        const isWarn = text.includes("⚠️") || text.includes("missing");
        const isSuccess = text.includes("✅");
        const cls = isWarn ? "warn" : isSuccess ? "success" : "";
        const style = `animation-delay: ${i * 0.1}s`;
        const formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        return `<div class="insight-card ${cls}" style="${style}">${formatted}</div>`;
    }).join("");
}

function renderTable(rows) {
    const tableDiv = document.getElementById("tableView");
    if (!rows || rows.length === 0) {
        tableDiv.innerHTML = `<div style="padding:24px;color:var(--text-muted);font-size:0.85rem;">No preview available.</div>`;
        return;
    }

    const headers = Object.keys(rows[0]);
    let html = `<table><thead><tr>${headers.map(h => `<th title="${h}">${h}</th>`).join("")}</tr></thead><tbody>`;

    rows.forEach(row => {
        html += `<tr>${headers.map(h => {
            const val = row[h];
            const isEmpty = val === "" || val === null || val === undefined;
            return `<td title="${val}" ${isEmpty ? 'style="color:var(--text-muted);font-style:italic"' : ""}>${isEmpty ? "—" : val}</td>`;
        }).join("")}</tr>`;
    });

    html += `</tbody></table>`;
    tableDiv.innerHTML = html;
}

function filterTable(query) {
    const rows = document.querySelectorAll("#tableView tbody tr");
    const q = query.toLowerCase();
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? "" : "none";
        row.classList.toggle("highlighted", q.length > 0 && text.includes(q));
    });
}

function renderViz(plots, summary) {
    const container = document.getElementById("vizView");
    container.innerHTML = "";

    if (!plots || plots.length === 0) {
        container.innerHTML = `<div class="card" style="padding:40px;text-align:center;color:var(--text-muted);font-size:0.9rem;">Not enough numeric data to generate visuals.</div>`;
        return;
    }

    const chartLabels = {
        "v1": { title: "Distribution", badge: "Histogram", color: "#7c6af7" },
        "v2": { title: "Correlation", badge: "Scatter", color: "#f472b6" },
        "v3": { title: "Breakdown", badge: "Donut", color: "#34d399" },
        "v4": { title: "Trends", badge: "Line", color: "#fb923c" },
        "v5": { title: "Comparison", badge: "Bar", color: "#60a5fa" },
        "v6": { title: "Spread", badge: "Box", color: "#a78bfa" },
    };

    plots.forEach((plot, i) => {
        const meta = chartLabels[plot.id] || { title: `Chart ${i + 1}`, badge: "Chart", color: "var(--primary)" };

        const wrapper = document.createElement("div");
        wrapper.className = "plot-card";
        wrapper.innerHTML = `
            <div class="plot-card-header">
                <span class="plot-card-title">${meta.title}</span>
                <span class="plot-card-badge" style="background:${meta.color}22;color:${meta.color};border:1px solid ${meta.color}44;">${meta.badge}</span>
            </div>
        `;

        const plotDiv = document.createElement("div");
        plotDiv.style.flex = "1";
        wrapper.appendChild(plotDiv);
        container.appendChild(wrapper);

        const plotData = JSON.parse(plot.json);
        const layout = {
            ...plotData.layout,
            autosize: true,
            height: 380,
            margin: { t: 20, b: 50, l: 50, r: 20 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { family: "DM Sans, sans-serif", size: 11, color: "rgba(255,255,255,0.5)" },
            xaxis: { ...(plotData.layout.xaxis || {}), gridcolor: "rgba(255,255,255,0.05)", zerolinecolor: "rgba(255,255,255,0.1)" },
            yaxis: { ...(plotData.layout.yaxis || {}), gridcolor: "rgba(255,255,255,0.05)", zerolinecolor: "rgba(255,255,255,0.1)" },
            showlegend: true,
            legend: { orientation: "h", y: -0.18, x: 0.5, xanchor: "center", font: { color: "rgba(255,255,255,0.5)", size: 11 }, bgcolor: "rgba(0,0,0,0)" },
        };

        Plotly.newPlot(plotDiv, plotData.data, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"],
            displaylogo: false,
        });
    });
}

// ======== CHAT ========

function toggleChat() {
    chatOpen = !chatOpen;
    const win = document.getElementById("chatWindow");
    win.classList.toggle("open", chatOpen);
    if (chatOpen) {
        document.getElementById("chatBadge").style.display = "none";
        document.getElementById("userQuery").focus();
    }
    lucide.createIcons();
}

function fillSuggestion(el) {
    document.getElementById("userQuery").value = el.textContent;
    document.getElementById("userQuery").focus();
}

function addBotMessage(text) {
    const box = document.getElementById("chatBox");
    const div = document.createElement("div");
    div.className = "msg bot";
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const formatted = text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\n/g, "<br>");
    div.innerHTML = `
        <div class="msg-avatar"><i data-lucide="bot"></i></div>
        <div class="msg-content"><p>${formatted}</p><span class="msg-time">${time}</span></div>
    `;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    lucide.createIcons();

    if (!chatOpen) {
        document.getElementById("chatBadge").style.display = "flex";
    }
}

function addTypingIndicator() {
    const box = document.getElementById("chatBox");
    const div = document.createElement("div");
    div.className = "msg bot typing";
    div.id = "typingIndicator";
    div.innerHTML = `
        <div class="msg-avatar"><i data-lucide="bot"></i></div>
        <div class="msg-content"><p></p></div>
    `;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    lucide.createIcons();
}

function removeTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
}

async function askBot() {
    const input = document.getElementById("userQuery");
    const query = input.value.trim();
    if (!query) return;

    const box = document.getElementById("chatBox");
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // User message
    const userDiv = document.createElement("div");
    userDiv.className = "msg user";
    userDiv.innerHTML = `
        <div class="msg-content">
            <p>${query}</p>
            <span class="msg-time">${time}</span>
        </div>
    `;
    box.appendChild(userDiv);
    input.value = "";
    box.scrollTop = box.scrollHeight;

    // Disable button
    const btn = document.getElementById("sendBtn");
    btn.disabled = true;

    // Typing indicator
    addTypingIndicator();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        removeTypingIndicator();
        addBotMessage(data.response || "No response received.");
    } catch (err) {
        removeTypingIndicator();
        addBotMessage("⚠️ Connection error. Please check the server.");
    } finally {
        btn.disabled = false;
    }
}

// ======== LOADER ========

function showLoader() {
    document.getElementById("loader").style.display = "flex";
    let step = 1;
    updateLoaderStep(1);
    loaderTimer = setInterval(() => {
        if (step < 3) { step++; updateLoaderStep(step); }
    }, 700);
}

function updateLoaderStep(n) {
    for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`step${i}`);
        if (!el) continue;
        if (i < n) { el.classList.add("done"); el.classList.remove("active"); }
        else if (i === n) { el.classList.add("active"); el.classList.remove("done"); }
        else { el.classList.remove("active", "done"); }
    }
}

function hideLoader() {
    clearInterval(loaderTimer);
    setTimeout(() => {
        document.getElementById("loader").style.display = "none";
    }, 500);
}

// ======== UTILITY ========

function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });

    // Update active nav
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.section === id);
    });

    // Breadcrumb
    const labels = {
        "summary-section": "Overview",
        "insights-section": "AI Insights",
        "table-section": "Data Table",
        "viz-section": "Visuals",
    };
    const bc = document.getElementById("breadcrumbSection");
    if (bc && labels[id]) bc.textContent = labels[id];
}

function handleSearch(val) {
    if (!val) return;
    const sections = ["summary-section", "insights-section", "table-section", "viz-section"];
    // Simple: filter table rows
    filterTable(val);
}

function downloadReport() {
    if (!currentData) {
        showToast("No data loaded yet.", "warn");
        return;
    }
    window.location.href = "/download-report";
}

function showToast(msg, type = "info") {
    const existing = document.getElementById("toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "toast";
    const colors = { error: "#f87171", warn: "#fbbf24", info: "#7c6af7", success: "#34d399" };
    toast.style.cssText = `
        position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
        background: rgba(12,12,20,0.95); border: 1px solid ${colors[type] || colors.info}44;
        color: ${colors[type] || colors.info}; border-radius: 10px; padding: 10px 20px;
        font-family: 'DM Sans', sans-serif; font-size: 0.82rem; font-weight: 500;
        z-index: 9999; backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        animation: fadeIn 0.3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function loadSampleData() {
    showToast("Loading sample dataset...", "info");
    // Create a sample CSV and trigger upload simulation
    const csv = `Name,Age,Department,Salary,Performance,Tenure
Alice,28,Engineering,85000,9.2,3
Bob,34,Marketing,72000,8.1,7
Carol,29,Engineering,91000,9.5,2
David,41,HR,65000,7.8,12
Eve,26,Engineering,88000,9.0,1
Frank,38,Marketing,78000,8.4,9
Grace,31,Finance,95000,9.3,5
Henry,45,HR,70000,7.5,15
Irene,27,Engineering,89000,9.1,2
Jack,36,Finance,102000,9.6,8
Karen,33,Marketing,76000,8.3,6
Liam,29,Engineering,87000,8.9,3`;

    const blob = new Blob([csv], { type: "text/csv" });
    const file = new File([blob], "sample_employees.csv", { type: "text/csv" });

    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById("csvFile").files = dt.files;
    processFile(file);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// Keyboard shortcut
document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        document.getElementById("globalSearch").focus();
    }
});