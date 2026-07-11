from .stt import run_once


def main() -> None:
    print("Sona Speech-to-Text Test\n")
    print("Press Enter to record for 5 seconds.")
    print("Type q and press Enter to quit.\n")
    while True:
        try:
            reply = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if reply == "q":
            return
        run_once()
        print()


if __name__ == "__main__":
    main()

