# 3D Model Optimizarion
A set of scripts that use blender scripting to visualy optimize a 3d Model. This repository is part of the E2E Digital Twin project and the main script was alredy being developed. This repository aims to enhance the process and correct some issues.

# Features
- Input High resolution model with vertex colors and get an optimized lowPoly version
- Exports in .GLB
- GUI for better usability

# Use cases
1. Run the GUI.py file and fill the entrys in the GUI:
<img width="852" height="732" alt="image" src="https://github.com/user-attachments/assets/20dd34fc-db51-403d-a20a-0fe0af1abc80" />

2. Run the script directly on the command line
```cmd

"[Blender path]" --background --python [cork_opt_v2.py] -- 
--input "[Input file path]" --output "[Output folder path]" 
--texture-size [####]

```
