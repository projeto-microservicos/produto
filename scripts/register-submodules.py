"""Register the team's actual repositories as pinned Git submodules."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("account", "auth", "gateway", "product", "exchange", "order")
GITHUB_URL = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?")


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, text=True,
                          capture_output=True, check=check)


def main():
    repositories = json.loads((ROOT / "repositories.json").read_text(encoding="utf-8"))
    if set(repositories) != set(SERVICES):
        raise ValueError("repositories.json must contain exactly: " + ", ".join(SERVICES))
    invalid = [name for name in SERVICES if not isinstance(repositories[name], str)
               or (repositories[name] and not GITHUB_URL.fullmatch(repositories[name]))]
    if invalid:
        raise ValueError("Set valid HTTPS GitHub URLs in repositories.json for: " + ", ".join(invalid))
    configured = [name for name in SERVICES if repositories[name]]
    missing = [name for name in SERVICES if not repositories[name]]
    if not configured:
        raise ValueError("Set at least one actual repository URL before registering submodules")
    if missing:
        print("Pending repository URLs: " + ", ".join(missing), flush=True)
    checkout = git("rev-parse", "--show-toplevel")
    if Path(checkout.stdout.strip()).resolve() != ROOT:
        raise ValueError("Initialize this aggregate as its own Git repository first (git init -b main)")

    pending = []
    for name in configured:
        url, destination = repositories[name], f"services/{name}"
        existing = git("config", "-f", ".gitmodules", "--get", f"submodule.{name}.url", check=False)
        if existing.returncode == 0:
            path = git("config", "-f", ".gitmodules", "--get", f"submodule.{name}.path")
            if existing.stdout.strip() != url or path.stdout.strip() != destination:
                raise ValueError(f"Existing submodule {name} differs; review .gitmodules before continuing")
        elif (ROOT / destination).exists():
            raise ValueError(f"Destination {destination} already exists; review it before continuing")
        else:
            pending.append((name, url, destination))

    for name, url, destination in pending:
        print(f"Registering {name}: {url}", flush=True)
        result = git("submodule", "add", "--name", name, "--", url, destination)
        print(result.stdout, end="")
    print("Submodules registered. Review git diff --cached and commit the gitlinks with .gitmodules.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
