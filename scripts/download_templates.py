#!/usr/bin/env python3
"""Download DP-GEN example templates from GitHub and save to local template dir.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""
import json
import os
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/deepmodeling/dpgen/master"
TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "dpgen_lsp", "templates")

INDEX_PATH = os.path.join(TEMPLATE_ROOT, "index.json")

def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        try:
            json.loads(data)
            print(f"  OK: {dest}")
        except json.JSONDecodeError as e:
            print(f"  JSON ERROR: {dest}: {e}")
    except Exception as e:
        print(f"  FAIL: {url} -> {dest}: {e}")

def main():
    with open(INDEX_PATH) as f:
        index = json.load(f)

    for entry in index.get("param", []):
        upstream = entry["upstream_path"]
        resource = entry["resource"]
        url = f"{BASE_URL}/{upstream}"
        dest = os.path.join(TEMPLATE_ROOT, resource)
        print(f"Downloading param: {upstream}")
        download(url, dest)

    for entry in index.get("machine", []):
        upstream = entry["upstream_path"]
        resource = entry["resource"]
        url = f"{BASE_URL}/{upstream}"
        dest = os.path.join(TEMPLATE_ROOT, resource)
        print(f"Downloading machine: {upstream}")
        download(url, dest)

    print("\nDone.")

if __name__ == "__main__":
    main()
