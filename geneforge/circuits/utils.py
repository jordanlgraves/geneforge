
import random
from geneforge.circuits.graph import Circuit
import simplesbml
import matplotlib.pyplot as plt
import networkx as nx

def generate_feed_forward_loop(gene1, gene2, gene3):
    circuit = Circuit()

    # Add nodes
    circuit.add_node(gene1)
    circuit.add_node(gene2)
    circuit.add_node(gene3)

    # Add edges
    circuit.add_edge(gene1, gene2, "activation", random.uniform(0.5, 2.0))
    circuit.add_edge(gene1, gene3, "activation", random.uniform(0.5, 2.0))
    circuit.add_edge(gene2, gene3, "activation", random.uniform(0.5, 2.0))

    # Set node parameters
    for gene_name in [gene1, gene2, gene3]:
        gene = circuit.get_node(gene_name)
        gene.set_parameter("basal_expression", random.uniform(0.01, 0.1))
        gene.set_parameter("max_expression", random.uniform(0.5, 1.0))
        gene.set_parameter("degradation_rate", random.uniform(0.05, 0.2))

    # Set edge parameters
    for edge in circuit.edges:
        edge.set_parameter("binding_affinity", random.uniform(0.1, 1.0))
        edge.set_parameter("hill_coefficient", random.uniform(1, 4))

    return circuit

def generate_toggle_switch(gene1, gene2):
    circuit = Circuit()

    # Add nodes
    circuit.add_node(gene1)
    circuit.add_node(gene2)

    # Add edges (mutual repression)
    circuit.add_edge(gene1, gene2, "repression", random.uniform(1.0, 3.0))
    circuit.add_edge(gene2, gene1, "repression", random.uniform(1.0, 3.0))

    # Set node parameters
    for gene_name in [gene1, gene2]:
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


def circuit_to_sbml(circuit, initial_conditions):
    model = simplesbml.SbmlModel()
    model.addCompartment(vol=1.0, comp_id='cell')

    for node_name, node in circuit.nodes.items():
        initial_amount = float(initial_conditions.get(node_name, 0.1))  # Default initial amount if not specified
        model.addSpecies(species_id=node_name, amt=initial_amount, comp='cell')

    for edge in circuit.edges:
        source = edge.source.name
        target = edge.target.name
        rate_constant = edge.strength
        if edge.edge_type == "activation":
            expression = f'cell * {rate_constant} * {source}'
        elif edge.edge_type == "repression":
            expression = f'cell * {rate_constant} * (1 - {source})'

        model.addReaction(reactants=[source], products=[target], expression=expression)

    for node_name, node in circuit.nodes.items():
        for param, value in node.parameters.items():
            model.addParameter(param_id=f'{node_name}_{param}', val=value)

    for edge in circuit.edges:
        for param, value in edge.parameters.items():
            model.addParameter(param_id=f'{edge.source.name}_to_{edge.target.name}_{param}', val=value)

    return model


def visualize_circuit(circuit, figsize=(6, 6)):
    G = nx.DiGraph()

    for node_name, node in circuit.nodes.items():
        G.add_node(node_name, **node.parameters)

    for edge in circuit.edges:
        G.add_edge(edge.source.name, edge.target.name,
                   edge_type=edge.edge_type,
                   strength=edge.strength,
                   **edge.parameters)

    pos = nx.spring_layout(G)

    # Set up the figure size
    plt.figure(figsize=figsize)

    # Draw nodes with parameters
    node_labels = {node: f"{node}\n" + "\n".join([f"{k}: {v:.2f}" for k, v in G.nodes[node].items()]) for node in G.nodes()}
    nx.draw_networkx_nodes(G, pos)
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)

    # Draw edges with parameters
    edge_colors = ['g' if G[u][v]['edge_type'] == 'activation' else 'r' for u, v in G.edges()]
    edge_labels = {(u, v): f"{d['strength']:.2f}\n" + "\n".join([f"{k}: {v:.2f}" for k, v in d.items() if k not in ['edge_type', 'strength']]) for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrows=True, arrowsize=20)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

    plt.axis('off')
    plt.show()


def component_type_to_color(component_type):
    type_to_color = {
        "gene": "green",
        "promoter": "blue",
        "repressor": "red"
    }
    return type_to_color.get(component_type, "gray")


if __name__ == "__main__":
    from geneforge.circuits.utils import fetch_mean_expression

    tissue="lung"
    cell_type="mucus secreting cell"
    mean_expression = fetch_mean_expression(cell_type, tissue)
    print(mean_expression)

    # ffl = generate_feed_forward_loop()
    # visualize_circuit(ffl)

    # toggle_switch = generate_toggle_switch()
    # visualize_circuit(toggle_switch)

    # Add input signals to both genes
    # add_input_signal(toggle_switch, "Gene1")
    # add_input_signal(toggle_switch, "Gene2")
    # visualize_circuit(toggle_switch)

    # # Add output reporters to both genes
    # add_output_reporter(toggle_switch, "Gene1")
    # add_output_reporter(toggle_switch, "Gene2")
    # visualize_circuit(toggle_switch)

    # # Add leaky expression to both genes
    # add_leaky_expression(toggle_switch, "Gene1")
    # add_leaky_expression(toggle_switch, "Gene2")
    # visualize_circuit(toggle_switch)
