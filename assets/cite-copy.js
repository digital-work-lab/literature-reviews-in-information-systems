(function () {
  const ICON_COPY = `
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
      <path fill="currentColor" d="M10 1.5H4A1.5 1.5 0 0 0 2.5 3v7H4V3h6V1.5z"/>
      <path fill="currentColor" d="M6 5a1.5 1.5 0 0 0-1.5 1.5v7A1.5 1.5 0 0 0 6 15h6a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 12 5H6zm0 1.5h6v7H6v-7z"/>
    </svg>
  `;

  const ICON_CHECK = `
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
      <path fill="currentColor" d="M6.2 12.1 2.7 8.6l1.1-1.1 2.4 2.4 6-6 1.1 1.1-7.1 7.1z"/>
    </svg>
  `;

  function addButtons(root = document) {
    root.querySelectorAll(".citebox").forEach((box) => {
      if (box.dataset.citeCopyBound === "true") return;
      box.dataset.citeCopyBound = "true";

      const text = box.innerText?.trim();
      if (!text) return;

      box.style.position = box.style.position || "relative";

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cite-copy";
      btn.setAttribute("aria-label", "Copy citation");
      btn.setAttribute("title", "Copy");
      btn.innerHTML = ICON_COPY;

      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(text);
          btn.innerHTML = ICON_CHECK;
          btn.setAttribute("title", "Copied");
          setTimeout(() => {
            btn.innerHTML = ICON_COPY;
            btn.setAttribute("title", "Copy");
          }, 900);
        } catch (e) {
          // fallback: select text so user can copy manually
          const range = document.createRange();
          range.selectNodeContents(box);
          const sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(range);
          btn.setAttribute("title", "Select & copy");
          setTimeout(() => btn.setAttribute("title", "Copy"), 1200);
        }
      });

      box.prepend(btn);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => addButtons());
  } else {
    addButtons();
  }

  window.addEventListener("quarto:after-render", () => addButtons());
})();
