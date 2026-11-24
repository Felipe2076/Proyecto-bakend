(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const loader = document.getElementById("sigedLoader");
    const stage = document.getElementById("sigedLoaderStage");
    const loaderSrc = loader ? loader.getAttribute("data-lottie") : "";
    let anim = null;
    let hideTimer = 0;

    const hideLoader = () => {
        if (!loader) return;
        loader.classList.remove("is-visible");
        loader.setAttribute("aria-hidden", "true");
        if (anim && typeof anim.stop === "function") anim.stop();
    };

    const showLoader = () => {
        if (reduced || !loader) return;
        loader.classList.add("is-visible");
        loader.setAttribute("aria-hidden", "false");
        if (anim && typeof anim.play === "function") anim.play();
        window.clearTimeout(hideTimer);
        hideTimer = window.setTimeout(hideLoader, 8000);
    };

    if (!reduced && stage && loaderSrc && window.lottie) {
        anim = window.lottie.loadAnimation({
            container: stage,
            renderer: "svg",
            loop: true,
            autoplay: false,
            path: loaderSrc,
        });
    }

    const sameOrigin = (href) => {
        try {
            const url = new URL(href, window.location.href);
            return url.origin === window.location.origin;
        } catch (_err) {
            return false;
        }
    };

    // Descargas (Excel, evidencias) no recargan la página: el loader quedaría pegado.
    const esDescarga = (href) => /exportar|excel|evidencia|\.xlsx|\.pdf/i.test(href);

    document.addEventListener("click", (event) => {
        if (event.defaultPrevented || event.button !== 0) return;
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        const link = event.target.closest("a[href]");
        if (!link || link.hasAttribute("data-sin-loader")) return;
        const href = link.getAttribute("href") || "";
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;
        if (link.target === "_blank" || link.hasAttribute("download") || esDescarga(href)) return;
        if (!sameOrigin(href)) return;
        // Se decide después de los demás manejadores: si alguno canceló (AJAX), no se muestra.
        window.setTimeout(() => { if (!event.defaultPrevented) showLoader(); }, 0);
    });

    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || form.hasAttribute("data-sin-loader")) return;
        if (esDescarga(form.getAttribute("action") || "")) return;
        window.setTimeout(() => { if (!event.defaultPrevented) showLoader(); }, 0);
    });

    window.addEventListener("pageshow", hideLoader);
})();
