import random
import networkx as nx
import matplotlib.pyplot as plt


class Node:
    def __init__(self, name):
        self.name = name
        self.outgoing_edges = []
        self.incoming_edges = []
        self.parameters = {}

    def add_outgoing_edge(self, edge):
        self.outgoing_edges.append(edge)

    def add_incoming_edge(self, edge):
        self.incoming_edges.append(edge)

    def set_parameter(self, key, value):
        self.parameters[key] = value

    def get_parameter(self, key, default=None):
        return self.parameters.get(key, default)

class Edge:
    def __init__(self, source, target, edge_type, strength):
        self.source = source
        self.target = target
        self.edge_type = edge_type  # 'activation' or 'repression'
        self.strength = strength
        self.parameters = {}

    def set_parameter(self, key, value):
        self.parameters[key] = value

    def get_parameter(self, key, default=None):
        return self.parameters.get(key, default)

class Circuit:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, name):
        if name not in self.nodes:
            self.nodes[name] = Node(name)
        return self.nodes[name]

    def add_edge(self, source_name, target_name, edge_type, strength):
        source = self.add_node(source_name)
        target = self.add_node(target_name)
        edge = Edge(source, target, edge_type, strength)
        self.edges.append(edge)
        source.add_outgoing_edge(edge)
        target.add_incoming_edge(edge)
        return edge

    def get_node(self, name):
        return self.nodes.get(name)

def generate_feed_forward_loop():
    circuit = Circuit()

    # Add nodes
    circuit.add_node("Gene1")
    circuit.add_node("Gene2")
    circuit.add_node("Gene3")

    # Add edges
    circuit.add_edge("Gene1", "Gene2", "activation", random.uniform(0.5, 2.0))
    circuit.add_edge("Gene1", "Gene3", "activation", random.uniform(0.5, 2.0))
    circuit.add_edge("Gene2", "Gene3", "activation", random.uniform(0.5, 2.0))

    # Set node parameters
    for gene_name in ["Gene1", "Gene2", "Gene3"]:
        gene = circuit.get_node(gene_name)
        gene.set_parameter("basal_expression", random.uniform(0.01, 0.1))
        gene.set_parameter("max_expression", random.uniform(0.5, 1.0))
        gene.set_parameter("degradation_rate", random.uniform(0.05, 0.2))

    # Set edge parameters
    for edge in circuit.edges:
        edge.set_parameter("binding_affinity", random.uniform(0.1, 1.0))
        edge.set_parameter("hill_coefficient", random.uniform(1, 4))

    return circuit

def generate_toggle_switch():
    circuit = Circuit()

    # Add nodes
    circuit.add_node("Gene1")
    circuit.add_node("Gene2")

    # Add edges (mutual repression)
    circuit.add_edge("Gene1", "Gene2", "repression", random.uniform(1.0, 3.0))
    circuit.add_edge("Gene2", "Gene1", "repression", random.uniform(1.0, 3.0))

    # Set node parameters
    for gene_name in ["Gene1", "Gene2"]:
        gene = circuit.get_node(gene_name)
        gene.set_parameter("basal_expression", random.uniform(0.01, 0.1))
        gene.set_parameter("max_expression", random.uniform(0.5, 1.0))
        gene.set_parameter("degradation_rate", random.uniform(0.05, 0.2))
        gene.set_parameter("hill_coefficient", random.uniform(2, 4))  # Cooperative binding

    # Set edge parameters
    for edge in circuit.edges:
        edge.set_parameter("binding_affinity", random.uniform(0.1, 1.0))
        edge.set_parameter("repression_strength", random.uniform(0.5, 1.0))

    return circuit

import networkx as nx
import matplotlib.pyplot as plt

def visualize_circuit(circuit):
    G = nx.DiGraph()

    for node_name, node in circuit.nodes.items():
        G.add_node(node_name)

    for edge in circuit.edges:
        G.add_edge(edge.source.name, edge.target.name, 
                   edge_type=edge.edge_type, 
                   strength=edge.strength)

    pos = nx.spring_layout(G)
    nx.draw_networkx_nodes(G, pos)
    nx.draw_networkx_labels(G, pos)

    edge_colors = ['g' if G[u][v]['edge_type'] == 'activation' else 'r' for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, 
                           arrows=True, arrowsize=20)

    plt.axis('off')
    plt.show()

def component_type_to_color(component_type):
    type_to_color = {
        "gene": "green",
        "promoter": "blue",
        "repressor": "red"
    }
    return type_to_color.get(component_type, "gray")


ffl = generate_feed_forward_loop()
visualize_circuit(ffl)

toggle_switch = generate_toggle_switch()
visualize_circuit(toggle_switch)

def add_input_signal(circuit, target_gene):
    input_name = f"Input_{target_gene}"
    circuit.add_node(input_name)
    circuit.add_edge(input_name, target_gene, "activation", random.uniform(1.0, 3.0))
    
    input_node = circuit.get_node(input_name)
    input_node.set_parameter("signal_strength", random.uniform(0.1, 1.0))

def add_output_reporter(circuit, source_gene):
    reporter_name = f"Reporter_{source_gene}"
    circuit.add_node(reporter_name)
    circuit.add_edge(source_gene, reporter_name, "activation", random.uniform(1.0, 3.0))
    
    reporter_node = circuit.get_node(reporter_name)
    reporter_node.set_parameter("reporter_efficiency", random.uniform(0.5, 1.0))

def add_leaky_expression(circuit, gene_name):
    leakage_strength = random.uniform(0.01, 0.1)
    circuit.add_edge(gene_name, gene_name, "activation", leakage_strength)

# Add input signals to both genes
add_input_signal(toggle_switch, "Gene1")
add_input_signal(toggle_switch, "Gene2")
visualize_circuit(toggle_switch)

# Add output reporters to both genes
add_output_reporter(toggle_switch, "Gene1")
add_output_reporter(toggle_switch, "Gene2")
visualize_circuit(toggle_switch)

# Add leaky expression to both genes
add_leaky_expression(toggle_switch, "Gene1")
add_leaky_expression(toggle_switch, "Gene2")
visualize_circuit(toggle_switch)