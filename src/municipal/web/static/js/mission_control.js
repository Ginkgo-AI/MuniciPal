/**
 * Mission Control — Staff Dashboard Logic
 * No external dependencies. Vanilla JS only.
 *
 * Note: All user-supplied content is escaped via escapeHtml() before
 * being inserted into the DOM. Classification badges and confidence
 * values use controlled/validated inputs only.
 */

(function () {
    "use strict";

    // ---- State ----
    var selectedSessionId = null;
    var sessions = [];
    var auditEntries = [];
    var refreshTimer = null;

    // ---- DOM refs ----
    var sessionList = document.getElementById("sessionList");
    var conversationView = document.getElementById("conversationView");
    var detailMeta = document.getElementById("detailMeta");
    var detailControls = document.getElementById("detailControls");
    var detailSessionId = document.getElementById("detailSessionId");
    var detailSessionType = document.getElementById("detailSessionType");
    var detailMessageCount = document.getElementById("detailMessageCount");
    var detailLastActive = document.getElementById("detailLastActive");
    var shadowToggle = document.getElementById("shadowToggle");
    var auditBody = document.getElementById("auditBody");
    var feedbackModal = document.getElementById("feedbackModal");
    var feedbackForm = document.getElementById("feedbackForm");
    var feedbackSessionId = document.getElementById("feedbackSessionId");
    var feedbackMessageIndex = document.getElementById("feedbackMessageIndex");
    var feedbackFlagType = document.getElementById("feedbackFlagType");
    var feedbackNote = document.getElementById("feedbackNote");
    var connectionStatus = document.getElementById("connectionStatus");
    var lastRefreshEl = document.getElementById("lastRefresh");

    // Filter inputs
    var filterActor = document.getElementById("filterActor");
    var filterAction = document.getElementById("filterAction");
    var filterClassification = document.getElementById("filterClassification");
    var filterAfter = document.getElementById("filterAfter");
    var filterBefore = document.getElementById("filterBefore");

    // ---- API helpers ----

    function apiGet(url) {
        return fetch(url).then(function (resp) {
            if (!resp.ok) throw new Error("HTTP " + resp.status);
            return resp.json();
        }).then(function (data) {
            connectionStatus.classList.remove("disconnected");
            return data;
        }).catch(function (err) {
            console.error("API GET error:", url, err);
            connectionStatus.classList.add("disconnected");
            return null;
        });
    }

    function apiPost(url, body) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        }).then(function (resp) {
            if (!resp.ok) {
                return resp.json().catch(function () { return {}; }).then(function (data) {
                    throw new Error(data.detail || "HTTP " + resp.status);
                });
            }
            return resp.json();
        });
    }

    // ---- Formatting helpers ----

    function truncateId(id) {
        if (!id) return "--";
        return id.substring(0, 8) + "...";
    }

    function formatTime(isoStr) {
        if (!isoStr) return "--";
        var d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }

    function formatDateTime(isoStr) {
        if (!isoStr) return "--";
        var d = new Date(isoStr);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }

    function escapeHtml(str) {
        var div = document.createElement("div");
        div.textContent = String(str);
        return div.innerHTML;
    }

    // Allowed classification values for badge rendering (whitelist)
    var VALID_CLASSIFICATIONS = ["public", "internal", "sensitive", "restricted"];

    // ---- Safe DOM construction helpers ----

    function createEl(tag, attrs, children) {
        var el = document.createElement(tag);
        if (attrs) {
            Object.keys(attrs).forEach(function (key) {
                if (key === "className") {
                    el.className = attrs[key];
                } else if (key === "textContent") {
                    el.textContent = attrs[key];
                } else if (key.indexOf("data-") === 0 || key === "role" || key === "tabindex" || key === "title" || key === "type" || key === "colspan" || key === "scope") {
                    el.setAttribute(key, attrs[key]);
                }
            });
        }
        if (children) {
            children.forEach(function (child) {
                if (typeof child === "string") {
                    el.appendChild(document.createTextNode(child));
                } else if (child) {
                    el.appendChild(child);
                }
            });
        }
        return el;
    }

    function createBadge(text, extraClass) {
        return createEl("span", { className: "mc-badge " + extraClass, textContent: text });
    }

    function createClassificationBadge(cls) {
        var safe = VALID_CLASSIFICATIONS.indexOf(cls) !== -1 ? cls : "public";
        return createBadge(safe, "mc-badge-" + safe);
    }

    function createConfidenceBadge(confidence) {
        if (confidence === null || confidence === undefined) return null;
        var level, label;
        if (confidence >= 0.8) { level = "high"; label = "High"; }
        else if (confidence >= 0.5) { level = "medium"; label = "Med"; }
        else { level = "low"; label = "Low"; }
        var badge = createEl("span", {
            className: "mc-badge mc-badge-confidence-" + level,
            title: "Confidence: " + (confidence * 100).toFixed(0) + "%",
            textContent: label + " " + (confidence * 100).toFixed(0) + "%",
        });
        return badge;
    }

    // ---- Sessions ----

    function loadSessions() {
        return apiGet("/api/staff/sessions").then(function (data) {
            if (data === null) return;
            lastRefreshEl.textContent = formatTime(new Date().toISOString());
            sessions = data;
            renderSessionList();
        });
    }

    function renderSessionList() {
        // Clear existing content
        while (sessionList.firstChild) {
            sessionList.removeChild(sessionList.firstChild);
        }

        if (sessions.length === 0) {
            sessionList.appendChild(createEl("div", { className: "mc-empty-state", textContent: "No active sessions" }));
            return;
        }

        sessions.forEach(function (s) {
            var isSelected = s.session_id === selectedSessionId;
            var item = createEl("div", {
                className: "mc-session-item" + (isSelected ? " selected" : ""),
                role: "listitem",
                tabindex: "0",
                "data-session-id": s.session_id,
            });

            var row = createEl("div", { className: "mc-session-item-row" }, [
                createEl("span", { className: "mc-session-id", textContent: truncateId(s.session_id) }),
                createBadge(s.session_type, "mc-badge-type"),
            ]);
            if (s.shadow_mode) {
                row.appendChild(createBadge("SHADOW", "mc-badge-shadow"));
            }
            item.appendChild(row);

            var meta = createEl("div", { className: "mc-session-meta" }, [
                createBadge(s.message_count + " msgs", "mc-badge-count"),
                createEl("span", { textContent: formatTime(s.last_active) }),
            ]);
            item.appendChild(meta);

            item.addEventListener("click", onSessionClick);
            item.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSessionClick.call(this, e);
                }
            });

            sessionList.appendChild(item);
        });
    }

    function onSessionClick(e) {
        var el = e.currentTarget || e.target.closest(".mc-session-item");
        var sid = el.getAttribute("data-session-id");
        selectSession(sid);
    }

    function selectSession(sid) {
        selectedSessionId = sid;
        renderSessionList();
        loadSessionDetail(sid);
    }

    function loadSessionDetail(sid) {
        return apiGet("/api/sessions/" + encodeURIComponent(sid)).then(function (data) {
            if (data === null) {
                while (conversationView.firstChild) conversationView.removeChild(conversationView.firstChild);
                conversationView.appendChild(createEl("div", { className: "mc-empty-state", textContent: "Failed to load session." }));
                return;
            }

            // Update meta
            detailMeta.style.display = "flex";
            detailControls.style.display = "flex";
            detailSessionId.textContent = sid;
            detailSessionType.textContent = data.session_type;
            detailMessageCount.textContent = String(data.message_count);
            detailLastActive.textContent = formatDateTime(data.last_active);

            // Update shadow toggle
            var session = sessions.find(function (s) { return s.session_id === sid; });
            shadowToggle.checked = session ? session.shadow_mode : false;

            // Render messages
            renderConversation(data.messages, sid);
        });
    }

    function renderConversation(messages, sid) {
        while (conversationView.firstChild) conversationView.removeChild(conversationView.firstChild);

        if (!messages || messages.length === 0) {
            conversationView.appendChild(createEl("div", { className: "mc-empty-state", textContent: "No messages in this session." }));
            return;
        }

        messages.forEach(function (msg, i) {
            var msgEl = createEl("div", { className: "mc-message mc-message-" + msg.role });

            // Header
            var headerChildren = [
                createEl("span", { className: "mc-message-role", textContent: msg.role }),
                createEl("span", { textContent: formatTime(msg.timestamp) }),
            ];
            var confBadge = createConfidenceBadge(msg.confidence);
            if (confBadge) headerChildren.push(confBadge);
            msgEl.appendChild(createEl("div", { className: "mc-message-header" }, headerChildren));

            // Content
            msgEl.appendChild(createEl("div", { className: "mc-message-content", textContent: msg.content }));

            // Flag button for assistant messages
            if (msg.role === "assistant") {
                var flagBtn = createEl("button", {
                    className: "mc-btn mc-btn-flag mc-btn-sm",
                    "data-session-id": sid,
                    "data-message-index": String(i),
                    textContent: "Flag this answer",
                });
                flagBtn.addEventListener("click", onFlagClick);
                msgEl.appendChild(createEl("div", { className: "mc-message-footer" }, [flagBtn]));
            }

            conversationView.appendChild(msgEl);
        });

        // Scroll to bottom
        conversationView.scrollTop = conversationView.scrollHeight;
    }

    // ---- Shadow mode ----

    function toggleShadowMode(sid, enabled) {
        apiPost("/api/staff/shadow", {
            session_id: sid,
            enabled: enabled,
        }).then(function () {
            loadSessions();
        }).catch(function (err) {
            alert("Failed to toggle shadow mode: " + err.message);
            shadowToggle.checked = !enabled;
        });
    }

    // ---- Feedback ----

    function onFlagClick(e) {
        var btn = e.currentTarget;
        var sid = btn.getAttribute("data-session-id");
        var idx = parseInt(btn.getAttribute("data-message-index"), 10);
        openFeedbackModal(sid, idx);
    }

    function openFeedbackModal(sid, messageIndex) {
        feedbackSessionId.value = sid;
        feedbackMessageIndex.value = String(messageIndex);
        feedbackFlagType.value = "inaccurate";
        feedbackNote.value = "";
        feedbackModal.style.display = "flex";
        feedbackFlagType.focus();
    }

    function closeFeedbackModal() {
        feedbackModal.style.display = "none";
    }

    function submitFeedback(e) {
        e.preventDefault();
        var body = {
            session_id: feedbackSessionId.value,
            message_index: parseInt(feedbackMessageIndex.value, 10),
            flag_type: feedbackFlagType.value,
            note: feedbackNote.value,
        };

        apiPost("/api/staff/feedback", body).then(function () {
            closeFeedbackModal();
        }).catch(function (err) {
            alert("Failed to submit feedback: " + err.message);
        });
    }

    // ---- Audit log ----

    function loadAuditLog() {
        var params = [];
        if (filterActor.value) params.push("actor=" + encodeURIComponent(filterActor.value));
        if (filterAction.value) params.push("action=" + encodeURIComponent(filterAction.value));
        if (filterClassification.value) params.push("classification=" + encodeURIComponent(filterClassification.value));
        if (filterAfter.value) params.push("after=" + encodeURIComponent(filterAfter.value + "T00:00:00"));
        if (filterBefore.value) params.push("before=" + encodeURIComponent(filterBefore.value + "T23:59:59"));

        var url = "/api/staff/audit";
        if (params.length > 0) url += "?" + params.join("&");

        return apiGet(url).then(function (data) {
            if (data === null) return;
            auditEntries = data;
            renderAuditTable();
        });
    }

    function renderAuditTable() {
        while (auditBody.firstChild) auditBody.removeChild(auditBody.firstChild);

        if (auditEntries.length === 0) {
            var emptyRow = createEl("tr", {}, [
                createEl("td", { colspan: "5", className: "mc-empty-state", textContent: "No audit entries found." }),
            ]);
            auditBody.appendChild(emptyRow);
            return;
        }

        auditEntries.forEach(function (entry) {
            var row = createEl("tr", {}, [
                createEl("td", { className: "mc-audit-timestamp", textContent: formatDateTime(entry.timestamp) }),
                createEl("td", { textContent: entry.actor }),
                createEl("td", { textContent: entry.action }),
                createEl("td", { textContent: entry.resource }),
                createEl("td", {}, [createClassificationBadge(entry.classification)]),
            ]);
            auditBody.appendChild(row);
        });
    }

    // ---- Keyboard navigation ----

    function setupKeyboardNav() {
        document.addEventListener("keydown", function (e) {
            // Alt+1/2/3 to focus panels
            if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                if (e.key === "1") {
                    e.preventDefault();
                    document.getElementById("panelSessions").focus();
                } else if (e.key === "2") {
                    e.preventDefault();
                    document.getElementById("panelDetail").focus();
                } else if (e.key === "3") {
                    e.preventDefault();
                    document.getElementById("panelAudit").focus();
                }
            }

            // Escape to close modal
            if (e.key === "Escape" && feedbackModal.style.display !== "none") {
                closeFeedbackModal();
            }
        });

        // Arrow key navigation in session list
        sessionList.addEventListener("keydown", function (e) {
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                var items = sessionList.querySelectorAll(".mc-session-item");
                if (items.length === 0) return;

                var current = document.activeElement;
                var idx = Array.prototype.indexOf.call(items, current);

                if (e.key === "ArrowDown" && idx < items.length - 1) {
                    items[idx + 1].focus();
                } else if (e.key === "ArrowUp" && idx > 0) {
                    items[idx - 1].focus();
                }
            }
        });
    }

    // ---- Auto-refresh ----

    function startAutoRefresh() {
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(function () {
            loadSessions();
            if (selectedSessionId) {
                loadSessionDetail(selectedSessionId);
            }
        }, 10000);
    }

    // ---- Event bindings ----

    function init() {
        // Button handlers
        document.getElementById("btnRefreshSessions").addEventListener("click", loadSessions);
        document.getElementById("btnRefreshAudit").addEventListener("click", loadAuditLog);
        document.getElementById("btnApplyFilters").addEventListener("click", loadAuditLog);
        document.getElementById("btnCloseFeedback").addEventListener("click", closeFeedbackModal);
        document.getElementById("btnCancelFeedback").addEventListener("click", closeFeedbackModal);

        // Shadow toggle
        shadowToggle.addEventListener("change", function () {
            if (selectedSessionId) {
                toggleShadowMode(selectedSessionId, shadowToggle.checked);
            }
        });

        // Feedback form
        feedbackForm.addEventListener("submit", submitFeedback);

        // Close modal on overlay click
        feedbackModal.addEventListener("click", function (e) {
            if (e.target === feedbackModal) {
                closeFeedbackModal();
            }
        });

        // Keyboard navigation
        setupKeyboardNav();

        // Initial data load
        loadSessions();
        loadAuditLog();

        // Auto-refresh
        startAutoRefresh();
    }

    // Start when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
