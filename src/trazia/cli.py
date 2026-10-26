import argparse
import json
import subprocess
import sys
from pathlib import Path

from .model import Revision, load_revision
from .revisions import compare


def write_json(data: dict, path: Path | None):
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="TrazIA-3D: del plano al modelo, con cada cambio trazado"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    migrate = commands.add_parser("migrate", help="Migrar un contrato 0.2 a 0.3 (DRAFT)")
    migrate.add_argument("input", type=Path)
    migrate.add_argument("--output", "-o", type=Path, required=True)
    validate = commands.add_parser("validate", help="Validar contrato y estado de revisión")
    validate.add_argument("input", type=Path)
    export = commands.add_parser("export", help="Exportar IFC4, IFC4X3 o IFC2X3")
    export.add_argument("input", type=Path)
    export.add_argument("--output", "-o", type=Path, required=True)
    export.add_argument("--draft", action="store_true")
    export.add_argument("--schema", choices=("IFC4", "IFC4X3", "IFC2X3"), default="IFC4")
    geometry = commands.add_parser(
        "compare-ifc", help="Distancias de superficie por GUID (extra geo)"
    )
    geometry.add_argument("before", type=Path)
    geometry.add_argument("after", type=Path)
    geometry.add_argument("--samples", type=int, default=1024)
    geometry.add_argument("--match", choices=("guid", "name"), default="guid")
    geometry.add_argument("--output", "-o", type=Path)
    ifc_validation = commands.add_parser("validate-ifc", help="Validar IFC y reglas EXPRESS")
    ifc_validation.add_argument("input", type=Path)
    diff = commands.add_parser("diff", help="Comparar revisiones y evidencia")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output", "-o", type=Path)
    schema = commands.add_parser("schema", help="Emitir JSON Schema")
    schema.add_argument("--output", "-o", type=Path)
    ingest = commands.add_parser("ingest", help="Leer PDF/XLSX/imagen y catalogar evidencia")
    ingest.add_argument("input", type=Path)
    ingest.add_argument("--id", required=True)
    ingest.add_argument("--revision", required=True)
    ingest.add_argument("--output", "-o", type=Path, required=True)
    extract = commands.add_parser("extract", help="Baseline de etiquetas explícitas, sin IA")
    extract.add_argument("bundles", nargs="+", type=Path)
    extract.add_argument("--project", required=True)
    extract.add_argument("--equipment", required=True)
    extract.add_argument("--revision", required=True)
    extract.add_argument("--synthetic", action="store_true")
    extract.add_argument("--output", "-o", type=Path, required=True)
    approval = commands.add_parser(
        "approve", help="Registrar revisión humana y verificar originales"
    )
    approval.add_argument("input", type=Path)
    approval.add_argument("--reviewer", required=True)
    approval.add_argument(
        "--original", action="append", required=True, help="ID=ruta del documento"
    )
    approval.add_argument("--output", "-o", type=Path, required=True)
    serve = commands.add_parser("serve", help="Abrir el espacio de revisión local")
    serve.add_argument("--port", type=int, default=8501)
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            write_json(Revision.model_json_schema(), args.output)
        elif args.command == "migrate":
            write_json(load_revision(args.input).model_dump(mode="json"), args.output)
        elif args.command == "validate":
            revision = load_revision(args.input)
            write_json(
                {
                    "valid": True,
                    "dataset": revision.dataset,
                    "approved": revision.approval is not None,
                    "pending_review": revision.pending_review(),
                },
                None,
            )
        elif args.command == "compare-ifc":
            from .families.metrics import compare_ifc

            write_json(
                compare_ifc(args.before, args.after, samples=args.samples, match=args.match),
                args.output,
            )
        elif args.command == "validate-ifc":
            from .ifc import validate_ifc

            issues = validate_ifc(args.input)
            write_json({"valid": not issues, "issues": issues}, None)
            return 1 if issues else 0
        elif args.command == "diff":
            write_json(compare(load_revision(args.before), load_revision(args.after)), args.output)
        elif args.command == "ingest":
            from .ingest import ingest_bytes

            bundle = ingest_bytes(args.input.read_bytes(), args.input.name, args.id, args.revision)
            write_json(bundle.model_dump(mode="json"), args.output)
        elif args.command == "extract":
            from .extraction import LabelExtractor, assemble
            from .ingest import Bundle

            bundles = [
                Bundle.model_validate_json(p.read_text(encoding="utf-8")) for p in args.bundles
            ]
            candidates = LabelExtractor().extract(bundles)
            revision = assemble(
                bundles,
                candidates,
                project_id=args.project,
                equipment_id=args.equipment,
                revision=args.revision,
                dataset="synthetic" if args.synthetic else "real",
            )
            write_json(revision.model_dump(mode="json"), args.output)
        elif args.command == "approve":
            from .review import approve

            originals = {}
            for item in args.original:
                key, separator, path = item.partition("=")
                if not separator:
                    raise ValueError("Original debe tener formato ID=ruta")
                originals[key] = Path(path).read_bytes()
            revision = approve(load_revision(args.input), args.reviewer, originals)
            write_json(revision.model_dump(mode="json"), args.output)
        elif args.command == "serve":
            app = Path(__file__).with_name("app.py")
            return subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(app),
                    "--server.port",
                    str(args.port),
                    "--server.address",
                    "127.0.0.1",
                    "--server.headless",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                ]
            )
        else:
            from .ifc import export_ifc

            destination = export_ifc(
                load_revision(args.input), args.output, draft=args.draft, schema=args.schema
            )
            print(f"IFC generado: {destination}")
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0
