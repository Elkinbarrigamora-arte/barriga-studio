#!/usr/bin/env python3
"""Barriga Studio: safe server-side fal image-to-video proof of integration.

Default mode is dry-run. Only --execute submits a potentially billable request.
Never put FAL_KEY in web pages, JavaScript, Git or JSON project backups.
"""
import argparse
import json
import os
import sys

MODEL = "fal-ai/wan/v2.2-5b/image-to-video"


def prepare(image_url, prompt):
    if not image_url.startswith("https://"):
        raise ValueError("image_url must start with https://")
    if not prompt.strip():
        raise ValueError("prompt cannot be empty")
    return {"image_url": image_url, "prompt": prompt.strip()}


def main():
    p = argparse.ArgumentParser(description="fal video cloud integration (safe dry-run)")
    p.add_argument("--image-url", required=True, help="HTTPS URL of reference image")
    p.add_argument("--prompt", required=True, help="Action/motion description")
    p.add_argument("--execute", action="store_true", help="Submit billable generation (explicit opt-in)")
    p.add_argument("--output", default="", help="Write resulting metadata to JSON file")
    args = p.parse_args()
    data = prepare(args.image_url, args.prompt)
    if not args.execute:
        print(json.dumps({"mode": "dry-run", "model": MODEL, "input": data,
                          "message": "No API call and no charge. Pass --execute to generate."},
                         ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FAL_KEY"):
        print("Missing FAL_KEY environment variable; nothing submitted.", file=sys.stderr)
        return 2
    try:
        import fal_client
    except ImportError:
        print("Install SDK: python3 -m pip install fal-client", file=sys.stderr)
        return 2
    print("Submitting a chargeable generation to fal.ai...", file=sys.stderr)
    result = fal_client.subscribe(MODEL, arguments=data)
    video_url = (result.get("video") or {}).get("url")
    if not video_url:
        print("No video URL in response; check provider result.", file=sys.stderr)
        return 1
    output = {"model": MODEL, "video_url": video_url, "response": result}
    if args.output:
        # Store output only in a PRIVATE local directory, never in public Git.
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
    print(json.dumps({"model": MODEL, "video_url": video_url}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
