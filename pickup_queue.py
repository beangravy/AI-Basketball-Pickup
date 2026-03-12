import json
import os


QUEUE_FILE = "queue.json"


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)


def parse_names(text):
    return [name.strip() for name in text.split(",") if name.strip()]


def show_queue(queue):
    if not queue:
        print("Queue is empty.")
        return
    print("Current queue:")
    for i, name in enumerate(queue, start=1):
        print(f"{i}. {name}")


def take_next(queue, count, remove):
    if not queue:
        print("Queue is empty.")
        return
    count = max(1, min(count, len(queue)))
    next_players = queue[:count]
    label = "Next up" if not remove else "Called to play"
    print(f"{label} ({count}): {', '.join(next_players)}")
    if remove:
        del queue[:count]


def parse_indices(text):
    cleaned = text.replace(",", " ").split()
    indices = []
    for token in cleaned:
        if not token.isdigit():
            return []
        indices.append(int(token))
    return indices


def select_players(queue, count):
    if not queue:
        print("Queue is empty.")
        return
    count = max(1, min(count, len(queue)))
    show_queue(queue)
    default_indices = list(range(1, count + 1))
    print(f"Default selection: {', '.join(str(i) for i in default_indices)}")
    raw = input("Enter player numbers to play (blank for default): ").strip()
    if not raw:
        indices = default_indices
    else:
        indices = parse_indices(raw)
        if not indices:
            print("Invalid input. Use numbers separated by spaces or commas.")
            return
        if len(set(indices)) != len(indices):
            print("Duplicate numbers detected.")
            return
        if any(i < 1 or i > len(queue) for i in indices):
            print("One or more numbers are out of range.")
            return

    players = [queue[i - 1] for i in indices]
    for i in sorted(indices, reverse=True):
        del queue[i - 1]
    print(f"Selected to play ({len(players)}): {', '.join(players)}")


def main():
    queue = load_queue()
    courts = 1
    print("Pickup Queue")
    print("Type 'help' for commands.")

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()
        arg = " ".join(parts[1:]).strip()

        if cmd in ("quit", "exit"):
            break
        elif cmd == "help":
            print("Commands:")
            print("  add            - Add players (comma-separated)")
            print("  list           - Show full queue")
            print("  courts [1|2]   - Set number of courts running")
            print("  next           - Show next 10 or 20 players (based on courts)")
            print("  callnext       - Remove next 10 or 20 players (based on courts)")
            print("  select         - Pick players by number (defaults to next 10 or 20)")
            print("  peek [n]       - Show next n players (default 5)")
            print("  call [n]       - Remove and show next n players (default 5)")
            print("  remove [n]     - Remove player at position n")
            print("  clear          - Clear the queue")
            print("  save           - Save queue to disk")
            print("  quit           - Exit")
        elif cmd == "add":
            if not arg:
                arg = input("Enter names (comma-separated): ").strip()
            names = parse_names(arg)
            if not names:
                print("No names added.")
            else:
                queue.extend(names)
                print(f"Added {len(names)} player(s).")
        elif cmd == "list":
            show_queue(queue)
        elif cmd == "peek":
            n = int(arg) if arg.isdigit() else 5
            take_next(queue, n, remove=False)
        elif cmd == "courts":
            if arg not in ("1", "2"):
                print(f"Courts currently set to {courts}. Use: courts 1 or courts 2")
            else:
                courts = int(arg)
                print(f"Courts set to {courts}.")
        elif cmd == "next":
            n = 10 * courts
            take_next(queue, n, remove=False)
        elif cmd == "callnext":
            n = 10 * courts
            take_next(queue, n, remove=True)
        elif cmd == "select":
            n = 10 * courts
            select_players(queue, n)
        elif cmd == "call":
            n = int(arg) if arg.isdigit() else 5
            take_next(queue, n, remove=True)
        elif cmd == "remove":
            if not arg.isdigit():
                print("Usage: remove [n]")
                continue
            idx = int(arg)
            if idx < 1 or idx > len(queue):
                print("Invalid position.")
            else:
                removed = queue.pop(idx - 1)
                print(f"Removed {removed}.")
        elif cmd == "clear":
            queue.clear()
            print("Queue cleared.")
        elif cmd == "save":
            save_queue(queue)
            print("Queue saved.")
        else:
            print("Unknown command. Type 'help' for commands.")

    save_queue(queue)


if __name__ == "__main__":
    main()
