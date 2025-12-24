#!/usr/bin/env python3
import sys
import webbrowser


def open_url(url):
    """
    Open a URL in the user's preferred browser.
    Args:
        url (str): The URL to open.
    Returns:
        None
    Raises:
        ValueError: If the URL is not valid.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL")
    webbrowser.open(url)


def main():
    if len(sys.argv) != 2:
        print("Usage: python cli_open_url.py <URL>")
        sys.exit(1)
    url = sys.argv[1]
    try:
        open_url(url)
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
