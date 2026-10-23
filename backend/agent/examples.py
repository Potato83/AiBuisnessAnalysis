"""Локальное демо: две компании, восемь новостей; режим из .env или --mode."""

import argparse
import json
from pathlib import Path

from .main import generate_insights


# Общие тестовые данные принадлежат data/synthetic, а здесь остаётся пример вызова.
# Путь от файла, а не от текущего каталога: одинаково работает локально и в Docker.
FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "agent_day1.json"
_fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
NEWS = _fixture["news"]
BANK_SOURCES = _fixture["bank_sources"]
COMPANIES = _fixture["companies"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mock", "llm"), default=None,
                        help="Переопределить AGENT_MODE из окружения/файла .env")
    parser.add_argument("--fallback-mock", action="store_true", help="Явно разрешить подмену неудачного LLM-вызова mock")
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH.with_name("agent_day2.json"))
    parser.add_argument("--output", type=Path, help="Записать два полных JSON-результата в файл")
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    results = [generate_insights(
        company, fixture["news"], fixture["bank_sources"],
        mode=args.mode, fallback_to_mock=args.fallback_mock,
    ) for company in fixture["companies"]]
    output = json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
