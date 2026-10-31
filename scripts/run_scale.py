"""Arranca Redis/Postgres/workers aislados y mide el corpus completo con uno y cuatro workers."""

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ARTIFACT_PROBE = """import json, os
from trazia.calibration import load_calibration
from trazia.strategies.fusion import load_fusion
c, f = load_calibration(), load_fusion()
keys = ('GEMINI_API_KEY','GOOGLE_API_KEY','MISTRAL_API_KEY','GROQ_API_KEY',
        'OPENROUTER_API_KEY','NVIDIA_API_KEY','CLOUDFLARE_API_TOKEN','CLOUDFLARE_ACCOUNT_ID')
print(json.dumps({'calibration': c.sha256 if c else None, 'fusion': f.sha256 if f else None,
    'cuda_visible_devices': os.getenv('CUDA_VISIBLE_DEVICES'),
    'external_credentials_present': [k for k in keys if os.getenv(k)]}))
"""


def deployment_override(image, port, calibration_source=None):
    services = []
    for name in ("api-scale", "worker"):
        service = f"  {name}:\n    image: {json.dumps(image)}\n"
        if name == "api-scale":
            service += f"    ports: !override [127.0.0.1:{port}:8000]\n"
        service += (
            "    environment:\n      TRAZIA_OFFLINE: '0'\n      TRAZIA_VISION_OFFLINE: '1'\n"
            "      CUDA_VISIBLE_DEVICES: '-1'\n      TRAZIA_OCR_CACHE: /data/cache/ocr\n"
            "      OMP_NUM_THREADS: '1'\n      OPENBLAS_NUM_THREADS: '1'\n"
        )
        if name == "worker":
            service += "      TRAZIA_WORKER_CONCURRENCY: '1'\n"
        if calibration_source:
            service += (
                "      TRAZIA_CALIBRATION: /run/trazia-calibracion.json\n"
                "    volumes:\n      - type: bind\n"
                f"        source: {json.dumps(calibration_source)}\n"
                "        target: /run/trazia-calibracion.json\n        read_only: true\n"
            )
        services.append(service)
    return "services:\n" + "".join(services)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wsl", help="Distribución con Docker y python3")
    p.add_argument("--workers", nargs="+", type=int, default=[1, 4])
    p.add_argument("--estrategia", default="d_hibrido")
    p.add_argument("--image", default="trazia-api:latest")
    p.add_argument("--data", type=Path, default=Path("generated/synthetic_v2"))
    p.add_argument("--output", type=Path, default=Path("generated/scale"))
    p.add_argument("--api-port", type=int, default=8030)
    p.add_argument("--calibration", type=Path, help="Parámetros montados en solo lectura")
    p.add_argument("--expected-calibration", help="Abortar si no coincide la huella de parámetros")
    p.add_argument("--expected-fusion", help="Abortar si no coincide el modelo de fusión")
    p.add_argument(
        "--sets", nargs="+", default=["s-dev", "s-reservado", "s-mecanico", "s-adversarial"]
    )
    p.add_argument("--casos", type=int, default=None)
    p.add_argument("--degradaciones", nargs="+", default=None)
    p.add_argument("--tags", nargs="+", default=None)
    p.add_argument("--exigir-todos", action="store_true")
    p.add_argument(
        "--eur-worker-hora", type=float, default=None, help="Tarifa hipotética, no coste medido"
    )
    args = p.parse_args()
    if any(n < 1 or n > 8 for n in args.workers):
        p.error("Usa entre uno y ocho workers")
    if (
        not 1 <= args.api_port <= 65535
        or args.api_port in (8010, 8011, 8020, 3100, 3125, 3300)
        or 3290 <= args.api_port <= 3299
    ):
        p.error("Puerto no disponible para el agente Plataforma")
    if args.casos is not None and args.casos < 1:
        p.error("casos debe ser positivo")
    if args.calibration and not args.calibration.is_file():
        p.error("No existe el archivo de calibración solicitado")
    if args.eur_worker_hora is not None and args.eur_worker_hora < 0:
        p.error("La tarifa hipotética no puede ser negativa")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    prefix = []
    if args.wsl:
        linux = "/mnt/" + ROOT.drive[0].lower() + ROOT.as_posix()[2:]
        prefix = ["wsl", "-d", args.wsl, "--cd", linux, "--exec"]

    def native_path(path):
        path = path.resolve()
        return "/mnt/" + path.drive[0].lower() + path.as_posix()[2:] if args.wsl else str(path)

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
            deployment_override(
                args.image,
                args.api_port,
                native_path(args.calibration) if args.calibration else None,
            ),
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
            native_path(override),
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
            image = execute(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"])
            containers = execute(compose + ["ps", "-q", "api-scale", "worker"]).splitlines()
            artifacts = []
            for identity in containers:
                metadata = json.loads(
                    execute(["docker", "exec", identity, ".venv/bin/python", "-c", ARTIFACT_PROBE])
                )
                if metadata["external_credentials_present"]:
                    raise RuntimeError("El contenedor tiene credenciales externas; no medir")
                for key, expected in (
                    ("calibration", args.expected_calibration),
                    ("fusion", args.expected_fusion),
                ):
                    if expected and metadata[key] != expected:
                        raise RuntimeError(f"Huella {key} incorrecta; no se ejecuta el lote")
                artifacts.append({"container": identity, **metadata})
            target = output / f"workers-{count}-{args.estrategia}.json"
            command = (
                prefix
                + (["python3"] if args.wsl else [sys.executable])
                + [
                    "scripts/measure_scale.py",
                    "--api",
                    f"http://127.0.0.1:{args.api_port}",
                    "--output",
                    native_path(target),
                    "--estrategia",
                    args.estrategia,
                    "--data",
                    native_path(args.data),
                    "--sets",
                    *args.sets,
                ]
            )
            if args.casos:
                command += ["--casos", str(args.casos)]
            if args.degradaciones:
                command += ["--degradaciones", *args.degradaciones]
            if args.tags:
                command += ["--tags", *args.tags]
            process = subprocess.run(command, cwd=ROOT)
            if process.returncode:
                raise RuntimeError("El lote no terminó; conserva el resultado parcial")
            report = json.loads(target.read_text(encoding="utf8"))
            report["deployment"] = {
                "workers": count,
                "concurrency_per_worker": 1,
                "image": image,
                "storage": "Postgres + SHA-256",
                "queue": "Redis/arq",
                "cpu_only": True,
                "vision_providers": [],
                "artifacts": artifacts,
            }
            projection = report["summary"]["projection_400x4"]
            seconds = projection["seconds_for_1600_terminal_jobs"]
            projection["compute_cost_scenario"] = {
                "measured": False,
                "assumed_eur_worker_hour": args.eur_worker_hora,
                "estimated_eur_for_1600_terminal_jobs": seconds
                * count
                / 3600
                * args.eur_worker_hora
                if seconds is not None and args.eur_worker_hora is not None
                else None,
                "excluded": "Energía local, almacenamiento, API y coste de producir IFC correctos",
            }
            target.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
            )
            results.append(
                {
                    "workers": count,
                    "strategy": args.estrategia,
                    "deployment": report["deployment"],
                    "input_sha256": report["input_sha256"],
                    "complete": report["complete"],
                    "summary": report["summary"],
                    "acceptance": report.get("acceptance"),
                }
            )
        finally:
            # Proyecto único creado por este script, sin datos ajenos.
            execute(compose + ["down", "--volumes", "--remove-orphans"])
        (output / f"comparison-{args.estrategia}.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )
    failed = any(not r["acceptance"]["all_revisions_have_draft_ifc"] for r in results)
    return 2 if args.exigir_todos and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
