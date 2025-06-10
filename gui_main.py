# gui_main.py
import tkinter as tk
from tkinter import filedialog
import sys
from pathlib import Path
import os

# Fixing relative import issue by ensuring the project root is on sys.path.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_file  # Reverted to relative import
from graph_model import Graph, Edge  # Reverted to relative import
import json
import xml.etree.ElementTree as ET

PIN_R = 4  # radius på input/output-sirkler

class NodeCanvas(tk.Canvas):
    def __init__(self, master, graph):
        super().__init__(master, bg="#1e1e1e", scrollregion=(0, 0, 4000, 4000))
        self.graph = graph  # Store reference to Graph
        self.pack(fill="both", expand=True)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonPress-3>", self.on_right_click)  # Right-click for context menu
        # Add zoom and pan functionality
        self.bind("<MouseWheel>", self.on_zoom)
        self.bind("<ButtonPress-2>", self.start_pan)
        self.bind("<B2-Motion>", self.on_pan)

        self.drag_item = None
        self.offset = (0, 0)
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Edit Node", command=self.edit_node)
        self.context_menu.add_command(label="Delete Edge", command=self.delete_edge)
        self.start_node = None  # For edge creation

        # Auto pan/zoom after loading the graph
        self.after(100, self.auto_pan_zoom)

    def load_graph(self, graph: Graph):
        print("Starting to load graph...")
        self.delete("all")
        max_nodes = 1000  # Limit the number of nodes processed
        max_edges = 2000  # Limit the number of edges processed

        nodes = list(graph.nodes.values())[:max_nodes]
        edges = graph.edges[:max_edges]

        print(f"Number of nodes to process: {len(nodes)}")
        print(f"Number of edges to process: {len(edges)}")

        if len(edges) > 400:
            print("Too many edges to render. Skipping edge rendering.")
            edges = []
            print("Rendering summary view with groups only.")
            for group_name in graph.groups:
                group = graph.groups[group_name]  # Retrieve the actual Group object
                self._draw_node(group)
                for connection in group.connections:
                    self._draw_edge(connection)
            print("Finished loading summary view.")
            return

        batch_size = 100  # Render nodes and edges in batches
        for i in range(0, len(nodes), batch_size):
            print(f"Processing batch of nodes: {i} to {i+batch_size}")
            for node in nodes[i:i+batch_size]:
                # Reduce node dimensions and adjust scaling factor
                node.width = 100
                node.height = 50
                self._draw_node(node)
            self.update_idletasks()  # Update canvas incrementally

        for i in range(0, len(edges), batch_size):
            print(f"Processing batch of edges: {i} to {i+batch_size}")
            for edge in edges[i:i+batch_size]:
                self._draw_edge(edge)
            self.update_idletasks()  # Update canvas incrementally

        print("Finished loading graph.")

    def toggle_group(self, group_node):
        """Toggle visibility of a group node's children with lazy loading."""
        if group_node.expanded:
            for child in group_node.children:
                self.delete(child.canvas_id)
            group_node.expanded = False
        else:
            for child in group_node.children:
                if not hasattr(child, 'canvas_id'):
                    self._draw_node(child)  # Lazy load child nodes
                else:
                    self.itemconfig(child.canvas_id, state='normal')
            group_node.expanded = True

    # ---------- intern ----------
    def _draw_node(self, node):
        x, y, w, h = node.x, node.y, node.width, node.height
        # hovedboks
        box = self.create_rectangle(x, y, x+w, y+h, fill="#2d2d30",
                                    outline="#8c8c8c", width=2, tags=("node", node.info.name))
        node.canvas_id = box
        # tekst
        self.create_text(x+w/2, y+15, text=node.info.name, fill="white", font=("Helvetica", 10, "bold"), tags=("node",))
        # input-pins
        for i, inp in enumerate(node.info.inputs):
            pin_y = y + 30 + i*15
            self.create_oval(x-PIN_R, pin_y-PIN_R, x+PIN_R, pin_y+PIN_R,
                             fill="#569cd6", outline="", tags=("pin",))
            self.create_text(x-10, pin_y, text=inp, anchor="e", fill="#d4d4d4", font=("Helvetica", 8))
        # output-pins
        for i, outp in enumerate(node.info.outputs):
            pin_y = y + 30 + i*15
            self.create_oval(x+w-PIN_R, pin_y-PIN_R, x+w+PIN_R, pin_y+PIN_R,
                             fill="#dcdcaa", outline="", tags=("pin",))
            self.create_text(x+w+10, pin_y, text=outp, anchor="w", fill="#d4d4d4", font=("Helvetica", 8))
        # husk taggen på hovedboksen for dragging
        self.addtag_withtag("draggable", box)

        # Add debug prints to verify node positions and dimensions
        print(f"Drawing node: {node.info.name}, Position: ({x}, {y}), Dimensions: ({w}x{h})")

    def _draw_edge(self, edge):
        # fra midt-høyre på src til midt-venstre på dst
        x1 = edge.src.x + edge.src.width
        y1 = edge.src.y + edge.src.height/2
        x2 = edge.dst.x
        y2 = edge.dst.y + edge.dst.height/2
        self.create_line(x1, y1, x2, y2, arrow=tk.LAST, fill="#c586c0", width=2)

    # ---------- interactivity ----------
    def edit_node(self):
        if self.drag_item:
            node_tag = self.gettags(self.drag_item)[1]
            node = self.graph.nodes[node_tag]

            # Open dialog to edit node properties
            edit_window = tk.Toplevel(self)
            edit_window.title("Edit Node")

            tk.Label(edit_window, text="Name:").grid(row=0, column=0)
            name_entry = tk.Entry(edit_window)
            name_entry.insert(0, node.info.name)
            name_entry.grid(row=0, column=1)

            tk.Label(edit_window, text="Inputs:").grid(row=1, column=0)
            inputs_entry = tk.Entry(edit_window)
            inputs_entry.insert(0, ",".join(node.info.inputs))
            inputs_entry.grid(row=1, column=1)

            tk.Label(edit_window, text="Outputs:").grid(row=2, column=0)
            outputs_entry = tk.Entry(edit_window)
            outputs_entry.insert(0, ",".join(node.info.outputs))
            outputs_entry.grid(row=2, column=1)

            def save_changes():
                node.info.name = name_entry.get()
                node.info.inputs = inputs_entry.get().split(",")
                node.info.outputs = outputs_entry.get().split(",")
                self.load_graph(self.graph)
                edit_window.destroy()

            tk.Button(edit_window, text="Save", command=save_changes).grid(row=3, columnspan=2)

    def delete_edge(self):
        if self.drag_item:
            edge_tag = self.gettags(self.drag_item)[1]
            edge = next((e for e in self.graph.edges if e.src.info.name == edge_tag or e.dst.info.name == edge_tag), None)
            if edge:
                self.graph.edges.remove(edge)
                self.load_graph(self.graph)

    def on_right_click(self, event):
        item = self.find_closest(event.x, event.y)[0]
        if "node" in self.gettags(item):
            self.drag_item = item
            self.context_menu.entryconfig("Edit Node", state="normal")
            self.context_menu.entryconfig("Delete Edge", state="disabled")
        elif "edge" in self.gettags(item):
            self.drag_item = item
            self.context_menu.entryconfig("Edit Node", state="disabled")
            self.context_menu.entryconfig("Delete Edge", state="normal")
        else:
            self.drag_item = None
            self.context_menu.entryconfig("Edit Node", state="disabled")
            self.context_menu.entryconfig("Delete Edge", state="disabled")

        self.context_menu.post(event.x_root, event.y_root)

    # ---------- dragging ----------
    def on_press(self, event):
        closest_items = self.find_closest(event.x, event.y)
        if not closest_items:
            print("No items found at the clicked location.")
            return
        item = closest_items[0]
        if "draggable" in self.gettags(item):
            self.drag_item = item
            self.offset = (event.x - self.coords(item)[0], event.y - self.coords(item)[1])
        elif "node" in self.gettags(item):
            # Safeguard to check the length of tags before accessing
            if len(self.gettags(item)) > 1:
                self.start_node = self.gettags(item)[1]

    def on_drag(self, event):
        if self.drag_item:
            new_x = event.x - self.offset[0]
            new_y = event.y - self.offset[1]
            dx = new_x - self.coords(self.drag_item)[0]
            dy = new_y - self.coords(self.drag_item)[1]
            # flytt hoved­rektangel + alt med samme nodenavn-tag
            tags = self.gettags(self.drag_item)
            node_tag = tags[1]  # andre tag er navnet
            for item in self.find_withtag(node_tag):
                self.move(item, dx, dy)
        elif self.start_node:
            end_node = self.find_closest(event.x, event.y)[0]
            if "node" in self.gettags(end_node):
                end_node_tag = self.gettags(end_node)[1]
                self.graph.edges.append(Edge(self.graph.nodes[self.start_node], self.graph.nodes[end_node_tag]))
                self.load_graph(self.graph)
                self.start_node = None

    def save_as_image(self, filename):
        self.postscript(file=filename + ".ps")
        try:
            from PIL import Image
            img = Image.open(filename + ".ps")
            img.save(filename + ".png")
        except ImportError:
            print("Pillow is required to save as PNG. Install it using 'pip install pillow'.")

    def export_to_json(self, filename):
        graph_data = {
            "nodes": [
                {
                    "name": node.info.name,
                    "inputs": node.info.inputs,
                    "outputs": node.info.outputs,
                    "x": node.x,
                    "y": node.y
                } for node in self.graph.nodes.values()
            ],
            "edges": [
                {
                    "src": edge.src.info.name,
                    "dst": edge.dst.info.name
                } for edge in self.graph.edges
            ]
        }
        with open(filename + ".json", "w") as f:
            json.dump(graph_data, f, indent=4)

    def export_to_xml(self, filename):
        root = ET.Element("Graph")
        nodes_elem = ET.SubElement(root, "Nodes")
        for node in self.graph.nodes.values():
            node_elem = ET.SubElement(nodes_elem, "Node", {
                "name": node.info.name,
                "x": str(node.x),
                "y": str(node.y)
            })
            inputs_elem = ET.SubElement(node_elem, "Inputs")
            for inp in node.info.inputs:
                ET.SubElement(inputs_elem, "Input").text = inp
            outputs_elem = ET.SubElement(node_elem, "Outputs")
            for outp in node.info.outputs:
                ET.SubElement(outputs_elem, "Output").text = outp

        edges_elem = ET.SubElement(root, "Edges")
        for edge in self.graph.edges:
            ET.SubElement(edges_elem, "Edge", {
                "src": edge.src.info.name,
                "dst": edge.dst.info.name
            })

        tree = ET.ElementTree(root)
        tree.write(filename + ".xml", encoding="utf-8", xml_declaration=True)

    # Define zoom and pan methods
    def on_zoom(self, event):
        scale = 1.1 if event.delta > 0 else 0.9
        self.scale("all", event.x, event.y, scale, scale)
        self.configure(scrollregion=self.bbox("all"))

    def start_pan(self, event):
        self.scan_mark(event.x, event.y)

    def on_pan(self, event):
        self.scan_dragto(event.x, event.y, gain=1)

    def auto_pan_zoom(self):
        # Refine auto pan/zoom to center and scale the canvas properly
        bbox = self.bbox("all")
        if bbox:
            canvas_width, canvas_height = self.winfo_width(), self.winfo_height()
            scale_x = canvas_width / (bbox[2] - bbox[0])
            scale_y = canvas_height / (bbox[3] - bbox[1])
            # Update auto pan/zoom scaling factor
            scale = min(scale_x, scale_y) * 0.9  # Slightly increase scaling factor
            self.scale("all", 0, 0, scale, scale)
            self.configure(scrollregion=bbox)
            self.xview_moveto(0.5)
            self.yview_moveto(0.5)

