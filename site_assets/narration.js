// Each narration iframe contains one player; speed changes stay local to it.
const audio = document.querySelector("audio");
const speedButtons = document.querySelectorAll("button[data-speed]");

if (audio) {
    const showSelectedSpeed = () => {
        for (const button of speedButtons) {
            const selected = Number(button.dataset.speed) === audio.playbackRate;
            button.setAttribute("aria-pressed", String(selected));
        }
    };

    for (const button of speedButtons) {
        button.addEventListener("click", () => {
            audio.playbackRate = Number(button.dataset.speed);
        });
    }

    audio.addEventListener("ratechange", showSelectedSpeed);
    showSelectedSpeed();
}

// Keep the visible transport small; verbose progress is announced only on errors.
const playButton = document.querySelector(".toggle-play");
const progress = document.querySelector(".audio-progress");
const timeLabel = document.querySelector(".audio-time");
const settingsButton = document.querySelector(".toggle-settings");
const settings = document.querySelector(".narration-options");

settingsButton?.addEventListener("click", () => {
    settings.hidden = !settings.hidden;
    settingsButton.setAttribute("aria-expanded", String(!settings.hidden));
});
document.addEventListener("keydown", event => {
    if (event.key === "Escape" && settings && !settings.hidden) {
        settings.hidden = true;
        settingsButton.setAttribute("aria-expanded", "false");
        settingsButton.focus();
    }
});

