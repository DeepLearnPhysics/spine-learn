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
