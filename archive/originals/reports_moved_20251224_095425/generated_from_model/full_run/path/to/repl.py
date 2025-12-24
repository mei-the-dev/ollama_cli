#!/usr/bin/env python3


def repl():
    print("Welcome to the interactive REPL! Type 'help' for commands, 'exit' or 'quit' to leave.")
    while True:
        command = input("> ").strip().lower()
        if command in ["exit", "quit"]:
            print("Exiting REPL. Goodbye!")
            break
        elif command == "help":
            print("Available commands:\n  help - Show this help message\n  exit/quit - Exit the REPL")
        else:
            try:
                exec(command)
            except Exception as e:
                print(f"Error executing command: {e}")


if __name__ == "__main__":
    repl()
