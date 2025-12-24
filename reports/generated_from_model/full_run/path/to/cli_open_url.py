#!/usr/bin/env python3
import sys
import webbrowser


def open_url(url):
    """
    Open a URL in the user's preferred browser.

    Args:
        url (str): The URL to open.
    """
    try:
        # Attempt to open the URL using the default web browser
        webbrowser.open(url)
        print(f"Opened {url} in your default browser.")
    except Exception as e:
        print(f"Failed to open {url}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cli_open_url.py <URL>")
        sys.exit(1)
    url = sys.argv[1]
    open_url(url)
