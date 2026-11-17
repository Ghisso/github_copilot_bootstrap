// Spike step 3: run one real session of the bundled Copilot runtime against a
// scripted local model (no account, no network model call) and record every
// session event, permission request, and model request.
//
// Usage: node step3_session.mjs <sdkRoot> <copilotHome> <project> <scenario.json> <outDir>
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [, , sdkRoot, copilotHome, project, scenarioFile, outDir] = process.argv;
const scenario = JSON.parse(
    fs
        .readFileSync(scenarioFile, "utf8")
        .replaceAll("{{PROJECT}}", project)
        .replaceAll("{{NODE}}", process.execPath)
        .replaceAll("{{SPIKE}}", path.dirname(new URL(import.meta.url).pathname)),
);
fs.mkdirSync(outDir, { recursive: true });
const eventsFile = path.join(outDir, "events.jsonl");
const modelFile = path.join(outDir, "model-requests.jsonl");
const permFile = path.join(outDir, "permissions.jsonl");
for (const file of [eventsFile, modelFile, permFile]) fs.writeFileSync(file, "");
const append = (file, value) => fs.appendFileSync(file, JSON.stringify(value) + "\n");

// ---- scripted model -------------------------------------------------------
let stepIndex = 0;
let callCounter = 0;
const children = {};
const steps = scenario.steps;
const pickTool = (step, toolNames) => {
    if (step.tool) return step.tool;
    if (step.toolMatch) return toolNames.find((name) => name.includes(step.toolMatch));
    return undefined;
};
const nextReply = (body) => {
    const toolNames = (body.tools ?? []).map((tool) => tool.function?.name ?? tool.custom?.name ?? tool.name);
    const last = body.messages?.[body.messages.length - 1];
    const isMain = toolNames.length > 0 && (body.messages ?? []).some((m) => typeof m.content === "string" ? m.content.includes(scenario.marker) : JSON.stringify(m.content ?? "").includes(scenario.marker));
    append(modelFile, {
        model: body.model,
        stream: !!body.stream,
        toolNames,
        isMain,
        lastRole: last?.role,
        messageRoles: (body.messages ?? []).map((m) => m.role),
        lastContent: typeof last?.content === "string" ? last.content.slice(0, 1500) : JSON.stringify(last?.content ?? "").slice(0, 1500),
        firstRequestTools: callCounter === 0 ? body.tools : undefined,
        firstRequestSystem: callCounter === 0 ? body.messages?.filter((m) => m.role === "system" || m.role === "developer").map((m) => (typeof m.content === "string" ? m.content : JSON.stringify(m.content))) : undefined,
        ctxHits: (body.messages ?? [])
            .map((m) => ({ role: m.role, text: typeof m.content === "string" ? m.content : JSON.stringify(m.content ?? "") }))
            .filter((m) => m.text.includes("PROBE-CTX"))
            .map((m) => ({ role: m.role, found: [...new Set(m.text.match(/PROBE-CTX-[a-z0-9-]+/g))] })),
    });
    callCounter += 1;
    // A sub-agent conversation: its user message carries a child marker, and it
    // gets its own copy of the child steps.
    const textOf = (m) => (typeof m.content === "string" ? m.content : JSON.stringify(m.content ?? ""));
    const childUser = !isMain && toolNames.length >= 0 ? (body.messages ?? []).find((m) => m.role === "user" && textOf(m).includes("PROBE-CHILD")) : undefined;
    if (childUser) {
        const key = (textOf(childUser).match(/PROBE-CHILD-[a-z0-9]+/) ?? ["PROBE-CHILD"])[0];
        const state = (children[key] ??= { index: 0, first: true });
        if (state.first) {
            state.first = false;
            append(modelFile, {
                childFirstRequest: key,
                toolNames,
                system: (body.messages ?? []).filter((m) => m.role === "system" || m.role === "developer").map(textOf),
                userMessages: (body.messages ?? []).filter((m) => m.role === "user").map((m) => textOf(m).slice(0, 3000)),
            });
        }
        const childSteps = scenario.childSteps?.[key] ?? scenario.childSteps?.default ?? [];
        while (state.index < childSteps.length) {
            const step = childSteps[state.index];
            state.index += 1;
            const name = pickTool(step, toolNames);
            if (!name) {
                append(modelFile, { skippedChildStep: step, child: key, reason: "tool not offered", toolNames });
                continue;
            }
            return { tool: { name, args: step.args ?? {}, input: step.input } };
        }
        return { text: `child ${key} complete` };
    }
    if (!isMain) return { text: "ok" };
    while (stepIndex < steps.length) {
        const step = steps[stepIndex];
        stepIndex += 1;
        const name = pickTool(step, toolNames);
        if (!name) {
            append(modelFile, { skippedStep: step, reason: "tool not offered", toolNames });
            continue;
        }
        return { tool: { name, args: step.args ?? {}, input: step.input } };
    }
    return { text: "probe complete" };
};
const completion = (body, reply) => {
    const id = `chatcmpl-probe-${callCounter}`;
    const base = { id, created: Math.floor(Date.now() / 1000), model: body.model };
    const usage = { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 };
    const message = reply.tool
        ? {
              role: "assistant",
              content: null,
              // A step with "input" is a freeform (custom) tool call such as apply_patch.
              tool_calls: [
                  reply.tool.input !== undefined
                      ? { id: `call_probe_${callCounter}`, type: "custom", custom: { name: reply.tool.name, input: reply.tool.input } }
                      : { id: `call_probe_${callCounter}`, type: "function", function: { name: reply.tool.name, arguments: JSON.stringify(reply.tool.args) } },
              ],
          }
        : { role: "assistant", content: reply.text };
    const finish = reply.tool ? "tool_calls" : "stop";
    if (!body.stream) {
        return { stream: false, json: { ...base, object: "chat.completion", choices: [{ index: 0, message, finish_reason: finish }], usage } };
    }
    const delta = reply.tool
        ? { role: "assistant", content: null, tool_calls: message.tool_calls.map((call, index) => ({ index, ...call })) }
        : { role: "assistant", content: reply.text };
    return {
        stream: true,
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
        let body = {};
        try {
            body = JSON.parse(raw || "{}");
        } catch {
            body = {};
        }
        if (!req.url.includes("chat/completions")) {
            append(modelFile, { unexpectedUrl: req.url, keys: Object.keys(body) });
            res.writeHead(404, { "content-type": "application/json" });
            res.end(JSON.stringify({ error: { message: "probe server only implements chat/completions" } }));
            return;
        }
        const result = completion(body, nextReply(body));
        if (!result.stream) {
            res.writeHead(200, { "content-type": "application/json" });
            res.end(JSON.stringify(result.json));
            return;
        }
        res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
        for (const chunk of result.chunks) res.write(`data: ${JSON.stringify(chunk)}\n\n`);
        res.end("data: [DONE]\n\n");
    });
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const baseUrl = `http://127.0.0.1:${server.address().port}/v1`;

