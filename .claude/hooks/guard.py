"""Core-logic guard: runs before Claude edits a file or runs a shell command.

Claude Code sends the planned tool call as JSON on stdin. This script answers:
- "ask"  for the core logic George wrote (CLAUDE.md: propose and explain first),
- "deny" for secrets and account data (.env, auth.db, *.db, accounts/),
- nothing (carry on as normal) for everything else.
"""
import json
import re
import sys

# Core logic: George must approve every change (CLAUDE.md "Core logic").
CORE_FILES = ["costing.py", "menu_engineering.py", "matching.py", "recipe_ai.py"]


def is_core(path):
    return any(path.endswith("/backend/" + name) for name in CORE_FILES)


def is_protected(path):
    name = path.rsplit("/", 1)[-1]
    return (
        name == ".env"
        or name.endswith(".db")
        or "/backend/accounts/" in path
    )


def answer(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def check_file_edit(path):
    path = path.replace("\\", "/").lower()
    if is_protected(path):
        answer("deny", "Secrets and account data (.env, *.db, accounts/) are never edited by Claude.")
    if is_core(path):
        answer("ask", "Core logic (CLAUDE.md): George approves every change to this file.")


# Shell commands that write to a file: redirects, sed -i, tee, copy/move/delete.
WRITE_WORDS = re.compile(
    r"(sed\s+-i|\btee\b|\bmv\b|\bcp\b|\brm\b|\btruncate\b|git\s+(checkout|restore)\b"
    r"|Set-Content|Add-Content|Out-File|Move-Item|Copy-Item|Remove-Item|Clear-Content"
    r"|\.write_text|\.write\(|open\()",
    re.IGNORECASE,
)


def check_shell(command):
    text = command.replace("\\", "/")
    # A redirect counts only when it writes into a real file (not 2>/dev/null or 2>&1).
    targets = re.findall(r">>?\s*[\"']?([^\s\"'|;&]+|&\d)", text)
    redirects = [t for t in targets if t.lower() not in ("/dev/null", "$null", "nul") and not t.startswith("&")]
    if not (redirects or WRITE_WORDS.search(text)):
        return
    lowered = text.lower()
    if re.search(r"(^|[/\s\"'])\.env\b|auth\.db|menu\.db|accounts/", lowered):
        answer("ask", "This command may write to secrets or account data. Check before allowing.")
    if any(name in lowered for name in CORE_FILES):
        answer("ask", "This command may change core logic (CLAUDE.md). George approves first.")


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return  # unreadable input: stay out of the way
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        check_file_edit(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    elif tool in ("Bash", "PowerShell"):
        check_shell(tool_input.get("command", ""))


main()
