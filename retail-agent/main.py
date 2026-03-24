import argparse
from pathlib import Path

from modules.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(description="Retail Analytics Agent")
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--query", "-q", required=True, help="User query")
    parser.add_argument("--target", "-t", help="Target column for explanation")
    parser.add_argument("--model", "-m", default="retail-analyst", help="Ollama model name")
    parser.add_argument("--output", "-o", default="report.md", help="Output markdown file")
    args = parser.parse_args()

    agent = Orchestrator(
        csv_path=args.csv,
        user_query=args.query,
        target_col=args.target,
        llm_model=args.model,
    )
    report = agent.run()

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report saved to {output_path}")


if __name__ == "__main__":
    main()
