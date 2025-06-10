# graph_model.py
from dataclasses import dataclass, field
import math
from parser import NodeInfo, GroupInfo  # Adjusted to relative import

@dataclass
class Node:
    info: NodeInfo  # Correct type reference
    x: float = 0.0  # Allow float for x
    y: float = 0.0  # Allow float for y
    width: int = 140
    height: int = 70

@dataclass
class Edge:
    src: "Node"
    dst: "Node"

@dataclass
class Group:
    info: GroupInfo
    x: float = 0.0
    y: float = 0.0
    width: int = 200
    height: int = 100
    expanded: bool = False
    connections: list[Edge] = field(default_factory=list)  # Initialize connections as an empty list

class Graph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.groups: dict[str, Group] = {}

    def build(self, node_infos, edge_infos, group_infos):
        if not node_infos:
            print("Warning: No nodes provided to build the graph.")
        if not edge_infos:
            print("Warning: No edges provided to build the graph.")
        if not group_infos:
            print("Warning: No groups provided to build the graph.")

        # Initialize nodes
        # Dynamically calculate node positions based on canvas dimensions
        canvas_width, canvas_height = 4000, 4000  # Match NodeCanvas scrollregion
        for idx, ni in enumerate(node_infos):
            self.nodes[ni.name] = Node(ni, x=(idx % 10) * (canvas_width // 10) + 50, y=(idx // 10) * (canvas_height // 10) + 50)

        # Convert EdgeInfo to Edge objects during graph building
        for ei in edge_infos:
            src = self.nodes.get(ei.caller)
            dst = self.nodes.get(ei.callee)
            if src and dst:
                self.edges.append(Edge(src=src, dst=dst))

        # Initialize groups
        for idx, gi in enumerate(group_infos):
            group = Group(gi, x=idx * 200, y=idx * 200)
            self.groups[gi.name] = group
            # Populate connections for the group
            # Convert EdgeInfo to Edge objects for group connections
            for edge_info in edge_infos:
                src = self.nodes.get(edge_info.caller)
                dst = self.nodes.get(edge_info.callee)
                if src and dst:
                    edge = Edge(src=src, dst=dst)
                    if edge.src.info.name in group.info.children or edge.dst.info.name in group.info.children:
                        group.connections.append(edge)

        # Apply force-directed layout
        self._apply_force_directed_layout()

    def _apply_force_directed_layout(self):
        iterations = min(50, len(self.nodes))  # Reduce iterations for large graphs
        width, height = 4000, 4000  # Canvas size
        k = math.sqrt((width * height) / max(len(self.nodes), 1))  # Optimal distance between nodes

        for _ in range(iterations):
            # Calculate repulsive forces
            for node_a in self.nodes.values():
                for node_b in self.nodes.values():
                    if node_a != node_b:
                        dx = node_a.x - node_b.x
                        dy = node_a.y - node_b.y
                        distance = math.sqrt(dx**2 + dy**2) or 0.01
                        force = k**2 / distance

                        node_a.x += (dx / distance) * force * 0.1  # Scale down movement
                        node_a.y += (dy / distance) * force * 0.1

            # Calculate attractive forces
            for edge in self.edges:
                dx = edge.src.x - edge.dst.x
                dy = edge.src.y - edge.dst.y
                distance = math.sqrt(dx**2 + dy**2) or 0.01
                force = (distance**2) / k

                edge.src.x -= (dx / distance) * force * 0.1  # Scale down movement
                edge.src.y -= (dy / distance) * force * 0.1
                edge.dst.x += (dx / distance) * force * 0.1
                edge.dst.y += (dy / distance) * force * 0.1

            # Keep nodes within bounds
            for node in self.nodes.values():
                node.x = max(0, min(width, node.x))
                node.y = max(0, min(height, node.y))

            # Detect and resolve overlapping nodes
            for node_a in self.nodes.values():
                for node_b in self.nodes.values():
                    if node_a != node_b and abs(node_a.x - node_b.x) < node_a.width and abs(node_a.y - node_b.y) < node_a.height:
                        node_a.x += 10
                        node_a.y += 10
