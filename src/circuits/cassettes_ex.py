def create_casssette_sbol2():
    from sbol2 import Document, ComponentDefinition, Sequence, setHomespace
    from sbol2.constants import SO_PROMOTER, SO_CDS, SO_RBS, SO_TERMINATOR

    setHomespace('http://sys-bio.org')
    doc = Document()

    gene = ComponentDefinition('gene_example')
    r0010 = ComponentDefinition('R0010')
    b0032 = ComponentDefinition('B0032')
    e0040 = ComponentDefinition('E0040')
    b0012 = ComponentDefinition('B0012')

    r0010.roles = SO_PROMOTER
    b0032.roles = SO_CDS
    e0040.roles = SO_RBS
    b0012.roles = SO_TERMINATOR

    doc.addComponentDefinition(gene)
    doc.addComponentDefinition([r0010, b0032, e0040, b0012])

    gene.assemblePrimaryStructure([r0010, b0032, e0040, b0012])

    first = gene.getFirstComponent()
    print(first.identity)
    last = gene.getLastComponent()
    print(last.identity)

    r0010.sequence = Sequence('R0010', 'ggctgca')
    b0032.sequence = Sequence('B0032', 'aattatataaa')
    e0040.sequence = Sequence('E0040', "atgtaa")
    b0012.sequence = Sequence('B0012', 'attcga')

    target_sequence = gene.compile()
    print(gene.sequence.elements)

    result = doc.write('parts/gene_cassette.xml')
    print(result)

    return target_sequence, result


def create_casssette_sbol3():
    import sbol3

    sbol3.set_namespace('http://sys-bio.org')
    # Ptet promoter
    ptet = sbol3.Component('pTetR', sbol3.SBO_DNA)
    ptet.roles = [sbol3.SO_PROMOTER]
    ptet.name = 'pTetR'
    ptet.description = 'TetR repressible promoter'

    # The operator
    op1 = sbol3.Component('op1', sbol3.SBO_DNA)
    op1.roles = [sbol3.SO_OPERATOR]
    op1.description = 'Your Description Here'

    # RBS
    utr1 = sbol3.Component('UTR1', sbol3.SBO_DNA)
    utr1.roles = [sbol3.SO_RBS]
    utr1.description = 'Your Description Here'

    # Create the GFP coding sequence
    gfp = sbol3.Component('GFP', sbol3.SBO_DNA)
    gfp.roles.append(sbol3.SO_CDS)
    gfp.name = 'GFP'
    gfp.description = 'GFP Coding Sequence'

    # Wrap it together
    circuit = sbol3.Component('circuit', sbol3.SBO_DNA)
    circuit.roles.append(sbol3.SO_ENGINEERED_REGION)
    ptet_sc = sbol3.SubComponent(ptet)
    op1_sc = sbol3.SubComponent(op1)
    utr1_sc = sbol3.SubComponent(utr1)
    gfp_sc = sbol3.SubComponent(gfp)

    # circuit.features can be set and appended to like any Python list
    circuit.features = [ptet_sc, op1_sc]
    circuit.features += [utr1_sc]
    circuit.features.append(gfp_sc)

    circuit.constraints = [sbol3.Constraint(sbol3.SBOL_PRECEDES, ptet_sc, op1_sc),
                        sbol3.Constraint(sbol3.SBOL_PRECEDES, op1_sc, utr1_sc),
                        sbol3.Constraint(sbol3.SBOL_PRECEDES, utr1_sc, gfp_sc)]

    doc = sbol3.Document()
    # TODO: doc.addAll([ptet, op1, utr1, ...])
    doc.add(ptet)
    doc.add(op1)
    doc.add(utr1)
    doc.add(gfp)
    doc.add(circuit)
    print(doc.validate())
    doc.write('parts/circuit_3.xml', sbol3.RDF_XML)


def create_mutli_part_gene_circuit():
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

    promoter = create_component(doc, 'promoter1', sbol2.SO_PROMOTER, promoter_seq)
    rbs = create_component(doc, 'rbs1', sbol2.SO_RBS, rbs_seq)
    cds = create_component(doc, 'cds1', sbol2.SO_CDS, cds_seq)
    terminator = create_component(doc, 'terminator1', sbol2.SO_TERMINATOR, terminator_seq)

    promoter2 = create_component(doc, 'promoter2', sbol2.SO_PROMOTER, promoter_seq)
    rbs2 = create_component(doc, 'rbs2', sbol2.SO_RBS, rbs_seq)
    cds2 = create_component(doc, 'cds2', sbol2.SO_CDS, cds_seq)
    terminator2 = create_component(doc, 'terminator2', sbol2.SO_TERMINATOR, terminator_seq)

    ex_component1.assemblePrimaryStructure([promoter, rbs, cds, terminator])
    ex_component2.assemblePrimaryStructure([promoter2, rbs2, cds2, terminator2])

    output_file = 'parts/multi_part_gene_circuit.xml'
    doc.write(output_file)
    print(f'SBOL document written to {output_file}')
