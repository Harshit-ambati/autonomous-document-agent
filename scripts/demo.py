"""Run the actual HTTP API for both assessment cases and download the artifacts."""

import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--case", choices=["standard", "complex", "both"], default="both")
    args = parser.parse_args()
    cases = ["standard", "complex"] if args.case == "both" else [args.case]
    out = ROOT / "outputs" / "demo"
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=args.base_url, timeout=300) as client:
        for case in cases:
            payload = json.loads((ROOT / "examples" / f"{case}.json").read_text(encoding="utf-8"))
            print(f"\n{case.upper()} REQUEST\n{payload['request']}", flush=True)
            response = client.post("/agent", json=payload)
            if response.status_code != 200:
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                raise SystemExit(f"Demo failed: HTTP {response.status_code}. No success is being claimed.")
            result = response.json()
            (out / f"{case}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print("\nAGENT PLAN", flush=True)
            for task in result["plan"]["tasks"]:
                print(f"  {task['id']} | {task['tool']} | {task['title']} | depends on {task['depends_on']}")
            print("\nASSUMPTIONS", *result["document"]["assumptions"], sep="\n  ")
            print("\nCONFLICTS AND DECISIONS", *result["document"]["conflicts"], sep="\n  ")
            print("\nEXECUTION TRACE", flush=True)
            for event in result["trace"]:
                print(f"  {event['status']:9} {event['tool']:18} {event['duration_ms']:6} ms | {event['step']}")
            print(f"\nSELF CHECK: {result['reviews'][-1]['passed']} | Reviews: {len(result['reviews'])}")
            artifact = client.get(result["download_url"])
            artifact.raise_for_status()
            path = out / f"{case}.docx"
            path.write_bytes(artifact.content)
            print(f"WORD DOCUMENT: {path}\nRUN: {result['run_id']} | {result['elapsed_ms']} ms", flush=True)


if __name__ == "__main__":
    main()