// ---- runtime --------------------------------------------------------------
const sdk = await import(pathToFileURL(path.join(sdkRoot, "dist", "index.js")).href);
const client = new sdk.CopilotClient({
    baseDirectory: copilotHome,
    useLoggedInUser: false,
    logLevel: scenario.logLevel ?? "error",
    workingDirectory: project,
    // Hooks inherit this environment. Drop the variables of the Claude Code
    // session this spike runs from, so hooks see what a Copilot session gives them.
    env: {
        ...Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(CLAUDE|ANTHROPIC|CLAUDECODE)/.test(key))),
        ...(scenario.env ?? {}),
    },
});
const sessionConfig = () => ({
    model: scenario.model,
    provider: { type: "openai", baseUrl, apiKey: "probe-key", wireApi: "completions" },
    workingDirectory: project,
    enableConfigDiscovery: scenario.enableConfigDiscovery ?? true,
    enableFileHooks: scenario.enableFileHooks ?? true,
    enableSessionTelemetry: false,
    streaming: true,
    ...(scenario.mcpServers ? { mcpServers: scenario.mcpServers } : {}),
    ...(scenario.hookDirectories ? { hookDirectories: scenario.hookDirectories } : {}),
    ...(scenario.agent ? { agent: scenario.agent } : {}),
    onPermissionRequest: async (request, invocation) => {
        const kinds = { approve: "approve-once", reject: "reject", unavailable: "user-not-available" };
        const decision = { kind: kinds[scenario.permission ?? "approve"] };
        append(permFile, { request, decision });
        return decision;
    },
});
const summary = { baseUrl: "<local>", errors: [] };
try {
    await client.start();
    summary.status = await client.getStatus();
    if (scenario.trust) {
        const first = await client.createSession(sessionConfig());
        try {
            summary.trustBefore = await first.rpc.permissions.folderTrust.isTrusted({ path: project });
            summary.trustAdd = await first.rpc.permissions.folderTrust.addTrusted({ path: project });
            summary.trustAfter = await first.rpc.permissions.folderTrust.isTrusted({ path: project });
        } catch (error) {
            summary.errors.push("trust: " + String(error?.message ?? error));
        }
        await first.disconnect();
    }
    try {
        summary.hooks = await client.rpc.hooks.discover({ projectPaths: [project] });
        summary.mcp = await client.rpc.mcp.discover({ workingDirectory: project, includeEffectiveSource: true });
    } catch (error) {
        summary.errors.push("discover: " + String(error?.message ?? error));
    }
    if (scenario.steps.length > 0 || scenario.prompt) {
        const session = await client.createSession(sessionConfig());
        session.on((event) => append(eventsFile, event));
        try {
            const reply = await session.sendAndWait({ prompt: `${scenario.marker} ${scenario.prompt ?? "Run the probe steps."}` }, scenario.timeoutMs ?? 240000);
            summary.finalMessage = reply?.data?.content?.slice?.(0, 300) ?? null;
        } catch (error) {
            summary.errors.push("send: " + String(error?.message ?? error));
        }
        try {
            summary.sessionId = session.sessionId;
            await session.disconnect();
        } catch (error) {
            summary.errors.push("disconnect: " + String(error?.message ?? error));
        }
    }
} catch (error) {
    summary.errors.push("fatal: " + String(error?.stack ?? error));
} finally {
    try {
        await client.stop();
    } catch (error) {
        summary.errors.push("stop: " + String(error?.message ?? error));
    }
    server.close();
}
summary.modelCalls = callCounter;
summary.stepsConsumed = stepIndex;
fs.writeFileSync(path.join(outDir, "summary.json"), JSON.stringify(summary, null, 2));
console.log(JSON.stringify({ errors: summary.errors, modelCalls: callCounter, stepsConsumed: stepIndex, trustBefore: summary.trustBefore, trustAfter: summary.trustAfter, hooks: summary.hooks?.hooks?.length, hookWarnings: summary.hooks?.warnings?.length, hookErrors: summary.hooks?.errors?.length, mcp: summary.mcp?.servers?.length, finalMessage: summary.finalMessage }, null, 1));
