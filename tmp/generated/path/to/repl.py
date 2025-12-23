#!/usr/bin/env python3

def repl():
    print("Welcome to the REPL! Type 'help' for commands, 'exit' or 'quit' to leave.")
    while True:
        command = input('> ').strip()
        if command.lower() in ['exit', 'quit']:
            print('Exiting REPL. Goodbye!')
            break
        elif command.lower() == 'help':
            print("Available commands: help, exit, quit")
        else:
            try:
                exec(command)
            except Exception as e:
                print(f'Error executing command: {e}')

if __name__ == '__main__':
    repl()