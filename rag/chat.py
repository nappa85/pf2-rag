import argparse
import sys

from rag.config import OLLAMA_HOST, OLLAMA_MODEL, INDEX_DIR, ALPHA
from rag.retriever import HybridRetriever
from rag.generator import OllamaGenerator
from rag.extract import build_chunks
from rag.index import build_index


def cmd_extract(args):
    build_chunks()


def cmd_index(args):
    build_index()


def cmd_query(args):
    retriever = HybridRetriever(index_dir=INDEX_DIR)
    generator = OllamaGenerator(host=OLLAMA_HOST, model=OLLAMA_MODEL)

    if not generator.check_health():
        print(f"ERROR: Cannot reach Ollama at {OLLAMA_HOST}")
        sys.exit(1)

    results = retriever.search(args.query, top_k=args.top_k, alpha=args.alpha, expand=args.expand)
    if not results:
        print("No results found.")
        return

    print(f"\n{'=' * 60}")
    print(f"Retrieved {len(results)} chunks")
    print(f"{'=' * 60}\n")

    for i, r in enumerate(results):
        print(f"  [{i + 1}] {r['source']} | {r.get('section', '')} (score={r['score']})")

    print(f"\n{'=' * 60}")
    print("Generating answer...")
    print(f"{'=' * 60}\n")

    generator.generate(args.query, results, stream=not args.no_stream)


def cmd_chat(args):
    retriever = HybridRetriever(index_dir=INDEX_DIR)
    generator = OllamaGenerator(host=OLLAMA_HOST, model=args.model or OLLAMA_MODEL)

    if not generator.check_health():
        print(f"ERROR: Cannot reach Ollama at {OLLAMA_HOST}")
        sys.exit(1)

    models = generator.list_models()
    print(f"Ollama connected ({OLLAMA_HOST}) | Model: {generator.model}")
    print(f"Available models: {', '.join(models) if models else 'none listed'}")
    print(f"Index: {INDEX_DIR} | Chunks: {len(retriever.chunks)}")
    print(f"Alpha (dense/sparse balance): {args.alpha}")
    print()
    print("Commands: /sources <query>  = show retrieved chunks only")
    print("          /alpha <0-1>      = adjust dense/sparse balance")
    print("          /model <name>     = switch Ollama model")
    print("          /expand           = toggle query expansion")
    print("          /quit             = exit")
    print()

    alpha = args.alpha
    expand = args.expand

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input == "/quit":
            break

        if user_input.startswith("/alpha"):
            parts = user_input.split()
            if len(parts) == 2:
                try:
                    alpha = float(parts[1])
                    print(f"Alpha set to {alpha}")
                except ValueError:
                    print("Usage: /alpha <0-1>")
            else:
                print(f"Current alpha: {alpha}")
            continue

        if user_input == "/expand":
            expand = not expand
            print(f"Query expansion: {'ON' if expand else 'OFF'}")
            continue

        if user_input.startswith("/model"):
            parts = user_input.split()
            if len(parts) == 2:
                generator.model = parts[1]
                print(f"Model set to {generator.model}")
            else:
                print(f"Current model: {generator.model}")
            continue

        if user_input.startswith("/sources"):
            query = user_input[len("/sources"):].strip()
            if not query:
                print("Usage: /sources <query>")
                continue
            results = retriever.search(query, top_k=args.top_k, alpha=alpha, expand=expand)
            for i, r in enumerate(results):
                print(f"\n--- [{i + 1}] {r['source']} | {r.get('section', '')} (score={r['score']}) ---")
                print(r["text"][:500])
                if len(r["text"]) > 500:
                    print("...")
            continue

        results = retriever.search(user_input, top_k=args.top_k, alpha=alpha, expand=expand)

        sources = [f"{r['source']}:{r.get('section', '')}" for r in results[:3]]
        print(f"\n  Sources: {', '.join(sources)}")
        print()

        generator.generate(user_input, results, stream=True)
        print()


def main():
    parser = argparse.ArgumentParser(prog="rag", description="Pathfinder 2e RAG System")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("extract", help="Extract and chunk PDFs")
    sub.add_parser("index", help="Build FAISS + BM25 index")

    q_parser = sub.add_parser("query", help="Single query")
    q_parser.add_argument("query", help="Query text")
    q_parser.add_argument("--top-k", type=int, default=5)
    q_parser.add_argument("--alpha", type=float, default=ALPHA)
    q_parser.add_argument("--no-stream", action="store_true")
    q_parser.add_argument("--no-expand", dest="expand", action="store_false", help="Disable query expansion")
    q_parser.set_defaults(expand=True)

    c_parser = sub.add_parser("chat", help="Interactive chat")
    c_parser.add_argument("--top-k", type=int, default=5)
    c_parser.add_argument("--alpha", type=float, default=ALPHA)
    c_parser.add_argument("--model", type=str, default=None)
    c_parser.add_argument("--no-expand", dest="expand", action="store_false", help="Disable query expansion")
    c_parser.set_defaults(expand=True)

    args = parser.parse_args()

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "index":
        cmd_index(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "chat":
        cmd_chat(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
