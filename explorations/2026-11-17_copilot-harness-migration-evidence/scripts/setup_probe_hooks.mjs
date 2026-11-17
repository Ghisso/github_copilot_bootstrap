// Write probe hook files into a probe project. Usage:
//   node setup_probe_hooks.mjs <project> <hooklog.sh> <mode>
// mode: "both" writes one camelCase and one PascalCase hook file beside the
// installed bootstrap hooks; "remove" deletes them again.
import fs from "node:fs";
import path from "node:path";

const [, , project, logger, mode = "both"] = process.argv;
const dir = path.join(project, ".github", "hooks");
const camelFile = path.join(dir, "zz-probe-camel.json");
const pascalFile = path.join(dir, "zz-probe-pascal.json");

const camel = [
    "sessionStart", "sessionEnd", "userPromptSubmitted", "userPromptTransformed", "preToolUse",
    "preMcpToolCall", "postToolUse", "postToolUseFailure", "agentStop", "subagentStart",
    "subagentStop", "errorOccurred", "preCompact", "permissionRequest", "notification",
];
const pascal = [
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PostToolUseFailure", "Stop", "SubagentStart", "SubagentStop", "PreCompact",
    "PermissionRequest", "Notification", "ErrorOccurred",
];
const fileFor = (events, style) => ({
    version: 1,
    hooks: Object.fromEntries(
        events.map((event) => [
            event,
            [{ type: "command", bash: `bash ${logger} ${style}-${event}`, cwd: ".", timeoutSec: 10 }],
        ]),
    ),
});

for (const file of [camelFile, pascalFile]) fs.rmSync(file, { force: true });
if (mode !== "remove") {
    fs.mkdirSync(dir, { recursive: true });
    if (mode === "both" || mode === "camel") fs.writeFileSync(camelFile, JSON.stringify(fileFor(camel, "camel"), null, 2));
    if (mode === "both" || mode === "pascal") fs.writeFileSync(pascalFile, JSON.stringify(fileFor(pascal, "pascal"), null, 2));
}
console.log("probe hook files:", fs.readdirSync(dir).join(", "));
