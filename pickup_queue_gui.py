import json
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog


QUEUE_FILE = "queue.json"
GAMES_FILE = "games.json"


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


def load_games():
    if not os.path.exists(GAMES_FILE):
        return {}
    try:
        with open(GAMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): int(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return {}


def save_games(games):
    with open(GAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)


class PickupQueueApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pickup Queue")
        self.queue = load_queue()
        self.games = load_games()
        self.courts = tk.IntVar(value=1)
        self.show_display = tk.BooleanVar(value=False)
        self.add_mode = tk.StringVar(value="first_in")
        self.last_selected_indices = []
        self.last_played_court1 = []
        self.last_played_court2 = []
        self.undo_snapshot = None
        self.added_since_play = []
        self.pending_after_play = []
        self.drag_played_source = None
        self.drag_played_index = None
        self.display_window = None
        self.display_queue = None
        self.display_court1 = None
        self.display_court2 = None
        self.display_queue_font = ("Helvetica", 16)
        self.locked = False
        self.lock_code = "6600"
        self.lock_controls = []

        self._build_ui()
        self.refresh_list()
        self.refresh_played()

    def _build_ui(self):
        self.root.geometry("900x700")

        top = tk.Frame(self.root, padx=10, pady=10)
        top.pack(fill=tk.X)

        tk.Label(top, text="Add players (comma-separated):").pack(anchor="w")
        self.entry = tk.Entry(top)
        self.entry.pack(fill=tk.X, pady=4)
        self.entry.bind("<Return>", lambda _e: self.add_players())

        btn_row = tk.Frame(top)
        btn_row.pack(fill=tk.X, pady=4)
        btn_add = tk.Button(btn_row, text="Add", command=self.add_players)
        btn_add.pack(side=tk.LEFT)
        btn_clear = tk.Button(btn_row, text="Clear Queue", command=self.clear_queue)
        btn_clear.pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="Save", command=self.save).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Unlock", command=self.unlock_controls).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="Lock", command=self.lock_controls_ui).pack(side=tk.LEFT)

        add_row = tk.Frame(top)
        add_row.pack(fill=tk.X, pady=4)
        tk.Label(add_row, text="Add position:").pack(side=tk.LEFT)
        rb_first = tk.Radiobutton(
            add_row, text="First In", variable=self.add_mode, value="first_in"
        )
        rb_first.pack(side=tk.LEFT, padx=6)
        rb_after = tk.Radiobutton(
            add_row, text="After Sitting", variable=self.add_mode, value="after_sitting"
        )
        rb_after.pack(side=tk.LEFT)

        court_row = tk.Frame(top)
        court_row.pack(fill=tk.X, pady=4)
        tk.Label(court_row, text="Courts running:").pack(side=tk.LEFT)
        tk.Radiobutton(court_row, text="1 Court", variable=self.courts, value=1).pack(side=tk.LEFT, padx=6)
        tk.Radiobutton(court_row, text="2 Courts", variable=self.courts, value=2).pack(side=tk.LEFT)
        tk.Button(court_row, text="Select Next 10/20", command=self.select_next).pack(side=tk.LEFT, padx=10)
        tk.Button(court_row, text="Play", command=self.play_selected).pack(side=tk.LEFT)
        tk.Button(court_row, text="Undo Play", command=self.undo_play).pack(side=tk.LEFT, padx=6)
        tk.Checkbutton(
            court_row,
            text="Show Display",
            variable=self.show_display,
            command=self.toggle_display,
        ).pack(side=tk.LEFT, padx=6)

        mid = tk.Frame(self.root, padx=10, pady=6)
        mid.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(mid)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = tk.Frame(mid)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(left, text="Current Queue:").pack(anchor="w")
        self.listbox = tk.Listbox(left, height=15)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<Button-1>", self.on_click)
        self.listbox.bind("<B1-Motion>", self.on_drag)
        self.listbox.bind("<ButtonRelease-1>", self.on_drop)
        self.drag_index = None
        self.drag_target = None

        tk.Label(right, text="On Courts (Last Play):").pack(anchor="w")
        played_row = tk.Frame(right)
        played_row.pack(fill=tk.BOTH, expand=True)

        court1 = tk.Frame(played_row)
        court1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        court2 = tk.Frame(played_row)
        court2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(court1, text="Court 1").pack(anchor="w")
        self.played_listbox_1 = tk.Listbox(court1, height=15, exportselection=False)
        self.played_listbox_1.pack(fill=tk.BOTH, expand=True)
        self.played_listbox_1.bind("<Button-1>", lambda e: self.on_played_click(e, 1))
        self.played_listbox_1.bind(
            "<ButtonRelease-1>", lambda e: self.on_played_drop(e, 1)
        )

        tk.Label(court2, text="Court 2").pack(anchor="w")
        self.played_listbox_2 = tk.Listbox(court2, height=15, exportselection=False)
        self.played_listbox_2.pack(fill=tk.BOTH, expand=True)
        self.played_listbox_2.bind("<Button-1>", lambda e: self.on_played_click(e, 2))
        self.played_listbox_2.bind(
            "<ButtonRelease-1>", lambda e: self.on_played_drop(e, 2)
        )

        swap_row = tk.Frame(right)
        swap_row.pack(fill=tk.X, pady=(6, 0))
        tk.Button(swap_row, text="Swap Selected", command=self.swap_selected_courts).pack(
            side=tk.LEFT
        )

        bottom = tk.Frame(self.root, padx=10, pady=10)
        bottom.pack(fill=tk.X)

        btn_clear_selection = tk.Button(
            bottom, text="Clear Selection", command=self.clear_selection
        )
        btn_clear_selection.pack(side=tk.LEFT)
        btn_remove = tk.Button(bottom, text="Remove Selected", command=self.remove_selected)
        btn_remove.pack(side=tk.LEFT, padx=6)
        btn_rename = tk.Button(bottom, text="Rename", command=self.rename_selected)
        btn_rename.pack(side=tk.LEFT)

        self.lock_controls = [
            btn_clear,
            rb_first,
            rb_after,
            btn_clear_selection,
            btn_remove,
            btn_rename,
        ]
        self.apply_lock_state()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, name in enumerate(self.queue, start=1):
            games = self.games.get(name, 0)
            self.listbox.insert(tk.END, f"{i}. {name} ({games})")
        self.listbox.selection_clear(0, tk.END)
        self.last_selected_indices = []
        self.refresh_display()

    def refresh_played(self):
        self.played_listbox_1.delete(0, tk.END)
        for i, name in enumerate(self.last_played_court1, start=1):
            games = self.games.get(name, 0)
            self.played_listbox_1.insert(tk.END, f"{i}. {name} ({games})")
        self.played_listbox_2.delete(0, tk.END)
        for i, name in enumerate(self.last_played_court2, start=1):
            games = self.games.get(name, 0)
            self.played_listbox_2.insert(tk.END, f"{i}. {name} ({games})")
        self.refresh_display()

    def add_players(self):
        if self.locked:
            messagebox.showinfo("Locked", "Unlock to add players.")
            return
        raw = self.entry.get().strip()
        if not raw:
            return
        names = [n.strip() for n in raw.split(",") if n.strip()]
        if not names:
            return
        existing = set(self.games.keys())
        dupes = [n for n in names if n in existing]
        if dupes:
            messagebox.showinfo(
                "Duplicate Names",
                "These names already exist and were not added:\n"
                + ", ".join(dupes),
            )
            names = [n for n in names if n not in existing]
            if not names:
                return
        for name in names:
            if name not in self.games:
                self.games[name] = 0
        self.added_since_play.extend(names)
        insert_at = self._get_insert_index()
        self.queue[insert_at:insert_at] = names
        self.entry.delete(0, tk.END)
        self.refresh_list()

    def clear_selection(self):
        if self.locked:
            messagebox.showinfo("Locked", "Unlock to clear the selection.")
            return
        self.last_selected_indices = []
        self.listbox.selection_clear(0, tk.END)

    def remove_selected(self):
        if self.locked:
            messagebox.showinfo("Locked", "Unlock to remove players.")
            return
        sel = list(self.listbox.curselection())
        if not sel:
            return
        names = [self.queue[i] for i in sel if i < len(self.queue)]
        label = names[0] if len(names) == 1 else f"{len(names)} players"
        if not messagebox.askyesno(
            "Remove Selected", f"Remove {label} from the queue?"
        ):
            return
        for i in sorted(sel, reverse=True):
            del self.queue[i]
        self.refresh_list()

    def move_selected(self, direction):
        if self.locked:
            messagebox.showinfo("Locked", "Unlock to move players.")
            return
        sel = list(self.listbox.curselection())
        if len(sel) != 1:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.queue):
            return
        self.queue[idx], self.queue[new_idx] = self.queue[new_idx], self.queue[idx]
        self.refresh_list()
        self.listbox.selection_set(new_idx)

    def rename_selected(self):
        sel = list(self.listbox.curselection())
        if len(sel) != 1:
            messagebox.showinfo("Rename", "Select one player to rename.")
            return
        idx = sel[0]
        old_name = self.queue[idx]
        new_name = simpledialog.askstring("Rename", f"Edit name for: {old_name}")
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        if new_name != old_name and new_name in self.games:
            messagebox.showinfo("Rename", "That name already exists.")
            return
        self.queue[idx] = new_name
        if old_name in self.games:
            self.games[new_name] = self.games.pop(old_name)
        for i, name in enumerate(self.last_played_court1):
            if name == old_name:
                self.last_played_court1[i] = new_name
        for i, name in enumerate(self.last_played_court2):
            if name == old_name:
                self.last_played_court2[i] = new_name
        self.added_since_play = [
            new_name if n == old_name else n for n in self.added_since_play
        ]
        self.pending_after_play = [
            new_name if n == old_name else n for n in self.pending_after_play
        ]
        self.refresh_list()
        self.refresh_played()

    def on_click(self, event):
        self.drag_index = self.listbox.nearest(event.y)
        self.drag_target = None

    def on_drag(self, event):
        if self.drag_index is None:
            return
        self.drag_target = self.listbox.nearest(event.y)

    def on_drop(self, _event):
        if self.drag_index is None or self.drag_target is None:
            self.drag_index = None
            self.drag_target = None
            return
        if self.drag_target == self.drag_index:
            self.drag_index = None
            self.drag_target = None
            return
        if self.drag_target < 0 or self.drag_target >= len(self.queue):
            self.drag_index = None
            self.drag_target = None
            return
        if self.locked:
            messagebox.showinfo("Locked", "Unlock to reorder the queue.")
            self.drag_index = None
            self.drag_target = None
            return
        confirm = messagebox.askyesno(
            "Reorder Queue",
            "Move the selected player to the new position?",
        )
        if confirm:
            item = self.queue.pop(self.drag_index)
            self.queue.insert(self.drag_target, item)
            self.refresh_list()
            self.listbox.selection_set(self.drag_target)
        self.drag_index = None
        self.drag_target = None

    def on_played_click(self, event, court):
        listbox = self.played_listbox_1 if court == 1 else self.played_listbox_2
        idx = listbox.nearest(event.y)
        names = self.last_played_court1 if court == 1 else self.last_played_court2
        if idx < 0 or idx >= len(names):
            self.drag_played_source = None
            self.drag_played_index = None
            return
        self.drag_played_source = court
        self.drag_played_index = idx

    def on_played_drop(self, event, court):
        if self.drag_played_source is None or self.drag_played_index is None:
            return
        if self.drag_played_source == court:
            return
        target_list = (
            self.played_listbox_1 if court == 1 else self.played_listbox_2
        )
        target_idx = target_list.nearest(event.y)
        source_list = (
            self.last_played_court1
            if self.drag_played_source == 1
            else self.last_played_court2
        )
        dest_list = self.last_played_court1 if court == 1 else self.last_played_court2
        if target_idx < 0 or target_idx >= len(dest_list):
            return
        source_list[self.drag_played_index], dest_list[target_idx] = (
            dest_list[target_idx],
            source_list[self.drag_played_index],
        )
        self.drag_played_source = None
        self.drag_played_index = None
        self.refresh_played()

    def _get_insert_index(self):
        mode = self.add_mode.get()
        if mode == "first_in":
            last_zero = -1
            for i, name in enumerate(self.queue):
                if self.games.get(name, 0) == 0:
                    last_zero = i
            return last_zero + 1
        if mode == "after_sitting":
            on_court = self.last_played_court1 + self.last_played_court2
            if not on_court:
                return len(self.queue)
            count_on_court = len(on_court)
            return max(0, len(self.queue) - count_on_court)
        return len(self.queue)

    def clear_queue(self):
        if self.locked:
            messagebox.showinfo("Locked", "Unlock to clear the queue.")
            return
        if messagebox.askyesno("Clear Queue", "Clear the entire queue?"):
            self.queue.clear()
            self.games.clear()
            self.last_played_court1 = []
            self.last_played_court2 = []
            self.undo_snapshot = None
            self.added_since_play = []
            self.pending_after_play = []
            self.refresh_list()
            self.refresh_played()

    def select_next(self):
        count = 10 * self.courts.get()
        if not self.queue:
            messagebox.showinfo("Select Next", "Queue is empty.")
            return
        count = min(count, len(self.queue))
        self.last_selected_indices = list(range(count))
        self.listbox.selection_clear(0, tk.END)
        for i in self.last_selected_indices:
            self.listbox.selection_set(i)

    def play_selected(self):
        if not self.last_selected_indices:
            messagebox.showinfo("Play", "No players selected. Use Select Next 10/20 first.")
            return
        self.undo_snapshot = {
            "queue": list(self.queue),
            "games": dict(self.games),
            "court1": list(self.last_played_court1),
            "court2": list(self.last_played_court2),
        }
        self.added_since_play = []
        selected_players = [self.queue[i] for i in self.last_selected_indices]
        for name in selected_players:
            self.games[name] = self.games.get(name, 0) + 1
        for i in sorted(self.last_selected_indices, reverse=True):
            del self.queue[i]
        self.queue.extend(selected_players)
        if self.pending_after_play:
            insert_at = self._get_insert_index()
            self.queue[insert_at:insert_at] = list(self.pending_after_play)
            self.pending_after_play = []
        if self.courts.get() == 2:
            self.last_played_court1 = list(selected_players[:10])
            self.last_played_court2 = list(selected_players[10:20])
        else:
            self.last_played_court1 = list(selected_players)
            self.last_played_court2 = []
        self.refresh_list()
        self.refresh_played()

    def swap_selected_courts(self):
        sel1 = list(self.played_listbox_1.curselection())
        sel2 = list(self.played_listbox_2.curselection())
        if len(sel1) != 1 or len(sel2) != 1:
            messagebox.showinfo(
                "Swap Selected", "Select one player in each court list to swap."
            )
            return
        i = sel1[0]
        j = sel2[0]
        if i >= len(self.last_played_court1) or j >= len(self.last_played_court2):
            return
        self.last_played_court1[i], self.last_played_court2[j] = (
            self.last_played_court2[j],
            self.last_played_court1[i],
        )
        self.refresh_played()
        self.played_listbox_1.selection_set(i)
        self.played_listbox_2.selection_set(j)

    def undo_play(self):
        if not self.undo_snapshot:
            return
        choice = "none"
        if self.added_since_play:
            choice = messagebox.askquestion(
                "Undo Play",
                "Add players who joined after the last Play now?",
            )
        self.queue = list(self.undo_snapshot["queue"])
        if choice == "yes":
            insert_at = self._get_insert_index()
            self.queue[insert_at:insert_at] = list(self.added_since_play)
        elif choice == "no" and self.added_since_play:
            if messagebox.askyesno(
                "Undo Play",
                "Add those players after the next Play instead?",
            ):
                self.pending_after_play = list(self.added_since_play)
        self.games = dict(self.undo_snapshot["games"])
        self.last_played_court1 = list(self.undo_snapshot["court1"])
        self.last_played_court2 = list(self.undo_snapshot["court2"])
        self.undo_snapshot = None
        self.added_since_play = []
        self.refresh_list()
        self.refresh_played()

    def save(self):
        save_queue(self.queue)
        save_games(self.games)
        messagebox.showinfo("Saved", "Queue saved.")

    def apply_lock_state(self):
        state = tk.DISABLED if self.locked else tk.NORMAL
        for w in self.lock_controls:
            w.config(state=state)

    def unlock_controls(self):
        code = simpledialog.askstring("Unlock", "Enter unlock code:", show="*")
        if code is None:
            return
        if code == self.lock_code:
            self.locked = False
            self.apply_lock_state()
        else:
            messagebox.showinfo("Unlock", "Incorrect code.")

    def lock_controls_ui(self):
        self.locked = True
        self.apply_lock_state()

    def toggle_display(self):
        if self.show_display.get():
            self.open_display()
        else:
            self.close_display()

    def open_display(self):
        if self.display_window is not None:
            return
        win = tk.Toplevel(self.root)
        win.title("Pickup Queue Display")
        win.state("zoomed")
        win.configure(bg="black")
        win.protocol("WM_DELETE_WINDOW", self.close_display)
        win.bind("<Configure>", lambda _e: self.update_display_fonts())
        self.display_window = win

        header = tk.Frame(win, bg="black", padx=20, pady=20)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="On Courts",
            fg="white",
            bg="black",
            font=("Helvetica", 36, "bold"),
        ).pack(anchor="w")

        main_row = tk.Frame(win, bg="black", padx=20, pady=10)
        main_row.pack(fill=tk.BOTH, expand=True)
        main_row.grid_columnconfigure(0, weight=2)
        main_row.grid_columnconfigure(1, weight=1)
        main_row.grid_rowconfigure(0, weight=1)

        courts_row = tk.Frame(main_row, bg="black")
        courts_row.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        queue_frame = tk.Frame(main_row, bg="black")
        queue_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(
            queue_frame,
            text="Current Queue",
            fg="white",
            bg="black",
            font=("Helvetica", 20, "bold"),
        ).pack(anchor="w")
        self.display_queue = tk.Listbox(
            queue_frame,
            bg="black",
            fg="white",
            highlightthickness=0,
            activestyle="none",
            font=self.display_queue_font,
        )
        self.display_queue.pack(fill=tk.BOTH, expand=True)

        court1 = tk.Frame(courts_row, bg="black")
        court1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        court2 = tk.Frame(courts_row, bg="black")
        court2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        tk.Label(
            court1, text="Court 1", fg="white", bg="black", font=("Helvetica", 24, "bold")
        ).pack(anchor="w")
        tk.Label(
            court2, text="Court 2", fg="white", bg="black", font=("Helvetica", 24, "bold")
        ).pack(anchor="w")

        self.display_court1 = tk.Listbox(
            court1,
            bg="black",
            fg="white",
            highlightthickness=0,
            activestyle="none",
            font=("Helvetica", 48, "bold"),
        )
        self.display_court1.pack(fill=tk.BOTH, expand=True)

        self.display_court2 = tk.Listbox(
            court2,
            bg="black",
            fg="white",
            highlightthickness=0,
            activestyle="none",
            font=("Helvetica", 48, "bold"),
        )
        self.display_court2.pack(fill=tk.BOTH, expand=True)

        self.refresh_display()

    def close_display(self):
        if self.display_window is None:
            return
        try:
            self.display_window.destroy()
        finally:
            self.display_window = None
            self.display_queue = None
            self.display_court1 = None
            self.display_court2 = None
            self.show_display.set(False)

    def update_display_fonts(self):
        if self.display_queue is None:
            return
        height = self.display_queue.winfo_height()
        width = self.display_queue.winfo_width()
        if height <= 1 or width <= 1:
            return
        n = max(1, len(self.queue))
        max_name_len = max((len(name) for name in self.queue), default=1)
        size_by_height = int((height / n) * 0.8)
        size_by_width = int(width / max(1, int(max_name_len * 0.6)))
        size = max(10, min(20, size_by_height, size_by_width))
        font = ("Helvetica", size)
        if font != self.display_queue_font:
            self.display_queue_font = font
            self.display_queue.config(font=font)

    def refresh_display(self):
        if self.display_window is None:
            return
        if self.display_court1 is not None:
            self.display_court1.delete(0, tk.END)
            for name in self.last_played_court1:
                self.display_court1.insert(tk.END, name)
        if self.display_court2 is not None:
            self.display_court2.delete(0, tk.END)
            for name in self.last_played_court2:
                self.display_court2.insert(tk.END, name)
        if self.display_queue is not None:
            self.display_queue.delete(0, tk.END)
            for i, name in enumerate(self.queue, start=1):
                self.display_queue.insert(tk.END, f"{i}. {name}")
        self.update_display_fonts()


def main():
    root = tk.Tk()
    app = PickupQueueApp(root)
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: (save_queue(app.queue), save_games(app.games), root.destroy()),
    )
    root.mainloop()


if __name__ == "__main__":
    main()
