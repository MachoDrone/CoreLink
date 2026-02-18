/* CoreLink - Frontend application */

(function () {
    "use strict";

    // ---- Socket.IO connection (prefer WebSocket) ----
    var socket = io({transports: ["websocket", "polling"]});

    var tbody        = document.getElementById("gpu-table-body");
    var nodeCount    = document.getElementById("node-count");
    var connBadge    = document.getElementById("connection-status");

    // ---- Connection status ----

    socket.on("connect", function () {
        if (connBadge) {
            connBadge.textContent = "connected";
            connBadge.className = "badge bg-success-subtle small";
        }
    });

    socket.on("disconnect", function () {
        if (connBadge) {
            connBadge.textContent = "disconnected";
            connBadge.className = "badge bg-danger-subtle small";
        }
    });

    // ---- Cluster state updates ----

    socket.on("cluster_state", function (nodes) {
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
                          + "<td>GPU" + gpus[g].id + "</td>"
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
