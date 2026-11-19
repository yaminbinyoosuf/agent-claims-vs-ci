#!/usr/bin/env python3
"""Daily: re-check MISMATCH PRs, export the data into the public dataset repo, push if changed.
Runs after radar.py on the server (cogext-radar.service). Writes only to this repo."""
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

RADAR = Path.home() / "cogext-radar"
REPO = Path.home() / "agent-claims-vs-ci"


def run(*cmd, cwd=REPO, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def stats_block(d: dict) -> str:
    t = d["total"]
    days = d["days"]
    lines = [f"Updated {d['updated'][:10]}. PRs opened {days[0]} to {days[-1]} ({len(days)} days).", "",
             f"- PRs judged: **{t['judged']}**",
             f"- Said tests pass while a test or build check failed: **{t['mismatch']} ({t['rate']}%)**",
             f"- Of those, merged anyway: **{d['merged_with_failing_tests']}**",
             f"- Not counted (failure also on base branch, chronic, roll-up only, passed later, or CI still running): "
             f"{t['unverifiable']}", "", "| Agent | Judged | Mismatch | Rate |", "|---|---:|---:|---:|"]
    for name, a in sorted(d["agents"].items(), key=lambda kv: -kv[1]["judged"]):
        rate = f"{a['rate']}%" if a["judged"] >= 20 else "too few"
        lines.append(f"| {name} | {a['judged']} | {a['mismatch']} | {rate} |")
    return "\n".join(lines)


def main() -> int:
    py = sys.executable
    subprocess.run([py, str(RADAR / "radar.py"), "--recheck"], cwd=RADAR, check=True)
    (REPO / "data").mkdir(exist_ok=True)
    subprocess.run([py, str(RADAR / "radar.py"), "--export", str(REPO / "data/summary.json"),
                    "--csv", str(REPO / "data/prs.csv")], cwd=RADAR, check=True, capture_output=True)
    shutil.copy(RADAR / "radar.py", REPO / "radar.py")
    d = json.loads((REPO / "data/summary.json").read_text())
    readme = (REPO / "README.md").read_text()
    a, b = "<!-- stats:start -->", "<!-- stats:end -->"
    readme = readme[:readme.index(a) + len(a)] + "\n" + stats_block(d) + "\n" + readme[readme.index(b):]
    (REPO / "README.md").write_text(readme)
    run("git", "add", "-A")
    if run("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
        print("no change")
        return 0
    run("git", "commit", "-m", f"Data update {dt.date.today().isoformat()}")
    run("git", "push", "origin", "HEAD")
    print("pushed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
