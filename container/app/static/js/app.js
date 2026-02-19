/* CoreLink - Frontend application */

(function () {
    "use strict";

    // ---- Socket.IO connection (prefer WebSocket) ----
    var socket = io({transports: ["websocket", "polling"]});

    var tbody        = document.getElementById("gpu-table-body");
    var nodeCount    = document.getElementById("node-count");
    var connBadge    = document.getElementById("connection-status");
    var appMonitor   = document.getElementById("app-monitor");

    // ---- Connection status ----

    socket.on("connect", function () {
        if (connBadge) {
            connBadge.textContent = "connected";
            connBadge.className = "badge bg-success-subtle";
        }
    });

    socket.on("disconnect", function () {
        if (connBadge) {
            connBadge.textContent = "disconnected";
            connBadge.className = "badge bg-danger-subtle";
        }
    });

    // ---- Cluster state updates ----

    socket.on("cluster_state", function (data) {
        var nodes = data.nodes || [];
        var mon   = data.monitor || {};

        // Update monitor line
        if (appMonitor) {
            var cpu  = mon.cpu  != null ? mon.cpu  : "\u2014";
            var ram  = mon.ram  != null ? mon.ram  : "\u2014";
            var net  = mon.net_mbps != null ? mon.net_mbps : "\u2014";
            var link = mon.link_speed ? mon.link_speed : "\u2014";
            var disk = mon.disk != null ? mon.disk : "\u2014";
            appMonitor.textContent = "CPU: " + cpu + "%\u2002 RAM: " + ram
                + "%\u2002 Net: " + net + " / " + link
                + " Mbps\u2002 Disk: " + disk + "%";
        }

        if (!tbody) return;

        // Count online nodes
        var onlineNodes = 0;
        for (var i = 0; i < nodes.length; i++) {
            if (nodes[i].status === "online") onlineNodes++;
        }
        if (nodeCount) nodeCount.textContent = onlineNodes;

        // Rebuild table rows
        var html = "";
        for (var n = 0; n < nodes.length; n++) {
            var node = nodes[n];
            var gpus = node.gpus || [];
            var rowClass = node.status === "stale" ? "node-stale" : "node-online";

            if (gpus.length === 0) {
                // Node with no GPUs (shouldn't happen but handle gracefully)
                html += "<tr class=\"" + rowClass + "\">"
                      + "<td>" + esc(node.node_id) + "</td>"
                      + "<td>—</td>"
                      + "<td>—</td>"
                      + "<td>" + esc(node.timestamp) + "</td>"
                      + "</tr>";
            } else {
                for (var g = 0; g < gpus.length; g++) {
                    html += "<tr class=\"" + rowClass + "\">"
                          + "<td>" + esc(node.node_id) + "</td>"
                          + "<td>" + gpus[g].id + "</td>"
                          + "<td>" + esc(gpus[g].model) + "</td>"
                          + "<td>" + esc(node.timestamp) + "</td>"
                          + "</tr>";
                }
            }
        }

        if (html === "") {
            html = "<tr><td colspan=\"4\" class=\"text-center text-muted\">"
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

    // ---- Framework for future command buttons ----
    // Command buttons can be wired via a Socket.IO event:
    //   socket.on("available_commands", function (cmds) { ... });
    //   socket.emit("execute_command", {command: cmdId});

})();
