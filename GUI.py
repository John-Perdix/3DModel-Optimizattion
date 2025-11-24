import tkinter as tk
from tkinter import ttk
from sv_ttk import set_theme
from tkinter import filedialog, messagebox
import subprocess, threading, re, sys, os, time
import tkinter.font as tkFont

# --- Main window ---
root = tk.Tk()
root.title("Blender Cork Optimizer")
root.geometry("850x850")

import pywinstyles, sys

pywinstyles.change_header_color(root, color="#252525") #change header window color

# --- Blender paths ---
BLENDER_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"


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

def browse_inputs():
    paths = filedialog.askopenfilenames(
        title="Select script file(s)",
        filetypes=[("GLTF files", "*.gltf *.glb")]
    )
    if paths:
        # Store the full paths (as a list) somewhere if needed
        input_entry.full_paths = paths
        
        # Show only the file names in the entry widget, joined by commas
        input_entry.delete(0, tk.END)
        filenames = [os.path.basename(p) for p in paths]
        input_entry.insert(0, ", ".join(filenames))
        # update input count label
        try:
            cnt = len(paths)
            input_count_label.config(text=(f"{cnt} file" if cnt == 1 else f"{cnt} files selected"))
        except NameError:
            pass

""" def browse_input():
    path = filedialog.askopenfilename(title="Select GLTF File", filetypes=[("GLTF files", "*.gltf *.glb")])
    if path:
        input_entry.full_path = path
        input_entry.delete(0, tk.END)
        input_entry.insert(0, os.path.basename(path)) """

def browse_output():
    path = filedialog.askdirectory(title="Select Output Folder")
    if path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, path)

