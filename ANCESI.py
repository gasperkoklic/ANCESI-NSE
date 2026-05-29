# =================================================================
# SECTION 1: CORE DATA STRUCTURE
# =================================================================
from decimal import Decimal
import argparse
from argparse import RawTextHelpFormatter
import math
from pathlib import Path
import copy
import csv

# Pre-import matplotlib for responsive graph opening
import matplotlib.pyplot as plt
try:
    import mplcursors
except ImportError:
    mplcursors = None

class component:
    __slots__ = ('Designator', 'Comment', 'Layer', 'Footprint', 'X', 'Y', 'Rotation', 
                 'Head', 'FeederNo', 'MountSpeed', 'PickHeight', 'PlaceHeight', 'Mode', 'Skip')
    
    def __init__(self, line):
        quotecount, newLine = 0, ''
        for char in line:
            if char == '"': quotecount += 1
            newLine += '_' if (quotecount % 2 == 1) and (char == ',') else char
                
        parts = newLine.split(',')
        self.Designator = parts[0].replace('"', '')
        self.Comment = parts[1].replace('"', '')
        self.Layer = parts[2].replace('"', '')
        self.Footprint = parts[3].replace('"', '')
        self.X = float(parts[4].replace('"', ""))
        self.Y = float(parts[5].replace('"', ""))
        self.Rotation = parts[6].replace('"', "")
        
        # NeoDen Default Parameters
        self.Head, self.FeederNo, self.MountSpeed = "1", "0", "100"
        self.PickHeight, self.PlaceHeight, self.Mode = "0.0", "0.0", "1"
        # DEFAULT CHANGED: No part skipped by default (0 = Include, 1 = Skip)
        self.Skip = "0"

# =================================================================
# SECTION 2: GUI IMPLEMENTATION
# =================================================================
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
from tkinter import scrolledtext

