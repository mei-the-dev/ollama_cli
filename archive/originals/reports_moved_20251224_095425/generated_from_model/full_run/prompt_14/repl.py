#!/usr/bin/env python3


def repl():
    print("Welcome to the REPL! Type 'help' for commands, 'exit' or 'quit' to leave.")
    while True:
        command = input("> ").strip().lower()
        if command in ["exit", "quit"]:
            print("Exiting REPL. Goodbye!")
            break
        elif command == "help":
            print("Available commands:\n  help - Show this help message\n  exit/quit - Exit the REPL")
        else:
            try:
                # Evaluate and execute the command
                result = eval(command)
                print(result)
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    repl()
