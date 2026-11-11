"""Drive an MCP stdio server: initialize, tools/list, then optional calls.

Usage: python3 -I mcp_probe.py <out.json> <client-name> <calls.json|-> -- cmd args...
calls.json: a JSON list of {"method": ..., "params": ...} sent after tools/list.
Writes every raw stdout line, stderr, exit code, and parsed responses to out.json.
"""

import json
import queue
import subprocess
import sys
import threading
import time


def reader(stream, sink):
    for line in iter(stream.readline, b""):
        sink.put(line)
    sink.put(None)


def main() -> int:
    out_path, client_name, calls_path = sys.argv[1], sys.argv[2], sys.argv[3]
    sep = sys.argv.index("--")
    cmd = sys.argv[sep + 1 :]
    calls = [] if calls_path == "-" else json.load(open(calls_path))
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    lines: queue.Queue = queue.Queue()
    errs: queue.Queue = queue.Queue()
    threading.Thread(target=reader, args=(proc.stdout, lines), daemon=True).start()
    threading.Thread(target=reader, args=(proc.stderr, errs), daemon=True).start()
    raw_out: list[str] = []
    responses: dict[str, object] = {}
    eof = False

    def send(msg: dict) -> None:
        try:
            proc.stdin.write((json.dumps(msg) + "\n").encode())
            proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raw_out.append(f"<send failed: {exc}>")

    def wait_for(msg_id: int, timeout: float) -> object:
        nonlocal eof
        deadline = time.time() + timeout
        while time.time() < deadline and not eof:
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if line is None:
                eof = True
                break
            text = line.decode(errors="replace")
            raw_out.append(text)
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "id" in parsed:
                responses[str(parsed["id"])] = parsed
                if parsed["id"] == msg_id:
                    return parsed
            elif isinstance(parsed, dict) and parsed.get("method") == "roots/list":
                pass
        return None

    started = time.time()
    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "0.0.0"},
            },
        }
    )
    init = wait_for(1, 40)
    if init is not None:
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        wait_for(2, 40)
        for offset, call in enumerate(calls):
            msg_id = 3 + offset
            call = dict(call)
            timeout = float(call.pop("_timeout", 60))
            send({"jsonrpc": "2.0", "id": msg_id, **call})
            wait_for(msg_id, timeout)
    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        code = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        code = proc.wait()
    while True:
        try:
            line = lines.get(timeout=0.5)
        except queue.Empty:
            break
        if line is None:
            break
        raw_out.append(line.decode(errors="replace"))
    stderr_lines = []
    while True:
        try:
            line = errs.get(timeout=0.5)
        except queue.Empty:
            break
        if line is None:
            break
        stderr_lines.append(line.decode(errors="replace"))
    result = {
        "cmd": cmd,
        "client_name": client_name,
        "exit_code": code,
        "seconds": round(time.time() - started, 2),
        "responses": responses,
        "raw_stdout": raw_out,
        "stderr": stderr_lines,
    }
    with open(out_path, "w") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    tools = (responses.get("2") or {}).get("result", {}).get("tools") if isinstance(responses.get("2"), dict) else None
    info = (init or {}).get("result", {}).get("serverInfo") if isinstance(init, dict) else None
    print(json.dumps({"exit": code, "serverInfo": info, "tools": [t.get("name") for t in tools] if tools else tools, "stderr_lines": len(stderr_lines), "init_error": (init or {}).get("error") if isinstance(init, dict) else "no-init-response"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
