#!/usr/bin/env python3

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        # Trigger the callback when a file is modified
        if not event.is_directory:
            self.callback(event.src_path)

    def on_created(self, event):
        # Trigger the callback when a new file is created
        if not event.is_directory:
            self.callback(event.src_path)

def watch_folder(path, callback):
    event_handler = ChangeHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    def my_callback(file_path):
        print(f'File changed: {file_path}')

    watch_folder('/path/to/watch', my_callback)