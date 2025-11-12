import tkinter as tk
from tkinter import ttk
from sv_ttk import set_theme
from tkinter import filedialog, messagebox, scrolledtext
import subprocess, threading, re, sys, os

# --- Main window ---
root = tk.Tk()
root.title("Blender Cork Optimizer")
root.geometry("850x700")

import pywinstyles, sys

pywinstyles.change_header_color(root, color="#252525") #change header window color

# --- Blender paths ---
BLENDER_PATH = r"C:\\Program Files (x86)\Steam\steamapps\\common\Blender\blender.exe"
SCRIPT_PATH = r"C:\\Users\\joao_\\Desktop\\Faculdade\\Douturamento\\Bolsa_investigacao\\Trabalhos\\Optimizacao_blender\\Script_Test\\3DModel-Optimizattion\\cork_opt_v2.py"



# --- Theme and Styles ---
# Apply the Sun Valley theme
set_theme("dark")  # or "light"




# --- UI Functions ---
def browse_script():
    path = filedialog.askopenfilename(title="Select script file", filetypes=[("Python files", "*.py")])
    if path:
        script_entry.full_path = path
        script_entry.delete(0, tk.END)
        script_entry.insert(0, os.path.basename(path))

def browse_input():
    path = filedialog.askopenfilename(title="Select GLTF File", filetypes=[("GLTF files", "*.gltf *.glb")])
    if path:
        input_entry.full_path = path
        input_entry.delete(0, tk.END)
        input_entry.insert(0, os.path.basename(path))

def browse_output():
    path = filedialog.askdirectory(title="Select Output Folder")
    if path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, path)

def run_blender():
    script_path = getattr(script_entry, "full_path", script_entry.get())
    input_path = getattr(input_entry, "full_path", input_entry.get())
    output_path = output_entry.get()
    texture_size = texture_entry.get()

    if not os.path.isfile(script_path):
        messagebox.showerror("Error", "Script file does not exist.")
        return
    if not os.path.isfile(input_path):
        messagebox.showerror("Error", "Input file does not exist.")
        return
    if not os.path.isdir(output_path):
        messagebox.showerror("Error", "Output folder does not exist.")
        return
    if not texture_size.isdigit():
        messagebox.showerror("Error", "Texture size must be numeric.")
        return

    command = [
        BLENDER_PATH, "--background", "--python", script_path, "--",
        "--input", input_path, "--output", output_path, "--texture-size", texture_size
    ]

    def worker():
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            combined_lines = []
            if proc.stdout:
                for line in proc.stdout:
                    output_text.config(state=tk.NORMAL)
                    output_text.insert(tk.END, line)
                    output_text.see(tk.END)
                    output_text.config(state=tk.DISABLED)
                    combined_lines.append(line)
            returncode = proc.wait()
            combined = "".join(combined_lines)
            if returncode == 0:
                m = re.search(r"Elapsed time:\s*([\d.]+)\s*seconds", combined)
                elapsed = float(m.group(1)) if m else None
                time_elapsed_label.config(text=f"{elapsed:.2f}s" if elapsed else "N/A")
                messagebox.showinfo("Success", f"Finished!\nElapsed time: {elapsed:.2f} s" if elapsed else "Success!")
            else:
                messagebox.showerror("Error", f"Blender failed ({returncode}).")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    threading.Thread(target=worker, daemon=True).start()

# --- Layout ---


frm = ttk.Frame(root, padding=10, style="My.TFrame")
frm.pack(fill="both", expand=True)


def labeled_entry(parent, text, browse_cmd=None):
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=5)
    ttk.Label(frame, text=text, width=15).pack(side="left")
    entry = ttk.Entry(frame)
    entry.pack(side="left", fill="x", expand=True, padx=5)
    if browse_cmd:
        ttk.Button(frame, text="Browse", command=browse_cmd).pack(side="right")
    return entry

script_entry = labeled_entry(frm, "Script File:", browse_script)
input_entry = labeled_entry(frm, "Input File:", browse_input)
output_entry = labeled_entry(frm, "Output Folder:", browse_output)

ttk.Label(frm, text="Texture Size:").pack(anchor="w")
texture_entry = ttk.Entry(frm, width=10)
texture_entry.insert(0, "2048")
texture_entry.pack(anchor="w", pady=5)

run_button = ttk.Button(text="Run Blender Script", command=run_blender, style="Accent.TButton")
run_button.pack(pady=10)

ttk.Label(text="Elapsed Time:").pack(anchor="center")
time_elapsed_label = ttk.Label(text="0.0s")
time_elapsed_label.pack(anchor="center", pady=5)

""" output_text = scrolledtext.Text(frm, width=90, height=15, wrap="word")
output_text.pack(side="left", fill="both", expand=True, pady=(0,10))

scrollbar = ttk.Scrollbar(frm, orient="vertical", command=output_text.yview, style="Accent.Vertical.TScrollbar")
scrollbar.pack(side="right", fill="y", pady=(0,10))

ttk.Label(frm, text="Blender Output:").pack(anchor="w", pady=(10, 0))
output_text = scrolledtext.ScrolledText(frm, width=90, height=15, wrap="word", state=tk.DISABLED)
output_text.pack(fill="both", expand=True) """

# --- Container frame for Text + Scrollbar ---
text_frame = ttk.Frame(frm)
text_frame.pack(fill="both", expand=True)

# --- Text widget ---
output_text = tk.Text(text_frame, wrap="word", state="disabled")
output_text.pack(side="left", fill="both", expand=True)

# --- Scrollbar ---
scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=output_text.yview, style="Accent.Vertical.TScrollbar")
scrollbar.pack(side="right", fill="y")

# --- Link scrollbar and text widget ---
output_text.configure(yscrollcommand=scrollbar.set)


# Default values
default_input = r"C:\Users\joao_\Desktop\Faculdade\Douturamento\Bolsa_investigacao\Trabalhos\Optimizacao_blender\Script_Test\3DModel-Optimizattion\input\0101_primeiro_2.gltf"
default_output = r"C:\Users\joao_\Desktop\Faculdade\Douturamento\Bolsa_investigacao\Trabalhos\Optimizacao_blender\Script_Test\3DModel-Optimizattion\output"
default_script = SCRIPT_PATH

script_entry.full_path = default_script
script_entry.insert(0, os.path.basename(default_script))
input_entry.full_path = default_input
input_entry.insert(0, os.path.basename(default_input))
output_entry.insert(0, default_output)

root.mainloop()
