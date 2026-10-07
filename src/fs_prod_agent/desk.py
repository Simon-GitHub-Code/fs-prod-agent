"""Open the local oversight desk in a browser: uv run python -m fs_prod_agent.desk

The page is http://127.0.0.1:8766.
"""

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local oversight desk.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--model", default=None, help="an Ollama Cloud model, e.g. gpt-oss:120b; needs OLLAMA_API_KEY")
    parser.add_argument("--otlp", default=None, help="an OTLP endpoint for traces, e.g. http://127.0.0.1:4318")
    args = parser.parse_args(argv)
    from fs_prod_agent.composition import serve_desk

    serve_desk(args.host, args.port, args.model, args.otlp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
