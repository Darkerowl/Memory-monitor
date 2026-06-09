"""
Lightweight Memory Monitor
A small Tkinter RAM monitor with a top-memory-process readout.

Requirements:
    pip install psutil
"""

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk

import psutil


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

APP_VERSION = "1.3.5"

WINDOW_TITLE = f"Memory Monitor v{APP_VERSION}"
WINDOW_SIZE = "280x120"

GUI_REFRESH_MS = 1000          # How often the window redraws text/bar.
RAM_REFRESH_SECONDS = 2.0      # How often RAM usage is checked.
TOP_REFRESH_SECONDS = 10.0     # How often top memory process is scanned.

PAUSE_UPDATES_WHILE_MOVING = True  # Prevents visual stutter while dragging.
MOVE_PAUSE_MS = 700                # How long to pause updates after movement.

TOP_NAME_LIMIT = 22

FONT_MAIN = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)


# ---------------------------------------------------------------------------
# SHARED STATE
# ---------------------------------------------------------------------------

stats_queue = queue.Queue(maxsize=1)
stop_event = threading.Event()

last_window_move_time = 0.0


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def bytes_to_mb(byte_count: int) -> float:
    return byte_count / (1024 * 1024)


def shorten_name(name: str, limit: int) -> str:
    if len(name) <= limit:
        return name

    return name[: limit - 3] + "..."


def put_latest_snapshot(snapshot: dict) -> None:
    try:
        stats_queue.put(snapshot, block=False)
    except queue.Full:
        try:
            stats_queue.get_nowait()
        except queue.Empty:
            pass

        stats_queue.put(snapshot, block=False)


def get_top_process() -> tuple[str, int] | None:
    top_name: str | None = None
    top_memory = 0

    for process in psutil.process_iter(
        attrs=["pid", "name", "memory_info"],
        ad_value=None,
    ):
        try:
            memory_info = process.info.get("memory_info")

            if memory_info is None:
                continue

            memory_used = memory_info.rss

            if memory_used > top_memory:
                top_memory = memory_used
                top_name = (
                    process.info.get("name")
                    or f"PID {process.info.get('pid', process.pid)}"
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if top_name is None:
        return None

    return top_name, top_memory


# ---------------------------------------------------------------------------
# BACKGROUND MONITOR
# ---------------------------------------------------------------------------

def monitor_loop() -> None:
    last_ram_check = 0.0
    last_top_check = 0.0

    used_mb = 0.0
    total_mb = 0.0
    percent = 0.0
    top_name = "n/a"
    top_mb = 0.0

    while not stop_event.is_set():
        now = time.monotonic()
        snapshot_changed = False

        if now - last_ram_check >= RAM_REFRESH_SECONDS:
            memory = psutil.virtual_memory()

            used_mb = bytes_to_mb(memory.used)
            total_mb = bytes_to_mb(memory.total)
            percent = memory.percent

            last_ram_check = now
            snapshot_changed = True

        if now - last_top_check >= TOP_REFRESH_SECONDS:
            top_process = get_top_process()

            if top_process is not None:
                process_name, process_memory = top_process
                top_name = process_name
                top_mb = bytes_to_mb(process_memory)
            else:
                top_name = "n/a"
                top_mb = 0.0

            last_top_check = now
            snapshot_changed = True

        if snapshot_changed:
            put_latest_snapshot({
                "used_mb": used_mb,
                "total_mb": total_mb,
                "percent": percent,
                "top_name": top_name,
                "top_mb": top_mb,
            })

        stop_event.wait(0.25)


# ---------------------------------------------------------------------------
# GUI UPDATE LOGIC
# ---------------------------------------------------------------------------

def window_is_being_moved() -> bool:
    if not PAUSE_UPDATES_WHILE_MOVING:
        return False

    elapsed_ms = (time.monotonic() - last_window_move_time) * 1000
    return elapsed_ms < MOVE_PAUSE_MS


def update_gui() -> None:
    if window_is_being_moved():
        root.after(GUI_REFRESH_MS, update_gui)
        return

    try:
        snapshot = stats_queue.get_nowait()
    except queue.Empty:
        root.after(GUI_REFRESH_MS, update_gui)
        return

    used_mb = snapshot["used_mb"]
    total_mb = snapshot["total_mb"]
    percent = snapshot["percent"]
    top_name = snapshot["top_name"]
    top_mb = snapshot["top_mb"]

    memory_text.set(f"{used_mb:,.0f} MB / {total_mb:,.0f} MB ({percent}%)")
    progress_bar["value"] = percent

    if top_name != "n/a":
        top_process_text.set(
            f"Top: {shorten_name(top_name, TOP_NAME_LIMIT)} {top_mb:,.0f} MB"
        )
    else:
        top_process_text.set("Top: n/a")

    root.after(GUI_REFRESH_MS, update_gui)


def on_window_configure(event: tk.Event) -> None:
    global last_window_move_time

    if event.widget is root:
        last_window_move_time = time.monotonic()


def on_close() -> None:
    stop_event.set()
    root.destroy()


# ---------------------------------------------------------------------------
# GUI SETUP
# ---------------------------------------------------------------------------

root = tk.Tk()
root.title(WINDOW_TITLE)
root.geometry(WINDOW_SIZE)
root.resizable(True, False)
root.columnconfigure(0, weight=1)

memory_text = tk.StringVar(value="Loading memory...")
top_process_text = tk.StringVar(value="Top: loading...")

memory_label = ttk.Label(
    root,
    textvariable=memory_text,
    font=FONT_MAIN,
    anchor="center",
)
memory_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

progress_bar = ttk.Progressbar(
    root,
    orient="horizontal",
    mode="determinate",
    maximum=100,
)
progress_bar.grid(row=1, column=0, padx=15, pady=(5, 0), sticky="ew")

top_process_label = ttk.Label(
    root,
    textvariable=top_process_text,
    font=FONT_SMALL,
    anchor="center",
)
top_process_label.grid(row=2, column=0, padx=10, pady=(4, 10), sticky="ew")


# ---------------------------------------------------------------------------
# START
# ---------------------------------------------------------------------------

root.bind("<Configure>", on_window_configure)
root.protocol("WM_DELETE_WINDOW", on_close)

worker_thread = threading.Thread(target=monitor_loop, daemon=True)
worker_thread.start()

update_gui()
root.mainloop()