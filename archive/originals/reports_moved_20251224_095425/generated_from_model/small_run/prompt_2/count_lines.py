#!/usr/bin/env python3
import argparse
import os


def count_lines(file_path):
    """Count the number of lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return sum(1 for line in file)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None


def main():
    """Main function to handle command-line arguments and execute line count."""
    parser = argparse.ArgumentParser(description='Count the number of lines in a file.')
    parser.add_argument('file_path', type=str, help='Path to the file')
    args = parser.parse_args()

    line_count = count_lines(args.file_path)
    if line_count is not None:
        print(f"Number of lines: {line_count}")


if __name__ == '__main__':
    main()