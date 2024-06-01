import random

# Example genetic circuit dataset
genetic_circuits = [
    ['promoter1', 'rbs1', 'cds1', 'terminator1'],
    ['promoter2', 'rbs2', 'cds2', 'terminator2'],
    # More circuits...
]

# Function to create training data for next component prediction
def create_next_component_data(circuits):
    input_sequences = []
    next_components = []
    for circuit in circuits:
        for i in range(len(circuit) - 1):
            input_sequences.append(circuit[:i+1])
            next_components.append(circuit[i+1])
    return input_sequences, next_components

import torch
import torch.nn as nn
import torch.optim as optim

class NextComponentPredictor(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim):
        super(NextComponentPredictor, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.rnn = nn.GRU(embedding_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(self, x):
        x = self.embedding(x)
        x, _ = self.rnn(x)
        x = self.fc(x[:, -1, :])
        return x

# Example usage
input_sequences, next_components = create_next_component_data(genetic_circuits)

# Example usage
vocab_size = len(set(sum(genetic_circuits, [])))  # Unique components
embedding_dim = 128
hidden_dim = 256

model = NextComponentPredictor(vocab_size, embedding_dim, hidden_dim)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Example usage
def sequences_to_tensor(sequences, vocab):
    return torch.tensor([[vocab[component] for component in sequence] for sequence in sequences])

# Create a vocabulary
vocab = {component: idx for idx, component in enumerate(set(sum(genetic_circuits, [])))}
input_tensors = sequences_to_tensor(input_sequences, vocab)
target_tensors = torch.tensor([vocab[component] for component in next_components])

# Training loop
epochs = 10
for epoch in range(epochs):
    model.train()
    optimizer.zero_grad()
    outputs = model(input_tensors)
    loss = criterion(outputs, target_tensors)
    loss.backward()
    optimizer.step()
    print(f'Epoch {epoch+1}/{epochs}, Loss: {loss.item()}')
