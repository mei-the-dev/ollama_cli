#!/usr/bin/env python3
import argparse


def parse_args(argv):
    # Create the main parser
    parser = argparse.ArgumentParser(description="A script with subcommands.")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommands")

    # Add 'init' subcommand
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("--project-name", type=str, required=True, help="Name of the project")

    # Add 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run the project")
    run_parser.add_argument("--config-file", type=str, default="config.json", help="Path to configuration file")

    # Parse arguments
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        exit(1)

    return args


if __name__ == "__main__":
    import sys

    args = parse_args(sys.argv[1:])
    print(args)