def run_blender():
    # resolve script, output and texture size once
    script_path = getattr(script_entry, "full_path", script_entry.get())
    output_path = output_entry.get()
    texture_size = texture_entry.get()

    # Base directory to resolve relative paths against: the GUI script directory
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # If user provided relative paths, resolve them relative to the GUI file location
    if script_path and not os.path.isabs(script_path):
        script_path = os.path.abspath(os.path.join(base_dir, script_path))
    if output_path and not os.path.isabs(output_path):
        output_path = os.path.abspath(os.path.join(base_dir, output_path))

    # resolve input paths: prefer full_paths (multiple), then full_path (single), then text value
    if hasattr(input_entry, "full_paths") and input_entry.full_paths:
        input_paths = list(input_entry.full_paths)
    elif hasattr(input_entry, "full_path") and input_entry.full_path:
        input_paths = [input_entry.full_path]
    else:
        # try text (may be a single filename shown)
        val = input_entry.get().strip()
        input_paths = [val] if val else []

    # Resolve any relative input paths against base_dir, and also try parent folder as fallback
    resolved_input_paths = []
    for p in input_paths:
        if not p:
            continue
        if os.path.isabs(p):
            resolved = p
        else:
            # primary resolution: GUI folder
            resolved = os.path.abspath(os.path.join(base_dir, p))
            # fallback: try parent directory of GUI folder (useful if inputs are in ../input)
            if not os.path.exists(resolved):
                alt = os.path.abspath(os.path.join(os.path.dirname(base_dir), p))
                if os.path.exists(alt):
                    resolved = alt
        resolved_input_paths.append(resolved)
    input_paths = resolved_input_paths

    if not input_paths:
        messagebox.showerror("Error", "No input files selected.")
        return

    # basic validations
    if not os.path.isfile(script_path):
        messagebox.showerror("Error", "Script file does not exist.")
        return
    if not os.path.isdir(output_path):
        messagebox.showerror("Error", "Output folder does not exist.")
        return
    if not texture_size.isdigit():
        messagebox.showerror("Error", "Texture size must be numeric.")
        return

    # helper to append text to output_text from any thread
    def append_output(text):
        def _append():
            output_text.config(state=tk.NORMAL)
            output_text.insert(tk.END, text)
            output_text.see(tk.END)
            output_text.config(state=tk.DISABLED)
        root.after(0, _append)

    def worker():
        # disable run button while running and clear previous elapsed label
        root.after(0, lambda: run_button.config(state=tk.DISABLED))
        root.after(0, lambda: time_elapsed_label.config(text=""))
        total_start = time.time()
        results = []
        try:
            for inp in input_paths:
                inp = os.path.abspath(inp)
                if not os.path.isfile(inp):
                    append_output(f"Input file not found: {inp}\n")
                    results.append((inp, None, "not found"))
                    continue

                append_output(f"\n--- Running: {os.path.basename(inp)} ---\n")

                command = [
                    BLENDER_PATH, "--background", "--python", script_path, "--",
                    "--input", inp, "--output", output_path, "--texture-size", texture_size
                ]

                try:
                    # run Blender with cwd set to base_dir so relative paths inside the command are interpreted
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=base_dir)
                    combined_lines = []
                    if proc.stdout:
                        for line in proc.stdout:
                            # print to terminal
                            try:
                                sys.stdout.write(line)
                                sys.stdout.flush()
                            except Exception:
                                pass
                            # append to GUI log
                            append_output(line)
                            combined_lines.append(line)

                    returncode = proc.wait()
                    combined = "".join(combined_lines)
                    if returncode == 0:
                        m = re.search(r"Elapsed time:\s*([\d.]+)\s*seconds", combined)
                        elapsed = float(m.group(1)) if m else None
                        results.append((inp, elapsed, None))
                        # update elapsed label with cumulative per-file results
                        def _update_elapsed_label():
                            lines = []
                            for _inp, _elapsed, _err in results:
                                _name = os.path.basename(_inp)
                                if _err:
                                    lines.append(f"{_name}: ERROR ({_err})")
                                else:
                                    lines.append(f"{_name}: {_elapsed:.2f}s" if _elapsed is not None else f"{_name}: N/A")
                            time_elapsed_label.config(text="\n".join(lines))

                        root.after(0, _update_elapsed_label)
                        append_output(f"Finished: {os.path.basename(inp)} - Elapsed: {elapsed:.2f}s\n" if elapsed else f"Finished: {os.path.basename(inp)}\n")
                    else:
                        results.append((inp, None, f"exit {returncode}"))
                        append_output(f"Error: {os.path.basename(inp)} exited with code {returncode}\n")

                except Exception as e:
                    results.append((inp, None, str(e)))
                    append_output(f"Exception while running {os.path.basename(inp)}: {e}\n")

        finally:
            # compute total elapsed for whole process
            total_elapsed = time.time() - total_start
            # re-enable run button
            root.after(0, lambda: run_button.config(state=tk.NORMAL))
            # build per-file summary lines
            summary_lines = []
            for inp, elapsed, err in results:
                name = os.path.basename(inp)
                if err:
                    summary_lines.append(f"{name}: ERROR ({err})")
                else:
                    summary_lines.append(f"{name}: {elapsed:.2f}s")
            summary = "\n".join(summary_lines) if summary_lines else "No runs performed."
            # set label with total first, then per-file lines
            label_text = f"Total: {total_elapsed:.2f}s"
            if summary:
                label_text = label_text + "\n" + summary
            root.after(0, lambda: time_elapsed_label.config(text=label_text))
            # also write summary to GUI log
            append_output("\n--- Run summary ---\n")
            append_output(summary + "\n")
            # show messagebox summary as well
            root.after(0, lambda: messagebox.showinfo("Run summary", summary))

    threading.Thread(target=worker, daemon=True).start()

# --- Layout ---


frm = ttk.Frame(root, padding=10, style="My.TFrame")
frm.pack(fill="both", expand=True)


