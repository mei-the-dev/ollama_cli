#!/usr/bin/env python3
import requests
from tqdm import tqdm

def download_file(url, destination):
    # Send a HEAD request to get the total size of the file
    response = requests.head(url)
    total_size = int(response.headers.get('content-length', 0))
    
    # Initialize a progress bar with the total size
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
    
    # Send a GET request to download the file in chunks
    response = requests.get(url, stream=True)
    with open(destination, 'wb') as f:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            progress_bar.update(size)
    
    # Close the progress bar after download is complete
    progress_bar.close()
    if total_size != 0 and progress_bar.n != total_size:
        print(f"ERROR, something went wrong. Downloaded {progress_bar.n} bytes instead of {total_size}")

if __name__ == '__main__':
    url = 'https://example.com/largefile.zip'
    destination = '/path/to/save/largefile.zip'
    download_file(url, destination)
