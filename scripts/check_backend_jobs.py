"""Prueba aislada del estudio en Redis/arq/Postgres, sin GPU ni puertos del usuario.

Preparar un conjunto sintético vectorial y construir Dockerfile.api antes de ejecutar.
El proyecto Compose y sus volúmenes son exclusivos de esta ejecución y se eliminan al salir.
"""

import argparse
import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = r"""
import json, time, urllib.request, uuid
base = "http://localhost:8000"
def request(path, body=None, key=None):
    headers = {"Content-Type":"application/json", "Idempotency-Key":key or str(uuid.uuid4())}
    req = urllib.request.Request(base + path, headers=headers,
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)
def done(identity):
    until = time.monotonic() + 90
    while time.monotonic() < until:
        value = request("/jobs/" + identity)
        if value["status"] in ("done", "error", "cancelled", "timeout"):
            return value
        time.sleep(.1)
    raise AssertionError("Trabajo sin terminar")
assert request("/health")["offline"]
body = {"variantes":["b_reglas"], "casos":1, "degradaciones":["vectorial"], "remuestreos":10}
key = str(uuid.uuid4())
job = request("/estudio", body, key)["job_id"]
assert request("/estudio", body, key)["job_id"] == job
value = done(job)
assert value["status"] == "done", value
report = request("/estudio?job_id=" + job)
assert report["variants"][0]["id"] == "b_reglas"
with urllib.request.urlopen(base + "/jobs/" + job + "/events", timeout=90) as response:
    events = response.read().decode()
assert "Estudio publicado" in events and "event: complete" in events
timeout = request("/estudio", {**body,"timeout_seconds":.01})["job_id"]
assert done(timeout)["status"] == "timeout"
cancelled = request("/estudio", body)["job_id"]
request("/jobs/" + cancelled + "/cancel", {})
assert done(cancelled)["status"] == "cancelled"
assert done(cancelled)["result_sha256"] is None
print(json.dumps({"job_id":job, "result_sha256":value["result_sha256"],
    "seconds":value["elapsed_seconds"], "idempotency":True, "sse":True,
    "cancelled":True,"timeout":True,"offline":True,"queue":"Redis/arq","database":"Postgres"}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wsl")
    parser.add_argument("--image", default="trazia-platform-check:20261030")
    parser.add_argument("--datos", type=Path, default=Path("generated/backend-check/input"))
    args = parser.parse_args()
    data = args.datos.resolve()
    manifest = json.loads((data / "s-dev/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("synthetic") is not True:
        parser.error("Solo se admite un conjunto sintético")
    project = "trazia-backend-check-" + uuid.uuid4().hex[:10]
    output = ROOT / "generated/backend-check"
    output.mkdir(parents=True, exist_ok=True)
    prefix = ["wsl", "-d", args.wsl, "--exec"] if args.wsl else []

    def linux(path):
        path = path.resolve()
        return "/mnt/" + path.drive[0].lower() + path.as_posix()[2:] if args.wsl else str(path)

    env = {
        "TRAZIA_DATA": "/data",
        "TRAZIA_ROOT": "/app",
        "TRAZIA_HOST": "0.0.0.0",
        "TRAZIA_QUEUE": "redis",
        "TRAZIA_REDIS_URL": "redis://redis:6379/0",
        "TRAZIA_DATABASE_URL": "postgresql+psycopg://trazia:local-check@postgres/trazia",
        "TRAZIA_OFFLINE": "1",
        "TRAZIA_STUDY_DATA": "/synthetic",
        "OMP_NUM_THREADS": "1",
    }
    api = {
        "image": args.image,
        "environment": env,
        "volumes": ["data:/data", f"{linux(data)}:/synthetic:ro"],
        "depends_on": {
            "redis": {"condition": "service_healthy"},
            "postgres": {"condition": "service_healthy"},
        },
    }
    config = {
        "services": {
            "redis": {
                "image": "redis:7.2-alpine",
                "healthcheck": {
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "1s",
                    "retries": 30,
                },
            },
            "postgres": {
                "image": "postgres:16-alpine",
                "environment": {
                    "POSTGRES_USER": "trazia",
                    "POSTGRES_DB": "trazia",
                    "POSTGRES_PASSWORD": "local-check",
                },
                "healthcheck": {
                    "test": ["CMD", "pg_isready", "-U", "trazia"],
                    "interval": "1s",
                    "retries": 30,
                },
            },
            "api": {
                **api,
                "healthcheck": {
                    "test": [
                        "CMD",
                        ".venv/bin/python",
                        "-c",
                        "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')",
                    ],
                    "interval": "1s",
                    "retries": 60,
                },
            },
            "worker": {
                **api,
                "command": [".venv/bin/arq", "trazia.queue.worker.WorkerSettings"],
                "depends_on": {"api": {"condition": "service_healthy"}},
            },
        },
        "volumes": {"data": {}},
    }
    compose_file = output / (project + ".json")
    compose_file.write_text(json.dumps(config), encoding="utf-8")
    command = prefix + ["docker", "compose", "-p", project, "-f", linux(compose_file)]

    def execute(*parts):
        result = subprocess.run(
            command + list(parts),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-6000:] or result.stdout[-6000:])
        return result.stdout.strip()

    try:
        execute("up", "-d", "--wait", "--wait-timeout", "90")
        result = json.loads(execute("exec", "-T", "api", ".venv/bin/python", "-c", CHECK))
        execute("restart", "api")
        execute("up", "-d", "--wait", "--wait-timeout", "90", "api")
        query = (
            "import json,urllib.request;"
            f"r=json.load(urllib.request.urlopen('http://localhost:8000/jobs/{result['job_id']}'));"
            f"assert r['result_sha256']=={result['result_sha256']!r};print('ok')"
        )
        assert execute("exec", "-T", "api", ".venv/bin/python", "-c", query) == "ok"
        result["restart_persistence"] = True
        (output / "redis-study.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False))
    except Exception:
        print(execute("logs", "--tail", "60", "api", "worker"))
        raise
    finally:
        execute("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
