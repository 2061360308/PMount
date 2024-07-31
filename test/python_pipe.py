import sys


def main():
    print("Listener process is running. Waiting for input...")
    for line in sys.stdin:
        print(f"Received message: {line.strip()}")


if __name__ == "__main__":
    main()
