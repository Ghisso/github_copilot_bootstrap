// Spike step 4: list the built-in tools the runtime offers for each known model family.
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , sdkRoot, copilotHome] = process.argv;
const sdk = await import(pathToFileURL(path.join(sdkRoot, "dist", "index.js")).href);
const client = new sdk.CopilotClient({ baseDirectory: copilotHome, useLoggedInUser: false, logLevel: "error" });
try {
    await client.start();
    let ids = [];
    try {
        const catalog = await client.rpc.models.getBuiltInCatalog({});
        const models = catalog.models ?? catalog.catalog ?? catalog;
        ids = (Array.isArray(models) ? models : Object.values(models)).map((m) => m.id ?? m.modelId ?? m.name).filter(Boolean);
        console.log("catalog models:", ids.length);
    } catch (error) {
        console.log("catalog error:", String(error?.message ?? error));
    }
    const extra = ["gpt-5.1", "gpt-5.2-codex", "gpt-4.1", "claude-sonnet-4.5", "claude-opus-4.5", "gemini-3-pro-preview", "probe-model"];
    const groups = new Map();
    for (const id of [...new Set([...ids, ...extra])]) {
        try {
            const result = await client.rpc.tools.list({ model: id });
            const names = result.tools.map((tool) => tool.name).sort().join(", ");
            groups.set(names, [...(groups.get(names) ?? []), id]);
        } catch (error) {
            groups.set("ERROR " + String(error?.message ?? error), [...(groups.get("ERROR") ?? []), id]);
        }
    }
    for (const [names, models] of groups) {
        console.log(`\nmodels (${models.length}): ${models.join(", ")}`);
        console.log(`tools: ${names}`);
    }
    const patch = (await client.rpc.tools.list({ model: "gpt-5.2-codex" })).tools.find((tool) => tool.name === "apply_patch");
    if (patch) console.log("\napply_patch definition:", JSON.stringify(patch).slice(0, 1500));
} finally {
    await client.stop();
}
