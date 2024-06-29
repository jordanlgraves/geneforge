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
