document.addEventListener("DOMContentLoaded", () => {
    const byId = id => document.getElementById(id);
    const form = byId("upload-form"), input = byId("pdf-input"), dropZone = byId("drop-zone");
    const filePanel = byId("file-panel"), fileList = byId("selected-files-list"), processButton = byId("process-btn");
    const processingPanel = byId("processing-panel"), errorPanel = byId("error-panel"), results = byId("results-container");
    const picker = byId("document-picker"), pickerWrap = byId("document-picker-wrap");
    let selectedFiles = [], documents = [], activeDoc = null, elapsedTimer = null, startedAt = 0;

    const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
    const humanize = value => String(value ?? "").replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim().replace(/^./, c => c.toUpperCase());
    const isEmpty = value => value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
    const formatValue = value => {
        if (isEmpty(value)) return "";
        if (typeof value === "boolean") return value ? "Yes" : "No";
        if (typeof value === "object") return Array.isArray(value) ? value.map(formatValue).filter(Boolean).join(", ") : "";
        return String(value);
    };
    const fileSize = size => size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;
    const fileType = file => (file.name.split(".").pop() || "FILE").toUpperCase();

    byId("choose-files").addEventListener("click", () => input.click());
    dropZone.addEventListener("click", event => { if (!event.target.closest("button")) input.click(); });
    dropZone.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); input.click(); } });
    input.addEventListener("change", () => addFiles(Array.from(input.files || [])));
    byId("clear-files").addEventListener("click", clearFiles);
    picker.addEventListener("change", () => showDocument(Number(picker.value)));
    byId("close-json").addEventListener("click", () => byId("json-display-wrapper").classList.add("hidden"));
    document.querySelectorAll("[data-json]").forEach(button => button.addEventListener("click", () => showJson(button.dataset.json)));
    byId("download-json-btn").addEventListener("click", downloadJson);

    function addFiles(files) {
        const allowed = /\.(pdf|png|jpe?g)$/i;
        selectedFiles.push(...files.filter(file => allowed.test(file.name)));
        const transfer = new DataTransfer();
        selectedFiles.forEach(file => transfer.items.add(file));
        input.files = transfer.files;
        renderFiles();
    }
    function clearFiles() {
        selectedFiles = [];
        input.value = "";
        filePanel.classList.add("hidden");
        byId("group-images-row").classList.add("hidden");
        dropZone.classList.remove("compact");
    }
    function renderFiles() {
        if (!selectedFiles.length) { clearFiles(); return; }
        filePanel.classList.remove("hidden");
        dropZone.classList.add("compact");
        byId("file-count").textContent = `${selectedFiles.length} ${selectedFiles.length === 1 ? "file" : "files"}`;
        const imagesCount = selectedFiles.filter(file => /\.(png|jpe?g)$/i.test(file.name)).length;
        byId("group-images-row").classList.toggle("hidden", imagesCount < 2);
        fileList.innerHTML = selectedFiles.map((file, index) => `
            <li class="file-row" data-index="${index}">
                <span class="file-type-mark">${escapeHtml(fileType(file))}</span>
                <span class="file-details"><strong title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</strong><small>${escapeHtml(fileType(file))} · ${fileSize(file.size)}</small></span>
                <span class="file-order-controls"><button type="button" class="icon-button" data-move="${index}" data-by="-1" aria-label="Move ${escapeHtml(file.name)} up" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" class="icon-button" data-move="${index}" data-by="1" aria-label="Move ${escapeHtml(file.name)} down" ${index === selectedFiles.length - 1 ? "disabled" : ""}>↓</button></span>
                <button type="button" class="icon-button remove-file" data-remove="${index}" aria-label="Remove ${escapeHtml(file.name)}">×</button>
            </li>`).join("");
    }
    fileList.addEventListener("click", event => {
        const remove = event.target.closest("[data-remove]");
        if (remove) { selectedFiles.splice(Number(remove.dataset.remove), 1); syncInput(); renderFiles(); return; }
        const move = event.target.closest("[data-move]");
        if (!move) return;
        const from = Number(move.dataset.move), to = from + Number(move.dataset.by);
        if (to < 0 || to >= selectedFiles.length) return;
        [selectedFiles[from], selectedFiles[to]] = [selectedFiles[to], selectedFiles[from]];
        syncInput(); renderFiles();
    });
    function syncInput() { const transfer = new DataTransfer(); selectedFiles.forEach(file => transfer.items.add(file)); input.files = transfer.files; }
    ["dragenter", "dragover"].forEach(name => dropZone.addEventListener(name, event => { event.preventDefault(); dropZone.classList.add("drag-over"); }));
    ["dragleave", "drop"].forEach(name => dropZone.addEventListener(name, event => { event.preventDefault(); dropZone.classList.remove("drag-over"); }));
    dropZone.addEventListener("drop", event => addFiles(Array.from(event.dataTransfer?.files || [])));

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!selectedFiles.length) return;
        setBusy(true);
        errorPanel.classList.add("hidden"); results.classList.add("hidden");
        processingPanel.classList.remove("hidden");
        byId("processing-title").textContent = "Processing your document";
        byId("processing-message").textContent = "URJA is working locally. The current API reports results when processing finishes.";
        startedAt = Date.now();
        updateElapsed();
        elapsedTimer = window.setInterval(updateElapsed, 1000);
        const payload = new FormData();
        selectedFiles.forEach(file => payload.append("files", file, file.name));
        payload.append("group_images", String(byId("group-images").checked));
        payload.append("force_ocr", String(byId("force-ocr")?.checked || false));
        try {
            const response = await fetch("/api/ingest", { method: "POST", body: payload });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || `Request failed (${response.status})`));
            documents = data.documents || [data];
            picker.innerHTML = documents.map((doc, index) => `<option value="${index}">${escapeHtml(doc.document?.document?.filename || doc.document_id || `Document ${index + 1}`)} · ${escapeHtml(doc.status || "unknown")}</option>`).join("");
            pickerWrap.classList.toggle("hidden", documents.length < 2);
            showDocument(0);
            results.classList.remove("hidden");
            processingPanel.classList.add("hidden");
            results.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
            processingPanel.classList.add("hidden");
            renderError(error);
        } finally {
            if (elapsedTimer) window.clearInterval(elapsedTimer);
            setBusy(false);
        }
    });
    function setBusy(busy) {
        processButton.disabled = busy;
        processButton.querySelector("span:first-child").textContent = busy ? "Processing…" : "Process document";
        processingPanel.setAttribute("aria-busy", String(busy));
    }
    function updateElapsed() { byId("processing-elapsed").textContent = `Elapsed ${Math.floor((Date.now() - startedAt) / 1000)}s`; }
    function renderError(error) {
        errorPanel.classList.remove("hidden");
        errorPanel.innerHTML = `<strong>Processing failed</strong><p>${escapeHtml(error.message || "The server could not process this upload.")}</p><div class="error-actions"><button type="button" id="retry-button" class="secondary-button">Try again</button><button type="button" id="back-button" class="quiet-button">Back to upload</button></div>`;
        byId("retry-button").addEventListener("click", () => form.requestSubmit());
        byId("back-button").addEventListener("click", () => { errorPanel.classList.add("hidden"); byId("upload-heading").scrollIntoView({ behavior: "smooth" }); });
    }

    function showDocument(index) {
        const data = documents[index];
        if (!data) return;
        activeDoc = data;
        renderResult(data);
    }
    function renderResult(data) {
        const normalized = data.document || {}, doc = normalized.document || {}, semantic = data.semantic || {};
        const raw = data.raw_ocr || {}, pages = raw.pages || [];
        const failedPages = pages.filter(page => page.status === "failed").length;
        const status = data.status || raw.status || "unknown";
        byId("result-heading").textContent = status === "completed" ? "Processing complete" : status === "completed_with_errors" ? "Completed with warnings" : status === "failed" ? "Processing failed" : "Processing finished";
        byId("result-status").textContent = humanize(status);
        byId("result-status").className = `result-pill ${status === "failed" ? "is-error" : status === "completed_with_errors" ? "is-warning" : "is-success"}`;
        byId("result-filename").textContent = doc.filename || (raw.sources || []).map(source => source.filename).join(", ") || "Uploaded document";
        const timingText = data.timing?.total_ms 
            ? `⚡ ${data.timing.total_ms < 1000 ? Math.round(data.timing.total_ms) + "ms" : (data.timing.total_ms / 1000).toFixed(2) + "s"} (${raw.ocr_engine || "OCR"})` 
            : "";
        byId("result-meta").textContent = [
            humanize(doc.document_type || "unknown document"), 
            `${doc.page_count ?? pages.length ?? 0} ${(doc.page_count ?? pages.length) === 1 ? "page" : "pages"}`, 
            `${Math.round((doc.document_type_confidence || 0) * 100)}% type confidence`,
            timingText
        ].filter(Boolean).join(" · ");
        const warning = byId("partial-warning");
        if (failedPages || status === "completed_with_errors") {
            const succeeded = pages.length - failedPages;
            warning.textContent = `${humanize(status)}${pages.length ? ` · ${succeeded} of ${pages.length} pages processed` : ""}${failedPages ? ` · ${failedPages} page${failedPages === 1 ? "" : "s"} reported an OCR error` : ""}`;
            warning.classList.remove("hidden");
        } else warning.classList.add("hidden");
        const resultError = byId("result-error");
        if (status === "failed") {
            resultError.innerHTML = `<strong>Processing failed</strong><p>${escapeHtml(data.error || "The server marked this document as failed.")}</p><div class="error-actions"><button type="button" id="result-retry" class="secondary-button">Try again</button><button type="button" id="result-back" class="quiet-button">Back to upload</button></div>`;
            resultError.classList.remove("hidden");
            byId("result-retry").addEventListener("click", () => form.requestSubmit());
            byId("result-back").addEventListener("click", () => { results.classList.add("hidden"); byId("upload-heading").scrollIntoView({ behavior: "smooth" }); });
        } else resultError.classList.add("hidden");

        const semanticGroups = flattenSemantic(semantic);
        const allFields = semanticGroups.flatMap(group => group.items);
        const important = allFields.filter(item => item.value && !/evidence|confidence|candidates|status|domain/i.test(item.key));
        renderInfoGrid("important-grid", important.slice(0, 8));
        byId("important-section").classList.toggle("hidden", !important.length);
        const domainItems = allFields.filter(item => !important.slice(0, 8).includes(item));
        renderInfoGrid("domain-grid", domainItems);
        byId("domain-heading").textContent = humanize(semantic.domain || doc.document_type || "Document information");
        byId("domain-section").classList.toggle("hidden", !domainItems.length);

        renderTables(normalized.tables || []);
        renderValidation(data.validation || {});
        renderOther(normalized, semantic, data.error);
    }
    function flattenSemantic(semantic) {
        const groups = [];
        function walk(value, path) {
            if (Array.isArray(value)) {
                if (value.length && value.every(item => item && typeof item === "object")) {
                    value.forEach((item, index) => walk(item, [...path, String(index + 1)]));
                } else if (value.length) add(path, value.map(formatValue).filter(Boolean).join(", "));
                return;
            }
            if (!value || typeof value !== "object") { if (!isEmpty(value)) add(path, formatValue(value)); return; }
            Object.entries(value).forEach(([key, item]) => {
                if (["evidence", "candidates"].includes(key)) return;
                walk(item, [...path, key]);
            });
        }
        function add(path, value) {
            if (!value) return;
            const groupName = path.length > 1 ? humanize(path[0]) : "Document";
            let group = groups.find(item => item.name === groupName);
            if (!group) { group = { name: groupName, items: [] }; groups.push(group); }
            group.items.push({ key: path.slice(1).map(humanize).filter(part => !/^\d+$/.test(part)).join(" · ") || humanize(path[0]), value, path: path.join(".") });
        }
        walk(semantic, []);
        return groups;
    }
    function renderInfoGrid(id, items) {
        const container = byId(id);
        container.innerHTML = items.map(item => `<button type="button" class="info-item" data-field-path="${escapeHtml(item.path)}"><span>${escapeHtml(item.key)}</span><strong>${escapeHtml(item.value)}</strong></button>`).join("");
        container.querySelectorAll("[data-field-path]").forEach(button => button.addEventListener("click", () => showEvidence(button.dataset.fieldPath)));
    }
    function renderTables(tables) {
        const container = byId("generic-tables-container");
        byId("table-count").textContent = tables.length;
        byId("tables-section").classList.toggle("hidden", !tables.length);
        container.innerHTML = tables.map((table, index) => {
            const columns = table.columns || [], rows = table.rows || [];
            const headers = columns.length ? `<thead><tr>${columns.map(column => `<th>${escapeHtml(formatValue(column))}</th>`).join("")}</tr></thead>` : "";
            const body = rows.map(row => `<tr>${(Array.isArray(row) ? row : [row]).map(cell => `<td>${escapeHtml(formatValue(cell))}</td>`).join("")}</tr>`).join("");
            const metadata = [table.page ? `Page ${table.page}` : "", table.confidence != null ? `${Math.round(table.confidence * 100)}% confidence` : ""].filter(Boolean).join(" · ");
            return `<details class="table-disclosure"><summary><span>${escapeHtml(table.title || `Table ${index + 1}`)}</span><small>${escapeHtml(metadata)}</small></summary><div class="table-scroll"><table class="generic-doc-table">${headers}<tbody>${body || `<tr><td>No rows reported.</td></tr>`}</tbody></table></div></details>`;
        }).join("");
    }
    function renderValidation(validation) {
        const checks = validation.checks || [], section = byId("validation-section");
        section.classList.toggle("hidden", !checks.length && !validation.status);
        byId("validation-summary").textContent = validation.status ? humanize(validation.status) : "";
        byId("validation-checks-container").innerHTML = checks.map(check => {
            const state = String(check.status || "unknown").toLowerCase();
            const detail = check.details ? `<details class="check-details"><summary>Details</summary><pre>${escapeHtml(JSON.stringify(check.details, null, 2))}</pre></details>` : "";
            return `<article class="validation-item ${escapeHtml(state)}"><span class="validation-icon" aria-hidden="true">${state === "passed" ? "✓" : state === "warning" ? "!" : state === "conflict" || state === "failed" ? "×" : "·"}</span><div><strong>${escapeHtml(humanize(check.name || "Check"))}</strong><p>${escapeHtml(check.message || "")}</p>${detail}</div><span class="validation-state">${escapeHtml(humanize(state))}</span></article>`;
        }).join("");
    }
    function renderOther(normalized, semantic, processingError) {
        const sections = normalized.sections || [], fields = normalized.fields || [], visuals = normalized.visual_elements || [];
        const doc = normalized.document || {};
        const additional = [doc.additional_fields, doc.additional_sections, doc.additional_elements].filter(value => value && (Array.isArray(value) ? value.length : Object.keys(value).length));
        const hasOther = sections.length || fields.length || visuals.length || additional.length || processingError;
        byId("other-section").classList.toggle("hidden", !hasOther);
        byId("other-count").textContent = `${sections.length + fields.length + visuals.length + additional.length}`;
        byId("generic-sections-container").innerHTML = sections.length ? `<h4>Detected sections</h4>${sections.map(section => `<details class="other-disclosure"><summary>${escapeHtml(section.title || "Section")} <small>${escapeHtml([section.page && `Page ${section.page}`, section.type].filter(Boolean).join(" · "))}</small></summary><pre>${escapeHtml(section.content || "")}</pre></details>`).join("")}` : "";
        byId("generic-fields-container").innerHTML = fields.length ? `<h4>Additional fields</h4><div class="table-scroll"><table class="generic-doc-table"><thead><tr><th>Field</th><th>Value</th><th>Page</th></tr></thead><tbody>${fields.map(field => `<tr><td>${escapeHtml(field.label || field.field_id || "Field")}</td><td>${escapeHtml(formatValue(field.value))}</td><td>${escapeHtml(field.page || "")}</td></tr>`).join("")}</tbody></table></div>` : "";
        byId("generic-visuals-container").innerHTML = visuals.length ? `<h4>Detected elements</h4>${visuals.map(visual => `<details class="other-disclosure"><summary>${escapeHtml(humanize(visual.type || "Element"))} <small>Page ${escapeHtml(visual.page || "—")}</small></summary><pre>${escapeHtml(JSON.stringify(visual, null, 2))}</pre></details>`).join("")}` : "";
        byId("additional-data-container").innerHTML = `${processingError ? `<div class="error-inline"><strong>Processing error</strong><p>${escapeHtml(processingError)}</p></div>` : ""}${additional.map((value, index) => `<details class="other-disclosure"><summary>${escapeHtml(["Additional fields", "Additional sections", "Additional elements"][index])}</summary><pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre></details>`).join("")}`;
    }

    function findEvidence(path) {
        const list = activeDoc?.semantic?.evidence || [];
        const leaf = path.split(".").pop();
        return list.filter(item => item.field === path || item.field?.split(".").pop() === leaf);
    }
    function showEvidence(path) {
        const matches = findEvidence(path), backdrop = byId("popover-backdrop"), popover = byId("evidence-popover");
        byId("evidence-title").textContent = humanize(path.split(".").slice(-1)[0]);
        byId("evidence-content").innerHTML = matches.length ? matches.map(item => `<dl class="evidence-list">${[
            ["Source", item.page ? `Page ${item.page}` : "Not reported"], ["Table", item.source_table || item.table || "Not reported"], ["OCR text", item.source_text || item.text || "Not reported"], ["Confidence", item.confidence == null ? "Not reported" : `${Math.round(item.confidence * 100)}%`], ["Value", formatValue(item.value)]
        ].map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>`).join("") : `<p class="subtle-label">The API did not return source evidence for this field.</p>`;
        backdrop.classList.remove("hidden"); popover.classList.remove("hidden");
    }
    function closeEvidence() { byId("evidence-popover").classList.add("hidden"); byId("popover-backdrop").classList.add("hidden"); }
    byId("close-evidence").addEventListener("click", closeEvidence);
    byId("popover-backdrop").addEventListener("click", closeEvidence);
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeEvidence(); });

    function showJson(which) {
        if (!activeDoc) return;
        const data = which === "raw" ? activeDoc.raw_ocr : which === "normalized" ? activeDoc.document : activeDoc.semantic;
        byId("json-title").textContent = ({ raw: "Raw IndicOCR JSON", normalized: "Normalized document JSON", semantic: "Semantic JSON" })[which];
        byId("json-code-block").textContent = JSON.stringify(data ?? {}, null, 2);
        byId("json-display-wrapper").classList.remove("hidden");
        byId("json-display-wrapper").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    function downloadJson() {
        if (!activeDoc) return;
        const url = URL.createObjectURL(new Blob([JSON.stringify({ raw_ocr: activeDoc.raw_ocr, normalized_document: activeDoc.document, semantic: activeDoc.semantic, validation: activeDoc.validation }, null, 2)], { type: "application/json" }));
        const link = document.createElement("a");
        link.href = url; link.download = `${activeDoc.document_id || "urja-document"}.json`; link.click();
        URL.revokeObjectURL(url);
    }
});
