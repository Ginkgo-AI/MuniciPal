/**
 * Munici-Pal Digital Librarian — Chat Frontend
 *
 * Vanilla JS chat client. No framework dependencies.
 * Handles session management, message send/receive, citation display,
 * keyboard navigation, and accessibility announcements.
 */

(function () {
    "use strict";

    // --- DOM References ---
    var chatMessages = document.getElementById("chat-messages");
    var chatForm = document.getElementById("chat-form");
    var chatInput = document.getElementById("chat-input");
    var sendButton = document.getElementById("send-button");
    var srAnnouncements = document.getElementById("sr-announcements");
    var themeToggle = document.getElementById("theme-toggle");

    // --- State ---
    var sessionId = null;
    var isLoading = false;

    // --- API Helpers ---

    function apiPost(url, body) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        }).then(function (response) {
            if (!response.ok) {
                return response.text().then(function (detail) {
                    throw new Error(detail || "Request failed (" + response.status + ")");
                });
            }
            return response.json();
        });
    }

    // --- Session Management ---

    function createSession() {
        apiPost("/api/sessions", { session_type: "anonymous" })
            .then(function (data) {
                sessionId = data.session_id;
                announce("Chat session started. Type your question below.");
            })
            .catch(function (err) {
                showError("Could not start a chat session. Please refresh the page.");
                console.error("Session creation failed:", err);
            });
    }

    // --- Message Rendering ---

    function removeWelcome() {
        var welcome = chatMessages.querySelector(".welcome-message");
        if (welcome) {
            welcome.remove();
        }
    }

    function createLoadingDots() {
        var dots = document.createElement("div");
        dots.className = "loading-dots";
        for (var i = 0; i < 3; i++) {
            var span = document.createElement("span");
            dots.appendChild(span);
        }
        return dots;
    }

    function createMessageElement(role, content, metadata) {
        var wrapper = document.createElement("div");
        wrapper.className = "message message--" + role;
        wrapper.setAttribute("role", "article");

        // Label
        var label = document.createElement("div");
        label.className = "message__label";
        label.textContent = role === "user" ? "You" : "Assistant";
        wrapper.appendChild(label);

        // Bubble
        var bubble = document.createElement("div");
        bubble.className = "message__bubble";
        bubble.textContent = content;
        wrapper.appendChild(bubble);

        if (role === "assistant" && metadata) {
            // Confidence indicator
            if (typeof metadata.confidence === "number") {
                var conf = metadata.confidence;
                var level = conf >= 0.7 ? "high" : conf >= 0.5 ? "medium" : "low";
                var pct = Math.round(conf * 100);

                var indicator = document.createElement("div");
                indicator.className = "confidence-indicator confidence--" + level;
                indicator.setAttribute("aria-label", "Confidence: " + pct + "% (" + level + ")");

                var bar = document.createElement("div");
                bar.className = "confidence-bar";
                var fill = document.createElement("div");
                fill.className = "confidence-bar__fill";
                fill.style.width = pct + "%";
                bar.appendChild(fill);

                var text = document.createElement("span");
                text.textContent = pct + "% confidence";

                indicator.appendChild(bar);
                indicator.appendChild(text);
                wrapper.appendChild(indicator);
            }

            // Low confidence warning
            if (metadata.low_confidence) {
                var warning = document.createElement("div");
                warning.className = "low-confidence-warning";
                warning.setAttribute("role", "alert");
                warning.textContent =
                    "This answer has low confidence. Please verify with city staff.";
                wrapper.appendChild(warning);
            }

            // Citations
            if (metadata.citations && metadata.citations.length > 0) {
                var citationsDiv = document.createElement("div");
                citationsDiv.className = "citations";

                var toggleId = "citations-" + Date.now();
                var listId = "citations-list-" + Date.now();

                var toggleBtn = document.createElement("button");
                toggleBtn.className = "citations__toggle";
                toggleBtn.setAttribute("aria-expanded", "false");
                toggleBtn.setAttribute("aria-controls", listId);
                toggleBtn.id = toggleId;
                toggleBtn.textContent = "Sources (" + metadata.citations.length + ")";
                toggleBtn.addEventListener("click", function () {
                    var expanded = this.getAttribute("aria-expanded") === "true";
                    this.setAttribute("aria-expanded", String(!expanded));
                    var list = document.getElementById(this.getAttribute("aria-controls"));
                    if (list) {
                        list.hidden = expanded;
                    }
                });

                var list = document.createElement("ul");
                list.className = "citations__list";
                list.id = listId;
                list.hidden = true;
                list.setAttribute("aria-labelledby", toggleId);

                metadata.citations.forEach(function (cite) {
                    var li = document.createElement("li");
                    li.className = "citation-item";

                    var source = document.createElement("div");
                    source.className = "citation-item__source";
                    source.textContent = cite.source;
                    li.appendChild(source);

                    if (cite.section) {
                        var section = document.createElement("div");
                        section.className = "citation-item__section";
                        section.textContent = "Section: " + cite.section;
                        li.appendChild(section);
                    }

                    if (cite.quote) {
                        var quote = document.createElement("div");
                        quote.className = "citation-item__quote";
                        quote.textContent = cite.quote;
                        li.appendChild(quote);
                    }

                    list.appendChild(li);
                });

                citationsDiv.appendChild(toggleBtn);
                citationsDiv.appendChild(list);
                wrapper.appendChild(citationsDiv);
            }
        }

        return wrapper;
    }

    function appendMessage(role, content, metadata) {
        removeWelcome();
        var el = createMessageElement(role, content, metadata);
        chatMessages.appendChild(el);
        scrollToBottom();
    }

    function showLoading() {
        var loader = document.createElement("div");
        loader.className = "message message--assistant";
        loader.id = "loading-indicator";
        loader.setAttribute("role", "status");
        loader.setAttribute("aria-label", "Assistant is typing");

        var label = document.createElement("div");
        label.className = "message__label";
        label.textContent = "Assistant";
        loader.appendChild(label);

        loader.appendChild(createLoadingDots());

        chatMessages.appendChild(loader);
        scrollToBottom();
    }

    function removeLoading() {
        var loader = document.getElementById("loading-indicator");
        if (loader) {
            loader.remove();
        }
    }

    function showError(msg) {
        var el = document.createElement("div");
        el.className = "error-message";
        el.setAttribute("role", "alert");
        el.textContent = msg;
        chatMessages.appendChild(el);
        scrollToBottom();
        announce("Error: " + msg);
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- Accessibility Announcements ---

    function announce(text) {
        srAnnouncements.textContent = "";
        // Brief delay so screen readers pick up the change
        setTimeout(function () {
            srAnnouncements.textContent = text;
        }, 50);
    }

    // --- Message Sending ---

    function sendMessage(text) {
        if (isLoading || !sessionId || !text.trim()) return;

        isLoading = true;
        sendButton.disabled = true;

        appendMessage("user", text.trim());
        showLoading();
        announce("Sending your question. Please wait.");

        apiPost("/api/chat", {
            session_id: sessionId,
            message: text.trim(),
        })
            .then(function (data) {
                removeLoading();
                appendMessage("assistant", data.response, {
                    citations: data.citations,
                    confidence: data.confidence,
                    low_confidence: data.low_confidence,
                });

                var confPct = Math.round((data.confidence || 0) * 100);
                var announceText = "Assistant responded with " + confPct + "% confidence.";
                if (data.low_confidence) {
                    announceText += " Warning: low confidence answer.";
                }
                if (data.citations && data.citations.length > 0) {
                    announceText += " " + data.citations.length + " source(s) cited.";
                }
                announce(announceText);
            })
            .catch(function (err) {
                removeLoading();
                showError(
                    "Sorry, something went wrong. Please try again or contact city staff."
                );
                console.error("Chat error:", err);
            })
            .finally(function () {
                isLoading = false;
                sendButton.disabled = false;
                chatInput.focus();
            });
    }

    // --- Auto-resize Textarea ---

    function autoResize() {
        chatInput.style.height = "auto";
        var newHeight = Math.min(chatInput.scrollHeight, 128); // max-height: 8rem
        chatInput.style.height = newHeight + "px";
    }

    // --- Theme Toggle ---

    function initTheme() {
        var stored = localStorage.getItem("municipal-theme");
        if (stored) {
            document.documentElement.setAttribute("data-theme", stored);
        }
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute("data-theme");
        var isDarkByPreference =
            window.matchMedia &&
            window.matchMedia("(prefers-color-scheme: dark)").matches;

        var next;
        if (current === "dark") {
            next = "light";
        } else if (current === "light") {
            next = "dark";
        } else {
            // No explicit theme set; toggle based on OS preference
            next = isDarkByPreference ? "light" : "dark";
        }

        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("municipal-theme", next);
        announce("Switched to " + next + " mode.");
    }

    // --- Event Listeners ---

    chatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var text = chatInput.value;
        if (text.trim()) {
            chatInput.value = "";
            chatInput.style.height = "auto";
            sendMessage(text);
        }
    });

    chatInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
        }
        if (e.key === "Escape") {
            chatInput.value = "";
            chatInput.style.height = "auto";
        }
    });

    chatInput.addEventListener("input", autoResize);

    themeToggle.addEventListener("click", toggleTheme);

    // --- Initialization ---

    initTheme();
    createSession();
})();
