import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import re
import os
import subprocess

LOG_FILE  = "parking_log.txt"
NUM_CARS  = 10
NUM_SPOTS = 3

BG        = "#0f172a"
CARD_BG   = "#1e293b"
BORDER    = "#334155"
ACCENT    = "#38bdf8"
GREEN     = "#4ade80"
YELLOW    = "#facc15"
RED       = "#f87171"
TEXT      = "#f1f5f9"
MUTED     = "#94a3b8"
SPOT_FREE = "#22c55e"
SPOT_USED = "#ef4444"
SPOT_WAIT = "#f59e0b"

class ParkingDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Parking Lot")
        self.root.configure(bg=BG)
        self.root.geometry("900x700")
        self.root.resizable(False, False)

        self.car_states      = {}
        self.spots_used      = 0
        self.total_parked    = 0
        self.total_wait      = 0.0
        self.running         = True
        self.simulation_done = False

        self._build_ui()
        self._compile_and_run()
        self._start_watcher()

    def _compile_and_run(self):
        self.status_lbl.config(text="Compiling...", fg=YELLOW)
        self.root.update()
        result = subprocess.run(
            ["gcc", "parking.c", "-o", "parking"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            self.status_lbl.config(text=f"Compile error: {result.stderr[:60]}", fg=RED)
            return
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        subprocess.Popen(["./parking"])
        self.status_lbl.config(text="Simulation running...", fg=GREEN)

    def _build_ui(self):
        title_font = tkfont.Font(family="Helvetica", size=16, weight="bold")
        label_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        small_font = tkfont.Font(family="Helvetica", size=9)
        mono_font  = tkfont.Font(family="Courier",   size=9)

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(14, 4))
        tk.Label(header, text="P  Smart Parking Lot", font=title_font,
                 bg=BG, fg=ACCENT).pack(side="left")
        self.status_lbl = tk.Label(header, text="Starting...",
                                   font=small_font, bg=BG, fg=YELLOW)
        self.status_lbl.pack(side="right")

        stats_frame = tk.Frame(self.root, bg=BG)
        stats_frame.pack(fill="x", padx=20, pady=6)
        self.stat_spots   = self._stat_card(stats_frame, "Free Spots",   str(NUM_SPOTS), ACCENT)
        self.stat_parked  = self._stat_card(stats_frame, "Cars Parked",  "0",            GREEN)
        self.stat_waiting = self._stat_card(stats_frame, "Cars Waiting", "0",            YELLOW)
        self.stat_avg     = self._stat_card(stats_frame, "Avg Wait (s)", "--",           RED)

        spots_outer = tk.Frame(self.root, bg=CARD_BG,
                               highlightbackground=BORDER, highlightthickness=1)
        spots_outer.pack(fill="x", padx=20, pady=6)
        tk.Label(spots_outer, text="Parking Spots", font=label_font,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=12, pady=(8, 4))
        spots_row = tk.Frame(spots_outer, bg=CARD_BG)
        spots_row.pack(padx=12, pady=(0, 10))
        self.spot_frames = []
        for i in range(NUM_SPOTS):
            f = tk.Frame(spots_row, bg=SPOT_FREE, width=100, height=64)
            f.pack_propagate(False)
            f.pack(side="left", padx=8)
            lbl = tk.Label(f, text=f"SPOT {i+1}\nFREE", bg=SPOT_FREE,
                           fg="white", font=small_font, justify="center")
            lbl.pack(expand=True)
            self.spot_frames.append((f, lbl))

        cars_outer = tk.Frame(self.root, bg=CARD_BG,
                              highlightbackground=BORDER, highlightthickness=1)
        cars_outer.pack(fill="x", padx=20, pady=6)
        tk.Label(cars_outer, text="Car Status", font=label_font,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=12, pady=(8, 4))
        cars_grid = tk.Frame(cars_outer, bg=CARD_BG)
        cars_grid.pack(padx=12, pady=(0, 10))
        self.car_labels = {}
        for i in range(NUM_CARS):
            f = tk.Frame(cars_grid, bg=BG, width=76, height=52,
                         highlightbackground=BORDER, highlightthickness=1)
            f.pack_propagate(False)
            f.grid(row=i // 5, column=i % 5, padx=5, pady=5)
            lbl = tk.Label(f, text=f"Car {i}\n---", bg=BG,
                           fg=MUTED, font=small_font, justify="center")
            lbl.pack(expand=True)
            self.car_labels[i] = (f, lbl)

        log_outer = tk.Frame(self.root, bg=CARD_BG,
                             highlightbackground=BORDER, highlightthickness=1)
        log_outer.pack(fill="both", expand=True, padx=20, pady=(6, 16))
        tk.Label(log_outer, text="Event Log", font=label_font,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=12, pady=(8, 2))
        self.log_text = tk.Text(log_outer, bg="#0a0f1e", fg=TEXT,
                                font=mono_font, relief="flat",
                                state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.log_text.tag_config("arrive",  foreground=ACCENT)
        self.log_text.tag_config("parked",  foreground=GREEN)
        self.log_text.tag_config("leaving", foreground=YELLOW)
        self.log_text.tag_config("stats",   foreground=RED)

    def _stat_card(self, parent, title, value, color):
        f = tk.Frame(parent, bg=CARD_BG,
                     highlightbackground=BORDER, highlightthickness=1)
        f.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(f, text=title, bg=CARD_BG, fg=MUTED,
                 font=tkfont.Font(family="Helvetica", size=9)).pack(pady=(8, 0))
        lbl = tk.Label(f, text=value, bg=CARD_BG, fg=color,
                       font=tkfont.Font(family="Helvetica", size=20, weight="bold"))
        lbl.pack(pady=(0, 8))
        return lbl

    def _start_watcher(self):
        t = threading.Thread(target=self._watch_log, daemon=True)
        t.start()

    def _watch_log(self):
        while not os.path.exists(LOG_FILE) and self.running:
            time.sleep(0.2)
        if not self.running:
            return
        with open(LOG_FILE, "r") as f:
            while self.running:
                line = f.readline()
                if line:
                    self.root.after(0, self._process_line, line.rstrip())
                else:
                    if self.simulation_done:
                        break
                    time.sleep(0.05)
        self.root.after(0, lambda: self.status_lbl.config(
            text="Simulation complete", fg=ACCENT))

    def _process_line(self, line):
        if not line.strip():
            return

        self._append_log(line)

        m_arrive  = re.search(r"Car (\d+): Arrived", line)
        m_parked  = re.search(r"Car (\d+): Parked successfully \(waited ([\d.]+)", line)
        m_leaving = re.search(r"Car (\d+): Leaving", line)
        m_avg     = re.search(r"Average wait time: ([\d.]+)", line)

        if m_arrive:
            cid = int(m_arrive.group(1))
            self.car_states[cid] = "waiting"
            self._update_car(cid, f"Car {cid}\nWaiting", SPOT_WAIT, "white")
            self._refresh_stats()

        elif m_parked:
            cid  = int(m_parked.group(1))
            wait = float(m_parked.group(2))
            self.car_states[cid] = "parked"
            self.spots_used    = min(self.spots_used + 1, NUM_SPOTS)
            self.total_parked += 1
            self.total_wait   += wait
            self._update_car(cid, f"Car {cid}\nParked {wait:.1f}s", SPOT_USED, "white")
            self._refresh_spots()
            self._refresh_stats()

        elif m_leaving:
            cid = int(m_leaving.group(1))
            self.car_states[cid] = "left"
            self.spots_used = max(self.spots_used - 1, 0)
            self._update_car(cid, f"Car {cid}\nLeft", BG, GREEN)
            self._refresh_spots()
            self._refresh_stats()

        elif m_avg:
            self.simulation_done = True
            avg = float(m_avg.group(1))
            self.stat_avg.config(text=f"{avg:.2f}")

    def _update_car(self, cid, text, bg, fg):
        if cid in self.car_labels:
            f, lbl = self.car_labels[cid]
            f.config(bg=bg, highlightbackground=bg)
            lbl.config(text=text, bg=bg, fg=fg)

    def _refresh_spots(self):
        free = max(NUM_SPOTS - self.spots_used, 0)
        self.stat_spots.config(text=str(free))
        for i, (f, lbl) in enumerate(self.spot_frames):
            if i < self.spots_used:
                f.config(bg=SPOT_USED)
                lbl.config(text=f"SPOT {i+1}\nOCCUPIED", bg=SPOT_USED)
            else:
                f.config(bg=SPOT_FREE)
                lbl.config(text=f"SPOT {i+1}\nFREE", bg=SPOT_FREE)

    def _refresh_stats(self):
        waiting = sum(1 for s in self.car_states.values() if s == "waiting")
        self.stat_waiting.config(text=str(waiting))
        self.stat_parked.config(text=str(self.total_parked))
        if self.total_parked > 0:
            self.stat_avg.config(text=f"{self.total_wait / self.total_parked:.2f}")

    def _append_log(self, line):
        tag = ""
        if "Arrived"  in line: tag = "arrive"
        elif "Parked"  in line: tag = "parked"
        elif "Leaving" in line: tag = "leaving"
        elif "Total"   in line or "Average" in line: tag = "stats"
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def on_close(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app  = ParkingDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
