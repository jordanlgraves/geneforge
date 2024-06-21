import random
from typing import List, Tuple, Dict
import networkx as nx
from matplotlib import pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout
import numpy as np

# Define logic gate operations
def AND(a, b):
    return int(a and b)

def OR(a, b):
    return int(a or b)

def XOR(a, b):
    return int(a ^ b)

def NAND(a, b):
    return int(not (a and b))

# Circuit class to represent circuits as genomes
class Circuit:
    def __init__(self, num_inputs, num_gates):
        self.num_inputs = num_inputs
        self.num_gates = num_gates
        self.gates = []
        self.output_gate = None
        self.initialize_random_circuit()

    def initialize_random_circuit(self):
        self.gates = []
        for _ in range(self.num_gates):
            input1 = random.randint(0, self.num_inputs + len(self.gates) - 1)
            input2 = random.randint(0, self.num_inputs + len(self.gates) - 1)
            self.gates.append((input1, input2))
        self.output_gate = random.randint(0, self.num_gates - 1)

    def evaluate(self, inputs):
        gate_values = list(inputs) + [None] * self.num_gates
        for i, (input1, input2) in enumerate(self.gates):
            gate_values[self.num_inputs + i] = NAND(gate_values[input1], gate_values[input2])
        return gate_values[self.num_inputs + self.output_gate]

    def mutate(self):
        # Implement different types of mutations here
        pass

    def calculate_fitness(self, goal):
        fitness = 0
        for inputs in generate_all_inputs(self.num_inputs):
            output = self.evaluate(inputs)
            fitness += int(output == goal(inputs))
        return fitness / (2 ** self.num_inputs)
    
    def calculate_entropy(self, samples: int = 1000) -> float:
        """
        Calculate the Shannon entropy of the circuit's output given random inputs.
        """
        output_counts = {}
        for _ in range(samples):
            inputs = [random.randint(0, 1) for _ in range(self.num_inputs)]
            output = self.evaluate(inputs)
            output_counts[output] = output_counts.get(output, 0) + 1

        probabilities = np.array(list(output_counts.values())) / samples
        entropy = -np.sum(probabilities * np.log2(probabilities))
        return entropy

    def get_modularity_score(self):
        # Create a NetworkX graph from the circuit
        circuit_graph = nx.DiGraph()
        for i in range(self.num_inputs):
            circuit_graph.add_node(f"input_{i}", bipartite=0)
        for i in range(self.num_gates):
            circuit_graph.add_node(f"gate_{i}", bipartite=1)
        for gate_idx, (input1, input2) in enumerate(self.gates):
            circuit_graph.add_edge(f"input_{input1}" if input1 < self.num_inputs else f"gate_{input1 - self.num_inputs}",
                                f"gate_{gate_idx}")
            circuit_graph.add_edge(f"input_{input2}" if input2 < self.num_inputs else f"gate_{input2 - self.num_inputs}",
                                f"gate_{gate_idx}")

        # Calculate the modularity score using the Louvain algorithm
        partitions = nx.algorithms.community.louvain_partitions(circuit_graph)
        if partitions:
            partition = list(partitions)[0]  # Take the first partition
            return nx.algorithms.community.modularity(circuit_graph, partition)
        else:
            return 0.0  # Return 0.0 if no partition is found

    def visualize(self):
        """
        Visualize the circuit using NetworkX's drawing capabilities.
        """
        circuit_graph = nx.DiGraph()
        for i in range(self.num_inputs):
            node_name = f"input_{i}"
            circuit_graph.add_node(node_name, node_color='lightgreen')
        for i in range(self.num_gates):
            node_name = f"gate_{i}"
            circuit_graph.add_node(node_name, node_color='lightblue')

        for gate_idx, (input1, input2) in enumerate(self.gates):
            source_node1 = f"input_{input1}" if input1 < self.num_inputs else f"gate_{input1 - self.num_inputs}"
            source_node2 = f"input_{input2}" if input2 < self.num_inputs else f"gate_{input2 - self.num_inputs}"
            target_node = f"gate_{gate_idx}"
            circuit_graph.add_edge(source_node1, target_node)
            circuit_graph.add_edge(source_node2, target_node)

        # Add the output node
        output_node = "output"
        output_gate_node = f"gate_{self.output_gate}"
        circuit_graph.add_node(output_node, node_color='lightcoral')
        circuit_graph.add_edge(output_gate_node, output_node)

        # Use graphviz_layout with the 'dot' program for a hierarchical layout
        pos = graphviz_layout(circuit_graph, prog='dot')
        plt.figure(figsize=(10, 6))
        nx.draw(circuit_graph, pos, with_labels=True, node_color=[circuit_graph.nodes[node]['node_color'] for node in circuit_graph.nodes])
        plt.axis('off')
        plt.show()

