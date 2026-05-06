(function () {
    "use strict";

    var themeOrder = ["system", "light", "dark"];
    var themeIcons = { system: "◐", light: "○", dark: "●" };

    function setAttr(name, value) {
        document.documentElement.setAttribute(name, value);
    }

    function stored(name, fallback) {
        try {
            return localStorage.getItem(name) || fallback;
        } catch (error) {
            return fallback;
        }
    }

    function persist(name, value) {
        try {
            localStorage.setItem(name, value);
        } catch (error) {
            return;
        }
    }

    function cycle(current, order) {
        var index = order.indexOf(current);
        return order[(index + 1) % order.length] || order[0];
    }

    function syncControls() {
        var theme = stored("chirpui-theme", "system");

        setAttr("data-theme", theme);

        document.querySelectorAll("[data-chirpui-theme-icon]").forEach(function (icon) {
            icon.textContent = themeIcons[theme] || themeIcons.system;
        });
    }

    function setupThemeControls() {
        document.querySelectorAll("[data-chirpui-theme-cycle]").forEach(function (button) {
            button.addEventListener("click", function () {
                var next = cycle(stored("chirpui-theme", "system"), themeOrder);
                persist("chirpui-theme", next);
                syncControls();
            });
        });

        syncControls();
    }

    function setupSearch() {
        var input = document.getElementById("q");
        var results = Array.prototype.slice.call(document.querySelectorAll("[data-chirpui-search-item]"));
        var groups = Array.prototype.slice.call(document.querySelectorAll("[data-chirpui-search-group]"));
        var empty = document.getElementById("chirpui-bengal-search-empty");
        var count = document.getElementById("chirpui-bengal-search-count");

        if (!input || results.length === 0) {
            return;
        }

        var params = new URLSearchParams(window.location.search);
        if (params.has(input.name)) {
            input.value = params.get(input.name) || "";
        }

        function apply() {
            var query = input.value.trim().toLowerCase();
            var visible = 0;

            results.forEach(function (item) {
                var text = (item.getAttribute("data-search-text") || "").toLowerCase();
                var match = !query || text.indexOf(query) !== -1;
                item.hidden = !match;
                if (match) {
                    visible += 1;
                }
            });

            groups.forEach(function (group) {
                var groupVisible = Array.prototype.some.call(
                    group.querySelectorAll("[data-chirpui-search-item]"),
                    function (item) {
                        return !item.hidden;
                    }
                );
                group.hidden = !groupVisible;
            });

            if (count) {
                count.textContent = visible + (visible === 1 ? " result" : " results");
            }

            if (empty) {
                empty.hidden = visible !== 0;
            }
        }

        input.addEventListener("input", apply);
        var form = input.closest("form");
        if (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                apply();
            });
        }
        apply();
    }

    function setupDrawers() {
        document.querySelectorAll("[data-chirpui-drawer-open]").forEach(function (button) {
            button.addEventListener("click", function () {
                var id = button.getAttribute("data-chirpui-drawer-open");
                var drawer = id ? document.getElementById(id) : null;
                if (!drawer) {
                    return;
                }
                if (typeof drawer.showModal === "function") {
                    drawer.showModal();
                    return;
                }
                drawer.setAttribute("open", "");
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setupThemeControls();
        setupSearch();
        setupDrawers();
    });
})();