def labeled_entry(parent, text, browse_cmd=None, width=None, expand=True):
    """Create a single-row labeled entry using grid inside the row frame.

    Parameters:
    - parent: parent widget
    - text: label text
    - browse_cmd: optional callback for a Browse button
    - width: optional entry width in characters (passed to ttk.Entry)
    - expand: if True the entry column will expand to fill available space;
              if False the entry will keep the given width and not stretch.

    This allows controlling the label column minimum width (in pixels) so labels
    have consistent horizontal space across rows, and lets callers request
    a fixed-size entry (useful for small numeric fields like texture size).
    """
    # change this value (pixels) to widen/narrow the label column
    LABEL_COL_MINWIDTH = 220

    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=5)

    lbl = ttk.Label(frame, text=text)
    lbl.grid(row=0, column=0, sticky="w")
    # reserve a fixed minimum width for the label column
    frame.grid_columnconfigure(0, minsize=LABEL_COL_MINWIDTH)

    # create entry with optional width
    if width is not None:
        entry = ttk.Entry(frame, width=width)
    else:
        entry = ttk.Entry(frame)

    # layout: either allow the entry to expand, or keep it fixed-size
    if expand:
        entry.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        # allow the entry to expand horizontally
        frame.grid_columnconfigure(1, weight=1)
    else:
        entry.grid(row=0, column=1, sticky="w", padx=(6, 6))
        frame.grid_columnconfigure(1, weight=0)

    if browse_cmd:
        btn = ttk.Button(frame, text="Browse", command=browse_cmd)
        btn.grid(row=0, column=2, sticky="e")

    return entry



script_entry = labeled_entry(frm, "Script File:", browse_script)
custom_font = tkFont.Font(size=8)
spacing_label = ttk.Label(frm, text="", font=custom_font)
spacing_label.pack(anchor="e")


input_entry = labeled_entry(frm, "Input Files 3d models:", browse_inputs)
# label showing how many input files are currently selected
input_count_label = ttk.Label(frm, text="0 files selected", font=custom_font)
input_count_label.pack(anchor="e")

output_entry = labeled_entry(frm, "Output Folder:", browse_output)
spacing_label = ttk.Label(frm, text="", font=custom_font)
spacing_label.pack(anchor="e")



texture_entry = labeled_entry(frm, "Texture Size:", width=4, expand=False)
texture_entry.insert(0, "2048")

# validation: allow only digits in the texture size entry (empty allowed while editing)
def _only_digits(p):
    # p is the proposed value for the entry ("%P")
    return p == "" or p.isdigit()

_vcmd = root.register(_only_digits)
try:
    # configure validation on the ttk.Entry
    texture_entry.configure(validate="key", validatecommand=(_vcmd, "%P"))
except Exception:
    # fallback: if ttk.Entry on this platform/version doesn't support validate, ignore
    pass

run_button = ttk.Button(text="Run Blender Script", command=run_blender, style="Accent.TButton")
run_button.pack(pady=10)

ttk.Label(text="Elapsed Time:").pack(anchor="center")
# Keep same look as before but allow multiple lines
time_elapsed_label = ttk.Label(text="0.0s", justify="center", anchor="center", wraplength=600)
time_elapsed_label.pack(anchor="center", pady=5)

# --- Container frame for Text + Scrollbar ---
text_frame = ttk.Frame(frm)
text_frame.pack(fill="both", expand=True)

# --- Log text widget ---
output_text = tk.Text(text_frame, wrap="word", state="disabled")
output_text.pack(side="left", fill="both", expand=True)

# --- Scrollbar ---
scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=output_text.yview, style="Accent.Vertical.TScrollbar")
scrollbar.pack(side="right", fill="y")

# --- Link scrollbar and text widget ---
output_text.configure(yscrollcommand=scrollbar.set)


# Default values
default_input = r"input/0101_primeiro_2.gltf"
default_output = r"output"
default_script = r"cork_opt_uc.py"

script_entry.full_path = default_script
script_entry.insert(0, os.path.basename(default_script))
input_entry.full_path = default_input
input_entry.insert(0, os.path.basename(default_input))
output_entry.insert(0, default_output)
# update input count label for defaults
try:
    input_count_label.config(text="1 file")
except NameError:
    pass

root.mainloop()
