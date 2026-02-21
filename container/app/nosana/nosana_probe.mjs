/**
 * CoreLink Nosana Probe
 *
 * Discovers Nosana containers via Docker socket, extracts wallet addresses,
 * and queries Solana blockchain for node status via @nosana/kit.
 *
 * Output: single JSON object to stdout.  Always exits 0.
 */

import http from "node:http";
import { createNosanaClient, NosanaNetwork, MarketQueueType } from "@nosana/kit";
import { createKeyPairSignerFromBytes } from "@solana/kit";

const DOCKER_SOCK = "/var/run/docker.sock";

// ---------------------------------------------------------------------------
// Docker socket helpers
// ---------------------------------------------------------------------------

function dockerGet(path) {
    return new Promise((resolve, reject) => {
        const req = http.request(
            { socketPath: DOCKER_SOCK, path, method: "GET" },
            (res) => {
                const chunks = [];
                res.on("data", (c) => chunks.push(c));
                res.on("end", () => {
                    const body = Buffer.concat(chunks);
                    resolve({ status: res.statusCode, body });
                });
            }
        );
        req.on("error", reject);
        req.setTimeout(10000, () => { req.destroy(); reject(new Error("timeout")); });
        req.end();
    });
}

async function listNosanaContainers() {
    const res = await dockerGet("/containers/json");
    if (res.status !== 200) return [];
    const containers = JSON.parse(res.body.toString());
    return containers.filter(
        (c) => c.Image && c.Image.toLowerCase().includes("nosana")
    );
}

/**
 * Extract a file from a container via the Docker archive API.
 * Returns the file contents as a Buffer, or null on failure.
 *
 * The archive API returns a tar stream.  For a single small file we do
 * minimal tar parsing: 512-byte header, size at offset 124 (octal ASCII),
 * then file data starting at byte 512.
 */
async function extractFileFromContainer(containerId, filePath) {
    const res = await dockerGet(
        `/containers/${containerId}/archive?path=${encodeURIComponent(filePath)}`
    );
    if (res.status !== 200) return null;

    const tar = res.body;
    if (tar.length < 512) return null;

    // Parse file size from tar header (offset 124, 12 bytes, octal ASCII)
    const sizeStr = tar.subarray(124, 136).toString().replace(/\0/g, "").trim();
    const size = parseInt(sizeStr, 8);
    if (isNaN(size) || size <= 0 || 512 + size > tar.length) return null;

    return tar.subarray(512, 512 + size);
}

async function getWalletAddress(containerId) {
    const buf = await extractFileFromContainer(
        containerId,
        "/root/.nosana/nosana_key.json"
    );
    if (!buf) return null;

    const keyArray = JSON.parse(buf.toString());
    if (!Array.isArray(keyArray) || keyArray.length !== 64) return null;

    const signer = await createKeyPairSignerFromBytes(new Uint8Array(keyArray));
    return signer.address;
}

// ---------------------------------------------------------------------------
// Blockchain queries
// ---------------------------------------------------------------------------

async function queryNodeStatus(client, walletAddress, allMarkets) {
    const result = {
        wallet: walletAddress,
        status: "idle",
        market: null,
        queue_position: null,
        queue_length: null,
        job: null,
        duration: null,
        max_duration: null,
    };

    // Build market lookup by address for jobTimeout
    const marketByAddr = {};
    for (const m of allMarkets) {
        marketByAddr[m.address] = m;
    }

    // Check queue position across all markets (always, regardless of status)
    try {
        for (const market of allMarkets) {
            if (market.queueType === MarketQueueType.NODE_QUEUE) {
                const idx = market.queue.indexOf(walletAddress);
                if (idx !== -1) {
                    result.status = "queued";
                    result.market = market.address || null;
                    result.max_duration = market.jobTimeout || null;
                    result.queue_position = idx + 1;
                    result.queue_length = market.queue.length;
                    break;
                }
            }
        }
    } catch (err) {
        // Non-fatal — continue to check runs
    }

    // Check active runs
    try {
        const runs = await client.jobs.runs({ node: walletAddress });
        if (runs.length > 0) {
            result.status = "running";
            result.job = runs[0].job || null;
            result.queue_position = null;
            result.queue_length = null;

            // Calculate elapsed duration from run start time
            if (runs[0].time) {
                const startSec = Number(runs[0].time);
                result.duration = Math.floor(Date.now() / 1000) - startSec;
            }

            // Get market from job to find max_duration
            try {
                const job = await client.jobs.get(runs[0].job);
                if (job && job.market) {
                    result.market = job.market;
                    const mkt = marketByAddr[job.market];
                    if (mkt) {
                        result.max_duration = mkt.jobTimeout || null;
                    }
                }
            } catch (e) {
                // Non-fatal
            }
        }
    } catch (err) {
        if (result.status === "idle") {
            result.status = "error";
            result.error = "runs query failed: " + err.message;
        }
    }

    return result;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
    const output = { nodes: [], error: null };

    let containers;
    try {
        containers = await listNosanaContainers();
    } catch (err) {
        output.error = "Docker socket unavailable: " + err.message;
        process.stdout.write(JSON.stringify(output));
        return;
    }

    if (containers.length === 0) {
        process.stdout.write(JSON.stringify(output));
        return;
    }

    // Create read-only Nosana client
    let client;
    try {
        client = createNosanaClient(NosanaNetwork.MAINNET);
    } catch (err) {
        output.error = "Failed to create Nosana client: " + err.message;
        process.stdout.write(JSON.stringify(output));
        return;
    }

    // Fetch markets once (shared across all nodes)
    let markets = [];
    try {
        markets = await client.jobs.markets();
    } catch (err) {
        // Non-fatal — queue position will be unavailable
    }

    // Fetch market names from REST API (address → human-readable name)
    let marketNames = {};
    try {
        const marketList = await client.api.markets.list();
        for (const m of marketList) {
            marketNames[m.address] = m.name || m.slug || m.address;
        }
    } catch (err) {
        // Non-fatal — will fall back to truncated address
    }

    // Process each container independently
    for (const container of containers) {
        const name = (container.Names && container.Names[0] || "").replace(/^\//, "");
        const node = {
            container: name || container.Id.substring(0, 12),
            wallet: null,
            status: "unknown",
            market: null,
            queue_position: null,
            queue_length: null,
            job: null,
            error: null,
        };

        try {
            const wallet = await getWalletAddress(container.Id);
            if (!wallet) {
                node.error = "Could not extract wallet key";
                output.nodes.push(node);
                continue;
            }
            node.wallet = wallet;

            const status = await queryNodeStatus(client, wallet, markets);
            Object.assign(node, status);
            if (node.market && marketNames[node.market]) {
                node.market_name = marketNames[node.market];
            }
        } catch (err) {
            node.error = err.message;
        }

        output.nodes.push(node);
    }

    process.stdout.write(JSON.stringify(output));
}

main().catch((err) => {
    process.stdout.write(JSON.stringify({ nodes: [], error: err.message }));
    process.exit(0);
});
