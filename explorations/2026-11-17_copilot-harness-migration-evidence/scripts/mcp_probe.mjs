// Minimal MCP stdio server with one tool, used to see how the runtime names MCP tools.
import readline from "node:readline";

const rl = readline.createInterface({ input: process.stdin });
const send = (message) => process.stdout.write(JSON.stringify(message) + "\n");
rl.on("line", (line) => {
    let request;
    try {
        request = JSON.parse(line);
    } catch {
        return;
    }
    const { id, method, params } = request;
    if (method === "initialize") {
        send({
            jsonrpc: "2.0",
            id,
            result: {
                protocolVersion: params?.protocolVersion ?? "2025-06-18",
                capabilities: { tools: {} },
                serverInfo: { name: "probe-server", version: "0.0.1" },
            },
        });
    } else if (method === "tools/list") {
        send({
            jsonrpc: "2.0",
            id,
            result: {
                tools: [
                    {
                        name: "echo_text",
                        description: "Return the given text.",
                        inputSchema: { type: "object", properties: { text: { type: "string" } }, required: ["text"] },
                    },
                ],
            },
        });
    } else if (method === "tools/call") {
        send({ jsonrpc: "2.0", id, result: { content: [{ type: "text", text: `echo:${params?.arguments?.text ?? ""}` }] } });
    } else if (id !== undefined) {
        send({ jsonrpc: "2.0", id, result: {} });
    }
});
