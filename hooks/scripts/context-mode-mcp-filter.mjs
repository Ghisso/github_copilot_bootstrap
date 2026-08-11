#!/usr/bin/env node
import { spawn } from "node:child_process";
import { lstatSync, realpathSync } from "node:fs";
import path from "node:path";

const PINNED_VERSION = "1.0.169";
const ALLOWED_TOOLS = new Set(["ctx_index", "ctx_search", "ctx_stats", "ctx_doctor"]);
const INDEX_ARGS = new Set(["content", "path", "source"]);
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
const initializeIds = new Set();
const listIds = new Set();
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

function handleClient(message, raw) {
  if (!message || typeof message !== "object") return;
  const key = idKey(message.id);
  if (message.method === "initialize" && Object.hasOwn(message, "id")) {
    initializeIds.add(key);
  }
  if (message.method === "tools/list" && Object.hasOwn(message, "id")) {
    if (!versionAccepted) {
      send(process.stdout, errorResponse(message.id, -32001, "pinned Context Mode runtime is not initialized"));
      return;
    }
    listIds.add(key);
  }
  if (message.method === "tools/call" && Object.hasOwn(message, "id")) {
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
  if (listIds.delete(key) && Array.isArray(message.result?.tools)) {
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
process.stdin.on("end", () => upstream.stdin.end());
