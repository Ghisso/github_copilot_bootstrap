#!/usr/bin/env node
import { spawn } from "node:child_process";
import { lstatSync, realpathSync } from "node:fs";
import path from "node:path";

const PINNED_VERSION = "1.0.169";
const ALLOWED_TOOLS = new Set(["ctx_index", "ctx_search", "ctx_stats", "ctx_doctor"]);
const INDEX_ARGS = new Set(["content", "path", "source"]);
const MAX_SOURCE_LENGTH = 200;
const MAX_PENDING_LIST_IDS = 256;
const argv = process.argv.slice(2);
const separator = argv.indexOf("--");
if (separator < 0 || separator === argv.length - 1) {
  process.stderr.write("context-mode-filter: missing upstream command\n");
  process.exit(64);
}

const repoRoot = realpathSync(process.env.CONTEXT_MODE_PROJECT_ROOT || process.cwd());
const upstream = spawn(argv[separator + 1], argv.slice(separator + 2), {
  env: process.env,
  stdio: ["pipe", "pipe", "pipe"],
});
// A killed/exited upstream (e.g. after a pinned-version mismatch) leaves a
// broken pipe. Any method not gated on `versionAccepted` still reaches
// `upstream.stdin.write` below; without this handler the resulting EPIPE is
// unhandled and crashes the filter instead of failing closed (MINOR 8).
upstream.stdin.on("error", () => {});
const initializeIds = new Set();
// Counts, not a Set: two requests that reuse the same id must each be
// filtered on their own matching response, or the second response would be
// written through raw and leak the unfiltered tool list (MAJOR 3).
const listIds = new Map();
let versionAccepted = false;

function idKey(id) {
  return JSON.stringify(id);
}

function send(stream, message) {
  stream.write(`${JSON.stringify(message)}\n`);
}

