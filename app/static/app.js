const form = document.querySelector("#search-form");
const results = document.querySelector("#results");
const message = document.querySelector("#message");
const resultCount = document.querySelector("#result-count");
const answerSection = document.querySelector("#answer-section");
const answer = document.querySelector("#answer");
const answerMeta = document.querySelector("#answer-meta");
const searchTerms = document.querySelector("#search-terms");
const providerNote = document.querySelector("#provider-note");

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

form.addEventListener("change", (event) => {
    if (event.target.name !== "provider") {
        return;
    }
    providerNote.textContent = event.target.value === "local"
        ? "Model berjalan melalui Ollama di perangkat ini."
        : "Model cloud melalui OpenRouter.";
});

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
        provider: form.elements.provider.value,
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
    setMessage("", false);

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

        resultCount.textContent = `${papers.length} paper ditemukan`;
        results.replaceChildren(...papers.map(renderPaper));

        if (papers.length) {
            renderAnswer(data.paragraphs || []);
            const language = { id: "Bahasa Indonesia", en: "English" }[data.answer_language]
                || data.answer_language;
            const provider = data.provider === "local" ? "Lokal" : "OpenRouter";
            answerMeta.textContent = `${language} | ${provider} | ${data.model}`;
            const extraQuery = (data.search_queries || []).slice(1).join("; ");
            searchTerms.textContent = extraQuery ? `Istilah pencarian tambahan: ${extraQuery}` : "";
            answerSection.hidden = false;
        } else {
            setMessage("Belum ada paper yang cocok. Coba pertanyaan lebih luas atau ubah batas tahun.");
        }
    } catch (error) {
        resultCount.textContent = "Permintaan gagal";
        setMessage(error.message);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Tanya";
    }
});
