const form = document.querySelector("#settings-form");
const saveState = document.querySelector("#save-state");
const resetButton = document.querySelector("#reset-button");
const submitButton = form.querySelector("button[type='submit']");
const intentInput = document.querySelector("#intent");
const instructionInput = document.querySelector("#response-instruction");
const temperatureInput = document.querySelector("#temperature");

const evidenceLabels = {
    strict: "Ketat",
    balanced: "Seimbang",
    exploratory: "Eksploratif",
};

function setState(text, kind = "neutral") {
    saveState.textContent = text;
    saveState.className = "rounded-md border px-4 py-2 text-sm font-semibold";
    if (kind === "success") {
        saveState.classList.add("border-sage/30", "bg-sage-soft", "text-sage-dark");
    } else if (kind === "error") {
        saveState.classList.add("border-danger/30", "bg-red-50", "text-danger");
    } else {
        saveState.classList.add("border-line", "bg-white", "text-muted");
    }
}

function formPayload() {
    const data = new FormData(form);
    return {
        provider: data.get("provider"),
        intent: String(data.get("intent") || "").trim(),
        response_instruction: String(data.get("response_instruction") || "").trim(),
        max_tokens: Number(data.get("max_tokens")),
        paragraph_count: Number(data.get("paragraph_count")),
        temperature: Number(data.get("temperature")),
        evidence_policy: data.get("evidence_policy"),
    };
}

function renderSettings(settings) {
    form.elements.provider.value = settings.provider;
    form.elements.intent.value = settings.intent;
    form.elements.response_instruction.value = settings.response_instruction;
    form.elements.max_tokens.value = settings.max_tokens;
    form.elements.paragraph_count.value = settings.paragraph_count;
    form.elements.temperature.value = settings.temperature;
    form.elements.evidence_policy.value = settings.evidence_policy;
    updatePreview();
}

function updatePreview() {
    const settings = formPayload();
    document.querySelector("#intent-count").textContent = `${settings.intent.length}/160`;
    document.querySelector("#instruction-count").textContent = `${settings.response_instruction.length}/2000`;
    document.querySelector("#temperature-value").value = settings.temperature.toFixed(1);
    document.querySelector("#summary-provider").textContent = settings.provider === "local" ? "Lokal (Ollama)" : "OpenRouter";
    document.querySelector("#summary-intent").textContent = settings.intent || "Belum diisi";
    document.querySelector("#summary-tokens").textContent = settings.max_tokens || "-";
    document.querySelector("#summary-paragraphs").textContent = settings.paragraph_count || "-";
    document.querySelector("#summary-evidence").textContent = evidenceLabels[settings.evidence_policy] || "-";
}

async function requestSettings(url, options) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = Array.isArray(data.detail)
            ? data.detail.map((item) => item.msg).join(", ")
            : data.detail;
        throw new Error(detail || `Permintaan gagal (HTTP ${response.status}).`);
    }
    return data;
}

async function loadSettings() {
    try {
        const settings = await requestSettings("/admin/model-settings");
        renderSettings(settings);
        setState("Konfigurasi tersimpan", "success");
    } catch (error) {
        setState(error.message, "error");
    }
}

form.addEventListener("input", () => {
    updatePreview();
    setState("Ada perubahan yang belum disimpan");
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
        return;
    }

    submitButton.disabled = true;
    setState("Menyimpan...");
    try {
        const settings = await requestSettings("/admin/model-settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formPayload()),
        });
        renderSettings(settings);
        setState("Konfigurasi berhasil disimpan", "success");
    } catch (error) {
        setState(error.message, "error");
    } finally {
        submitButton.disabled = false;
    }
});

resetButton.addEventListener("click", async () => {
    resetButton.disabled = true;
    setState("Mengembalikan konfigurasi...");
    try {
        const settings = await requestSettings("/admin/model-settings/reset", { method: "POST" });
        renderSettings(settings);
        setState("Konfigurasi default dipulihkan", "success");
    } catch (error) {
        setState(error.message, "error");
    } finally {
        resetButton.disabled = false;
    }
});

loadSettings();
