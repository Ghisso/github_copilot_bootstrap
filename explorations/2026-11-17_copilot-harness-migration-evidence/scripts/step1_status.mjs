// Spike step 1: start the Copilot runtime bundled with VS Code, with a private
// data folder and no account, and list what it offers. No model call is made.
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , sdkRoot, copilotHome] = process.argv;
const sdk = await import(pathToFileURL(path.join(sdkRoot, "dist", "index.js")).href);

const client = new sdk.CopilotClient({
    baseDirectory: copilotHome,
    useLoggedInUser: false,
    logLevel: "error",
});
try {
    await client.start();
    console.log("status", JSON.stringify(await client.getStatus()));
    try {
        console.log("auth", JSON.stringify(await client.getAuthStatus()));
    } catch (error) {
        console.log("auth error", String(error));
    }
    const rpc = client.rpc;
    const describe = (obj, depth = 0, prefix = "") => {
        if (!obj || depth > 2) return;
        for (const key of Object.keys(obj)) {
            const value = obj[key];
            if (typeof value === "function") console.log("rpc", prefix + key + "()");
            else if (value && typeof value === "object") describe(value, depth + 1, prefix + key + ".");
        }
    };
    describe(rpc);
} finally {
    const errors = await client.stop();
    if (errors.length) console.log("stop errors", errors.map(String));
}
