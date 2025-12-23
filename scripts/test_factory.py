#!/usr/bin/env python3
"""Simple CLI to generate tests from TestSpec instances.

Usage:
    python scripts/test_factory.py generate
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.factory.spec import TestSpec
from tests.factory.generator import write_test_from_spec

EXAMPLES_DIR = ROOT / 'tests' / 'factory_converted'
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_SPECS = [
    TestSpec(
        name='code_mode_loader',
        description='Code-mode: generate an animated loader component',
        markers=['fast'],
        intent='Model interaction recorded',
        interaction='agent',
        input_prompt='generate an animated ux loading component',
        expected_contains=['<svg', 'animated']
    ),
    TestSpec(
        name='parsed_tool_write_code',
        description='Parsed tool: model should emit write_code tool',
        markers=['fast'],
        intent='Model interaction recorded',
        input_prompt='write a file with content hello',
        expected_contains=['write_code']
    ),
    TestSpec(
        name='stream_fragmented_json',
        description='Streaming: receives fragmented json and assembles into tool call',
        markers=['fast'],
        intent='Model interaction recorded',
        input_prompt='send fragmented json for write_code',
        expected_contains=['write_code']
    ),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('cmd', choices=['generate'])
    args = p.parse_args()

    if args.cmd == 'generate':
        for s in SAMPLE_SPECS:
            p = write_test_from_spec(s, EXAMPLES_DIR)
            print('Wrote', p)


if __name__ == '__main__':
    main()
