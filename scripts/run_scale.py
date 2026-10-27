"""Arranca Redis/Postgres/workers aislados y mide el corpus completo con uno y cuatro workers."""

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wsl", help="Distribución con Docker y python3")
    p.add_argument("--workers", nargs="+", type=int, default=[1, 4])
    args = p.parse_args()
    if any(n < 1 or n > 8 for n in args.workers):
        p.error("Usa entre uno y ocho workers")
    output = ROOT / "generated/scale"
    output.mkdir(parents=True, exist_ok=True)
    prefix = []
    if args.wsl:
        linux = "/mnt/" + ROOT.drive[0].lower() + ROOT.as_posix()[2:]
        prefix = ["wsl", "-d", args.wsl, "--cd", linux, "--exec"]

    def execute(command, **kwargs):
        result = subprocess.run(
            prefix + command,
            cwd=ROOT,
            text=True,
            encoding="utf8",
            errors="replace",
            capture_output=True,
            **kwargs,
        )
        if result.returncode:
            raise RuntimeError(result.stderr[-5000:] or result.stdout[-5000:])
        return result.stdout.strip()

    results = []
    for count in args.workers:
        project = "trazia-scale-" + uuid.uuid4().hex[:10]
        override = output / (project + ".yml")
        override.write_text(
            "services:\n  api-scale:\n    image: trazia-api:latest\n"
            "    ports: !override [127.0.0.1:18000:8000]\n"
            "  worker:\n    image: trazia-api:latest\n    environment:\n"
            "      TRAZIA_WORKER_CONCURRENCY: '1'\n"
            "      OMP_NUM_THREADS: '1'\n      OPENBLAS_NUM_THREADS: '1'\n",
            encoding="utf8",
        )
        compose = [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            "docker-compose.yml",
            "-f",
            "generated/scale/" + override.name,
            "--profile",
            "escala",
        ]
        print(f"Workers: {count}, proyecto: {project}", flush=True)
        try:
            execute(
                compose
                + [
                    "up",
                    "--no-build",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    "180",
                    "--scale",
                    f"worker={count}",
                    "api-scale",
                    "worker",
                ]
            )
            image = execute(
                ["docker", "image", "inspect", "trazia-api:latest", "--format", "{{.Id}}"]
            )
            target = f"generated/scale/workers-{count}.json"
            command = (
                prefix
                + (["python3"] if args.wsl else [sys.executable])
                + [
                    "scripts/measure_scale.py",
                    "--api",
                    "http://127.0.0.1:18000",
                    "--output",
                    target,
                ]
            )
            process = subprocess.run(command, cwd=ROOT)
            if process.returncode:
                raise RuntimeError("El lote no terminó; conserva el resultado parcial")
            report = json.loads((ROOT / target).read_text(encoding="utf8"))
            report["deployment"] = {
                "workers": count,
                "concurrency_per_worker": 1,
                "image": image,
                "storage": "Postgres + SHA-256",
                "queue": "Redis/arq",
            }
            (ROOT / target).write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
            )
            results.append(
                {
                    "workers": count,
                    "deployment": report["deployment"],
                    "input_sha256": report["input_sha256"],
                    "complete": report["complete"],
                    "summary": report["summary"],
                }
            )
        finally:
            # Proyecto único creado por este script, sin datos ajenos.
            execute(compose + ["down", "--volumes", "--remove-orphans"])
        (output / "comparison.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
