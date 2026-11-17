// Add a logging hook to the Claude Code local settings file of a probe project copy,
// to see what the Copilot runtime gives a hook that it loads from Claude settings.
import fs from "node:fs";
import path from "node:path";

const [, , project, logger] = process.argv;
const file = path.join(project, ".claude", "settings.local.json");
const hook = (label) => ({ type: "command", command: `bash ${logger} claudelocal-${label}` });
const settings = {
    hooks: {
        PreToolUse: [{ matcher: "Bash", hooks: [hook("PreToolUse-Bash")] }, { matcher: "Edit|Write", hooks: [hook("PreToolUse-EditWrite")] }],
        SessionStart: [{ hooks: [hook("SessionStart")] }],
        Stop: [{ hooks: [hook("Stop")] }],
    },
};
fs.writeFileSync(file, JSON.stringify(settings, null, 2));
console.log("wrote", path.relative(project, file));
