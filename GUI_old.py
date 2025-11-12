import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import re
import threading
import sys
import os
from tkinter import scrolledtext




# Path to your Blender executable
BLENDER_PATH = r"C:\\Program Files (x86)\Steam\steamapps\\common\Blender\blender.exe"
SCRIPT_PATH = r"C:\\Users\\joao_\Desktop\\Faculdade\Douturamento\Bolsa_investigacao\\Trabalhos\\Optimizacao_blender\Script_Test\\3DModel-Optimizattion\\cork_opt.py"

def browse_script():
    path = filedialog.askopenfilename(
        title="Select script file to run",
        filetypes=[("Python files", "*.py")]
    )
    if path:
        # Store the full path in the Entry widget for later use
        script_entry.full_path = path
        # Display only the file name
        script_entry.delete(0, tk.END)
        script_entry.insert(0, os.path.basename(path))


def browse_input():
    path = filedialog.askopenfilename(
        title="Select GLTF File",
        filetypes=[("GLTF files", "*.gltf *.glb")]
    )
    if path:
        # Store the full path in the Entry widget for later use
        input_entry.full_path = path
        # Display only the file name
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
        messagebox.showerror("Error", "Texture size must be a number.")
        return

    command = [
        BLENDER_PATH,
        "--background",
        "--python", script_path,
        "--",
        "--input", input_path,
        "--output", output_path,
        "--texture-size", texture_size
    ]

    # Run Blender in a background thread so the GUI remains responsive.
    def worker():
        try:
            # Use Popen so we can stream output to the terminal while capturing it
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            combined_lines = []
            # Stream output line-by-line to the terminal and capture it
            if proc.stdout is not None:
                for line in proc.stdout:
                    # Print to the terminal immediately
                    try:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    except Exception:
                        # In case stdout isn't writable, ignore
                        pass
                    combined_lines.append(line)

            returncode = proc.wait()
            combined = "".join(combined_lines)

            if returncode == 0:
                m = re.search(r"Elapsed time:\s*([0-9]+(?:\.[0-9]+)?)\s*seconds", combined)
                if m:
                    elapsed = float(m.group(1))
                    # Update GUI from main thread
                    root.after(0, lambda: time_elapsed_label.config(text=f"{elapsed:.2f}s"))
                    root.after(0, lambda: messagebox.showinfo("Success", f"Blender script finished successfully!\nElapsed time: {elapsed:.2f} s"))
                else:
                    root.after(0, lambda: messagebox.showinfo("Success", "Blender script finished successfully! (elapsed time not found)"))
            else:
                # Non-zero exit code
                out = combined
                root.after(0, lambda: messagebox.showerror("Error", f"Blender script failed (exit code {returncode}).\n\nOutput:\n{out}"))

        except Exception as e:
            root.after(0, lambda: messagebox.showerror("Error", f"Failed to run Blender script:\n{e}"))

    threading.Thread(target=worker, daemon=True).start()

# --- GUI Setup ---
root = tk.Tk()
bg_color = "#3d3d3d"
root_bg_color = "#2e2e2e"
fg_color = "white"

root.configure(bg=root_bg_color, bd=2, relief="groove", padx=10, pady=10)
root.title("Blender Cork Optimizer")



tk.Label(root, text="Script File:", bg=root_bg_color, fg=fg_color).grid(row=0, column=0, sticky="e")
script_entry = tk.Entry(root, width=60, bg=bg_color, fg=fg_color,)
script_entry.grid(row=0, column=1, padx=5, sticky="w")
tk.Button(root, text="Browse...", command=browse_script, bg=bg_color, fg=fg_color).grid(row=0, column=2, sticky="w")

tk.Label(root, text="Input File:", bg=root_bg_color, fg=fg_color).grid(row=1, column=0, sticky="e")
input_entry = tk.Entry(root, width=60, bg=bg_color, fg=fg_color)
input_entry.grid(row=1, column=1, padx=5, sticky="w")
tk.Button(root, text="Browse...", command=browse_input, bg=bg_color, fg=fg_color).grid(row=1, column=2, sticky="w")

tk.Label(root, text="Output Folder:", bg=root_bg_color, fg=fg_color).grid(row=2, column=0, sticky="e")
output_entry = tk.Entry(root, width=60, bg=bg_color, fg=fg_color)
output_entry.grid(row=2, column=1, padx=5, sticky="w")
tk.Button(root, text="Browse...", command=browse_output, bg=bg_color, fg=fg_color).grid(row=2, column=2, sticky="w")

tk.Label(root, text="Texture Size:", bg=root_bg_color, fg=fg_color).grid(row=3, column=0, sticky="e")
texture_entry = tk.Entry(root, width=10, bg=bg_color, fg=fg_color)
texture_entry.insert(0, "2048")
texture_entry.grid(row=3, column=1, sticky="w", padx=5)

tk.Label(root, text="Time elapsed:", bg=root_bg_color, fg=fg_color).grid(row=4, column=0, sticky="e")
time_elapsed_label = tk.Label(root, text="0.0s", bg=bg_color, fg=fg_color)
time_elapsed_label.grid(row=4, column=1, sticky="w", padx=5)

tk.Button(root, text="Run Blender Script", command=run_blender, bg="orange", fg=bg_color).grid(row=4, column=0, columnspan=3, pady=10)

# Console Output Box
tk.Label(root, text="Blender Output:", bg=bg_color, fg=fg_color).grid(row=5, column=0, sticky="ne")
output_text = scrolledtext.ScrolledText(root, width=80, height=15, bg="black", fg="lime", insertbackground="white", wrap="word")
output_text.grid(row=5, column=1, columnspan=2, pady=5, sticky="w")
output_text.config(state=tk.DISABLED)  # Make it read-only




default_input = r"C:\Users\joao_\Desktop\Faculdade\Douturamento\Bolsa_investigacao\Trabalhos\Optimizacao_blender\Script_Test\3DModel-Optimizattion\input\0101_primeiro_2.gltf"
default_output = r"C:\Users\joao_\Desktop\Faculdade\Douturamento\Bolsa_investigacao\Trabalhos\Optimizacao_blender\Script_Test\3DModel-Optimizattion\output"
default_script = r"C:\\Users\\joao_\Desktop\\Faculdade\Douturamento\Bolsa_investigacao\\Trabalhos\\Optimizacao_blender\Script_Test\\3DModel-Optimizattion\\cork_opt.py"


output_entry.insert(0, default_output)

# Store the full path separately
script_entry.full_path = default_script
# Display only the filename in the Entry
script_entry.insert(0, os.path.basename(default_script))


# Store the full path separately
input_entry.full_path = default_input
# Display only the filename in the Entry
input_entry.insert(0, os.path.basename(default_input))


root.mainloop()
