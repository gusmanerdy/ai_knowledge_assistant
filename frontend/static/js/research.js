const form = document.querySelector("#search-form");
const results = document.querySelector("#results");
const message = document.querySelector("#message");
const resultCount = document.querySelector("#result-count");
const answerSection = document.querySelector("#answer-section");
const answer = document.querySelector("#answer");
const answerMeta = document.querySelector("#answer-meta");
const searchTerms = document.querySelector("#search-terms");
const modelProfile = document.querySelector("#model-profile");
const modelStatus = document.querySelector("#model-status");
const modelLatency = document.querySelector("#model-latency");
const modelEvidence = document.querySelector("#model-evidence");

let activeProvider = "openrouter";

function applyClasses(element, classes) {
    element.className = classes;
    return element;
}

function setMessage(text, isVisible = true) {
    message.textContent = text;
    message.hidden = !isVisible;
}

function textOrFallback(value, fallback) {
    return value && String(value).trim() ? value : fallback;
}

function externalUrl(value) {
    try {
        const url = new URL(value);
        return ["http:", "https:"].includes(url.protocol) ? url.href : null;
    } catch {
        return null;
    }
}

function renderPaper(paper, index) {
    const article = document.createElement("article");
    article.id = `paper-${index + 1}`;
    applyClasses(
        article,
        "grid scroll-mt-5 grid-cols-[minmax(0,1fr)_auto] gap-5 rounded-lg border border-line bg-white p-5 max-sm:grid-cols-1",
    );

    const body = document.createElement("div");

    const title = document.createElement("h3");
    applyClasses(title, "mb-2 text-lg font-bold leading-snug");
    const url = externalUrl(paper.url);
    if (url) {
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = textOrFallback(paper.title, "Paper tanpa judul");
        applyClasses(link, "underline decoration-sage/35 underline-offset-4 hover:text-sage-dark");
        title.appendChild(link);
    } else {
        title.textContent = textOrFallback(paper.title, "Paper tanpa judul");
    }

    const meta = document.createElement("div");
    applyClasses(meta, "mb-3 flex flex-wrap gap-2 text-sm text-muted");
    const authors = Array.isArray(paper.authors) && paper.authors.length
        ? paper.authors.slice(0, 4).join(", ")
        : "Penulis tidak tersedia";
    meta.textContent = [
        paper.year || "Tahun tidak tersedia",
        authors,
        paper.citation_count ? `${paper.citation_count} sitasi` : null,
        paper.doi ? `DOI ${paper.doi}` : null,
    ].filter(Boolean).join(" | ");

    const summary = document.createElement("p");
    applyClasses(summary, "text-[15px] leading-7 text-neutral-700");
    summary.textContent = textOrFallback(paper.summary, "Abstrak tidak tersedia.");

    const source = document.createElement("div");
    applyClasses(
        source,
        "h-fit min-w-28 rounded-md bg-sage-soft px-3 py-2 text-center text-xs font-bold text-sage-dark max-sm:w-fit",
    );
    source.textContent = `[${index + 1}] ${textOrFallback(paper.source, "sumber")}`;

    body.append(title, meta, summary);
    article.append(body, source);
    return article;
}

function renderAnswer(paragraphs) {
    const items = paragraphs.map((paragraph) => {
        const item = document.createElement("p");
        item.textContent = paragraph.text;
        paragraph.citations.forEach((citation) => {
            const link = document.createElement("a");
            link.href = `#paper-${citation}`;
            link.textContent = `[${citation}]`;
            link.setAttribute("aria-label", `Lihat paper ${citation}`);
            applyClasses(link, "ml-1 whitespace-nowrap font-bold text-sage underline underline-offset-2 hover:text-sage-dark");
            item.appendChild(link);
        });
        return item;
    });
    answer.replaceChildren(...items);
}

function selectedSources() {
    return Array.from(document.querySelectorAll("input[name='sources']:checked"))
        .map((input) => input.value);
}

