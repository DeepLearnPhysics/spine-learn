// No credentials or persistent chat storage live in the browser.
const isLocal = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);
const status = document.querySelector("#status");
const availability = document.querySelector("#availability");
const feedback = document.querySelector("#feedback");
const setup = document.querySelector("#setup");
const question = document.querySelector("#question");
const send = document.querySelector("#send");
const clear = document.querySelector("#clear");
const reconnect = document.querySelector("#reconnect");
const messages = document.querySelector("#messages");
const suggestions = [...document.querySelectorAll("[data-question]")];
let history = [];
let ready = false;
let busy = false;

function updateControls() {
    question.disabled = !ready || busy;
    send.disabled = !ready || busy;
    clear.disabled = busy;
    reconnect.disabled = busy;
    suggestions.forEach(button => { button.disabled = !ready || busy; });
    send.querySelector("span").textContent = busy ? "…" : "↑";
    send.setAttribute("aria-label", busy ? "Sending question" : "Send question");
    send.title = busy ? "Sending question" : "Send question (Enter)";
    messages.setAttribute("aria-busy", String(busy));
}

async function loadConfiguration() {
    busy = true;
    updateControls();
    try {
        const response = await fetch("/api/tutor/status", {signal: AbortSignal.timeout(5000)});
        if (!response.ok) throw new Error("No backend");
        const data = await response.json();
        ready = data.configured === true;
        status.textContent = ready
            ? `Ready · ${data.model}`
            : (isLocal ? "The local tutor needs a Gemini API key." : "The lesson assistant is not configured yet.");
    } catch {
        ready = false;
        status.textContent = isLocal ? "Chat is available in the local tutor preview. See setup below." : "The lesson assistant is temporarily unavailable.";
        if (!isLocal) {
            availability.textContent = "The lesson assistant is not available on this hosted site yet. You can read the full lesson and download its notebook while public chat hosting is being set up.";
            availability.hidden = false;
            document.body.classList.add("tutor-unavailable");
            frame?.parentElement?.classList.add("tutor-unavailable");
        }
    }
    setup.hidden = ready || !isLocal;
    busy = false;
    updateControls();
}

