import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


DEFAULT_ANALYSIS = Path("data/analysis/analysis_summary.json")
DEFAULT_TABLE = Path("data/final/app_research_final.json")
DEFAULT_VERIFICATION = Path("data/processed/verification_summary.json")
DEFAULT_TEMPLATE = Path("web/templates/microsite.html.j2")
DEFAULT_OUTPUT = Path("web/case_study.html")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_case_study(
    analysis_path: Path,
    table_path: Path,
    verification_path: Path,
    template_path: Path,
    output_path: Path,
) -> None:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_path.name)
    analysis_json = json.dumps(load_json(analysis_path))
    table_json = json.dumps(load_json(table_path))
    verification_json = json.dumps(load_json(verification_path))

    pages = [
        ("home", "Composio Analyzer | Agentic Integration Research", Path("index.html"), ""),
        ("dataset", "Dataset | Composio Analyzer", Path("dataset/index.html"), "../"),
        ("workflow", "Workflow | Composio Analyzer", Path("workflow/index.html"), "../"),
        ("home", "Composio Analyzer | Agentic Integration Research", Path("web/composio-analyzer/index.html"), ""),
        ("dataset", "Dataset | Composio Analyzer", Path("web/composio-analyzer/dataset/index.html"), "../"),
        ("workflow", "Workflow | Composio Analyzer", Path("web/composio-analyzer/workflow/index.html"), "../"),
        ("home", "Composio Analyzer | Agentic Integration Research", output_path, "composio-analyzer/"),
        ("home", "Composio Analyzer | Agentic Integration Research", Path("../index.html"), ""),
        ("dataset", "Dataset | Composio Analyzer", Path("../dataset/index.html"), "../"),
        ("workflow", "Workflow | Composio Analyzer", Path("../workflow/index.html"), "../"),
    ]

    for page, title, path, base_path in pages:
        html = template.render(
            page=page,
            title=title,
            base_path=base_path,
            analysis_json=analysis_json,
            table_json=table_json,
            verification_json=verification_json,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    Path("web/index.html").write_text(
        """<!doctype html><html><head><meta charset=\"utf-8\"><meta http-equiv=\"refresh\" content=\"0; url=./composio-analyzer/index.html\"><title>Composio Analyzer</title></head><body><a href=\"./composio-analyzer/index.html\">Open Composio Analyzer</a></body></html>""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the self-contained HTML case study.")
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    build_case_study(args.analysis, args.table, args.verification, args.template, args.output)
    print("Wrote microsite pages to web/composio-analyzer/, /dataset/, and /workflow/")
    print(f"Wrote compatibility overview page to {args.output}")


if __name__ == "__main__":
    main()
