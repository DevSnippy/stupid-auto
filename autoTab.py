import customtkinter as ctk
from tkinter import filedialog, messagebox
import pyautogui
import threading
import re
import time

# Set the appearance and theme
ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

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
        self.root.geometry("400x400")
        self.filepath = ""
        self.parser = None
        self.selected_stage = ctk.StringVar(value="A")
        self.sending = False
        self.stop_event = threading.Event()
        self.countdown_seconds = 10  # Countdown duration in seconds

        self.create_widgets()

    def create_widgets(self):
        # File selection button
        self.select_btn = ctk.CTkButton(self.root, text="Select TXT File", command=self.select_file)
        self.select_btn.pack(pady=10, padx=20, fill="x")

        # Label to show selected file
        self.file_label = ctk.CTkLabel(self.root, text="No file selected")
        self.file_label.pack(pady=5, padx=20)

        # Dropdown for stage selection
        self.stage_dropdown = ctk.CTkOptionMenu(
            self.root,
            variable=self.selected_stage,
            values=["A", "N"],
            state="disabled"
        )
        self.stage_dropdown.pack(pady=10, padx=20, fill="x")

        # Start Sending button
        self.start_btn = ctk.CTkButton(self.root, text="Start Sending", command=self.start_sending, state='disabled')
        self.start_btn.pack(pady=10, padx=20, fill="x")

        # Stop button
        self.stop_btn = ctk.CTkButton(self.root, text="Stop", command=self.stop_sending, state='disabled')
        self.stop_btn.pack(pady=10, padx=20, fill="x")

        # Label to show messages
        self.message_label = ctk.CTkLabel(self.root, text="", fg_color=None, text_color="blue")
        self.message_label.pack(pady=10, padx=20)

        # Label to show countdown
        self.countdown_label = ctk.CTkLabel(self.root, text="", fg_color=None, text_color="red", font=("Helvetica", 16))
        self.countdown_label.pack(pady=5, padx=20)

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
            self.stage_dropdown.configure(state='normal')
            self.selected_stage.set("A")  # Default selection
            self.start_btn.configure(state='normal')
        elif a_exists:
            self.message_label.config(text="Only Stage A table found.")
            self.stage_dropdown.configure(state='disabled')
            self.start_btn.configure(state='normal')
            self.selected_stage.set("A")
        elif n_exists:
            self.message_label.config(text="Only Stage N table found.")
            self.stage_dropdown.configure(state='disabled')
            self.start_btn.configure(state='normal')
            self.selected_stage.set("N")
        else:
            messagebox.showerror("Error", "No Stage A or Stage N tables found in the file.")
            self.stage_dropdown.configure(state='disabled')
            self.start_btn.configure(state='disabled')

        # Show array sizes
        size_a = len(self.parser.stage_a)
        size_n = len(self.parser.stage_n)
        size_msg = f"Size - Stage A: {size_a} | Stage N: {size_n}"
        current_text = self.message_label.cget("text")
        self.message_label.config(text=f"{current_text}\n{size_msg}")

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
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.select_btn.configure(state='disabled')
        if self.stage_dropdown.cget("state") != "disabled":
            self.stage_dropdown.configure(state='disabled')
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
            self.stop_btn.configure(state='disabled')

    def reset_ui(self):
        self.sending = False
        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.select_btn.configure(state='normal')
        if len(self.parser.stage_a) > 0 and len(self.parser.stage_n) > 0:
            self.stage_dropdown.configure(state='normal')
        elif len(self.parser.stage_a) > 0 or len(self.parser.stage_n) > 0:
            self.stage_dropdown.configure(state='disabled')
        self.countdown_label.configure(text="")

    def update_message(self, message):
        # Update the message_label in the main thread
        self.message_label.configure(text=message)

    def update_countdown(self, countdown_text):
        # Update the countdown_label in the main thread
        self.countdown_label.configure(text=countdown_text)

def main():
    root = ctk.CTk()
    app = AutoGUIApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
