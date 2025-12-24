#!/usr/bin/env python3
import requests
from tqdm import tqdm


def download_file(url, destination):
    # Send a HEAD request to get the total size of the file
    response = requests.head(url)
    total_size_in_bytes = int(response.headers.get("content-length", 0))

    # Initialize the progress bar with the total size
    progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)

    # Send a GET request to download the file in chunks
    response = requests.get(url, stream=True)
    with open(destination, "wb") as file:
        for data in response.iter_content(chunk_size=1024):
            progress_bar.update(len(data))
            file.write(data)

    # Close the progress bar when done
    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR, something went wrong")


if __name__ == "__main__":
    url = "https://example.com/file.zip"
    destination = "/path/to/save/file.zip"
    download_file(url, destination)