class NeoDenApp:
    DEFAULT_MAIN_GEOMETRY = "400x520"
    DEFAULT_EDITOR_GEOMETRY = "400x650"
    DEFAULT_HELP_GEOMETRY = "600x500"

    def __init__(self, raw_components, filename):
        self.master_list = raw_components
        self.filename = filename
        self.root = tk.Tk()
        self.root.title("Atium PnP to Neoden YY1 PnP Converter")
        self.root.geometry(self.DEFAULT_MAIN_GEOMETRY)
        self.clipboard_data = []
        self.is_cut_operation = False
        self.status_text = ""
        self.status_clear_id = None
        self.stock_inventory = {}  # {comment: {head, feeder_no, mount_speed, pick_height, place_height}}
        self.sort_state = {}  # {column_name: 'original'/'a_to_z'/'z_to_a'}
        self.original_order = []  # Store original order for reset
        
        first_comp = raw_components[0] if raw_components else None
        self.final_settings = {
            "rel": False,
            "off": [0.0, 0.0],
            "rot": [0.0, 0.0, 0.0],
            "side": "Both Layers",
            "fiducial": [first_comp.X, first_comp.Y] if first_comp else [0.0, 0.0],
            "comment_source": "Altium Comment"
        }
        
        self.show_menu()
        self.root.mainloop()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def update_status(self, message, duration=3000):
        """Update status box and auto-clear after duration (ms)"""
        self.status_text = message
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.config(text=message)
            self.status_label.pack(side="right", padx=5)  # Show the box
            # Cancel previous scheduled clear
            if self.status_clear_id:
                self.root.after_cancel(self.status_clear_id)
            # Schedule new clear
            self.status_clear_id = self.root.after(duration, self.clear_status)
    
    def clear_status(self):
        """Clear the status text and hide the box"""
        self.status_text = ""
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            self.status_label.pack_forget()  # Hide the box


    def show_help(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("Help")
        help_win.geometry(self.DEFAULT_HELP_GEOMETRY)
        text_area = scrolledtext.ScrolledText(
            help_win, 
            wrap=tk.WORD, 
            font=("Consolas", 10), 
            padx=10, 
            pady=10
        )
        text_area.pack(expand=True, fill='both')

        help_text = (
            "NEODEN YY1 INTERFACE & PARAMETER GUIDE\n"
            "================================================================================\n\n"
            "OVERVIEW:\n"
            "This tool converts Altium Pick & Place files and Neoden CSV files to Neoden YY1\n"
            "format, with support for coordinate transformations, mirroring, and detailed\n"
            "component editing.\n\n"
            "================================================================================\n"
            "1. MAIN MENU\n"
            "================================================================================\n\n"
            "GLOBAL CONFIGURATION OPTIONS:\n"
            "- Relative to first component: when ticked, the first component becomes the\n"
            "  global 0,0 point and all other coordinates are adjusted relative to it.\n"
            "- Offset (X, Y): applies the chosen X and Y offsets to all components.\n"
            "- Rotation (X, Y, Ang): rotates the board around the point (X,Y) by Ang degrees.\n"
            "- Fiducial (X, Y): sets the fiducial reference point for the board.\n"
            "- Layer Selection: choose which layer(s) to export (TopLayer, BottomLayer, or Both).\n"
            "- Machine Comment Source: choose between Footprint or Altium Comment for export.\n"
            "- Plot: opens the graph view to visualize current component layout.\n\n"
            "MIRROR OPERATIONS:\n"
            "- Mirror over Y-Axis: flips all components left-to-right around the board's\n"
            "  horizontal center. All coordinates remain positive.\n"
            "- Mirror over X-Axis: flips all components top-to-bottom around the board's\n"
            "  vertical center. All coordinates remain positive.\n\n"
            "MAIN BUTTONS:\n"
            "- Enter editor: opens the detailed editor menu where you can view and modify\n"
            "  individual component parameters in a table format.\n"
            "- Load & Edit CSV File: opens a file dialog to load either a Neoden YY1 P&P CSV\n"
            "  or Altium format CSV file. The converter automatically detects the file type\n"
            "  and loads it for editing. You can then apply any transformations and export.\n"
            "- Quick export: exports the current component list to Neoden CSV format. When\n"
            "  starting with no file, this prompts you for a filename. The system automatically\n"
            "  applies all global transformations before exporting.\n\n"
            "================================================================================\n"
            "2. EDITOR MENU\n"
            "================================================================================\n\n"
            "TOOLBAR BUTTONS:\n"
            "- Edit row: opens the selected row in a dialog for detailed editing.\n"
            "  Alternatively, double-click a row to edit it.\n"
            "- Add row: appends a new empty component row at the end of the list.\n"
            "- Delete row: removes selected rows from the list. To select a row, left-click it.\n"
            "  To select multiple rows, hold Ctrl and click. You can also select and press Delete.\n"
            "- Show graph: opens the interactive graph view of the current component list.\n"
            "- Set fiducial: sets the selected component's coordinates as the fiducial point.\n"
            "- Back to menu: returns to the main menu.\n"
            "- Finalize & export: exports the current component list to Neoden CSV format.\n"
            "  Prompts you for a filename. Files are saved to Output/ directory.\n\n"
            "KEYBOARD SHORTCUTS (EDITOR):\n"
            "- X: Cut selected components (removes them, stores in clipboard)\n"
            "- C: Copy selected components (stores in clipboard without removing)\n"
            "- V: Paste at selected position (or end if nothing selected)\n"
            "- Delete: Remove selected rows\n"
            "- Enter/Double-click: Edit selected row\n"
            "- Down arrow: Select first row if nothing is selected\n\n"
            "STATUS BOX (Top Right):\n"
            "- Shows feedback for cut/copy/paste operations\n"
            "- Green box appears on action, auto-hides after 3 seconds\n"
            "- Displays action count (e.g., '✓ Cut 3 components')\n\n"
            "ADD ROW BUTTON:\n"
            "- No selection: adds new row at the end\n"
            "- Single item selected: adds new row at that position\n"
            "- Multiple items selected: blocked (shows warning)\n"
            "- Newly added row is automatically selected\n\n"
            "COMPONENT TABLE:\n"
            "Displays all components with the following columns:\n"
            "- No.: row number\n"
            "- Skip: checkbox to mark component as skipped (0 = include, 1 = skip)\n"
            "- Designator: component name/reference (e.g., R1, C2, U3)\n"
            "- Altium Comment: original comment from Altium file (display only)\n"
            "- Layer: component layer (TopLayer or BottomLayer)\n"
            "- Footprint: footprint package name/comment for the machine\n"
            "- X: X coordinate in mm\n"
            "- Y: Y coordinate in mm\n"
            "- Rotation: component rotation angle in degrees\n"
            "- Head: pick head number (1, 2, 3, or 4)\n"
            "- FeederNo: feeder slot number\n"
            "- Mount Speed(%): mounting speed percentage (0-100)\n"
            "- Pick Height: pick-up height in mm (default 0.0)\n"
            "- Place Height: place height in mm (default 0.0)\n"
            "- Mode: machine check mode (see below)\n\n"
            "EDIT ROW DIALOG:\n"
            "- Skip: checkbox to mark component as skipped. Press S to toggle quickly.\n"
            "- Designator: component reference designator.\n"
            "- Altium Comment: original Altium comment (stored but not exported).\n"
            "- Layer: select TopLayer or BottomLayer.\n"
            "- Footprint: comment exported to the machine.\n"
            "- X, Y: component position coordinates.\n"
            "- Rotation: rotation in degrees.\n"
            "- Head: head number (typically 1).\n"
            "- FeederNo: feeder number for component.\n"
            "- Mount Speed(%): speed percentage for mounting.\n"
            "- Pick Height: height for picking component.\n"
            "- Place Height: height for placing component.\n"
            "- Mode: machine check mode:\n"
            "    0 = no check\n"
            "    1 = camera check (default)\n"
            "    2 = suction check\n"
            "    3 = camera + suction check\n"
            "    4 = big IC mode (WARNING: cannot change modes after this)\n"
            "- Set all: copies this field value to all components in the list.\n"
            "- Save: saves changes and returns to table. Press Enter as shortcut.\n"
            "- Cancel: discards changes and returns to table.\n\n"
            "================================================================================\n"
            "3. GRAPH VIEW (INTERACTIVE LAYOUT VIEW)\n"
            "================================================================================\n\n"
            "VISUALIZATION:\n"
            "- Gray X markers: original component positions (before any transformations)\n"
            "- Blue dots: components on TopLayer\n"
            "- Red dots: components on BottomLayer\n"
            "- Grid background: helps with position reference\n"
            "- Legend: shows the meaning of each marker type\n\n"
            "INTERACTION:\n"
            "- Left-click: hover over any component dot to display a tooltip showing:\n"
            "  * Designator (component name)\n"
            "  * X, Y coordinates\n"
            "  * Rotation angle\n"
            "  * Layer (TopLayer or BottomLayer)\n"
            "- Right-click or Press Escape: clears all tooltips\n"
            "- Press D: toggles dark green rotation direction arrows on/off\n"
            "  (each arrow points in the component's rotation direction)\n\n"
            "================================================================================\n"
            "4. EXPORT FILENAME DIALOG\n"
            "================================================================================\n\n"
            "When you click 'Quick export' or 'Finalize & export', you'll see a simple dialog:\n"
            "- Enter the base filename (without .csv extension)\n"
            "- Example: type 'my_pcb' to create:\n"
            "    Output/my_pcb-NEODEN-TopLayer.csv\n"
            "    Output/my_pcb-NEODEN-BottomLayer.csv\n"
            "- Press Enter or click Export to save\n"
            "- Click Cancel to go back without exporting\n"
            "- The .csv extension is added automatically\n\n"
            "================================================================================\n"
            "5. STARTING THE APPLICATION\n"
            "================================================================================\n\n"
            "Command Line Usage:\n"
            "  python Altium_to_Neoden_converter.py                  (GUI with no file)\n"
            "  python Altium_to_Neoden_converter.py myfile.csv       (GUI with file)\n"
            "  python Altium_to_Neoden_converter.py myfile.csv -r    (with relative)\n"
            "  python Altium_to_Neoden_converter.py myfile.csv -o 10 20  (with offset)\n"
            "  python Altium_to_Neoden_converter.py myfile.csv -a 50 50 90  (with rotation)\n"
            "  python Altium_to_Neoden_converter.py myfile.csv -s TopLayer  (single layer)\n\n"
            "File Format Support:\n"
            "- Altium P&P CSV files (standard Altium export format)\n"
            "- Neoden YY1 CSV files (previously exported from this tool)\n"
            "- Automatic format detection on load\n\n"
        )
        text_area.insert(tk.INSERT, help_text)
        text_area.configure(state='disabled') # Make the text read-only

    def plot_current(self):
        fig, ax = plt.subplots(num="Interactive Layout View")
        self.arrows_visible = False
        
        # Separate components by layer
        top_layer_comps = [c for c in self.master_list if c.Layer == "TopLayer"]
        bottom_layer_comps = [c for c in self.master_list if c.Layer == "BottomLayer"]
        
        # Collect all scatter collections for cursor interaction
        scatter_collections = []
        
        # Plot original positions (gray X markers) - all components
        if self.master_list:
            x, y = zip(*[(c.X, c.Y) for c in self.master_list])
            orig_sc = ax.scatter(x, y, label="Original Position", marker='x', color='gray', s=10)
            scatter_collections.append(orig_sc)
        
        # Plot TopLayer components (blue dots)
        if top_layer_comps:
            x_top, y_top = zip(*[(c.X, c.Y) for c in top_layer_comps])
            top_sc = ax.scatter(x_top, y_top, label="TopLayer", marker='o', color='red', 
                               alpha=0.7, edgecolors='black', s=35)
            scatter_collections.append(top_sc)
            # Store mapping for cursor
            self.top_layer_indices = [self.master_list.index(c) for c in top_layer_comps]
        else:
            self.top_layer_indices = []
        
        # Plot BottomLayer components (red dots)
        if bottom_layer_comps:
            x_bot, y_bot = zip(*[(c.X, c.Y) for c in bottom_layer_comps])
            bot_sc = ax.scatter(x_bot, y_bot, label="BottomLayer", marker='o', color='blue', 
                               alpha=0.7, edgecolors='black', s=35)
            scatter_collections.append(bot_sc)
            # Store mapping for cursor
            self.bottom_layer_indices = [self.master_list.index(c) for c in bottom_layer_comps]
        else:
            self.bottom_layer_indices = []
        
        # Plot rotation arrows
        if self.master_list:
            x, y = zip(*[(c.X, c.Y) for c in self.master_list])
            angles = [math.radians(float(c.Rotation)) for c in self.master_list]
            u = [math.cos(a) for a in angles]
            v = [math.sin(a) for a in angles]
            self.quiver = ax.quiver(x, y, u, v, color='darkgreen', scale=30, width=0.007, alpha=0.9)
            self.quiver.set_visible(False)
        else:
            self.quiver = None

        ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))

        if mplcursors and scatter_collections:
            cursor = mplcursors.cursor(scatter_collections, hover=False)
            @cursor.connect("add")
            def _(sel):
                # Map scatter plot index to component index
                if sel.artist in scatter_collections[1:]:
                    # For layer-based scatter plots
                    if sel.artist.get_label() == "TopLayer":
                        comp_idx = self.top_layer_indices[sel.index]
                    elif sel.artist.get_label() == "BottomLayer":
                        comp_idx = self.bottom_layer_indices[sel.index]
                    else:
                        comp_idx = sel.index
                else:
                    # Original position scatter
                    comp_idx = sel.index
                
                comp = self.master_list[comp_idx]
                sel.annotation.set(text=f"{comp.Designator}\nX: {comp.X:.2f}\nY: {comp.Y:.2f}\nRotation: {comp.Rotation}\nLayer: {comp.Layer}")
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9, boxstyle="round,pad=0.3")

            def clear_popups():
                for sel in cursor.selections: cursor.remove_selection(sel)
                fig.canvas.draw_idle()

            fig.canvas.mpl_connect('key_press_event', lambda event: clear_popups() if event.key == 'escape' else None)
            fig.canvas.mpl_connect('button_press_event', lambda event: clear_popups() if event.button == 3 else None)
            
            def toggle_arrows(event):
                if event.key == 'd' or event.key == 'D':
                    self.arrows_visible = not self.arrows_visible
                    self.quiver.set_visible(self.arrows_visible)
                    fig.canvas.draw_idle()
            
            fig.canvas.mpl_connect('key_press_event', toggle_arrows)

        plt.tight_layout()
        plt.show()

    def mirror_y_axis(self):
        if not self.master_list:
            messagebox.showwarning("No Data", "Please load or create components first.")
            return
        
        max_x = max(c.X for c in self.master_list)
        for c in self.master_list:
            c.X = max_x - c.X
            rotation = float(c.Rotation)
            c.Rotation = str((360 - rotation) % 360)
        
        messagebox.showinfo("Success", "Mirrored over Y-Axis")
        if hasattr(self, 'refresh_editor_table'):
            self.refresh_editor_table()

    def mirror_x_axis(self):
        if not self.master_list:
            messagebox.showwarning("No Data", "Please load or create components first.")
            return
        
        max_y = max(c.Y for c in self.master_list)
        for c in self.master_list:
            c.Y = max_y - c.Y
            rotation = float(c.Rotation)
            c.Rotation = str((180 - rotation) % 360)
        
        messagebox.showinfo("Success", "Mirrored over X-Axis")
        if hasattr(self, 'refresh_editor_table'):
            self.refresh_editor_table()

    def load_csv_file(self):
        file_path = filedialog.askopenfilename(
            title="Load CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        # Save current settings before loading new file
        current_side = self.final_settings["side"]
        current_comment_source = self.final_settings["comment_source"]
        
        # Check if it's a Neoden file or Altium file
        if NeoDenConverter.is_neoden_file(file_path):
            # Load Neoden file
            components = NeoDenConverter.load_neoden_csv(file_path)
            if components is None:
                messagebox.showerror("Error", "Failed to load Neoden CSV file.")
                return
            
            # Infer layer from filename
            if "TopLayer" in file_path:
                for c in components:
                    c.Layer = "TopLayer"
            elif "BottomLayer" in file_path:
                for c in components:
                    c.Layer = "BottomLayer"
            
            file_type = "Neoden"
        else:
            # Try to load as Altium file
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
                
                # Altium files typically have a header, try to find the data start
                # If file has fewer than 13 lines, assume it's not standard Altium format
                if len(lines) > 13:
                    components = [component(line.strip()) for line in lines[13:] if line.strip()]
                else:
                    # Try parsing from beginning if no header detected
                    components = [component(line.strip()) for line in lines if line.strip()]
                
                if not components:
                    messagebox.showerror("Error", "No components found in file.")
                    return
                
                file_type = "Altium"
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load Altium CSV file: {str(e)}")
                return
        
        # Replace master list with loaded components
        self.master_list = components
        self.filename = file_path
        
        # Restore previous settings
        self.final_settings["side"] = current_side
        self.final_settings["comment_source"] = current_comment_source
        
        messagebox.showinfo("Success", f"Loaded {len(components)} components from {file_type} file.")
        self.show_editor()

    def load_stock_csv(self):
        """Load stock inventory CSV file"""
        filepath = filedialog.askopenfilename(title="Load Stock CSV", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not filepath:
            return
        
        try:
            self.stock_inventory = {}
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.stock_inventory[row['comment']] = {
                        'head': row['head'], 'feeder_no': row['feeder_no'],
                        'mount_speed': row['mount_speed'], 'pick_height': row['pick_height'],
                        'place_height': row['place_height']
                    }
            messagebox.showinfo("Success", f"Loaded {len(self.stock_inventory)} stock components")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load stock: {str(e)}")

    def capture_menu_state(self):
        if not hasattr(self, 'ent_offx') or not self.ent_offx.winfo_exists():
            return True 
        try:
            self.final_settings["rel"] = self.var_rel.get()
            self.final_settings["off"] = [float(self.ent_offx.get()), float(self.ent_offy.get())]
            self.final_settings["rot"] = [float(self.ent_rotx.get()), float(self.ent_roty.get()), float(self.ent_rota.get())]
            self.final_settings["fiducial"] = [float(self.ent_fid_x.get()), float(self.ent_fid_y.get())]
            self.final_settings["side"] = self.combo_side.get()
            self.final_settings["comment_source"] = self.combo_comment.get()
            return True
        except ValueError:
            messagebox.showerror("Error", "Global settings must contain numbers.")
            return False

    def show_menu(self):
        self.clear_window()
        self.root.unbind("<Left>")
        self.root.unbind("<Right>")
        self.root.unbind("<Up>")
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        menubar.add_cascade(label="Help", command=self.show_help)
        
        # Create main container with scrolling capability
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        tk.Label(main_frame, text="Atium PnP to Neoden YY1 PnP Converter", font=('Arial', 12, 'bold')).pack(pady=10)
        opts = tk.LabelFrame(main_frame, text="Global Configuration", padx=10, pady=10)
        opts.pack(padx=20, pady=5, fill="both", expand=False)

        self.var_rel = tk.BooleanVar(value=self.final_settings["rel"])
        tk.Checkbutton(opts, text="Relative to first component", variable=self.var_rel).grid(row=0, column=0, columnspan=3, sticky="w")

        tk.Label(opts, text="Offset (X, Y):").grid(row=1, column=0, sticky="w")
        self.ent_offx = tk.Entry(opts, width=7); self.ent_offx.insert(0, str(self.final_settings["off"][0]))
        self.ent_offy = tk.Entry(opts, width=7); self.ent_offy.insert(0, str(self.final_settings["off"][1]))
        self.ent_offx.grid(row=1, column=1); self.ent_offy.grid(row=1, column=2)

        tk.Label(opts, text="Rotation (X, Y, Ang):").grid(row=2, column=0, sticky="w")
        self.ent_rotx = tk.Entry(opts, width=7); self.ent_rotx.insert(0, str(self.final_settings["rot"][0]))
        self.ent_roty = tk.Entry(opts, width=7); self.ent_roty.insert(0, str(self.final_settings["rot"][1]))
        self.ent_rota = tk.Entry(opts, width=7); self.ent_rota.insert(0, str(self.final_settings["rot"][2]))
        self.ent_rotx.grid(row=2, column=1); self.ent_roty.grid(row=2, column=2); self.ent_rota.grid(row=2, column=3)

        tk.Label(opts, text="Fiducial (X, Y):").grid(row=3, column=0, sticky="w")
        self.ent_fid_x = tk.Entry(opts, width=7); self.ent_fid_x.insert(0, str(self.final_settings["fiducial"][0]))
        self.ent_fid_y = tk.Entry(opts, width=7); self.ent_fid_y.insert(0, str(self.final_settings["fiducial"][1]))
        self.ent_fid_x.grid(row=3, column=1); self.ent_fid_y.grid(row=3, column=2)

        self.combo_side = ttk.Combobox(opts, values=["Both Layers", "TopLayer", "BottomLayer"], state="readonly")
        self.combo_side.set(self.final_settings["side"])
        self.combo_side.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        tk.Button(opts, text="Plot", command=self.plot_current).grid(row=4, column=2, padx=5)

        tk.Label(opts, text="Machine Comment Source:").grid(row=5, column=0, sticky="w")
        self.combo_comment = ttk.Combobox(opts, values=["Footprint", "Altium Comment"], state="readonly")
        self.combo_comment.set(self.final_settings["comment_source"])
        self.combo_comment.grid(row=5, column=1, columnspan=2, pady=10, sticky="ew")

        # Mirror buttons frame
        mirror_frame = tk.LabelFrame(main_frame, text="Mirror Operations", padx=10, pady=10)
        mirror_frame.pack(padx=20, pady=5, fill="x")
        tk.Button(mirror_frame, text="Mirror over Y-Axis", command=self.mirror_y_axis, bg="#fff3cd", width=20).pack(side="left", padx=5)
        tk.Button(mirror_frame, text="Mirror over X-Axis", command=self.mirror_x_axis, bg="#fff3cd", width=20).pack(side="left", padx=5)

        # Buttons frame - with proper fill
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(padx=20, pady=10, fill="both", expand=False)
        tk.Button(buttons_frame, text="Enter editor", command=self.go_to_editor, bg="#d4edda", font='bold', height=2).pack(pady=5, fill="x")
        tk.Button(buttons_frame, text="Load & Edit CSV File", command=self.load_csv_file, bg="#cfe2ff", font='bold', height=2).pack(pady=5, fill="x")
        tk.Button(buttons_frame, text="Quick export", command=self.finish_all, height=2).pack(pady=5, fill="x")
        
        # Update geometry AFTER all widgets are packed to fit content
        self.root.update_idletasks()
        req_width = self.root.winfo_reqwidth()
        req_height = self.root.winfo_reqheight()
        self.root.geometry(f"{req_width}x{req_height}")

    def go_to_editor(self):
        if self.capture_menu_state():
            self.show_editor()

    def show_editor(self):
        self.clear_window()
        self.root.geometry(self.DEFAULT_EDITOR_GEOMETRY)
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        menubar.add_cascade(label="Help", command=self.show_help)

        self.params = ["Designator", "Altium Comment", "Layer", "Footprint", "X", "Y", "Rotation", 
                       "Head", "FeederNo", "Mount Speed(%)", "Pick Height", "Place Height", "Mode"]

        # Top frame with status box on the right
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        toolbar = tk.Frame(top_frame)
        toolbar.pack(side="left", fill="x", expand=True)
        tk.Button(toolbar, text="Edit row", command=self.edit_selected_row, width=12).pack(side="left", padx=2)
        tk.Button(toolbar, text="Add row", command=self.add_row, width=12).pack(side="left", padx=2)
        tk.Button(toolbar, text="Delete row", command=self.delete_selected_rows, width=12).pack(side="left", padx=2)
        tk.Button(toolbar, text="Show graph", command=self.plot_current, width=12, bg="#e2e2e2").pack(side="left", padx=2)
        tk.Button(toolbar, text="Set fiducial", command=self.set_current_as_fiducial, width=12, bg="#ffeeba").pack(side="left", padx=2)
        tk.Button(toolbar, text="Load Stock", command=self.load_stock_csv, width=12, bg="#fff3cd").pack(side="left", padx=2)

        # Status box in top right (initially hidden)
        self.status_label = tk.Label(top_frame, text="", font=('Arial', 9), fg="#006400", 
                                     bg="#e8f5e9", padx=10, pady=5, relief="solid", borderwidth=1)
        # Don't pack it initially - only show when there's a message

        self.lbl_info = tk.Label(self.root, text="", font=('Arial', 10, 'bold'))
        self.lbl_info.pack(pady=5)

        tree_frame = tk.Frame(self.root); tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ["No.", "Skip"] + self.params
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='extended')
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=1, minwidth=30, stretch=False, anchor="center")

        self.auto_adjust_column_widths()
        self.update_editor_geometry()

        self.tree.bind("<Double-1>", lambda event: self.edit_selected_row())
        self.tree.bind("<Return>", lambda event: self.edit_selected_row())
        self.tree.bind("<Delete>", lambda event: self.delete_selected_rows())
        self.tree.bind("<s>", lambda event: self.toggle_skip_selected())
        self.tree.bind("<S>", lambda event: self.toggle_skip_selected())
        self.tree.bind("<c>", lambda event: self.copy_components())
        self.tree.bind("<C>", lambda event: self.copy_components())
        self.tree.bind("<x>", lambda event: self.cut_components())
        self.tree.bind("<X>", lambda event: self.cut_components())
        self.tree.bind("<v>", lambda event: self.paste_components())
        self.tree.bind("<V>", lambda event: self.paste_components())

        # Unbind any previous Down key bindings, then add our handler
        self.root.unbind("<Down>")
        self.root.bind("<Down>", self.on_down_arrow_key)
        
        btn_frame = tk.Frame(self.root); btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Back to menu", command=self.show_menu, bg="#ffcccb").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Finalize & export", command=self.finish_all, bg="#cce5ff", font='bold', height=2).pack(side="left", padx=10)

        self.refresh_editor_table()
        # Set focus to the tree after everything is initialized
        self.tree.focus_set()


    def on_down_arrow_key(self, event):
        """Handle down arrow key press: select first row if nothing is selected"""
        # Only handle if tree is in editor and has focus
        if not hasattr(self, 'tree') or not self.tree.winfo_exists():
            return None
        
        # Check if the tree widget has focus
        if self.root.focus_get() != self.tree:
            return None
        
        # Check if anything is currently selected
        if not self.tree.selection():
            # No selection, select the first row
            children = self.tree.get_children()
            if children:
                first_item = children[0]
                self.tree.selection_set(first_item)
                self.tree.focus(first_item)
                return 'break'  # Prevent default behavior
        # If something is already selected, allow default down arrow behavior
        return None

    def cut_components(self, event=None):
        """Cut selected components (removes them from list, stores in clipboard)"""
        indices = self.get_selected_indices()
        if not indices:
            self.update_status("⚠ Select rows to cut")
            return 'break'
        
        try:
            # Validate all indices before making any changes
            valid_indices = [idx for idx in indices if 0 <= idx < len(self.master_list)]
            if not valid_indices:
                self.update_status("⚠ Invalid selection")
                return 'break'
            
            # Store components in clipboard (deep copy)
            self.clipboard_data = []
            for idx in valid_indices:
                self.clipboard_data.append(copy.deepcopy(self.master_list[idx]))
            
            # Remove from master list (in reverse order to maintain correct indices)
            for idx in sorted(valid_indices, reverse=True):
                del self.master_list[idx]
            
            self.is_cut_operation = True
            count = len(self.clipboard_data)
            self.update_status(f"✓ Cut {count} component{'s' if count != 1 else ''}")
            self.refresh_editor_table()
        except Exception as e:
            self.update_status(f"✗ Cut failed: {str(e)[:30]}")
        
        return 'break'

    def copy_components(self, event=None):
        """Copy selected components (stores in clipboard without removing)"""
        indices = self.get_selected_indices()
        if not indices:
            self.update_status("⚠ Select rows to copy")
            return 'break'
        
        try:
            # Validate all indices before making any changes
            valid_indices = [idx for idx in indices if 0 <= idx < len(self.master_list)]
            if not valid_indices:
                self.update_status("⚠ Invalid selection")
                return 'break'
            
            # Store components in clipboard (deep copy)
            self.clipboard_data = []
            for idx in valid_indices:
                self.clipboard_data.append(copy.deepcopy(self.master_list[idx]))
            
            self.is_cut_operation = False
            count = len(self.clipboard_data)
            self.update_status(f"✓ Copied {count} component{'s' if count != 1 else ''}")
        except Exception as e:
            self.update_status(f"✗ Copy failed: {str(e)[:30]}")
        
        return 'break'

    def paste_components(self, event=None):
        """Paste components from clipboard at the selected row position"""
        if not self.clipboard_data:
            self.update_status("⚠ Clipboard empty - use C to copy or X to cut")
            return 'break'
        
        try:
            # Get the index where to paste
            selected_idx = self.get_selected_index()
            if selected_idx is None:
                # If nothing is selected, append to the end
                paste_position = len(self.master_list)
            else:
                # Paste AT the selected component position
                paste_position = selected_idx
            
            # Store original count before clearing
            paste_count = len(self.clipboard_data)
            
            # Insert copied/cut components at the paste position
            for i, comp in enumerate(self.clipboard_data):
                # Deep copy each component to avoid shared references
                pasted_comp = copy.deepcopy(comp)
                self.master_list.insert(paste_position + i, pasted_comp)
            
            # If this was a cut operation, clear the clipboard after pasting
            if self.is_cut_operation:
                self.clipboard_data = []
                self.is_cut_operation = False
                self.update_status(f"✓ Pasted {paste_count} component(s) (cut cleared)")
            else:
                self.update_status(f"✓ Pasted {paste_count} component(s)")
            
            self.refresh_editor_table()
            
            # Select the pasted components
            self.select_row_by_index(paste_position)
        except Exception as e:
            self.update_status(f"✗ Paste failed: {str(e)[:30]}")
        
        return 'break'

    def jump_to_comp(self):
        query = self.ent_jump.get().strip().upper()
        if not query: return
        
        self.save_edit()
        if hasattr(self, 'btn_jump'):
            self.btn_jump.config(relief='sunken')
            self.root.after(100, lambda: self.btn_jump.config(relief='raised'))
        found_idx = -1
        
        if query.isdigit():
            target = int(query) - 1
            if 0 <= target < len(self.master_list):
                found_idx = target
        else:
            for i, comp in enumerate(self.master_list):
                if comp.Designator.upper() == query:
                    found_idx = i
                    break
        
        if found_idx != -1:
            self.idx = found_idx
            self.ent_jump.delete(0, tk.END)
            self.refresh_edit()
        else:
            messagebox.showwarning("Not Found", f"Could not find component '{query}'")

    def save_edit(self):
        # Retained for compatibility, but the editor now uses the tree-based editor.
        return

    def set_current_as_fiducial(self):
        idx = None
        if hasattr(self, 'tree'):
            idx = self.get_selected_index()
        if idx is None and self.master_list:
            idx = 0
        if idx is None:
            messagebox.showwarning("Select Row", "Please select a row or load data first.")
            return
        c = self.master_list[idx]
        self.final_settings["fiducial"] = [c.X, c.Y]
        messagebox.showinfo("Fiducial set", f"Fiducial set to X={c.X}, Y={c.Y}")

    def get_selected_indices(self):
        items = self.tree.selection()
        indexes = []
        for item in items:
            values = self.tree.item(item).get('values', [])
            if values:
                try:
                    indexes.append(int(values[0]) - 1)
                except ValueError:
                    pass
        return sorted(set(indexes), reverse=True)

    def get_selected_index(self):
        indexes = self.get_selected_indices()
        return indexes[0] if indexes else None

    def select_row_by_index(self, idx):
        """Select a row in the tree by its data index"""
        if not hasattr(self, 'tree') or not self.tree.winfo_exists():
            return
        
        tree_children = self.tree.get_children()
        if 0 <= idx < len(tree_children):
            item = tree_children[idx]
            self.tree.selection_set(item)
            self.tree.focus(item)
            self.tree.see(item)

    def auto_adjust_column_widths(self):
        if not hasattr(self, 'tree'): return
        font = tkfont.nametofont("TkDefaultFont")
        attr_map = {
            "Designator": "Designator", "Altium Comment": "Comment", "Footprint": "Footprint",
            "Layer": "Layer", "X": "X", "Y": "Y", "Rotation": "Rotation",
            "Head": "Head", "FeederNo": "FeederNo", "Mount Speed(%)": "MountSpeed",
            "Pick Height": "PickHeight", "Place Height": "PlaceHeight", "Mode": "Mode"
        }
        for col in self.tree['columns']:
            if col == "No.":
                text_samples = [str(len(self.master_list)), col]
            elif col == "Skip":
                text_samples = ["☑", "☐", col]
            else:
                attr = attr_map.get(col, col)
                text_samples = [col] + [str(getattr(c, attr, "")) for c in self.master_list]
            width = max(font.measure(value) for value in text_samples) + 20
            width = max(width, 40)
            self.tree.column(col, width=width, minwidth=30, stretch=False, anchor="center")

    def update_editor_geometry(self):
        if not hasattr(self, 'tree'): return
        self.root.update_idletasks()
        total_width = sum(self.tree.column(col, option='width') for col in self.tree['columns']) + 60
        total_height = max(self.root.winfo_height(), 600)
        self.root.geometry(f"{total_width}x{total_height}")

    def sort_by_column(self, col):
        """Sort the master_list by a given column and refresh the table"""
        # Determine the sort order
        current_state = self.sort_state.get(col, 'original')
        
        if current_state == 'original':
            # First click: sort A to Z
            new_state = 'a_to_z'
            self.sort_state[col] = new_state
            # Save original order if not already done
            if not self.original_order:
                self.original_order = copy.deepcopy(self.master_list)
            
            # Sort based on column
            if col == "No.":
                # No. is based on index, so keep original order
                pass
            elif col == "Skip":
                self.master_list.sort(key=lambda c: (c.Skip, self.original_order.index(c) if c in self.original_order else 0))
            elif col == "Designator":
                self.master_list.sort(key=lambda c: c.Designator.lower())
            elif col == "Altium Comment":
                self.master_list.sort(key=lambda c: c.Comment.lower())
            elif col == "Layer":
                self.master_list.sort(key=lambda c: c.Layer.lower())
            elif col == "Footprint":
                self.master_list.sort(key=lambda c: c.Footprint.lower())
            elif col == "X":
                self.master_list.sort(key=lambda c: float(c.X) if isinstance(c.X, (int, float)) else 0)
            elif col == "Y":
                self.master_list.sort(key=lambda c: float(c.Y) if isinstance(c.Y, (int, float)) else 0)
            elif col == "Rotation":
                self.master_list.sort(key=lambda c: float(c.Rotation) if isinstance(c.Rotation, (int, float, str)) else 0)
            elif col == "Head":
                self.master_list.sort(key=lambda c: c.Head.lower())
            elif col == "FeederNo":
                self.master_list.sort(key=lambda c: c.FeederNo.lower())
            elif col == "Mount Speed(%)":
                self.master_list.sort(key=lambda c: float(c.MountSpeed) if isinstance(c.MountSpeed, (int, float, str)) else 0)
            elif col == "Pick Height":
                self.master_list.sort(key=lambda c: float(c.PickHeight) if isinstance(c.PickHeight, (int, float, str)) else 0)
            elif col == "Place Height":
                self.master_list.sort(key=lambda c: float(c.PlaceHeight) if isinstance(c.PlaceHeight, (int, float, str)) else 0)
            elif col == "Mode":
                self.master_list.sort(key=lambda c: c.Mode.lower())
            
            self.update_status(f"Sorted {col} A→Z")
        elif current_state == 'a_to_z':
            # Second click: sort Z to A
            new_state = 'z_to_a'
            self.sort_state[col] = new_state
            self.master_list.reverse()
            self.update_status(f"Sorted {col} Z→A")
        else:
            # Third click: return to original order
            new_state = 'original'
            self.sort_state[col] = new_state
            if self.original_order:
                self.master_list = copy.deepcopy(self.original_order)
            # Reset all sort states when returning to original
            self.sort_state = {col: 'original'}
            self.update_status(f"Sorted {col} - Original order")
        
        self.refresh_editor_table()

    def refresh_editor_table(self):
        if not hasattr(self, 'tree'): return
        self.tree.delete(*self.tree.get_children())
        for idx, c in enumerate(self.master_list, start=1):
            skip_display = "☑" if c.Skip == "1" else "☐"
            self.tree.insert("", "end", values=(idx, skip_display, c.Designator, c.Comment, c.Layer, c.Footprint, c.X, c.Y, c.Rotation, c.Head, c.FeederNo, c.MountSpeed, c.PickHeight, c.PlaceHeight, c.Mode))
        self.lbl_info.config(text=f"Rows: {len(self.master_list)}")
        self.auto_adjust_column_widths()
        self.update_editor_geometry()

    def edit_selected_row(self):
        idx = self.get_selected_index()
        if idx is None:
            messagebox.showwarning("Select Row", "Please select a row to edit.")
            return
        self.open_edit_dialog(idx)

    def add_row(self):
        """Add a new row at selected position or end of list"""
        indices = self.get_selected_indices()
        
        # Check if multiple items are selected
        if len(indices) > 1:
            self.update_status("⚠ Cannot add row - multiple items selected")
            return
        
        new_comp = component('"NEW","","","",0,0,0')
        
        # If nothing selected, append to end
        if not indices:
            self.master_list.append(new_comp)
            insert_position = len(self.master_list) - 1
            self.update_status("✓ New row added at end")
        else:
            # Insert at selected position
            insert_position = indices[0]
            self.master_list.insert(insert_position, new_comp)
            self.update_status("✓ New row added at selection")
        
        self.refresh_editor_table()
        # Select the newly added row
        self.select_row_by_index(insert_position)

    def toggle_skip_selected(self, event=None):
        """Toggle skip status for selected components"""
        indices = self.get_selected_indices()
        if not indices:
            return 'break'
        
        selected_items = self.tree.selection()
        
        for idx in indices:
            if 0 <= idx < len(self.master_list):
                self.master_list[idx].Skip = "0" if self.master_list[idx].Skip == "1" else "1"
        
        self.refresh_editor_table()
        
        # Restore selection
        tree_children = self.tree.get_children()
        for idx in indices:
            if idx < len(tree_children):
                self.tree.selection_add(tree_children[idx])
        
        self.update_status(f"✓ Toggled skip for {len(indices)} component(s)")
        return 'break'

    def delete_selected_rows(self):
        indexes = self.get_selected_indices()
        if not indexes:
            messagebox.showwarning("Select Row", "Please select one or more rows to delete.")
            return
        
        # Track the position to select after deletion
        # Get the minimum index that will be deleted
        min_index = min(indexes)
        
        # Delete items (in reverse order to maintain correct indices)
        for idx in indexes:
            if 0 <= idx < len(self.master_list):
                del self.master_list[idx]
        
        self.refresh_editor_table()
        
        # Select the next item after deletion
        # If we deleted the last item(s), select the new last item
        # Otherwise select the item that took the place of the deleted one
        if self.master_list:
            next_index = min(min_index, len(self.master_list) - 1)
            # Get the tree items and select the corresponding one
            tree_children = self.tree.get_children()
            if next_index < len(tree_children):
                next_item = tree_children[next_index]
                self.tree.selection_set(next_item)
                self.tree.focus(next_item)
                self.tree.see(next_item)

    def open_edit_dialog(self, idx):
        c = self.master_list[idx]
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Row {idx + 1}")
        dialog.grab_set()
        dialog.bind('<Return>', lambda event: save_row())

        entries = []
        skip_var = tk.BooleanVar(value=(str(c.Skip) == "1"))
        
        # Stock dropdown row - full width to match text inputs
        tk.Label(dialog, text="Stock Component:", anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=4)
        stock_var = tk.StringVar(value="")
        stock_combo = ttk.Combobox(dialog, textvariable=stock_var, width=35)
        stock_combo.grid(row=0, column=1, padx=10, pady=4, sticky="ew")
        
        # Store all stock items and original list
        all_stock_items = list(self.stock_inventory.keys())
        stock_combo['values'] = all_stock_items
        
        def update_stock_filter(event=None):
            """Filter stock items based on search text"""
            search_text = stock_var.get().lower()
            if search_text:
                # Filter items that contain the search text
                filtered_items = [item for item in all_stock_items if search_text in item.lower()]
            else:
                # Show all items if search is empty
                filtered_items = all_stock_items
            
            # Update the dropdown values without changing selection
            stock_combo['values'] = filtered_items
        
        # Bind to any key press in the combobox
        stock_combo.bind('<KeyRelease>', update_stock_filter)
        
        def apply_stock():
            if stock_var.get() in self.stock_inventory:
                stock = self.stock_inventory[stock_var.get()]
                entries[7].delete(0, tk.END)
                entries[7].insert(0, stock['head'])
                entries[8].delete(0, tk.END)
                entries[8].insert(0, stock['feeder_no'])
                entries[9].delete(0, tk.END)
                entries[9].insert(0, stock['mount_speed'])
                entries[10].delete(0, tk.END)
                entries[10].insert(0, stock['pick_height'])
                entries[11].delete(0, tk.END)
                entries[11].insert(0, stock['place_height'])
        
        def apply_stock_to_comment():
            if stock_var.get() not in self.stock_inventory:
                return
            stock = self.stock_inventory[stock_var.get()]
            target_comment = c.Comment
            for comp in self.master_list:
                if comp.Comment == target_comment:
                    comp.Head = stock['head']
                    comp.FeederNo = stock['feeder_no']
                    comp.MountSpeed = stock['mount_speed']
                    comp.PickHeight = stock['pick_height']
                    comp.PlaceHeight = stock['place_height']
            self.refresh_editor_table()
            count = sum(1 for comp in self.master_list if comp.Comment == target_comment)
            self.update_status(f"✓ Applied to {count} components")
            dialog.destroy()
        
        def apply_stock_to_footprint():
            if stock_var.get() not in self.stock_inventory:
                return
            stock = self.stock_inventory[stock_var.get()]
            target_footprint = c.Footprint
            for comp in self.master_list:
                if comp.Footprint == target_footprint:
                    comp.Head = stock['head']
                    comp.FeederNo = stock['feeder_no']
                    comp.MountSpeed = stock['mount_speed']
                    comp.PickHeight = stock['pick_height']
                    comp.PlaceHeight = stock['place_height']
            self.refresh_editor_table()
            count = sum(1 for comp in self.master_list if comp.Footprint == target_footprint)
            self.update_status(f"✓ Applied to {count} components")
            dialog.destroy()
        
        # Create stock buttons now that functions are defined
        tk.Button(dialog, text="Apply", width=10, command=apply_stock).grid(row=0, column=2, padx=2, pady=4)
        tk.Button(dialog, text="All Comment", width=10, command=apply_stock_to_comment).grid(row=0, column=3, padx=2, pady=4)
        tk.Button(dialog, text="All Footprint", width=10, command=apply_stock_to_footprint).grid(row=0, column=4, padx=2, pady=4)
        
        def toggle_skip(event=None):
            skip_var.set(not skip_var.get())
            return "break"

        row_values = [c.Designator, c.Comment, c.Layer, c.Footprint, c.X, c.Y, c.Rotation, c.Head, c.FeederNo, c.MountSpeed, c.PickHeight, c.PlaceHeight, c.Mode]

        def set_all_field(name, value):
            for comp in self.master_list:
                try:
                    if name == "Skip":
                        comp.Skip = "1" if value in ("1", "true", "yes", "y", True) else "0"
                    elif name == "Designator":
                        comp.Designator = value
                    elif name == "Altium Comment":
                        comp.Comment = value
                    elif name == "Footprint":
                        if self.final_settings["comment_source"] == "Altium Comment":
                            comp.Comment = value
                        else:
                            comp.Footprint = value
                    elif name == "Layer":
                        comp.Layer = value
                    elif name == "X":
                        comp.X = float(value)
                    elif name == "Y":
                        comp.Y = float(value)
                    elif name == "Rotation":
                        comp.Rotation = value
                    elif name == "Head":
                        comp.Head = value
                    elif name == "FeederNo":
                        comp.FeederNo = value
                    elif name == "Mount Speed(%)":
                        comp.MountSpeed = value
                    elif name == "Pick Height":
                        comp.PickHeight = value
                    elif name == "Place Height":
                        comp.PlaceHeight = value
                    elif name == "Mode":
                        comp.Mode = value
                except ValueError:
                    messagebox.showerror("Error", f"Invalid value for {name}")
                    return
            self.refresh_editor_table()
        
        def apply_to_comment(name, value):
            """Apply a parameter value to all components with same comment"""
            target_comment = c.Comment
            count = 0
            for comp in self.master_list:
                if comp.Comment == target_comment:
                    try:
                        if name == "Skip":
                            comp.Skip = "1" if value in ("1", "true", "yes", "y", True) else "0"
                        elif name == "Designator":
                            comp.Designator = value
                        elif name == "Altium Comment":
                            comp.Comment = value
                        elif name == "Footprint":
                            if self.final_settings["comment_source"] == "Altium Comment":
                                comp.Comment = value
                            else:
                                comp.Footprint = value
                        elif name == "Layer":
                            comp.Layer = value
                        elif name == "X":
                            comp.X = float(value)
                        elif name == "Y":
                            comp.Y = float(value)
                        elif name == "Rotation":
                            comp.Rotation = value
                        elif name == "Head":
                            comp.Head = value
                        elif name == "FeederNo":
                            comp.FeederNo = value
                        elif name == "Mount Speed(%)":
                            comp.MountSpeed = value
                        elif name == "Pick Height":
                            comp.PickHeight = value
                        elif name == "Place Height":
                            comp.PlaceHeight = value
                        elif name == "Mode":
                            comp.Mode = value
                        count += 1
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid value for {name}")
                        return
            self.refresh_editor_table()
            self.update_status(f"✓ Applied {name} to {count} components with same comment")
        
        def apply_to_footprint(name, value):
            """Apply a parameter value to all components with same footprint"""
            target_footprint = c.Footprint
            count = 0
            for comp in self.master_list:
                if comp.Footprint == target_footprint:
                    try:
                        if name == "Skip":
                            comp.Skip = "1" if value in ("1", "true", "yes", "y", True) else "0"
                        elif name == "Designator":
                            comp.Designator = value
                        elif name == "Altium Comment":
                            comp.Comment = value
                        elif name == "Footprint":
                            if self.final_settings["comment_source"] == "Altium Comment":
                                comp.Comment = value
                            else:
                                comp.Footprint = value
                        elif name == "Layer":
                            comp.Layer = value
                        elif name == "X":
                            comp.X = float(value)
                        elif name == "Y":
                            comp.Y = float(value)
                        elif name == "Rotation":
                            comp.Rotation = value
                        elif name == "Head":
                            comp.Head = value
                        elif name == "FeederNo":
                            comp.FeederNo = value
                        elif name == "Mount Speed(%)":
                            comp.MountSpeed = value
                        elif name == "Pick Height":
                            comp.PickHeight = value
                        elif name == "Place Height":
                            comp.PlaceHeight = value
                        elif name == "Mode":
                            comp.Mode = value
                        count += 1
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid value for {name}")
                        return
            self.refresh_editor_table()
            self.update_status(f"✓ Applied {name} to {count} components with same footprint")

        tk.Label(dialog, text="Skip:", anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=4)
        skip_check = tk.Checkbutton(dialog, variable=skip_var, text="Skip this part")
        skip_check.grid(row=1, column=1, padx=10, pady=4, sticky="w")
        skip_check.focus_set()
        skip_check.bind('<s>', toggle_skip)
        skip_check.bind('<S>', toggle_skip)
        tk.Button(dialog, text="Apply All", width=10, command=lambda: set_all_field("Skip", skip_var.get())).grid(row=1, column=2, padx=2, pady=4)
        tk.Button(dialog, text="All Comment", width=10, command=lambda: apply_to_comment("Skip", skip_var.get())).grid(row=1, column=3, padx=2, pady=4)
        tk.Button(dialog, text="All Footprint", width=10, command=lambda: apply_to_footprint("Skip", skip_var.get())).grid(row=1, column=4, padx=2, pady=4)

        for i, name in enumerate(self.params, start=2):
            tk.Label(dialog, text=f"{name}:", anchor="w").grid(row=i, column=0, sticky="w", padx=10, pady=4)
            ent = tk.Entry(dialog, width=60)
            ent.grid(row=i, column=1, padx=10, pady=4)
            ent.insert(0, str(row_values[i - 2]))
            entries.append(ent)
            tk.Button(dialog, text="Apply All", width=10, command=lambda n=name, e=ent: set_all_field(n, e.get().strip())).grid(row=i, column=2, padx=2, pady=4)
            tk.Button(dialog, text="All Comment", width=10, command=lambda n=name, e=ent: apply_to_comment(n, e.get().strip())).grid(row=i, column=3, padx=2, pady=4)
            tk.Button(dialog, text="All Footprint", width=10, command=lambda n=name, e=ent: apply_to_footprint(n, e.get().strip())).grid(row=i, column=4, padx=2, pady=4)

        def save_row():
            try:
                c.Skip = "1" if skip_var.get() else "0"
                c.Designator = entries[0].get().strip()
                c.Comment = entries[1].get().strip()
                c.Layer = entries[2].get().strip()
                if self.final_settings["comment_source"] == "Altium Comment":
                    c.Comment = entries[3].get().strip()
                else:
                    c.Footprint = entries[3].get().strip()
                c.X = float(entries[4].get().strip())
                c.Y = float(entries[5].get().strip())
                c.Rotation = entries[6].get().strip()
                c.Head = entries[7].get().strip()
                c.FeederNo = entries[8].get().strip()
                c.MountSpeed = entries[9].get().strip()
                c.PickHeight = entries[10].get().strip()
                c.PlaceHeight = entries[11].get().strip()
                c.Mode = entries[12].get().strip()
            except ValueError:
                messagebox.showerror("Error", "Invalid numeric value for X or Y.")
                return
            self.refresh_editor_table()
            dialog.destroy()
            self.root.after(10, lambda: self.select_row_by_index(idx))

        button_frame = tk.Frame(dialog)
        button_frame.grid(row=len(self.params) + 2, column=0, columnspan=2, pady=10)
        tk.Button(button_frame, text="Save", command=save_row, width=12).pack(side="left", padx=6)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=12).pack(side="left", padx=6)

    

    def view_table(self):
        columns = ["No."] + self.params
        win = tk.Toplevel(self.root); tree = ttk.Treeview(win, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=80)
        for idx, c in enumerate(self.master_list, start=1):
            tree.insert("", "end", values=(idx, c.Designator, c.Comment, c.Layer, c.Footprint, c.X, c.Y, c.Rotation, c.Head, c.FeederNo, c.MountSpeed, c.PickHeight, c.PlaceHeight, c.Mode, c.Skip))
        tree.pack(fill="both", expand=True)

    def finish_all(self):
        if self.master_list:
            # Create a simple dialog for filename input
            filename_dialog = tk.Toplevel(self.root)
            filename_dialog.title("Export Filename")
            filename_dialog.geometry("400x150")
            filename_dialog.transient(self.root)
            filename_dialog.grab_set()
            
            tk.Label(filename_dialog, text="Enter filename for export (without .csv):", font=('Arial', 10)).pack(pady=10)
            filename_entry = tk.Entry(filename_dialog, width=40, font=('Arial', 11))
            filename_entry.pack(pady=5, padx=20)
            filename_entry.focus_set()
            
            def do_export():
                filename = filename_entry.get().strip()
                if not filename:
                    messagebox.showwarning("Empty Filename", "Please enter a filename.")
                    return
                
                # Create output directory if it doesn't exist
                Path("Output").mkdir(exist_ok=True)
                
                # Determine which layers to export based on side setting
                if self.final_settings["side"] == "Both Layers":
                    sides_to_export = ["TopLayer", "BottomLayer"]
                elif self.final_settings["side"] == "TopLayer":
                    sides_to_export = ["TopLayer"]
                elif self.final_settings["side"] == "BottomLayer":
                    sides_to_export = ["BottomLayer"]
                else:
                    sides_to_export = ["TopLayer", "BottomLayer"]
                
                # Export to CSV
                for side in sides_to_export:
                    out_path = f"Output/{filename}-NEODEN-{side}.csv"
                    with open(out_path, "w") as f:
                        f.write("NEODEN,YY1,P&P FILE,,,,,,,,,,,\n,,,,,,,,,,,,,\nPanelizedPCB,UnitLength,0,UnitWidth,0,Rows,1,Columns,1,\n,,,,,,,,,,,,,\n")
                        f.write(f"Fiducial,1-X,{self.final_settings['fiducial'][0]},1-Y,{self.final_settings['fiducial'][1]},OverallOffsetX,0,OverallOffsetY,0,\n")
                        f.write(",,,,,,,,,,,,,\n" + "NozzleChange,OFF,BeforeComponent,1,Head1,Drop,Station1,PickUp,Station1,\n"*4 + ",,,,,,,,,,,,,\n")
                        f.write("Designator,Comment,Footprint,Mid X(mm),Mid Y(mm) ,Rotation,Head ,FeederNo,Mount Speed(%),Pick Height(mm),Place Height(mm),Mode,Skip\n")
                        for c in self.master_list:
                            if c.Layer == side:
                                comment = c.Comment if self.final_settings["comment_source"] == "Altium Comment" else c.Footprint
                                f.write(f"{c.Designator},{comment},{c.Footprint},{round(Decimal(c.X),2)},{round(Decimal(c.Y),2)},{c.Rotation},{c.Head},{c.FeederNo},{c.MountSpeed},{c.PickHeight},{c.PlaceHeight},{c.Mode},{c.Skip}\n")
                
                messagebox.showinfo("Success", f"Exported to Output/{filename}-NEODEN-*.csv")
                filename_dialog.destroy()
            
            export_button = tk.Button(filename_dialog, text="Export", command=do_export, width=15, height=2, bg="#cce5ff", font='bold')
            export_button.pack(pady=10, padx=20)
            cancel_button = tk.Button(filename_dialog, text="Cancel", command=filename_dialog.destroy, width=15)
            cancel_button.pack(pady=5, padx=20)
        else:
            messagebox.showwarning("No Data", "Please load or create components before exporting.")

