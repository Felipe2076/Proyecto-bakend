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

    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");
        if (!link) return;
        const href = link.getAttribute("href") || "";
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;
        if (link.target === "_blank" || link.hasAttribute("download")) return;
        if (!sameOrigin(href)) return;
        showLoader();
    });

    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.classList.contains("needs-validation") && !form.checkValidity()) return;
        showLoader();
    });

    window.addEventListener("pageshow", hideLoader);

    if (!reduced && window.Lenis) {
        const lenis = new window.Lenis({
            duration: 1.05,
            smoothWheel: true,
            syncTouch: false,
        });
        const raf = (time) => {
            lenis.raf(time);
            window.requestAnimationFrame(raf);
        };
        window.requestAnimationFrame(raf);
    }
})();
