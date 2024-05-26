import sbol2

# Initialize SBOL document
sbol2.setHomespace('http://sys-bio.org')
doc = sbol2.Document()

# Function to create a component and add it to the document
def create_component(doc, name, role, sequence):
    component = sbol2.ComponentDefinition(name)
    component.roles = role
    seq = sbol2.Sequence(name + '_seq', sequence)
    component.sequences = [seq]
    doc.addSequence(seq)
    doc.addComponentDefinition(component)
    return component

# Define parts sequences
promoter_seq = 'ttgacaattaaacgctacta'
rbs_seq = 'aggagg'
cds_seq = 'atggctgaagtcggtgacg'
terminator_seq = 'ttactagtagcggccgctgcag'

ex_component1 = sbol2.ComponentDefinition('example_component1')
ex_component2 = sbol2.ComponentDefinition('example_component2')

doc.addComponentDefinition(ex_component1)
doc.addComponentDefinition(ex_component2)

# Create components
promoter = create_component(doc, 'promoter1', sbol2.SO_PROMOTER, promoter_seq)
rbs = create_component(doc, 'rbs1', sbol2.SO_RBS, rbs_seq)
cds = create_component(doc, 'cds1', sbol2.SO_CDS, cds_seq)
terminator = create_component(doc, 'terminator1', sbol2.SO_TERMINATOR, terminator_seq)

# Create another set of components
promoter2 = create_component(doc, 'promoter2', sbol2.SO_PROMOTER, promoter_seq)
rbs2 = create_component(doc, 'rbs2', sbol2.SO_RBS, rbs_seq)
cds2 = create_component(doc, 'cds2', sbol2.SO_CDS, cds_seq)
terminator2 = create_component(doc, 'terminator2', sbol2.SO_TERMINATOR, terminator_seq)

ex_component1.assemblePrimaryStructure([promoter, rbs, cds, terminator])
ex_component2.assemblePrimaryStructure([promoter2, rbs2, cds2, terminator2])

# Save the document
output_file = 'multi_part_gene_circuit.xml'
doc.write(output_file)
print(f'SBOL document written to {output_file}')