function setDashboard({ status, latency, evidence } = {}) {
    if (status) {
        modelStatus.textContent = status;
    }
    if (latency) {
        modelLatency.textContent = latency;
    }
    if (evidence) {
        modelEvidence.textContent = evidence;
    }
}

async function loadModelProfile() {
    try {
        const response = await fetch("/model-profile");
        if (!response.ok) {
            throw new Error();
        }
        const settings = await response.json();
        activeProvider = settings.provider;
        const provider = settings.provider === "local" ? "Lokal" : "OpenRouter";
        modelProfile.textContent = `${provider} | ${settings.intent} | ${settings.max_tokens} token`;
    } catch {
        modelProfile.textContent = "Konfigurasi model tidak dapat dimuat";
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const submitButton = form.querySelector("button[type='submit']");
    const sources = selectedSources();
    if (!sources.length) {
        setMessage("Pilih setidaknya satu sumber paper.");
        return;
    }
    const payload = {
        query: document.querySelector("#query").value.trim(),
        limit: Number(document.querySelector("#limit").value || 8),
        sources,
    };

    const yearFrom = document.querySelector("#year-from").value;
    if (yearFrom) {
        payload.year_from = Number(yearFrom);
    }

    submitButton.disabled = true;
    submitButton.textContent = "Memproses...";
    answerSection.hidden = true;
    answer.replaceChildren();
    results.replaceChildren();
    resultCount.textContent = "Mencari paper dan menyusun jawaban...";
    setDashboard({ status: "Memproses", latency: "0 detik", evidence: "Mengumpulkan" });
    setMessage("", false);
    const startedAt = Date.now();
    const progressTimer = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - startedAt) / 1000);
        modelLatency.textContent = `${elapsed} detik`;
        resultCount.textContent = activeProvider === "local"
            ? `Model lokal sedang menyusun jawaban... ${elapsed} detik`
            : `Mencari paper dan menyusun jawaban... ${elapsed} detik`;
    }, 1000);

    try {
        const response = await fetch("/research/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Permintaan gagal (HTTP ${response.status}).`);
        }

        const data = await response.json();
        const papers = Array.isArray(data.papers) ? data.papers : [];
        const elapsed = Math.max(1, Math.round((Date.now() - startedAt) / 1000));

        resultCount.textContent = `${papers.length} paper ditemukan`;
        results.replaceChildren(...papers.map(renderPaper));

        if (papers.length) {
            renderAnswer(data.paragraphs || []);
            const language = { id: "Bahasa Indonesia", en: "English" }[data.answer_language]
                || data.answer_language;
            const provider = data.provider === "local" ? "Lokal" : "OpenRouter";
            const intent = data.model_settings?.intent || "Riset berbasis bukti";
            answerMeta.textContent = `${language} | ${provider} | ${data.model} | ${intent}`;
            const diagnostics = data.diagnostics || {};
            const cited = Number(diagnostics.cited_papers || 0);
            const abstracts = Number(diagnostics.papers_with_abstract || 0);
            setDashboard({
                status: "Selesai",
                latency: `${elapsed} detik`,
                evidence: `${cited}/${papers.length} paper dikutip, ${abstracts} abstrak`,
            });
            const extraQuery = (data.search_queries || []).slice(1).join("; ");
            searchTerms.textContent = extraQuery ? `Istilah pencarian tambahan: ${extraQuery}` : "";
            answerSection.hidden = false;
        } else {
            setDashboard({ status: "Tidak ada hasil", latency: `${elapsed} detik`, evidence: "0 paper" });
            setMessage("Belum ada paper yang cocok. Coba pertanyaan lebih luas atau ubah batas tahun.");
        }
    } catch (error) {
        resultCount.textContent = "Permintaan gagal";
        setDashboard({ status: "Gagal", evidence: "Periksa pesan" });
        setMessage(error.message);
    } finally {
        window.clearInterval(progressTimer);
        submitButton.disabled = false;
        submitButton.textContent = "Tanya";
    }
});

loadModelProfile();
