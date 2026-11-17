// Offline probe of the Copilot runtime that ships with VS Code. Started by
// scripts/check_copilot_runtime.py; run it through that script.
//
// It starts the runtime through its own SDK with a private data folder and no
// login. The model is a small server on 127.0.0.1 that returns scripted tool
// calls, so no model call leaves this computer and no account is needed.
//
// Usage: node copilot_runtime_probe.mjs <config.json>
//   mode "discover": ask the runtime what it finds in a folder (no session)
//   mode "session":  discovery before and after folder trust, then one scripted session
// A scripted step is { label, tool, args } for an ordinary tool call, or { label, tool, input }
// for a free-form one (apply_patch). `childSteps` maps a sub-agent marker (PROBE-CHILD-<name>,
// put in the task prompt) to the steps that sub-agent plays.
// Everything is written to <outDir>: record.json, and for a session events.jsonl.
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { pathToFileURL } from "node:url";

const config = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const { mode, sdkRoot, baseDir, project, outDir } = config;
fs.mkdirSync(outDir, { recursive: true });
const record = { errors: [] };

const sdk = await import(pathToFileURL(path.join(sdkRoot, "dist", "index.js")).href);
const client = new sdk.CopilotClient({
    baseDirectory: baseDir,
    useLoggedInUser: false,
    logLevel: "error",
    workingDirectory: project,
    // The caller already removed the variables of the agent that started the
    // probe. Hooks inherit this environment.
    env: { ...process.env },
});

const attempt = async (name, fn) => {
    try {
        return await fn();
    } catch (error) {
        record.errors.push(`${name}: ${String(error?.message ?? error)}`);
        return { __error: String(error?.message ?? error) };
    }
};
const hooksAndMcp = async (directory) => ({
    hooks: await attempt("hooks.discover", () => client.rpc.hooks.discover({ projectPaths: [directory] })),
    mcp: await attempt("mcp.discover", () =>
        client.rpc.mcp.discover({ workingDirectory: directory, includeEffectiveSource: true }),
    ),
});

// ---- scripted model on 127.0.0.1 -----------------------------------------
const scenario = config.scenario ?? { steps: [] };
const eventsFile = path.join(outDir, "events.jsonl");
let callCounter = 0;
const mainState = { index: 0 };
const childState = {};
record.stepCalls = {};
record.skippedSteps = {};
record.subagentFirstRequests = {};

const textOf = (message) => (typeof message.content === "string" ? message.content : JSON.stringify(message.content ?? ""));
const nextReply = (body) => {
    callCounter += 1;
    const messages = body.messages ?? [];
    const toolNames = (body.tools ?? []).map((tool) => tool.function?.name ?? tool.custom?.name ?? tool.name);
    const isMain = toolNames.length > 0 && messages.some((message) => textOf(message).includes(scenario.marker));
    if (isMain && record.firstRequestTools === undefined) record.firstRequestTools = body.tools;
    if (!isMain) {
        // A sub-agent: its first user message carries the marker the main model put in its task.
        const child = messages.find((message) => message.role === "user" && textOf(message).includes("PROBE-CHILD"));
        const key = child ? (textOf(child).match(/PROBE-CHILD-[a-z0-9]+/) ?? ["PROBE-CHILD"])[0] : undefined;
        if (key && record.subagentFirstRequests[key] === undefined) {
            record.subagentFirstRequests[key] = {
                toolNames,
                system: messages.filter((m) => m.role === "system" || m.role === "developer").map(textOf),
                user: messages.filter((m) => m.role === "user").map((m) => textOf(m).slice(0, 3000)),
            };
        }
        // The sub-agent plays its own scripted steps, in order, one per model request.
        const steps = (key && scenario.childSteps?.[key]) || [];
        const state = key ? (childState[key] ??= { index: 0 }) : { index: 0 };
        return takeStep(steps, state, toolNames) ?? { text: "ok" };
    }
    return takeStep(scenario.steps, mainState, toolNames) ?? { text: "probe complete" };
};
// The next scripted step the model was offered a tool for, as a model reply. A step with `input`
// is a free-form (custom) tool call such as apply_patch. A step whose tool was not offered is
// recorded and skipped.
const takeStep = (steps, state, toolNames) => {
    while (state.index < steps.length) {
        const step = steps[state.index];
        state.index += 1;
        if (!toolNames.includes(step.tool)) {
            record.skippedSteps[step.label] = `tool ${step.tool} not offered`;
            continue;
        }
        const id = `call_probe_${callCounter}`;
        record.stepCalls[step.label] = id;
        return { tool: { id, name: step.tool, args: step.args ?? {}, input: step.input } };
    }
    return undefined;
};
const completion = (body, reply) => {
    const base = { id: `chatcmpl-probe-${callCounter}`, created: Math.floor(Date.now() / 1000), model: body.model };
    const usage = { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 };
    const message = reply.tool
        ? {
              role: "assistant",
              content: null,
              tool_calls: [
                  reply.tool.input !== undefined
                      ? { id: reply.tool.id, type: "custom", custom: { name: reply.tool.name, input: reply.tool.input } }
                      : { id: reply.tool.id, type: "function", function: { name: reply.tool.name, arguments: JSON.stringify(reply.tool.args) } },
              ],
          }
        : { role: "assistant", content: reply.text };
    const finish = reply.tool ? "tool_calls" : "stop";
    if (!body.stream) {
        return { json: { ...base, object: "chat.completion", choices: [{ index: 0, message, finish_reason: finish }], usage } };
    }
    const delta = reply.tool
        ? { role: "assistant", content: null, tool_calls: message.tool_calls.map((call, index) => ({ index, ...call })) }
        : { role: "assistant", content: reply.text };
    return {
        chunks: [
            { ...base, object: "chat.completion.chunk", choices: [{ index: 0, delta, finish_reason: null }] },
            { ...base, object: "chat.completion.chunk", choices: [{ index: 0, delta: {}, finish_reason: finish }], usage },
        ],
    };
};
const server = http.createServer((req, res) => {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
        if (req.method === "GET") {
            res.writeHead(200, { "content-type": "application/json" });
            res.end(JSON.stringify({ object: "list", data: [{ id: scenario.model, object: "model", owned_by: "probe" }] }));
            return;
        }
        if (!req.url.includes("chat/completions")) {
            res.writeHead(404, { "content-type": "application/json" });
            res.end(JSON.stringify({ error: { message: "probe server only implements chat/completions" } }));
            return;
        }
        let body = {};
        try {
            body = JSON.parse(raw || "{}");
        } catch {
            body = {};
        }
        const result = completion(body, nextReply(body));
        if (result.json) {
            res.writeHead(200, { "content-type": "application/json" });
            res.end(JSON.stringify(result.json));
            return;
        }
        res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
        for (const chunk of result.chunks) res.write(`data: ${JSON.stringify(chunk)}\n\n`);
        res.end("data: [DONE]\n\n");
    });
});

