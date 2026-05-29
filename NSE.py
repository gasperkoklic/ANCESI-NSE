#!/usr/bin/env python3
"""
Stock Inventory Manager - Manage component stock with parameters
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import csv
import copy

class StockComponent:
    """Component in stock inventory"""
    def __init__(self, comment="", head="1", feeder_no="0", mount_speed="100", 
                 pick_height="0.0", place_height="0.0"):
        self.comment = comment
        self.head = head
        self.feeder_no = feeder_no
        self.mount_speed = mount_speed
        self.pick_height = pick_height
        self.place_height = place_height
    
    def to_dict(self):
        return {
            'comment': self.comment, 'head': self.head, 'feeder_no': self.feeder_no,
            'mount_speed': self.mount_speed, 'pick_height': self.pick_height,
            'place_height': self.place_height
        }
    
    @staticmethod
    def from_dict(d):
        return StockComponent(d['comment'], d['head'], d['feeder_no'], 
                            d['mount_speed'], d['pick_height'], d['place_height'])

class StockManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Stock Inventory Manager")
        self.root.geometry("900x600")
        self.stock = {}
        self.filename = None
        self.sort_column = None
        self.sort_reverse = False
        self.show_menu()
        self.root.mainloop()
    
    def clear_window(self):
        for w in self.root.winfo_children():
            w.destroy()
    
    def show_menu(self):
        self.clear_window()
        tk.Label(self.root, text="Stock Inventory Manager", font=('Arial', 14, 'bold')).pack(pady=20)
        
        tk.Button(self.root, text="New Stock", command=self.new_stock, 
                 bg="#d4edda", font='bold', height=2, width=30).pack(pady=10, fill="x", padx=20)
        tk.Button(self.root, text="Load Stock CSV", command=self.load_stock, 
                 bg="#cfe2ff", font='bold', height=2, width=30).pack(pady=10, fill="x", padx=20)
        tk.Button(self.root, text="Exit", command=self.root.quit, height=2, width=30).pack(pady=10, fill="x", padx=20)
    
    def new_stock(self):
        self.stock = {}
        self.filename = None
        self.show_editor()
    
    def load_stock(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not filepath:
            return
        
        try:
            self.stock = {}
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.stock[row['comment']] = StockComponent(
                        row['comment'], row['head'], row['feeder_no'],
                        row['mount_speed'], row['pick_height'], row['place_height']
                    )
            self.filename = filepath
            messagebox.showinfo("Success", f"Loaded {len(self.stock)} components")
            self.show_editor()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {str(e)}")
    
    def show_editor(self):
        self.clear_window()
        tk.Label(self.root, text="Stock Inventory Editor", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Toolbar
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill="x", padx=10, pady=5)
        tk.Button(toolbar, text="Add Component", command=self.add_component, width=15).pack(side="left", padx=2)
        tk.Button(toolbar, text="Delete Component", command=self.delete_component, width=15).pack(side="left", padx=2)
        tk.Button(toolbar, text="Save CSV", command=self.save_stock, width=15, bg="#cce5ff").pack(side="left", padx=2)
        tk.Button(toolbar, text="Back", command=self.show_menu, width=15, bg="#ffcccb").pack(side="left", padx=2)
        
        # Table
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ["Comment", "Head", "Feeder No", "Mount Speed(%)", "Pick Height(mm)", "Place Height(mm)"]
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='extended')
        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_table(c))
            self.tree.column(col, width=120, anchor="center")
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<Double-1>", lambda e: self.edit_component())
        self.root.unbind("<n>")
        self.root.unbind("<N>")
        self.root.bind("<n>", lambda e: self.add_component())
        self.root.bind("<N>", lambda e: self.add_component())
        self.refresh_table()
    
    def _to_float(self, val):
        """Safely convert a value to float for numeric sorting, fallback to 0."""
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())

        # Get components in current sort order
        if self.sort_column:
            if self.sort_column == "Comment":
                items = sorted(self.stock.items(), key=lambda x: x[0].lower(), reverse=self.sort_reverse)
            elif self.sort_column == "Head":
                items = sorted(self.stock.items(), key=lambda x: self._to_float(x[1].head), reverse=self.sort_reverse)
            elif self.sort_column == "Feeder No":
                items = sorted(self.stock.items(), key=lambda x: self._to_float(x[1].feeder_no), reverse=self.sort_reverse)
            elif self.sort_column == "Mount Speed(%)":
                items = sorted(self.stock.items(), key=lambda x: self._to_float(x[1].mount_speed), reverse=self.sort_reverse)
            elif self.sort_column == "Pick Height(mm)":
                items = sorted(self.stock.items(), key=lambda x: self._to_float(x[1].pick_height), reverse=self.sort_reverse)
            elif self.sort_column == "Place Height(mm)":
                items = sorted(self.stock.items(), key=lambda x: self._to_float(x[1].place_height), reverse=self.sort_reverse)
            else:
                items = sorted(self.stock.items(), reverse=self.sort_reverse)
        else:
            items = sorted(self.stock.items())
        
        for comment, comp in items:
            self.tree.insert("", "end", values=(comp.comment, comp.head, comp.feeder_no,
                                                comp.mount_speed, comp.pick_height, comp.place_height))
    
    def sort_table(self, col):
        """Toggle sorting by column: A-Z, Z-A, original"""
        if self.sort_column == col:
            # Same column clicked - toggle reverse
            if not self.sort_reverse:
                self.sort_reverse = True  # Now Z-A
            else:
                # Return to original
                self.sort_column = None
                self.sort_reverse = False
        else:
            # New column - sort A-Z
            self.sort_column = col
            self.sort_reverse = False
        
        self.refresh_table()
    
    def add_component(self, event=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Component")
        dialog.geometry("400x250")
        dialog.grab_set()
        dialog.lift()
        dialog.focus_set()
        
        fields = {
            'comment': ("Comment", "NEW"),
            'head': ("Head", "1"),
            'feeder_no': ("Feeder No", "0"),
            'mount_speed': ("Mount Speed(%)", "100"),
            'pick_height': ("Pick Height(mm)", "0.0"),
            'place_height': ("Place Height(mm)", "0.0")
        }
        
        entries = {}
        for i, (key, (label, default)) in enumerate(fields.items()):
            tk.Label(dialog, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=10, pady=5)
            ent = tk.Entry(dialog, width=30)
            ent.insert(0, default)
            ent.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = ent
        
        def save():
            comment = entries['comment'].get().strip()
            if not comment:
                messagebox.showwarning("Error", "Comment required")
                return
            if comment in self.stock:
                messagebox.showwarning("Error", "Component already exists")
                return
            self.stock[comment] = StockComponent(
                comment, entries['head'].get(), entries['feeder_no'].get(),
                entries['mount_speed'].get(), entries['pick_height'].get(),
                entries['place_height'].get()
            )
            self.refresh_table()
            dialog.destroy()
        
        dialog.bind('<Return>', lambda e: save())
        tk.Button(dialog, text="Save", command=save, width=15).grid(row=6, column=0, columnspan=2, pady=10)
        return 'break'
    
    def edit_component(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Select", "Select a component")
            return
        
        item = selection[0]
        values = self.tree.item(item)['values']
        comment = str(values[0])
        
        if comment not in self.stock:
            messagebox.showerror("Error", f"Component '{comment}' not found in stock")
            return
        
        comp = self.stock[comment]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {comment}")
        dialog.geometry("400x300")
        dialog.grab_set()
        dialog.lift()
        dialog.focus_set()
        
        fields = {
            'comment': ("Comment", comp.comment),
            'head': ("Head", comp.head),
            'feeder_no': ("Feeder No", comp.feeder_no),
            'mount_speed': ("Mount Speed(%)", comp.mount_speed),
            'pick_height': ("Pick Height(mm)", comp.pick_height),
            'place_height': ("Place Height(mm)", comp.place_height)
        }
        
        entries = {}
        for i, (key, (label, value)) in enumerate(fields.items()):
            tk.Label(dialog, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=10, pady=5)
            ent = tk.Entry(dialog, width=30)
            ent.insert(0, str(value))
            ent.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = ent
        
        def save():
            new_comment = entries['comment'].get().strip()
            if not new_comment:
                messagebox.showwarning("Error", "Comment required")
                return
            
            # Handle renaming if comment changed
            if new_comment != comment:
                if new_comment in self.stock:
                    messagebox.showwarning("Error", "Component with this name already exists")
                    return
                del self.stock[comment]
                comp.comment = new_comment
                self.stock[new_comment] = comp
            
            comp.head = entries['head'].get()
            comp.feeder_no = entries['feeder_no'].get()
            comp.mount_speed = entries['mount_speed'].get()
            comp.pick_height = entries['pick_height'].get()
            comp.place_height = entries['place_height'].get()
            self.refresh_table()
            dialog.destroy()
        
        dialog.bind('<Return>', lambda e: save())
        tk.Button(dialog, text="Save", command=save, width=15).grid(row=6, column=0, columnspan=2, pady=10)
    
    def delete_component(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Select", "Select component(s)")
            return
        
        for item in selection:
            comment = self.tree.item(item)['values'][0]
            if comment in self.stock:
                del self.stock[comment]
        self.refresh_table()
    
    def save_stock(self):
        if not self.stock:
            messagebox.showwarning("Empty", "No components to save")
            return
        
        if not self.filename:
            self.filename = filedialog.asksaveasfilename(defaultext=".csv", 
                                                        filetypes=[("CSV Files", "*.csv")])
        if not self.filename:
            return
        
        try:
            Path("Stock").mkdir(exist_ok=True)
            filepath = f"Stock/{Path(self.filename).name}" if not self.filename.startswith("Stock/") else self.filename
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['comment', 'head', 'feeder_no', 
                                                      'mount_speed', 'pick_height', 'place_height'])
                writer.writeheader()
                for row_id in self.tree.get_children():
                    comment = str(self.tree.item(row_id)['values'][0])
                    if comment in self.stock:
                        writer.writerow(self.stock[comment].to_dict())
            
            messagebox.showinfo("Success", f"Saved to {filepath}")
            self.filename = filepath
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {str(e)}")

if __name__ == "__main__":
    StockManager()