# Update main menu to include export options
def main():
    root = tk.Tk()
    root.title("Python Node Visualizer")

    graph = Graph()
    canvas = NodeCanvas(root, graph)

    # Meny for å åpne fil
    menubar = tk.Menu(root)
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Åpne Python-fil…", command=lambda: open_py(canvas, graph))
    filemenu.add_separator()
    filemenu.add_command(label="Lagre som bilde…", command=lambda: canvas.save_as_image("graph"))
    filemenu.add_command(label="Eksporter til JSON…", command=lambda: canvas.export_to_json("graph"))
    filemenu.add_command(label="Eksporter til XML…", command=lambda: canvas.export_to_xml("graph"))
    filemenu.add_separator()
    filemenu.add_command(label="Avslutt", command=root.quit)
    menubar.add_cascade(label="Fil", menu=filemenu)
    root.config(menu=menubar)

    root.state("zoomed")  # fullskjerm
    root.mainloop()

def open_py(canvas, graph):
    path = filedialog.askopenfilename(filetypes=[("Python-filer", "*.py")])
    if not path:
        print("No file selected.")
        return
    try:
        nodes, edges, groups = parse_file(Path(path))
        graph.build(nodes, edges, groups)
        canvas.load_graph(graph)
    except Exception as e:
        print(f"Error loading graph: {e}")

if __name__ == "__main__":
    main()