class LayeredCircuit(Circuit):
    def __init__(self, num_inputs, num_gates, num_layers, gates_per_layer=None):
        super().__init__(num_inputs, num_gates)
        self.num_layers = num_layers
        self.gates_per_layer = gates_per_layer or [num_gates // num_layers] * num_layers
        self.gates_per_layer[-1] += num_gates % num_layers  # Assign remaining gates to last layer
        self.initialize_layered_circuit()
    def initialize_layered_circuit(self):
        self.gates = []
        input_nodes = list(range(self.num_inputs))
        layer_inputs = input_nodes.copy()

        for layer_idx, num_gates_in_layer in enumerate(self.gates_per_layer):
            layer_gates = []
            for _ in range(num_gates_in_layer):
                if layer_idx == 0:
                    input1 = random.choice(input_nodes)
                    input2 = random.choice(input_nodes)
                else:
                    input1 = random.choice(layer_inputs)
                    input2 = random.choice(layer_inputs)
                layer_gates.append((input1, input2))
                layer_inputs.append(len(self.gates) + self.num_inputs)
            self.gates.extend(layer_gates)

        self.output_gate = random.randint(len(self.gates) - self.gates_per_layer[-1], len(self.gates) - 1)
    def visualize(self):
        """
        Visualize the circuit using NetworkX's drawing capabilities.
        """
        circuit_graph = nx.DiGraph()

        # Add input nodes with node_color attribute
        for i in range(self.num_inputs):
            node_name = f"input_{i}"
            circuit_graph.add_node(node_name, node_color='lightgreen')

        # Add gate nodes with node_color attribute
        for layer_idx, num_gates_in_layer in enumerate(self.gates_per_layer):
            for i in range(num_gates_in_layer):
                node_name = f"gate_{layer_idx}_{i}"
                circuit_graph.add_node(node_name, node_color='lightblue')

        # Add edges between nodes
        layer_inputs = list(range(self.num_inputs))
        for layer_idx, num_gates_in_layer in enumerate(self.gates_per_layer):
            for gate_idx in range(num_gates_in_layer):
                input1, input2 = self.gates[sum(self.gates_per_layer[:layer_idx]) + gate_idx]
                source_node1 = f"input_{input1}" if input1 < self.num_inputs else f"gate_{input1 // self.gates_per_layer[input1 // len(self.gates_per_layer)]}_{input1 % self.gates_per_layer[input1 // len(self.gates_per_layer)]}"
                source_node2 = f"input_{input2}" if input2 < self.num_inputs else f"gate_{input2 // self.gates_per_layer[input2 // len(self.gates_per_layer)]}_{input2 % self.gates_per_layer[input2 // len(self.gates_per_layer)]}"
                target_node = f"gate_{layer_idx}_{gate_idx}"
                circuit_graph.add_edge(source_node1, target_node)
                circuit_graph.add_edge(source_node2, target_node)
                layer_inputs.append(target_node)

        # Add the output node
        output_node = "output"
        output_gate_node = f"gate_{self.output_gate // self.gates_per_layer[-1]}_{self.output_gate % self.gates_per_layer[-1]}"
        circuit_graph.add_node(output_node, node_color='lightcoral')
        circuit_graph.add_edge(output_gate_node, output_node)

        # Use graphviz_layout with the 'dot' program for a hierarchical layout
        pos = graphviz_layout(circuit_graph, prog='dot')
        plt.figure(figsize=(10, 6))
        # node_colors = [circuit_graph.nodes[node]['node_color'] for node in circuit_graph.nodes()]
        nx.draw(circuit_graph, pos, with_labels=True) #, node_color=node_colors)
        plt.axis('off')
        plt.show()

# Helper function to generate all possible input combinations
def generate_all_inputs(num_inputs):
    inputs = [0] * num_inputs
    all_inputs = []
    i = 0
    while i < num_inputs:
        all_inputs.append(inputs.copy())
        inputs[i] = 1 - inputs[i]
        i += 1 if inputs[i] else 0
    return all_inputs

# Define fitness function for a given goal
def fitness_function(circuit, goal):
    return circuit.calculate_fitness(goal)

# Simulate evolution with constant goal
def evolve_constant_goal(goal, population_size, mutation_rate, max_generations, num_inputs, num_gates):
    population = [Circuit(num_inputs, num_gates) for _ in range(population_size)]
    for circuit in population:
        circuit.visualize()
    best_fitnesses = []
    best_modularities = []
    entropies = []
    for generation in range(max_generations):
        fitnesses = [fitness_function(circuit, goal) for circuit in population]
        best_fitness = max(fitnesses)
        best_fitnesses.append(best_fitness)
        best_circuit = max((circuit for circuit in population if circuit.calculate_fitness(goal) == best_fitness),
                           key=lambda circuit: circuit.get_modularity_score())
        best_modularities.append(best_circuit.get_modularity_score())
        entropies.append(best_circuit.calculate_entropy())
        selected_circuits = select_fittest(population, fitnesses)
        mutated_circuits = apply_mutations(selected_circuits, mutation_rate)
        population = repopulate(mutated_circuits, population_size, num_inputs, num_gates)
        if best_fitness == 1.0:
            break
    return best_fitnesses, best_modularities, entropies, best_circuit, generation + 1

# Simulate evolution with modularly varying goals (MVG)
def evolve_mvg(goals, population_size, mutation_rate, max_generations, num_inputs, num_gates, switch_period):
    population = [Circuit(num_inputs, num_gates) for _ in range(population_size)]
    best_fitnesses = []
    best_modularities = []
    entropies = []
    for generation in range(max_generations):
        current_goal = goals[generation // switch_period % len(goals)]
        fitnesses = [fitness_function(circuit, current_goal) for circuit in population]
        best_fitness = max(fitnesses)
        best_fitnesses.append(best_fitness)
        best_circuit = max((circuit for circuit in population if circuit.calculate_fitness(current_goal) == best_fitness),
                           key=lambda circuit: circuit.get_modularity_score())
        best_modularities.append(best_circuit.get_modularity_score())
        entropies.append(best_circuit.calculate_entropy())
        selected_circuits = select_fittest(population, fitnesses)
        mutated_circuits = apply_mutations(selected_circuits, mutation_rate)
        population = repopulate(mutated_circuits, population_size, num_inputs, num_gates)
        if best_fitness == 1.0:
            break
    return best_fitnesses, best_modularities, entropies, best_circuit, generation + 1

from typing import List, Tuple

# Helper function to select the fittest circuits based on fitnesses
def select_fittest(population, fitnesses):
    sorted_indices = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)
    sorted_population = [population[i] for i in sorted_indices]
    return sorted_population[:len(population) // 2]

# Helper function to apply mutations to the circuits
def apply_mutations(circuits, mutation_rate):
    mutated_circuits = []
    for circuit in circuits:
        if random.random() < mutation_rate:
            mutated_circuit = Circuit(circuit.num_inputs, circuit.num_gates)
            mutated_circuit.gates = circuit.gates.copy()
            
            # Implement different types of mutations
            
            # Point mutation (change a single connection)
            gate_idx = random.randint(0, len(mutated_circuit.gates) - 1)
            input_idx = random.randint(0, 1)
            new_input = random.randint(0, mutated_circuit.num_inputs + len(mutated_circuit.gates) - 1)
            mutated_circuit.gates[gate_idx] = list(mutated_circuit.gates[gate_idx])
            mutated_circuit.gates[gate_idx][input_idx] = new_input
            mutated_circuit.gates[gate_idx] = tuple(mutated_circuit.gates[gate_idx])
            
            mutated_circuits.append(mutated_circuit)
        else:
            mutated_circuits.append(circuit)
    return mutated_circuits

# Helper function to repopulate the population with the mutated circuits
def repopulate(circuits, population_size, num_inputs, num_gates):
    new_population = circuits.copy()
    while len(new_population) < population_size:
        parent1 = random.choice(circuits)
        parent2 = random.choice(circuits)
        
        # Recombination (crossover)
        crossover_point = random.randint(0, len(parent1.gates))
        child_gates = parent1.gates[:crossover_point] + parent2.gates[crossover_point:]
        child = Circuit(num_inputs, num_gates)
        child.gates = child_gates
        child.output_gate = random.randint(0, num_gates - 1)
        
        new_population.append(child)
    return new_population[:population_size]

# Usage
constant_goal = lambda inputs: XOR(inputs[0], inputs[1])
modular_goals = [
    lambda inputs: AND(XOR(inputs[0], inputs[1]), XOR(inputs[2], inputs[3])),
    lambda inputs: OR(XOR(inputs[0], inputs[1]), XOR(inputs[2], inputs[3]))
]

population_size = 100 # 100
mutation_rate = 0.1
max_generations = 1000 #1000
num_inputs = 4
num_gates = 6
switch_period = 10

# Create a layered circuit with 4 inputs, 6 gates, and 3 layers
layered_circuit = LayeredCircuit(num_inputs=4, num_gates=6, num_layers=3)
layered_circuit.visualize()
# Create a layered circuit with 4 inputs, 6 gates, and 2 layers with 2 and 4 gates respectively
layered_circuit = LayeredCircuit(num_inputs=4, num_gates=6, num_layers=2, gates_per_layer=[2, 4])
layered_circuit.visualize()

# Evolve circuits for a constant goal
constant_fitnesses, constant_modularities, constant_entropies, constant_best_circuit, constant_generations = evolve_constant_goal(
    constant_goal, population_size, mutation_rate, max_generations, num_inputs, num_gates)
print(f"Constant goal: fitness={constant_fitnesses[-1]}, generations={constant_generations}")
print(f"Constant goal modularity: {constant_modularities[-1]}")
print(f"Constant goal entropy: {constant_entropies[-1]}")

# Evolve circuits for modularly varying goals
mvg_fitnesses, mvg_modularities, mvg_entropies, mvg_best_circuit, mvg_generations = evolve_mvg(
    modular_goals, population_size, mutation_rate, max_generations, num_inputs, num_gates, switch_period)
print(f"MVG: fitness={mvg_fitnesses[-1]}, generations={mvg_generations}")
print(f"MVG modularity: {mvg_modularities[-1]}")
print(f"MVG entropy: {mvg_entropies[-1]}")

constant_best_circuit.visualize()
mvg_best_circuit.visualize()

# Compare and analyze the results
plt.figure(figsize=(12, 6))
plt.plot(constant_entropies, label='Constant Goal Entropy')
plt.plot(mvg_entropies, label='MVG Entropy')
plt.xlabel('Generation')
plt.ylabel('Entropy')
plt.legend()
plt.title('Entropy Comparison: Constant Goal vs MVG')
plt.show()
