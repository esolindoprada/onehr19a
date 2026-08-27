(() => {
    "use strict";

    const byId = (id) => document.getElementById(id);
    const app = byId("onehr-kiosk-app");
    if (!app) {
        return;
    }

    const deviceCode = app.dataset.deviceCode;
    const tokenKey = `onehr:kiosk:${deviceCode}:token`;
    const queueKey = `onehr:kiosk:${deviceCode}:offline`;
    let deviceToken = sessionStorage.getItem(tokenKey) || "";
    let bootstrap = null;
    let currentIdentity = "";
    let currentCredentialType = "manual";
    let cameraStream = null;

    const state = {
        tokenPanel: byId("kiosk-token-panel"),
        workspace: byId("kiosk-workspace"),
        connectivity: byId("kiosk-connectivity"),
        message: byId("kiosk-message"),
        identity: byId("kiosk-identity"),
        employeeCard: byId("kiosk-employee-card"),
        scheduleCard: byId("kiosk-schedule-card"),
        punchCard: byId("kiosk-punch-card"),
        timeoffCard: byId("kiosk-timeoff-card"),
        queueCount: byId("kiosk-queue-count"),
    };

    function show(el, yes = true) {
        if (el) {
            el.classList.toggle("hidden", !yes);
        }
    }

    function message(text, kind = "info") {
        if (!state.message) return;
        state.message.textContent = text || "";
        state.message.className = `kiosk-message ${kind}`;
        show(state.message, Boolean(text));
    }

    function setConnectivity() {
        state.connectivity.textContent = navigator.onLine ? "Online" : "Offline";
        state.connectivity.className = `kiosk-badge ${navigator.onLine ? "success" : "warning"}`;
    }

    function rpc(path, params) {
        return fetch(path, {
            method: "POST",
            credentials: "same-origin",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params,
                id: Date.now(),
            }),
        }).then(async (response) => {
            const payload = await response.json();
            if (payload.error) {
                const detail = payload.error.data || {};
                throw new Error(detail.message || payload.error.message || "OneHR kiosk request failed.");
            }
            return payload.result;
        });
    }

    function serverDateTimeNow() {
        return new Date().toISOString().slice(0, 19).replace("T", " ");
    }

    function makeEventId() {
        if (window.crypto && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    async function positionEvidence() {
        if (!navigator.geolocation) {
            return {};
        }
        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy,
                }),
                () => resolve({}),
                {enableHighAccuracy: true, timeout: 7000, maximumAge: 15000}
            );
        });
    }

    // ---------------------------------------------------------------------
    // Encrypted browser queue
    // ---------------------------------------------------------------------

    function arrayToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = "";
        bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
        return btoa(binary);
    }

    function base64ToArray(value) {
        const binary = atob(value);
        return Uint8Array.from(binary, (char) => char.charCodeAt(0));
    }

    async function queueCryptoKey() {
        if (!crypto.subtle || !deviceToken) {
            throw new Error("Secure browser encryption is unavailable; offline event was not stored.");
        }
        const material = new TextEncoder().encode(deviceToken);
        const digest = await crypto.subtle.digest("SHA-256", material);
        return crypto.subtle.importKey("raw", digest, "AES-GCM", false, ["encrypt", "decrypt"]);
    }

    function readQueue() {
        try {
            const value = JSON.parse(localStorage.getItem(queueKey) || "[]");
            return Array.isArray(value) ? value : [];
        } catch (_) {
            return [];
        }
    }

    function writeQueue(queue) {
        localStorage.setItem(queueKey, JSON.stringify(queue));
        refreshQueueCount();
    }

    async function encryptEvent(event) {
        const key = await queueCryptoKey();
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const data = new TextEncoder().encode(JSON.stringify(event));
        const cipher = await crypto.subtle.encrypt({name: "AES-GCM", iv}, key, data);
        return {
            id: event.client_event_id,
            iv: arrayToBase64(iv),
            cipher: arrayToBase64(cipher),
        };
    }

    async function decryptEvent(record) {
        const key = await queueCryptoKey();
        const plain = await crypto.subtle.decrypt(
            {name: "AES-GCM", iv: base64ToArray(record.iv)},
            key,
            base64ToArray(record.cipher)
        );
        return JSON.parse(new TextDecoder().decode(plain));
    }

    async function enqueueOffline(event) {
        if (!bootstrap?.capabilities?.offline_queue) {
            throw new Error("Offline queue is disabled on this kiosk.");
        }
        const queue = readQueue();
        if (queue.some((item) => item.id === event.client_event_id)) {
            return;
        }
        queue.push(await encryptEvent(event));
        writeQueue(queue.slice(-250));
        message("Offline: event encrypted in the local sync queue.", "warning");
    }

    function refreshQueueCount() {
        if (state.queueCount) {
            state.queueCount.textContent = String(readQueue().length);
        }
    }

    async function syncOfflineQueue() {
        const queue = readQueue();
        if (!queue.length || !navigator.onLine || !deviceToken) {
            refreshQueueCount();
            return;
        }
        const batchSize = bootstrap?.policy?.sync_batch_size || 25;
        const selected = queue.slice(0, batchSize);
        const events = [];
        for (const record of selected) {
            try {
                events.push(await decryptEvent(record));
            } catch (_) {
                message(
                    "Some queued events cannot be decrypted with the current token. Restore the prior token or review the device queue.",
                    "danger"
                );
                return;
            }
        }
        const result = await rpc("/onehr/kiosk/api/sync", {
            device_code: deviceCode,
            device_token: deviceToken,
            events,
        });
        const processed = Number(result?.processed || 0);
        if (processed > 0) {
            writeQueue(queue.slice(processed));
            message(`${processed} offline event(s) handed to the governed server queue.`, "success");
        }
    }

    // ---------------------------------------------------------------------
    // Device and employee experience
    // ---------------------------------------------------------------------

    async function connectDevice() {
        const input = byId("kiosk-device-token");
        deviceToken = (input?.value || deviceToken || "").trim();
        if (!deviceToken) {
            message("Enter the device token.", "danger");
            return;
        }
        try {
            bootstrap = await rpc("/onehr/kiosk/api/bootstrap", {
                device_code: deviceCode,
                device_token: deviceToken,
                client_version: "onehr-kiosk-web-19.0.1",
            });
            sessionStorage.setItem(tokenKey, deviceToken);
            show(state.tokenPanel, false);
            show(state.workspace, true);
            byId("kiosk-scan-qr").disabled = !bootstrap.capabilities.qr;
            byId("kiosk-scan-nfc").disabled = !bootstrap.capabilities.nfc;
            show(state.timeoffCard, false);
            refreshQueueCount();
            setConnectivity();
            message("Device session verified.", "success");
            if (navigator.onLine) {
                await syncOfflineQueue();
            }
        } catch (error) {
            sessionStorage.removeItem(tokenKey);
            deviceToken = "";
            show(state.tokenPanel, true);
            show(state.workspace, false);
            message(error.message, "danger");
        }
    }

    function renderSnapshot(snapshot) {
        byId("kiosk-employee-name").textContent = snapshot.employee.name || "—";
        byId("kiosk-employee-number").textContent = snapshot.employee.employee_number || "—";
        byId("kiosk-attendance-status").textContent =
            snapshot.attendance.checked_in ? "Checked In" : "Checked Out";
        byId("kiosk-current-checkin").textContent = snapshot.attendance.check_in || "—";
        show(state.employeeCard, true);
        show(state.punchCard, true);

        const schedule = snapshot.schedule || {};
        byId("kiosk-shift-name").textContent = schedule.available ? schedule.shift : "No assigned shift";
        byId("kiosk-shift-start").textContent = schedule.planned_start || "—";
        byId("kiosk-shift-end").textContent = schedule.planned_end || "—";
        show(state.scheduleCard, true);

        const timeoff = snapshot.timeoff || {};
        if (bootstrap?.capabilities?.quick_timeoff && timeoff.available) {
            const select = byId("kiosk-leave-type");
            select.innerHTML = "";
            const strip = byId("kiosk-leave-balances");
            strip.innerHTML = "";
            (timeoff.balances || []).forEach((item) => {
                const option = document.createElement("option");
                option.value = item.code;
                option.textContent = `${item.name} (${item.balance})`;
                select.appendChild(option);

                const badge = document.createElement("span");
                badge.className = "kiosk-badge neutral";
                badge.textContent = `${item.code}: ${item.balance}`;
                strip.appendChild(badge);
            });
            show(state.timeoffCard, true);
        } else {
            show(state.timeoffCard, false);
        }
    }

    async function identifyEmployee() {
        currentIdentity = (state.identity.value || "").trim();
        if (!currentIdentity) {
            message("Scan or enter an employee identifier.", "danger");
            return;
        }
        if (!navigator.onLine) {
            message("Employee detail lookup needs connectivity. Attendance events can still be queued securely.", "warning");
            show(state.punchCard, true);
            return;
        }
        try {
            const snapshot = await rpc("/onehr/kiosk/api/identify", {
                device_code: deviceCode,
                device_token: deviceToken,
                identity: currentIdentity,
            });
            renderSnapshot(snapshot);
            message("Employee identified.", "success");
        } catch (error) {
            message(error.message, "danger");
            show(state.employeeCard, false);
            show(state.scheduleCard, false);
            show(state.punchCard, false);
            show(state.timeoffCard, false);
        }
    }

    async function buildEvent(eventType, extra = {}) {
        const geo = await positionEvidence();
        return Object.assign({
            event_type: eventType,
            identity: currentIdentity || (state.identity.value || "").trim(),
            credential_type: currentCredentialType,
            client_event_id: makeEventId(),
            event_at: serverDateTimeNow(),
        }, geo, extra);
    }

    async function submitPunch(mode) {
        currentIdentity = currentIdentity || (state.identity.value || "").trim();
        if (!currentIdentity) {
            message("Identify an employee before recording attendance.", "danger");
            return;
        }
        const event = await buildEvent("punch", {punch_mode: mode});
        if (!navigator.onLine) {
            try {
                await enqueueOffline(event);
            } catch (error) {
                message(error.message, "danger");
            }
            return;
        }
        try {
            const result = await rpc("/onehr/kiosk/api/punch", {
                device_code: deviceCode,
                device_token: deviceToken,
                payload: event,
            });
            const kind = result.state === "synced" ? "success" : result.state === "blocked" ? "danger" : "warning";
            message(result.message || `Attendance event: ${result.state}.`, kind);
            await identifyEmployee();
        } catch (error) {
            try {
                await enqueueOffline(event);
            } catch (_) {
                message(error.message, "danger");
            }
        }
    }

    async function submitTimeOff() {
        currentIdentity = currentIdentity || (state.identity.value || "").trim();
        if (!currentIdentity) {
            message("Identify an employee first.", "danger");
            return;
        }
        const leaveType = byId("kiosk-leave-type").value;
        const dateFrom = byId("kiosk-leave-from").value;
        const dateTo = byId("kiosk-leave-to").value || dateFrom;
        if (!leaveType || !dateFrom) {
            message("Leave Type and Start Date are required.", "danger");
            return;
        }
        const event = await buildEvent("timeoff", {
            leave_type_code: leaveType,
            date_from: dateFrom,
            date_to: dateTo,
            reason: byId("kiosk-leave-reason").value || "",
        });
        if (!navigator.onLine) {
            try {
                await enqueueOffline(event);
            } catch (error) {
                message(error.message, "danger");
            }
            return;
        }
        try {
            const result = await rpc("/onehr/kiosk/api/timeoff", {
                device_code: deviceCode,
                device_token: deviceToken,
                payload: event,
            });
            const kind = result.state === "synced" ? "success" : "warning";
            message(result.message || `Time Off request: ${result.state}.`, kind);
            if (result.state === "synced") {
                await identifyEmployee();
            }
        } catch (error) {
            try {
                await enqueueOffline(event);
            } catch (_) {
                message(error.message, "danger");
            }
        }
    }

    // ---------------------------------------------------------------------
    // QR / NFC capability
    // ---------------------------------------------------------------------

    async function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach((track) => track.stop());
            cameraStream = null;
        }
        show(byId("kiosk-camera"), false);
    }

    async function scanQr() {
        if (!("BarcodeDetector" in window)) {
            message("This browser does not support BarcodeDetector. Use a USB scanner or manual identifier.", "warning");
            return;
        }
        try {
            const detector = new BarcodeDetector({formats: ["qr_code", "code_128", "code_39"]});
            const video = byId("kiosk-camera");
            cameraStream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}});
            video.srcObject = cameraStream;
            await video.play();
            show(video, true);

            const detect = async () => {
                if (!cameraStream) return;
                const codes = await detector.detect(video);
                if (codes.length) {
                    state.identity.value = codes[0].rawValue || "";
                    currentIdentity = state.identity.value.trim();
                    currentCredentialType = "qr";
                    await stopCamera();
                    await identifyEmployee();
                    return;
                }
                requestAnimationFrame(detect);
            };
            detect();
        } catch (error) {
            await stopCamera();
            message(error.message || "QR scan failed.", "danger");
        }
    }

    async function scanNfc() {
        if (!("NDEFReader" in window)) {
            message("Web NFC is not available in this browser. Use QR or manual identifier.", "warning");
            return;
        }
        try {
            const reader = new NDEFReader();
            await reader.scan();
            message("NFC reader ready. Tap employee credential.", "info");
            reader.addEventListener("reading", async (event) => {
                for (const record of event.message.records) {
                    if (record.recordType === "text") {
                        const text = new TextDecoder(record.encoding || "utf-8").decode(record.data);
                        state.identity.value = text.trim();
                        currentIdentity = state.identity.value;
                        currentCredentialType = "nfc";
                        await identifyEmployee();
                        break;
                    }
                }
            }, {once: true});
        } catch (error) {
            message(error.message || "NFC scan failed.", "danger");
        }
    }

    // ---------------------------------------------------------------------
    // Wiring
    // ---------------------------------------------------------------------

    byId("kiosk-connect")?.addEventListener("click", connectDevice);
    byId("kiosk-identify")?.addEventListener("click", () => {
        currentCredentialType = "manual";
        identifyEmployee();
    });
    state.identity?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            currentCredentialType = "qr"; // USB barcode scanners normally terminate with Enter.
            identifyEmployee();
        }
    });
    byId("kiosk-checkin")?.addEventListener("click", () => submitPunch("check_in"));
    byId("kiosk-checkout")?.addEventListener("click", () => submitPunch("check_out"));
    byId("kiosk-autopunch")?.addEventListener("click", () => submitPunch("auto"));
    byId("kiosk-submit-timeoff")?.addEventListener("click", submitTimeOff);
    byId("kiosk-sync-now")?.addEventListener("click", () => syncOfflineQueue().catch((e) => message(e.message, "danger")));
    byId("kiosk-scan-qr")?.addEventListener("click", scanQr);
    byId("kiosk-scan-nfc")?.addEventListener("click", scanNfc);

    window.addEventListener("online", () => {
        setConnectivity();
        syncOfflineQueue().catch((error) => message(error.message, "danger"));
    });
    window.addEventListener("offline", setConnectivity);
    window.addEventListener("beforeunload", stopCamera);

    const today = new Date().toISOString().slice(0, 10);
    if (byId("kiosk-leave-from")) byId("kiosk-leave-from").value = today;
    if (byId("kiosk-leave-to")) byId("kiosk-leave-to").value = today;

    setInterval(() => {
        byId("kiosk-clock").textContent = new Date().toLocaleString();
    }, 1000);
    setConnectivity();
    refreshQueueCount();

    if (deviceToken) {
        connectDevice();
    }
})();