# =================================================================
# SECTION 3: FILE CONVERSION & PROCESSING
# =================================================================
class NeoDenConverter:
    @staticmethod
    def is_neoden_file(fileName):
        """Check if the file is a Neoden YY1 P&P CSV file"""
        try:
            with open(fileName, "r") as f:
                first_line = f.readline().strip()
            return "NEODEN" in first_line and "YY1" in first_line and "P&P FILE" in first_line
        except:
            return False
    
    @staticmethod
    def load_neoden_csv(fileName):
        """Load components from a Neoden CSV file"""
        components = []
        try:
            with open(fileName, "r") as f:
                lines = f.readlines()
            
            # Find the header line
            header_line_idx = None
            for idx, line in enumerate(lines):
                if "Designator,Comment,Footprint" in line:
                    header_line_idx = idx
                    break
            
            if header_line_idx is None:
                return None
            
            # Parse components from data lines
            for line in lines[header_line_idx + 1:]:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 13:
                    try:
                        comp = component.__new__(component)
                        comp.Designator = parts[0].strip()
                        comp.Comment = parts[1].strip()
                        comp.Footprint = parts[2].strip()
                        comp.X = float(parts[3].strip())
                        comp.Y = float(parts[4].strip())
                        comp.Rotation = parts[5].strip()
                        comp.Head = parts[6].strip()
                        comp.FeederNo = parts[7].strip()
                        comp.MountSpeed = parts[8].strip()
                        comp.PickHeight = parts[9].strip()
                        comp.PlaceHeight = parts[10].strip()
                        comp.Mode = parts[11].strip()
                        comp.Skip = parts[12].strip()
                        comp.Layer = "TopLayer"  # Will be inferred from filename or default
                        components.append(comp)
                    except (ValueError, IndexError):
                        continue
            
            return components if components else None
        except:
            return None
    
    def __init__(self, fileName, _Side, _Offset, _Relative, _rotation, _plot, _gui):
        # Check if this is a Neoden CSV file or Altium file
        is_neoden = self.is_neoden_file(fileName)
        
        if is_neoden:
            # Load from Neoden CSV
            self.components = self.load_neoden_csv(fileName)
            if self.components is None:
                messagebox.showerror("Error", "Failed to load Neoden CSV file.")
                return
            # Infer layer from filename
            if "TopLayer" in fileName:
                for c in self.components:
                    c.Layer = "TopLayer"
            elif "BottomLayer" in fileName:
                for c in self.components:
                    c.Layer = "BottomLayer"
            self.comment_source = 'Altium Comment'
        else:
            # Load from Altium file
            with open(fileName, "r") as f:
                lines = f.readlines()
            self.components = [component(line.strip()) for line in lines[13:] if line.strip()]
            self.comment_source = 'Altium Comment'

        self.fiducial = [self.components[0].X, self.components[0].Y] if self.components else [0.0, 0.0]
        
        if _gui:
            app = NeoDenApp(self.components, fileName)
            if not app.final_settings: return
            s = app.final_settings
            _Relative, _Offset, _rotation, _Side = s['rel'], s['off'], s['rot'], s['side']
            self.fiducial = s['fiducial']
            self.comment_source = s.get('comment_source', 'Altium Comment')
            if _Side == "Both Layers": _Side = None
        else:
            self.comment_source = 'Altium Comment'

        if _Relative: self.apply_rel()
        if _rotation:
            try:
                rot_floats = [float(r) for r in _rotation]
                if any(rot_floats): self.apply_rot(rot_floats)
            except (ValueError, TypeError):
                pass  # Skip rotation if values can't be converted to float
        if _Offset and any(_Offset): self.apply_off(_Offset)
        
        sides = ["TopLayer", "BottomLayer"] if not _Side else [_Side]
        for side in sides: self.createOutput(side, fileName)

    def apply_rel(self):
        fx, fy = self.components[0].X, self.components[0].Y
        for c in self.components: c.X -= fx; c.Y -= fy

    def apply_rot(self, r):
        for c in self.components:
            angle = math.radians(r[2])
            nx = r[0] + math.cos(angle)*(c.X-r[0]) - math.sin(angle)*(c.Y-r[1])
            ny = r[1] + math.sin(angle)*(c.X-r[0]) + math.cos(angle)*(c.Y-r[1])
            c.X, c.Y = nx, ny

    def apply_off(self, o):
        try:
            offset_floats = [float(val) for val in o]
            for c in self.components: c.X += offset_floats[0]; c.Y += offset_floats[1]
        except (ValueError, TypeError, IndexError):
            pass  # Skip offset if values can't be converted

    def createOutput(self, side, original_name):
        Path("Output").mkdir(exist_ok=True)
        base = Path(original_name).stem
        out_path = f"Output/{base}-NEODEN-{side}.csv"
        with open(out_path, "w") as f:
            f.write("NEODEN,YY1,P&P FILE,,,,,,,,,,,\n,,,,,,,,,,,,,\nPanelizedPCB,UnitLength,0,UnitWidth,0,Rows,1,Columns,1,\n,,,,,,,,,,,,,\n")
            f.write(f"Fiducial,1-X,{self.fiducial[0]},1-Y,{self.fiducial[1]},OverallOffsetX,0,OverallOffsetY,0,\n")
            f.write(",,,,,,,,,,,,,\n" + "NozzleChange,OFF,BeforeComponent,1,Head1,Drop,Station1,PickUp,Station1,\n"*4 + ",,,,,,,,,,,,,\n")
            f.write("Designator,Comment,Footprint,Mid X(mm),Mid Y(mm) ,Rotation,Head ,FeederNo,Mount Speed(%),Pick Height(mm),Place Height(mm),Mode,Skip\n")
            for c in self.components:
                if c.Layer == side:
                    comment = c.Comment if self.comment_source == "Altium Comment" else c.Footprint
                    f.write(f"{c.Designator},{comment},{c.Footprint},{round(Decimal(c.X),2)},{round(Decimal(c.Y),2)},{c.Rotation},{c.Head},{c.FeederNo},{c.MountSpeed},{c.PickHeight},{c.PlaceHeight},{c.Mode},{c.Skip}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atium PnP to Neoden YY1 PnP Converter", formatter_class=RawTextHelpFormatter)
    parser.add_argument('File', nargs='?', default=None, help="Altium or Neoden CSV file to load (optional)")
    parser.add_argument('-r','--relative', action='store_true')
    parser.add_argument('-a','--angle', nargs=3, type=float)
    parser.add_argument('-o','--offset', nargs=2, type=float)
    parser.add_argument('-p','--plot', action='store_true')
    parser.add_argument('-s','--side', type=str)
    parser.add_argument('-g','--gui', action='store_true', default=True)
    args = parser.parse_args()
    
    # If no file provided, default to GUI mode with empty component list
    if args.File is None:
        app = NeoDenApp([], None)
    else:
        NeoDenConverter(args.File, args.side, args.offset, args.relative, args.angle, args.plot, args.gui)