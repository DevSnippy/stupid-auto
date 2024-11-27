import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
import threading
import re
import time

class TableParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.stage_a = []
        self.stage_n = []
        self.parse_file()

    def parse_file(self):
        try:
            with open(self.filepath, 'r') as file:
                content = file.read()

            # Regex patterns to extract tables
            pattern_a = r"AJ Table #0 Stage A - 256 Frequencies\s*-+\s*([\s\S]*?)(?=AJ Table|$)"
            pattern_n = r"AJ Table #0 Stage N - 256 Frequencies\s*-+\s*([\s\S]*?)(?=AJ Table|$)"

            match_a = re.search(pattern_a, content)
            match_n = re.search(pattern_n, content)

            if match_a:
                self.stage_a = self.extract_numbers(match_a.group(1))
            if match_n:
                self.stage_n = self.extract_numbers(match_n.group(1))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")

    def extract_numbers(self, table_text):
        numbers = []
        lines = table_text.strip().split('\n')
        for line in lines:
            # Split by spaces, handle multiple spaces
            nums = re.findall(r'\d{5}', line)
            for num in nums:
                converted = self.convert_number(num)
                numbers.append(converted)
        return numbers

    def convert_number(self, num_str):
        return float(num_str[:2] + '.' + num_str[2:])

class AutoGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("stupidTabSender")
        self.filepath = ""
        self.parser = None
        self.selected_stage = tk.StringVar()
        self.sending = False
        self.stop_event = threading.Event()
        self.countdown_seconds = 10  # Countdown duration in seconds

        self.create_widgets()

    def create_widgets(self):
        # File selection
        self.select_btn = tk.Button(self.root, text="Select TXT File", command=self.select_file)
        self.select_btn.pack(pady=10)

        # Label to show selected file
        self.file_label = tk.Label(self.root, text="No file selected")
        self.file_label.pack()

        # Dropdown for stage selection
        self.stage_dropdown = tk.OptionMenu(self.root, self.selected_stage, "A", "N")
        self.stage_dropdown.config(state='disabled')
        self.stage_dropdown.pack(pady=10)

        # Button to start sending
        self.start_btn = tk.Button(self.root, text="Start Sending", command=self.start_sending, state='disabled')
        self.start_btn.pack(pady=10)

        # Button to stop sending
        self.stop_btn = tk.Button(self.root, text="Stop", command=self.stop_sending, state='disabled')
        self.stop_btn.pack(pady=10)

        # Label to show messages
        self.message_label = tk.Label(self.root, text="", fg="blue")
        self.message_label.pack(pady=10)

        # Label to show countdown
        self.countdown_label = tk.Label(self.root, text="", fg="red", font=("Helvetica", 16))
        self.countdown_label.pack(pady=5)

    def select_file(self):
        filepath = filedialog.askopenfilename(
            title="Select TXT File",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )
        if filepath:
            self.filepath = filepath
            self.file_label.config(text=f"Selected File: {filepath}")
            self.parser = TableParser(filepath)
            self.evaluate_tables()

    def evaluate_tables(self):
        a_exists = len(self.parser.stage_a) > 0
        n_exists = len(self.parser.stage_n) > 0

        if a_exists and n_exists:
            self.message_label.config(text="Both Stage A and Stage N tables found.")
            self.stage_dropdown.config(state='normal')
            self.selected_stage.set("A")  # Default selection
            self.start_btn.config(state='normal')
        elif a_exists:
            self.message_label.config(text="Only Stage A table found.")
            self.stage_dropdown.config(state='disabled')
            self.start_btn.config(state='normal')
            self.selected_stage.set("A")
        elif n_exists:
            self.message_label.config(text="Only Stage N table found.")
            self.stage_dropdown.config(state='disabled')
            self.start_btn.config(state='normal')
            self.selected_stage.set("N")
        else:
            messagebox.showerror("Error", "No Stage A or Stage N tables found in the file.")
            self.stage_dropdown.config(state='disabled')
            self.start_btn.config(state='disabled')

        # Show array sizes
        size_a = len(self.parser.stage_a)
        size_n = len(self.parser.stage_n)
        size_msg = f"Size - Stage A: {size_a} | Stage N: {size_n}"
        self.message_label.config(text=self.message_label.cget("text") + f"\n{size_msg}")

    def start_sending(self):
        if self.sending:
            messagebox.showwarning("Warning", "Already sending data.")
            return

        stage = self.selected_stage.get()
        if stage == "A":
            data = self.parser.stage_a
        elif stage == "N":
            data = self.parser.stage_n
        else:
            messagebox.showerror("Error", "Invalid stage selected.")
            return

        if not data:
            messagebox.showerror("Error", f"No data available for Stage {stage}.")
            return

        self.sending = True
        self.stop_event.clear()
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.select_btn.config(state='disabled')
        self.stage_dropdown.config(state='disabled')
        self.message_label.config(text="Starting in 10 seconds...")
        self.countdown_label.config(text=str(self.countdown_seconds))

        # Start the countdown in a separate thread to keep the GUI responsive
        threading.Thread(target=self.countdown_and_send, args=(data,), daemon=True).start()

    def countdown_and_send(self, data):
        for remaining in range(self.countdown_seconds, 0, -1):
            if self.stop_event.is_set():
                self.update_message("Sending stopped by user.")
                self.reset_ui()
                return
            self.update_countdown(str(remaining))
            time.sleep(1)

        self.update_countdown("")
        self.update_message("Sending data...")
        self.send_data(data)

    def send_data(self, data):
        try:
            for num in data:
                if self.stop_event.is_set():
                    break
                pyautogui.typewrite(f"{num}\t")
                pyautogui.press('tab')
            if not self.stop_event.is_set():
                self.update_message("Done sending data.")
            else:
                self.update_message("Sending stopped by user.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during sending: {e}")
            self.update_message("Error occurred.")
        finally:
            self.reset_ui()

    def stop_sending(self):
        if self.sending:
            self.stop_event.set()
            self.update_message("Stopping...")
            self.stop_btn.config(state='disabled')

    def reset_ui(self):
        self.sending = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.select_btn.config(state='normal')
        if len(self.parser.stage_a) > 0 and len(self.parser.stage_n) > 0:
            self.stage_dropdown.config(state='normal')
        elif len(self.parser.stage_a) > 0 or len(self.parser.stage_n) > 0:
            self.stage_dropdown.config(state='disabled')
        self.countdown_label.config(text="")

    def update_message(self, message):
        # Update the message_label in the main thread
        self.message_label.config(text=message)

    def update_countdown(self, countdown_text):
        # Update the countdown_label in the main thread
        self.countdown_label.config(text=countdown_text)

def main():
    root = tk.Tk()
    app = AutoGUIApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