function formatTime(seconds) {
    if (!Number.isFinite(seconds)) return "0:00";
    return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

if (audio && playButton) {
    const updateTransport = () => {
        const paused = audio.paused;
        const label = paused ? "Play narration" : "Pause narration";
        playButton.setAttribute("aria-label", label);
        playButton.title = label;
        playButton.querySelector("path").setAttribute("d", paused
            ? "M8 5v14l11-7z" : "M8 5v14M16 5v14");
        const hasDuration = Number.isFinite(audio.duration) && audio.duration > 0;
        progress.disabled = !hasDuration;
        progress.value = hasDuration ? 100 * audio.currentTime / audio.duration : 0;
        progress.setAttribute("aria-valuetext",
            `${formatTime(audio.currentTime)} of ${formatTime(audio.duration)}`);
        timeLabel.textContent = hasDuration
            ? `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}` : "0:00";
    };
    const showError = () => {
        const status = document.querySelector(".guidance-status");
        status.classList.remove("visually-hidden");
        status.textContent = "Audio could not play. Try again or download the transcript from audio settings.";
    };
    playButton.addEventListener("click", async () => {
        if (!audio.paused) { audio.pause(); return; }
        try { await audio.play(); } catch { showError(); }
    });
    progress.addEventListener("input", () => {
        if (Number.isFinite(audio.duration)) {
            audio.currentTime = Number(progress.value) * audio.duration / 100;
        }
    });
    for (const event of ["loadedmetadata", "durationchange", "timeupdate", "play", "pause", "ended"]) {
        audio.addEventListener(event, updateTransport);
    }
    audio.addEventListener("error", showError);
    updateTransport();
}

// Fit the iframe to its controls, including wrapped rows on narrow screens.
// Standalone player pages have no containing frame and need no adjustment.
const frame = window.frameElement;
if (frame && frame.parentElement) {
    const fitPlayer = () => {
        const height = Math.ceil(document.body.getBoundingClientRect().height);
        frame.parentElement.style.height = `${height}px`;
    };
    new ResizeObserver(fitPlayer).observe(document.body);
    fitPlayer();
}

// Guided narration observes playback, but the learner decides when to continue.
const guidance = document.querySelector(".narration-guidance");
const parentDocument = frame ? window.parent.document : null;
// Keep reporting beside the notebook action, including while reading lower sections.
function prepareFeedback(downloadButton) {
    const toolbar = downloadButton.closest(".myst-fm-block-header");
    if (!toolbar || toolbar.querySelector(".lesson-feedback")) return;

    const colab = parentDocument.createElement("a");
    colab.className = "lesson-colab";
    colab.href = document.body.dataset.colab;
    colab.textContent = "Open in Colab";
    colab.title = "Run and edit this lesson in Google Colab (Google account required)";
    colab.target = "_blank";
    colab.rel = "noopener noreferrer";
    toolbar.append(colab);

    const menu = parentDocument.createElement("details");
    menu.className = "lesson-feedback";
    const toggle = parentDocument.createElement("summary");
    toggle.textContent = "Feedback";
    menu.append(toggle);
    const panel = parentDocument.createElement("div");
    panel.className = "lesson-feedback-panel";
    const lesson = parentDocument.querySelector("h1")?.textContent.trim()
        || parentDocument.title;
    for (const [label, template, field] of [
        ["Report a problem", "problem.yml", "lesson"],
        ["Suggest an improvement", "suggestion.yml", "related"],
    ]) {
        const link = parentDocument.createElement("a");
        const url = new URL("https://github.com/DeepLearnPhysics/spine-learn/issues/new");
        url.searchParams.set("template", template);
        url.searchParams.set(field, lesson);
        link.href = url.href;
        link.textContent = label;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.addEventListener("click", () => { menu.open = false; });
        panel.append(link);
    }
    const note = parentDocument.createElement("small");
    note.textContent = "Opens GitHub · account required";
    panel.append(note);
    menu.append(panel);
    toolbar.append(menu);
    toolbar.classList.add("lesson-actions");

    // A marker preserves the original position when the action row is pinned.
    const marker = parentDocument.createElement("div");
    marker.className = "lesson-actions-marker";
    toolbar.before(marker);
    const updatePosition = () => {
        if (!toolbar.isConnected) return;
        const nav = parentDocument.querySelector(".myst-top-nav-bar");
        const top = Math.max(0, nav?.getBoundingClientRect().bottom || 0) + 8;
        const bounds = marker.getBoundingClientRect();
        const pinned = bounds.top < top;
        if (pinned && !toolbar.classList.contains("is-pinned")) {
            marker.style.height = `${toolbar.getBoundingClientRect().height + 20}px`;
        } else if (!pinned) {
            marker.style.height = "0px";
        }
        toolbar.classList.toggle("is-pinned", pinned);
        if (pinned) {
            toolbar.style.top = `${top}px`;
            toolbar.style.right = `${parentDocument.documentElement.clientWidth - bounds.right}px`;
            toolbar.style.width = "max-content";
            toolbar.style.maxWidth = `${bounds.width}px`;
        } else {
            for (const property of ["top", "right", "width", "max-width"]) toolbar.style.removeProperty(property);
        }
    };
    const dismiss = event => {
        if (event.key === "Escape" && menu.open) {
            menu.open = false;
            toggle.focus();
        } else if (event.type === "click" && !menu.contains(event.target)) {
            menu.open = false;
        }
    };
    parentDocument.addEventListener("click", dismiss);
    parentDocument.addEventListener("keydown", dismiss);
    window.parent.addEventListener("scroll", updatePosition, {passive: true});
    window.parent.addEventListener("resize", updatePosition);
    updatePosition();
    window.addEventListener("pagehide", () => {
        parentDocument.removeEventListener("click", dismiss);
        parentDocument.removeEventListener("keydown", dismiss);
        window.parent.removeEventListener("scroll", updatePosition);
        window.parent.removeEventListener("resize", updatePosition);
    });
}

// MyST uses a menu for downloads. This lesson has one portable notebook, so
// adapt the existing control to a direct download without adding another button.
if (parentDocument && document.body.dataset.notebook) {
    const notebookUrl = new URL(document.body.dataset.notebook, window.location.href).href;
    const prepareDownload = () => {
        const button = parentDocument.querySelector(".myst-fm-downloads-button");
        if (!button) return;
        prepareFeedback(button);
        if (button.dataset.notebookUrl === notebookUrl) return;
        button.dataset.notebookUrl = notebookUrl;
        button.setAttribute("aria-label", "Download notebook (.ipynb)");
        button.setAttribute("title", "Download notebook (.ipynb)");
        button.removeAttribute("aria-haspopup");
        button.removeAttribute("aria-expanded");
    };
    prepareDownload();
    // Hydration/navigation can replace the theme's button after frames load.
    const downloadObserver = new MutationObserver(prepareDownload);
    downloadObserver.observe(parentDocument.body, {childList: true, subtree: true});
    window.addEventListener("pagehide", () => downloadObserver.disconnect());
    if (!parentDocument.documentElement.dataset.directNotebookDownload) {
        parentDocument.documentElement.dataset.directNotebookDownload = "true";
        parentDocument.addEventListener("keydown", event => {
            const button = event.target.closest?.(".myst-fm-downloads-button");
            if (!button?.dataset.notebookUrl) return;
            if (!["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key)) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            if (event.key === "Enter" || event.key === " ") button.click();
        }, true);
        parentDocument.addEventListener("click", event => {
            const button = event.target.closest?.(".myst-fm-downloads-button");
            if (!button?.dataset.notebookUrl) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            const link = parentDocument.createElement("a");
            link.href = button.dataset.notebookUrl;
            link.download = new URL(link.href).pathname.split("/").pop();
            parentDocument.body.append(link);
            link.click();
            link.remove();
        }, true);
    }
}

// Iframes do not inherit the site's theme; follow its explicit theme toggle.
if (parentDocument) {
    const syncTheme = () => document.body.classList.toggle("dark",
        parentDocument.documentElement.classList.contains("dark"));
    new MutationObserver(syncTheme).observe(parentDocument.documentElement,
        {attributes: true, attributeFilter: ["class"]});
    syncTheme();
}
const scrollChoice = guidance?.querySelector(".follow-scroll");
scrollChoice?.addEventListener("click", () => {
    const enabled = scrollChoice.getAttribute("aria-pressed") === "true";
    scrollChoice.setAttribute("aria-pressed", String(!enabled));
});
const continueButton = guidance?.querySelector(".continue-narration");
const guidanceStatus = guidance?.querySelector(".guidance-status");

// One shared overlay marks the full step across MyST's separate notebook cells.
// Measuring rather than wrapping those cells preserves MyST's layout and React tree.
let activeHeading = null;
function positionStepMarker() {
    const marker = parentDocument?.getElementById("narration-step-marker");
    if (!marker || marker.dataset.owner !== frame.src || !activeHeading?.isConnected) return;
    const headingBox = activeHeading.getBoundingClientRect();
    let bottom = headingBox.bottom;
    for (const element of parentDocument.querySelectorAll(
        "article h2, article h3, article p, article pre, article figure, article table, article ul, article ol, article iframe"
    )) {
        if (!(activeHeading.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
        if (element.matches("h2, h3")) break;
        bottom = Math.max(bottom, element.getBoundingClientRect().bottom);
    }
    const parentWindow = window.parent;
    marker.style.left = `${Math.max(2, headingBox.left - 15) + parentWindow.scrollX}px`;
    marker.style.top = `${headingBox.top + parentWindow.scrollY}px`;
    marker.style.height = `${bottom - headingBox.top}px`;
}

if (parentDocument) {
    const article = parentDocument.querySelector("article");
    if (article) new ResizeObserver(positionStepMarker).observe(article);
    window.parent.addEventListener("resize", positionStepMarker);
    // Expanded settings and late-loading figures can move the active step.
    parentDocument.addEventListener("load", positionStepMarker, true);
}

function highlightStep(id) {
    if (!parentDocument || !id) return;
    const target = parentDocument.getElementById(id);
    if (!target) return;
    parentDocument.querySelectorAll(".narration-active").forEach(element => {
        element.classList.remove("narration-active");
    });
    for (const player of parentDocument.querySelectorAll('iframe[src*="/players/"]')) {
        player.contentDocument?.body.classList.toggle("active-narration", player === frame);
    }
    target.classList.add("narration-active");
    activeHeading = target;
    let marker = parentDocument.getElementById("narration-step-marker");
    if (!marker) {
        marker = parentDocument.createElement("div");
        marker.id = "narration-step-marker";
        marker.setAttribute("aria-hidden", "true");
        parentDocument.body.append(marker);
    }
    marker.dataset.owner = frame.src;
    positionStepMarker();
    if (scrollChoice?.getAttribute("aria-pressed") === "true") {
        target.scrollIntoView({block: "start", behavior: "instant"});
    }
}

function pauseOtherPlayers() {
    if (!parentDocument) return;
    for (const player of parentDocument.querySelectorAll('iframe[src*="/players/"]')) {
        if (player !== frame) player.contentDocument?.querySelector("audio")?.pause();
    }
}

if (audio) {
    audio.addEventListener("play", () => {
        pauseOtherPlayers();
        // Every clip owns a section, even without a guided Continue sequence.
        highlightStep(document.body.dataset.focus);
        if (!guidance) return;
        continueButton.classList.remove("ready");
        guidanceStatus.textContent = "Listening. You can pause, replay, or continue at your own pace.";
    });
    audio.addEventListener("ended", () => {
        if (!guidance) return;
        highlightStep(guidance.dataset.nextStep);
        continueButton.classList.add("ready");
        guidanceStatus.textContent = guidance.dataset.nextChunk
            ? "Your turn: try the highlighted activity. Continue when you are ready for the explanation."
            : "Ready for the next section? Continue when you choose.";
    });
}

continueButton?.addEventListener("click", async () => {
    audio?.pause();
    const nextChunk = guidance.dataset.nextChunk;
    if (!nextChunk || !parentDocument) {
        highlightStep(guidance.dataset.nextStep);
        guidanceStatus.textContent = "The next section is highlighted. Continue reading at your own pace.";
        return;
    }
    const nextFrame = [...parentDocument.querySelectorAll("iframe")].find(player =>
        new URL(player.src).pathname.endsWith(`/players/${nextChunk}.html`));
    const nextAudio = nextFrame?.contentDocument?.querySelector("audio");
    highlightStep(nextChunk);
    if (!nextAudio) {
        guidanceStatus.textContent = "Read the explanation below or download its transcript; audio is not available.";
        return;
    }
    // One explicit user gesture advances one clip; finishing audio never autoplays.
    const nextScrollChoice = nextFrame.contentDocument.querySelector(".follow-scroll");
    if (nextScrollChoice) {
        nextScrollChoice.setAttribute("aria-pressed", scrollChoice.getAttribute("aria-pressed"));
    }
    continueButton.classList.remove("ready");
    nextAudio.playbackRate = audio?.playbackRate || 1;
    nextAudio.currentTime = 0;
    try {
        await nextAudio.play();
        guidanceStatus.textContent = "Playing the explanation. You can pause it in the next player.";
    } catch {
        guidanceStatus.textContent = "Use Play on the explanation below to start its narration.";
    }
});