async function checkConnection() {
    await loadConfiguration();
    if (!ready) return;
    busy = true;
    updateControls();
    reconnect.textContent = "Checking Gemini…";
    status.textContent = "Testing an actual response from Gemini…";
    feedback.textContent = "";
    try {
        const response = await fetch("/api/tutor/check", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: "{}",
            signal: AbortSignal.timeout(55000),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Connection check failed.");
        status.textContent = `Connected · ${data.model} · Gemini answered successfully.`;
    } catch (error) {
        status.textContent = error.name === "TimeoutError"
            ? "Gemini took too long to respond. Try again."
            : error.message;
        feedback.textContent = status.textContent;
        feedback.className = "error";
    } finally {
        busy = false;
        reconnect.textContent = "Check connection";
        updateControls();
    }
}

function addMessage(speaker, text) {
    const entry = document.createElement("div");
    entry.className = "message";
    const label = document.createElement("strong");
    label.textContent = speaker;
    entry.append(label);
    const content = document.createElement("div");
    content.className = "message-content";
    if (speaker === "You") {
        content.textContent = text;
    } else {
        // Model output is untrusted: render Markdown, then allow only prose tags.
        content.innerHTML = DOMPurify.sanitize(marked.parse(text), {
            ALLOWED_TAGS: ["p", "br", "strong", "em", "del", "code", "pre",
                "ul", "ol", "li", "blockquote", "h1", "h2", "h3", "h4",
                "h5", "h6", "a", "hr", "table", "thead", "tbody", "tr", "th", "td"],
            ALLOWED_ATTR: ["href", "title", "start"],
        });
        content.querySelectorAll("a").forEach(link => {
            let url;
            try {
                url = new URL(link.getAttribute("href") || "", window.location.href);
            } catch {
                link.removeAttribute("href");
                return;
            }
            if (!["https:", "http:"].includes(url.protocol)) {
                link.removeAttribute("href");
            } else {
                link.target = "_blank";
                link.rel = "noopener noreferrer";
            }
        });
    }
    entry.append(content);
    messages.append(entry);
    // Start each answer at its beginning, especially when it exceeds the panel.
    messages.scrollTop += entry.getBoundingClientRect().top - messages.getBoundingClientRect().top;
    return entry;
}

function recentHistory() {
    let recent = history.slice(-12);
    while (recent.reduce((total, turn) => total + turn.text.length, 0) > 24000) {
        recent = recent.slice(2);
    }
    return recent;
}

// Enter submits; Shift+Enter retains the textarea's native newline behavior.
// Composition events must finish before Enter can send an IME user's text.
question.addEventListener("keydown", event => {
    if (event.key !== "Enter" || event.isComposing || event.keyCode === 229) return;
    if (event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return;
    event.preventDefault();
    if (event.repeat || !ready || busy || !question.value.trim()) return;
    document.querySelector("#chat").requestSubmit();
});

document.querySelector("#chat").addEventListener("submit", async event => {
    event.preventDefault();
    const text = question.value.trim();
    if (!text || !ready || busy) return;
    busy = true;
    updateControls();
    const pending = addMessage("You", text);
    status.textContent = "Thinking about your question…";
    feedback.className = "";
    feedback.textContent = status.textContent;
    try {
        const response = await fetch("/api/tutor/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: text, history: recentHistory()}),
            signal: AbortSignal.timeout(55000),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "The tutor is unavailable.");
        if (typeof data.answer !== "string") throw new Error("The tutor returned no answer.");
        addMessage("Lesson companion", data.answer);
        history = [...recentHistory(), {role: "user", text}, {role: "model", text: data.answer}];
        question.value = "";
        status.textContent = data.truncated
            ? "The answer reached its length limit. Ask a follow-up for more detail."
            : "Ask a follow-up, or return to the lesson.";
        feedback.textContent = status.textContent;
    } catch (error) {
        pending.remove();
        status.textContent = error.name === "TimeoutError"
            ? "The tutor took too long. Your question is still here; try again."
            : error.message;
        feedback.textContent = status.textContent;
        feedback.className = "error";
    } finally {
        busy = false;
        updateControls();
        question.focus({preventScroll: true});
    }
});

clear.addEventListener("click", () => {
    history = [];
    feedback.textContent = "";
    messages.replaceChildren();
    question.value = "";
    status.textContent = "New conversation. What would you like to understand?";
});
reconnect.addEventListener("click", checkConnection);
suggestions.forEach(button => button.addEventListener("click", () => {
    question.value = button.dataset.question;
    question.focus({preventScroll: true});
}));

// Keep the launcher pinned to the viewport without changing the lesson grid.
const companion = document.querySelector("#companion");
const launcher = companion.querySelector("summary");
const frame = window.frameElement;
function resizePanel() {
    if (frame?.parentElement) {
        frame.parentElement.classList.toggle("tutor-open", companion.open);
    }
    launcher.setAttribute("aria-label", companion.open ? "Minimize lesson help" : "Open lesson help");
    launcher.querySelector(".toggle-icon").textContent = companion.open ? "−" : "+";
}
companion.addEventListener("toggle", resizePanel);
document.addEventListener("keydown", event => {
    if (event.key === "Escape" && companion.open) {
        companion.open = false;
        launcher.focus();
    }
});
if (frame?.parentElement) {
    const syncTheme = () => {
        document.documentElement.classList.toggle("dark",
            window.parent.document.documentElement.classList.contains("dark"));
    };
    syncTheme();
    new MutationObserver(syncTheme).observe(window.parent.document.documentElement,
        {attributes: true, attributeFilter: ["class"]});
}
resizePanel();
loadConfiguration();