const sessionConfig = (baseUrl) => ({
    model: scenario.model,
    provider: { type: "openai", baseUrl, apiKey: "probe-key", wireApi: "completions" },
    workingDirectory: project,
    enableConfigDiscovery: true,
    enableFileHooks: true,
    enableSessionTelemetry: false,
    streaming: true,
    // Every permission question is approved once, so the permission requests
    // that reach this handler are recorded as session events.
    onPermissionRequest: async () => ({ kind: "approve-once" }),
});

// ---- run -------------------------------------------------------------------
try {
    await client.start();
    record.status = await client.getStatus();
    if (mode === "discover") {
        const projectPaths = [project];
        const rpc = client.rpc;
        record.discovery = {
            ...(await hooksAndMcp(project)),
            instructions: await attempt("instructions.discover", () => rpc.instructions.discover({ projectPaths })),
            skills: await attempt("skills.discover", () => rpc.skills.discover({ projectPaths })),
            agents: await attempt("agents.discover", () => rpc.agents.discover({ projectPaths })),
        };
    } else {
        await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
        const baseUrl = `http://127.0.0.1:${server.address().port}/v1`;
        record.discovery = { untrusted: await hooksAndMcp(project) };
        // Repository hooks load only for a trusted folder. The trust is stored
        // under baseDir, which is private to this run.
        const first = await client.createSession(sessionConfig(baseUrl));
        try {
            await first.rpc.permissions.folderTrust.addTrusted({ path: project });
        } catch (error) {
            record.errors.push(`trust: ${String(error?.message ?? error)}`);
        }
        await first.disconnect();
        record.discovery.trusted = await hooksAndMcp(project);
        const subfolder = path.join(project, scenario.subfolder);
        fs.mkdirSync(subfolder, { recursive: true });
        record.discovery.subfolder = await hooksAndMcp(subfolder);

        fs.writeFileSync(eventsFile, "");
        const session = await client.createSession(sessionConfig(baseUrl));
        session.on((event) => fs.appendFileSync(eventsFile, JSON.stringify(event) + "\n"));
        try {
            await session.sendAndWait({ prompt: `${scenario.marker} Run the probe steps.` }, scenario.timeoutMs);
        } catch (error) {
            record.errors.push(`send: ${String(error?.message ?? error)}`);
        }
        await attempt("disconnect", () => session.disconnect());
    }
} catch (error) {
    record.errors.push(`fatal: ${String(error?.stack ?? error)}`);
} finally {
    await attempt("stop", () => client.stop());
    server.close();
}
record.modelCalls = callCounter;
// A hook can put the project's MCP file back during a session (the restore of root adapters).
if (mode === "session") record.mcpFileAfterSession = fs.existsSync(path.join(project, ".mcp.json"));
fs.writeFileSync(path.join(outDir, "record.json"), JSON.stringify(record, null, 2));
process.exit(0);
