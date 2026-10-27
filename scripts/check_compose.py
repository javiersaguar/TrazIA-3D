"""Comprueba perfiles reales en un proyecto aislado, sin publicar puertos del host.

uv run python scripts/check_compose.py --wsl Ubuntu --profiles local escala gpu
Requiere las imágenes construidas con docker compose --profile local build.
Solo elimina los contenedores y volúmenes sintéticos del proyecto de esta ejecución.
"""

import argparse
import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_PROBE = r"""import json, time, urllib.request, uuid
base = "http://localhost:8000"
def get(path):
    with urllib.request.urlopen(base + path, timeout=90) as r:
        return json.load(r)
assert get("/health")["schema_version"] == "0.3"
revision = get("/equipment/V-101/revisions/A")
assert revision["schema_version"] == "0.3"
key = str(uuid.uuid4())
body = {"documents": ["seed-a-" + d["id"] for d in revision["documents"]],
        "revision": "COMPOSE-CHECK", "strategy": "b_reglas"}
def submit():
    req = urllib.request.Request(base + "/equipment/V-101/jobs", method="POST",
        headers={"Content-Type":"application/json", "Idempotency-Key":key},
        data=json.dumps(body).encode())
    with urllib.request.urlopen(req, timeout=90) as r:
        assert r.status == 202
        return json.load(r)["job_id"]
job_id = submit()
assert submit() == job_id
for _ in range(180):
    job = get("/jobs/" + job_id)
    if job["status"] in ("done", "error", "cancelled"):
        break
    time.sleep(0.5)
assert job["status"] == "done", job
with urllib.request.urlopen(base + "/jobs/" + job_id + "/events", timeout=90) as r:
    events = r.read().decode()
assert "event: complete" in events and "event: stage" in events
ifc_url = base + "/revisions/" + job["revision_id"] + "/ifc?draft=true"
with urllib.request.urlopen(ifc_url, timeout=90) as r:
    assert r.read().startswith(b"ISO-10303-21;")
assert get("/equipment/V-101/revisions/A") == revision
print(json.dumps({"schema":"0.3", "job":job_id, "status":job["status"],
    "run":job["run"], "sse":True, "ifc":True, "idempotency":True}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wsl", help="Distribución WSL donde está Docker")
    parser.add_argument(
        "--profiles", nargs="+", choices=("local", "escala", "gpu"), default=["local", "escala"]
    )
    args = parser.parse_args()
    output = ROOT / "generated/phase1"
    output.mkdir(parents=True, exist_ok=True)
    project = "trazia-check-" + uuid.uuid4().hex[:10]
    prefix = []
    if args.wsl:
        linux_root = "/mnt/" + ROOT.drive[0].lower() + ROOT.as_posix()[2:]
        prefix = ["wsl", "-d", args.wsl, "--cd", linux_root, "--exec"]
    override = output / (project + ".yml")
    api_services = ("api", "api-gpu", "api-scale", "worker")
    web_services = ("web", "web-scale")
    override.write_text(
        "services:\n"
        + "".join(
            f"  {name}:\n    image: trazia-{'api' if name in api_services else 'web'}:latest\n"
            "    ports: !reset []\n"
            for name in (*api_services, *web_services)
        ),
        encoding="utf8",
    )
    base = prefix + [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        "docker-compose.yml",
        "-f",
        "generated/phase1/" + override.name,
    ]
    report = {"project": project, "profiles": {}}

    def run(*command, stdin=None):
        process = subprocess.run(
            prefix + list(command),
            cwd=ROOT,
            input=stdin,
            text=True,
            encoding="utf8",
            errors="replace",
            capture_output=True,
        )
        if process.returncode:
            raise RuntimeError(process.stderr[-6000:] or process.stdout[-6000:])
        return process.stdout.strip()

    def compose(profile, *command, stdin=None):
        return run(*base[len(prefix) :], "--profile", profile, *command, stdin=stdin)

    for profile in args.profiles:
        print(f"Comprobando {profile} en {project}", flush=True)
        try:
            compose(profile, "config", "--quiet")
            compose(profile, "up", "--no-build", "-d", "--wait", "--wait-timeout", "180")
            api = {"local": "api", "escala": "api-scale", "gpu": "api-gpu"}[profile]
            web = "web-scale" if profile == "escala" else "web"
            result = json.loads(
                compose(profile, "exec", "-T", api, ".venv/bin/python", "-", stdin=API_PROBE)
            )
            compose(
                profile,
                "exec",
                "-T",
                web,
                "node",
                "-e",
                "fetch('http://localhost:3000/proyecto').then(async r=>{"
                "if(!r.ok||!(await r.text()).includes('<html'))process.exit(1)})",
            )
            result["web_http"] = 200
            compose(profile, "restart", api)
            compose(profile, "up", "--no-build", "-d", "--wait", "--wait-timeout", "90")
            compose(
                profile,
                "exec",
                "-T",
                api,
                ".venv/bin/python",
                "-c",
                "import urllib.request; urllib.request.urlopen("
                "'http://localhost:8000/equipment/V-101/revisions/COMPOSE-CHECK')",
            )
            result["persisted_after_restart"] = True
            if profile == "gpu":
                result["gpu"] = compose(
                    profile,
                    "exec",
                    "-T",
                    "ollama",
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader",
                )
            report["profiles"][profile] = {"passed": True, **result}
        except Exception as error:
            report["profiles"][profile] = {"passed": False, "error": str(error)}
            print(str(error), flush=True)
            try:
                (output / f"compose-{profile}.log").write_text(
                    compose(profile, "logs", "--no-color"), encoding="utf8"
                )
            except RuntimeError:
                pass
        finally:
            # El nombre aleatorio pertenece exclusivamente a este chequeo; no toca otros proyectos.
            compose(profile, "down", "--volumes", "--remove-orphans")
            (output / "compose-results.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
            )
        print(json.dumps(report["profiles"][profile], ensure_ascii=False), flush=True)
    return int(not all(r["passed"] for r in report["profiles"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
