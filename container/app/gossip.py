"""CoreLink - Gossip protocol for GPU cluster state sharing.

Uses UDP multicast heartbeats for fast dissemination and anti-entropy
digest exchanges for guaranteed convergence across up to 254 nodes on
a single subnet.
"""

import json
import random
import select
import socket
import struct
import threading
import time

MULTICAST_GROUP = "239.77.77.77"
HEARTBEAT_INTERVAL = 5.0       # seconds between heartbeats
HEARTBEAT_JITTER = 1.5         # +/- random jitter
NODE_TIMEOUT = 20.0            # seconds before marking a node stale
NODE_REMOVE = 60.0             # seconds before removing a node
ANTI_ENTROPY_INTERVAL = 10.0   # seconds between anti-entropy rounds
TTL = 1                        # multicast TTL (LAN only)


class GossipNode:
    """Manages cluster membership and state via gossip protocol."""

    def __init__(self, hostname, local_gpu_info, port=47100,
                 link_speed=0, link_speed_max=0):
        self.hostname = hostname
        self.local_gpu_info = local_gpu_info
        self.port = port
        self.anti_entropy_port = port + 1  # 47101

        self.seq = 0
        self._lock = threading.Lock()
        self._cluster = {}  # {node_id: {gpus, timestamp, seq, last_seen, ip, net_kbps, ...}}
        self._net_kbps = 0.0  # local node's AppComm rate, set by server push loop
        self._link_speed = link_speed
        self._link_speed_max = link_speed_max

        self._mcast_send_sock = None
        self._mcast_recv_sock = None
        self._unicast_sock = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start all gossip threads (call once)."""
        self._running = True
        self._setup_sockets()

        for target in (
            self._heartbeat_loop,
            self._receive_loop,
            self._anti_entropy_loop,
            self._reaper_loop,
        ):
            t = threading.Thread(target=target, daemon=True)
            t.start()

    def stop(self):
        self._running = False

    def set_net_kbps(self, value):
        """Update the local node's network throughput (Kbps) for gossip."""
        self._net_kbps = value

    def get_cluster_state(self):
        """Return the current cluster state for the web UI.

        Returns a list of node dicts sorted by hostname, with self first.
        Each GPU is kept inside its node dict so the frontend can expand
        rows per GPU.
        """
        now = time.time()
        nodes = []

        # Self always first
        nodes.append({
            "node_id": self.hostname,
            "gpus": self.local_gpu_info,
            "timestamp": time.strftime("%d%b%y %H:%M:%S").upper() + "utc",
            "status": "online",
            "net_kbps": self._net_kbps,
            "epoch": time.time(),
            "link_speed": self._link_speed,
            "link_speed_max": self._link_speed_max,
        })

        with self._lock:
            for nid in sorted(self._cluster.keys()):
                if nid == self.hostname:
                    continue
                info = self._cluster[nid]
                age = now - info["last_seen"]
                if age < NODE_TIMEOUT:
                    status = "online"
                else:
                    status = "stale"
                nodes.append({
                    "node_id": nid,
                    "gpus": info["gpus"],
                    "timestamp": info["timestamp"],
                    "status": status,
                    "net_kbps": info.get("net_kbps", 0.0),
                    "epoch": info.get("epoch", 0),
                    "link_speed": info.get("link_speed", 0),
                    "link_speed_max": info.get("link_speed_max", 0),
                })

        return nodes

    # ------------------------------------------------------------------
    # Socket setup
    # ------------------------------------------------------------------

    def _setup_sockets(self):
        # Multicast sender
        self._mcast_send_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP,
        )
        self._mcast_send_sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL,
        )

        # Multicast receiver
        self._mcast_recv_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP,
        )
        self._mcast_recv_sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,
        )
        self._mcast_recv_sock.bind(("", self.port))
        mreq = struct.pack(
            "4sL", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY,
        )
        self._mcast_recv_sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq,
        )

        # Unicast socket for anti-entropy responses
        self._unicast_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP,
        )
        self._unicast_sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,
        )
        self._unicast_sock.bind(("", self.anti_entropy_port))

    # ------------------------------------------------------------------
    # Heartbeat — periodic multicast announcement
    # ------------------------------------------------------------------

    def _heartbeat_loop(self):
        while self._running:
            self.seq += 1
            msg = {
                "type": "heartbeat",
                "node_id": self.hostname,
                "gpus": self.local_gpu_info,
                "timestamp": time.strftime("%d%b%y %H:%M:%S").upper() + "utc",
                "seq": self.seq,
                "net_kbps": self._net_kbps,
                "epoch": time.time(),
                "link_speed": self._link_speed,
                "link_speed_max": self._link_speed_max,
            }
            try:
                data = json.dumps(msg).encode("utf-8")
                self._mcast_send_sock.sendto(
                    data, (MULTICAST_GROUP, self.port),
                )
            except Exception:
                pass

            jitter = random.uniform(-HEARTBEAT_JITTER, HEARTBEAT_JITTER)
            time.sleep(max(1.0, HEARTBEAT_INTERVAL + jitter))

    # ------------------------------------------------------------------
    # Receive loop — listen on multicast + unicast
    # ------------------------------------------------------------------

    def _receive_loop(self):
        sockets = [self._mcast_recv_sock, self._unicast_sock]
        while self._running:
            try:
                readable, _, _ = select.select(sockets, [], [], 1.0)
            except Exception:
                continue

            for sock in readable:
                try:
                    data, addr = sock.recvfrom(65535)
                    msg = json.loads(data.decode("utf-8"))
                    self._handle_message(msg, addr)
                except Exception:
                    pass

    def _handle_message(self, msg, addr):
        msg_type = msg.get("type")
        if msg_type == "heartbeat":
            self._process_heartbeat(msg, addr)
        elif msg_type == "digest_req":
            self._process_digest_request(msg, addr)
        elif msg_type == "digest_resp":
            self._process_digest_response(msg)

    # ------------------------------------------------------------------
    # Heartbeat processing
    # ------------------------------------------------------------------

    def _process_heartbeat(self, msg, addr=None):
        node_id = msg.get("node_id")
        if not node_id or node_id == self.hostname:
            return

        seq = msg.get("seq", 0)
        with self._lock:
            existing = self._cluster.get(node_id)
            if existing is None or seq > existing.get("seq", 0):
                self._cluster[node_id] = {
                    "gpus": msg.get("gpus", []),
                    "timestamp": msg.get("timestamp", ""),
                    "seq": seq,
                    "last_seen": time.time(),
                    "ip": addr[0] if addr else "",
                    "net_kbps": msg.get("net_kbps", 0.0),
                    "epoch": msg.get("epoch", 0),
                    "link_speed": msg.get("link_speed", 0),
                    "link_speed_max": msg.get("link_speed_max", 0),
                }

    # ------------------------------------------------------------------
    # Anti-entropy — digest-based state synchronization
    # ------------------------------------------------------------------

    def _anti_entropy_loop(self):
        while self._running:
            sleep = ANTI_ENTROPY_INTERVAL + random.uniform(-2.0, 2.0)
            time.sleep(max(2.0, sleep))

            with self._lock:
                peer_ids = [
                    nid for nid in self._cluster if nid != self.hostname
                ]
            if not peer_ids:
                continue

            target_id = random.choice(peer_ids)

            # Build digest: {node_id: seq}
            with self._lock:
                digest = {
                    nid: info["seq"] for nid, info in self._cluster.items()
                }
            digest[self.hostname] = self.seq

            msg = {
                "type": "digest_req",
                "node_id": self.hostname,
                "target": target_id,
                "digest": digest,
            }

            try:
                data = json.dumps(msg).encode("utf-8")
                self._mcast_send_sock.sendto(
                    data, (MULTICAST_GROUP, self.port),
                )
            except Exception:
                pass

    def _process_digest_request(self, msg, addr):
        """Respond only if we are the target."""
        if msg.get("target") != self.hostname:
            return

        their_digest = msg.get("digest", {})
        updates = []

        with self._lock:
            for nid, info in self._cluster.items():
                if info["seq"] > their_digest.get(nid, 0):
                    updates.append({
                        "node_id": nid,
                        "gpus": info["gpus"],
                        "timestamp": info["timestamp"],
                        "seq": info["seq"],
                        "net_kbps": info.get("net_kbps", 0.0),
                        "epoch": info.get("epoch", 0),
                        "link_speed": info.get("link_speed", 0),
                        "link_speed_max": info.get("link_speed_max", 0),
                    })

        # Include self if the requester is behind
        if self.seq > their_digest.get(self.hostname, 0):
            updates.append({
                "node_id": self.hostname,
                "gpus": self.local_gpu_info,
                "timestamp": time.strftime("%d%b%y %H:%M:%S").upper() + "utc",
                "seq": self.seq,
                "net_kbps": self._net_kbps,
                "epoch": time.time(),
                "link_speed": self._link_speed,
                "link_speed_max": self._link_speed_max,
            })

        if updates:
            resp = {
                "type": "digest_resp",
                "node_id": self.hostname,
                "updates": updates,
            }
            try:
                data = json.dumps(resp).encode("utf-8")
                self._unicast_sock.sendto(
                    data, (addr[0], self.anti_entropy_port),
                )
            except Exception:
                pass

    def _process_digest_response(self, msg):
        for update in msg.get("updates", []):
            self._process_heartbeat(update)

    # ------------------------------------------------------------------
    # Reaper — remove nodes that have gone silent
    # ------------------------------------------------------------------

    def _reaper_loop(self):
        while self._running:
            time.sleep(5)
            now = time.time()
            with self._lock:
                stale = [
                    nid for nid, info in self._cluster.items()
                    if now - info["last_seen"] > NODE_REMOVE
                ]
                for nid in stale:
                    del self._cluster[nid]
