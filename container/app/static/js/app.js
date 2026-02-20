/* CoreLink - Frontend application */

(function () {
    "use strict";

    // ---- Initialize Bootstrap tooltips ----
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });

    // ---- Socket.IO connection (prefer WebSocket) ----
    var socket = io({transports: ["websocket", "polling"]});

    var tbody        = document.getElementById("gpu-table-body");
    var nodeCount    = document.getElementById("node-count");
    var connBadge    = document.getElementById("connection-status");
    var appMonitor   = document.getElementById("app-monitor");

    var badgeHostname = connBadge ? (connBadge.getAttribute("data-hostname") || "") : "";

    // ---- Connection status ----

    socket.on("connect", function () {
        if (connBadge) {
            connBadge.textContent = badgeHostname + " connected";
            connBadge.className = "badge bg-success-subtle";
        }
    });

    socket.on("disconnect", function () {
        if (connBadge) {
            connBadge.textContent = badgeHostname + " disconnected";
            connBadge.className = "badge bg-danger-subtle";
        }
    });

    // ---- Cluster state updates ----

    socket.on("cluster_state", function (data) {
        var nodes = data.nodes || [];
        var mon   = data.monitor || {};

        if (!tbody) return;

        // Count online nodes and sum LAN traffic
        var onlineNodes = 0;
        var totalKbps = 0;
        for (var i = 0; i < nodes.length; i++) {
            if (nodes[i].status === "online") {
                onlineNodes++;
                totalKbps += (nodes[i].net_kbps || 0);
            }
        }
        if (nodeCount) {
            var pcLabel = onlineNodes === 1 ? "PC" : "PCs";
            var hosts = 0;
            var hostLabel = hosts === 1 ? "Host" : "Hosts";
            nodeCount.textContent = onlineNodes + " " + pcLabel + ", " + hosts + " " + hostLabel;
        }

        // Update CoreLink Resources line
        if (appMonitor) {
            var cpu  = mon.cpu  != null ? Number(mon.cpu).toFixed(2)  : "\u2014";
            var ram  = mon.ram  != null ? Number(mon.ram).toFixed(2)  : "\u2014";
            var disk = mon.disk != null ? Number(mon.disk).toFixed(2) : "\u2014";
            var lanMbps = (totalKbps / 1000).toFixed(3);
            appMonitor.textContent = "CoreLink Resources \u2014 CPU: " + cpu
                + "%\u2002 RAM: " + ram + "%\u2002 Disk: " + disk
                + "%\u2002 LAN Saturation: " + lanMbps + " Mbps";
        }

        // Rebuild table rows
        var html = "";
        for (var n = 0; n < nodes.length; n++) {
            var node = nodes[n];
            var gpus = node.gpus || [];
            var rowClass = node.status === "stale" ? "node-stale" : "node-online";

            var netDisplay = (node.net_kbps != null) ? Number(node.net_kbps).toFixed(2) + " Kbps" : "0.00 Kbps";
            var nicLabel = fmtNicSpeed(node.link_speed);
            var nicColor = nicSpeedClass(node.link_speed, node.link_speed_max);
            var nicHtml = "<span style=\"" + nicColor + "\">" + nicLabel + "</span>";
            var tsIndicator = timeSyncIndicator(node.ntp_drift);

            if (gpus.length === 0) {
                // Node with no GPUs (shouldn't happen but handle gracefully)
                html += "<tr class=\"" + rowClass + "\">"
                      + "<td>" + esc(node.node_id) + "</td>"
                      + "<td>\u2014</td>"
                      + "<td>\u2014</td>"
                      + "<td>" + nicHtml + "</td>"
                      + "<td>\u2014</td>"
                      + "<td>" + esc(node.timestamp) + tsIndicator + "</td>"
                      + "<td>" + netDisplay + "</td>"
                      + "</tr>";
            } else {
                for (var g = 0; g < gpus.length; g++) {
                    html += "<tr class=\"" + rowClass + "\">"
                          + "<td>" + esc(node.node_id) + "</td>"
                          + "<td>" + gpus[g].id + "</td>"
                          + "<td>" + esc(gpus[g].limit || "0.0 x 0") + "</td>"
                          + "<td>" + (g === 0 ? nicHtml : "---") + "</td>"
                          + "<td>" + esc(gpus[g].model) + "</td>"
                          + "<td>" + esc(node.timestamp) + tsIndicator + "</td>"
                          + "<td>" + (g === 0 ? netDisplay : "---") + "</td>"
                          + "</tr>";
                }
            }
        }

        if (html === "") {
            html = "<tr><td colspan=\"7\" class=\"text-center text-muted\">"
                 + "No nodes detected yet...</td></tr>";
        }

        tbody.innerHTML = html;
    });

    // ---- Helpers ----

    function esc(str) {
        if (str == null) return "";
        var d = document.createElement("div");
        d.appendChild(document.createTextNode(String(str)));
        return d.innerHTML;
    }

    function fmtNicSpeed(mbps) {
        if (!mbps || mbps === 0) return "?";
        if (mbps < 1000) return mbps + "M";
        return (mbps / 1000).toFixed(1).replace(/\.0$/, "") + "G";
    }

    function nicSpeedClass(speed, maxSpeed) {
        if (!speed || speed <= 0) return "";
        if (speed <= 1000) return "color: var(--cl-danger)";
        if (maxSpeed && speed < maxSpeed) return "color: var(--cl-warning)";
        return "color: var(--cl-success)";
    }

    function timeSyncIndicator(ntp_drift) {
        if (ntp_drift == null) return "";
        if (Math.abs(ntp_drift) <= 5) {
            return " <span style=\"color:var(--cl-success)\">\u2713</span>";
        }
        return " <span style=\"color:var(--cl-danger)\">\u2717</span>";
    }

    // ---- Framework for future command buttons ----
    // Command buttons can be wired via a Socket.IO event:
    //   socket.on("available_commands", function (cmds) { ... });
    //   socket.emit("execute_command", {command: cmdId});

})();
