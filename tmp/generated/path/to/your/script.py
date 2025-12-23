#!/usr/bin/env python3

import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            print(f'File {event.src_path} has been modified.')
            self.callback(event)

    def on_created(self, event):
        if not event.is_directory:
            print(f'File {event.src_path} has been created.')
            self.callback(event)

    def on_deleted(self, event):
        if not event.is_directory:
            print(f'File {event.src_path} has been deleted.')
            self.callback(event)

def watch_folder(path, callback):
    observer = Observer()
    event_handler = ChangeHandler(callback)
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def my_callback(event):
    print(f'Callback triggered for event: {event.event_type} on file {event.src_path}')

if __name__ == '__main__':
    folder_to_watch = '/path/to/watch'
    watch_folder(folder_to_watch, my_callback)