function errorResponse(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

function isContained(candidate) {
  return candidate === repoRoot || candidate.startsWith(`${repoRoot}${path.sep}`);
}

function validateIndex(args) {
  const input = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  const extra = Object.keys(input).find((key) => !INDEX_ARGS.has(key));
  if (extra) return `ctx_index argument ${extra} is not allowed by repository policy`;
  if (
    Object.hasOwn(input, "source") &&
    (typeof input.source !== "string" || input.source.length > MAX_SOURCE_LENGTH)
  ) {
    return `ctx_index source must be a string of at most ${MAX_SOURCE_LENGTH} characters`;
  }
  const hasContent = typeof input.content === "string";
  const hasPath = typeof input.path === "string" && input.path.length > 0;
  if (hasContent === hasPath) {
    return "ctx_index requires exactly one of content or path";
  }
  if (hasContent) return null;
  if (input.path.split(/[\\/]/).includes("..")) {
    return "ctx_index path traversal is not allowed";
  }
  const resolved = path.resolve(repoRoot, input.path);
  let canonical;
  let stat;
  try {
    stat = lstatSync(resolved);
    canonical = realpathSync(resolved);
  } catch {
    return "ctx_index path must exist and be readable";
  }
  if (stat.isSymbolicLink()) return "ctx_index path must not be a symbolic link";
  if (!isContained(canonical)) return "ctx_index path must remain inside the repository";
  if (stat.isDirectory()) {
    return "ctx_index directory input is temporarily disabled; provide content or one regular file";
  }
  if (!stat.isFile()) return "ctx_index path must be a regular file";
  return null;
}

// Default-deny: only a single JSON-RPC object is ever a candidate for
// forwarding. A batch array (CRITICAL 1b) or any other non-object shape is
// dropped before any method/id is inspected.
function handleClient(message, raw) {
  if (!message || typeof message !== "object" || Array.isArray(message)) {
    process.stderr.write("context-mode-filter: dropped a non-object/array client message\n");
    return;
  }
  const hasId = Object.hasOwn(message, "id");
  const key = idKey(message.id);
  if (message.method === "initialize" && hasId) {
    initializeIds.add(key);
  }
  // The allowlist, version gate, and ctx_index validation below gate on
  // `method` alone (CRITICAL 1a). A notification-shaped tools/list or
  // tools/call (no `id`) has nobody to answer, so it is dropped rather than
  // forwarded, instead of falling through unchecked to the upstream write.
  if (message.method === "tools/list") {
    if (!hasId) {
      process.stderr.write("context-mode-filter: dropped a tools/list notification\n");
      return;
    }
    if (!versionAccepted) {
      send(process.stdout, errorResponse(message.id, -32001, "pinned Context Mode runtime is not initialized"));
      return;
    }
    // An id whose response is never list-shaped never decrements, so the map
    // needs a bound. Refuse new ids at capacity instead of evicting a tracked
    // one: evicting would untrack a genuinely pending tools/list, and its later
    // response would then be written through unfiltered. Reused ids only
    // increment an existing entry, so they never grow the map.
    if (listIds.size >= MAX_PENDING_LIST_IDS && !listIds.has(key)) {
      send(process.stdout, errorResponse(message.id, -32000, "too many pending tools/list requests"));
      return;
    }
    listIds.set(key, (listIds.get(key) || 0) + 1);
  }
  if (message.method === "tools/call") {
    if (!hasId) {
      process.stderr.write("context-mode-filter: dropped a tools/call notification\n");
      return;
    }
    if (!versionAccepted) {
      send(process.stdout, errorResponse(message.id, -32001, "pinned Context Mode runtime is not initialized"));
      return;
    }
    const name = message.params?.name;
    if (!ALLOWED_TOOLS.has(name)) {
      send(process.stdout, errorResponse(message.id, -32601, "Context Mode tool is not allowed by repository policy"));
      return;
    }
    if (name === "ctx_index") {
      const problem = validateIndex(message.params?.arguments);
      if (problem) {
        send(process.stdout, errorResponse(message.id, -32602, problem));
        return;
      }
    }
  }
  upstream.stdin.write(raw);
}

function handleUpstream(message, raw) {
  if (!message || typeof message !== "object") return;
  const key = idKey(message.id);
  if (initializeIds.delete(key)) {
    const version = message.result?.serverInfo?.version;
    if (version !== PINNED_VERSION) {
      send(process.stdout, errorResponse(message.id, -32002, `Context Mode ${PINNED_VERSION} required`));
      upstream.kill();
      return;
    }
    versionAccepted = true;
  }
  // Decrement/delete the pending count only once a response is structurally
  // confirmed to be the actual tools/list result. A client may reuse one id
  // across a pending tools/list and another concurrently outstanding
  // request (e.g. a tools/call); if that other response arrives first it
  // must not consume the counter, or the later genuine tools/list response
  // would find nothing pending and fall through unfiltered (MAJOR 5). N
  // requests that reused one id each still get their own filtered response
  // because the count, not a one-shot Set entry, is decremented per match
  // (MAJOR 3).
  const pendingListResponses = listIds.get(key);
  if (pendingListResponses && Array.isArray(message.result?.tools)) {
    if (pendingListResponses <= 1) {
      listIds.delete(key);
    } else {
      listIds.set(key, pendingListResponses - 1);
    }
    message.result.tools = message.result.tools.filter((tool) => ALLOWED_TOOLS.has(tool?.name));
    send(process.stdout, message);
    return;
  }
  process.stdout.write(raw);
}

function linePump(stream, handler) {
  let buffer = "";
  stream.setEncoding("utf8");
  stream.on("data", (chunk) => {
    buffer += chunk;
    for (;;) {
      const newline = buffer.indexOf("\n");
      if (newline < 0) break;
      const raw = buffer.slice(0, newline + 1);
      buffer = buffer.slice(newline + 1);
      const text = raw.trim();
      if (!text) continue;
      try {
        handler(JSON.parse(text), raw);
      } catch {
        process.stderr.write("context-mode-filter: invalid JSON-RPC message\n");
        process.exitCode = 1;
        upstream.kill();
        return;
      }
    }
  });
}

linePump(process.stdin, handleClient);
linePump(upstream.stdout, handleUpstream);
upstream.stderr.pipe(process.stderr);
upstream.on("error", () => {
  process.stderr.write("context-mode-filter: pinned upstream failed to start\n");
  process.exitCode = 127;
});
upstream.on("exit", (code, signal) => {
  if (process.exitCode === undefined) process.exitCode = signal ? 1 : (code ?? 1);
});
// "close" rather than "exit": exit can fire while upstream.stdout still has
// buffered data to deliver, and ending our stdout early would drop an
// already-valid filtered response. The swallowed stdin EPIPE keeps this process
// alive after upstream dies, so closing stdout here gives the client an
// immediate EOF instead of waiting forever for a response that cannot arrive.
upstream.on("close", () => process.stdout.end());
process.stdout.on("error", () => {});
process.stdin.on("end", () => upstream.stdin.end());

// Terminate the spawned upstream deterministically on every exit path
// instead of relying on it noticing a closed stdin (MINOR 7).
process.on("exit", () => upstream.kill());
for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => {
    upstream.kill();
    process.exit(0);
  });
}
