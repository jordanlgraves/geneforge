from pyensembl import EnsemblRelease


def fetch_ensembl_ids(gene_names, species='human', release=None):
    # Initialize the EnsemblRelease object
    # If release is not specified, it will use the latest version
    if release is None:
        ensembl = EnsemblRelease(species=species)
    else:
        ensembl = EnsemblRelease(release=release, species=species)

    ensembl_ids = {}
    for gene_name in gene_names:
        try:
            gene = ensembl.genes_by_name(gene_name)
            if gene:
                ensembl_ids[gene_name] = gene[0].gene_id
            else:
                ensembl_ids[gene_name] = None
        except Exception as e:
            print(f"Error fetching Ensembl ID for {gene_name}: {str(e)}")
            ensembl_ids[gene_name] = None

    return ensembl_ids


def fetch_mean_expression(cell_type, tissue):
    """
    Returns a dictionary of all genes and their mean expression values for a specified cell type and tissue.

    Parameters:
    cell_type (str): The cell type to filter for.
    tissue (str): The tissue type to filter for.

    Returns:
    dict: A dictionary mapping gene IDs to their mean expression values.
    """
    # check if adata is saved locally for cell_type and tissue saves
    # if not, download

    import os
    import scanpy as sc
    import numpy as np
    if os.path.exists(f"data/cellxgene/adata_{cell_type}_{tissue}.h5ad"):
        print(f"Loading saved adata from {f'data/cellxgene/adata_{cell_type}_{tissue}.h5ad'}")
        adata = sc.read_h5ad(f"data/cellxgene/adata_{cell_type}_{tissue}.h5ad")
    else:
        print(f"Fetching adata for {cell_type} in {tissue}")
        import gget
        # Fetch expression data for all genes for the given tissue and cell type
        adata = gget.cellxgene(
            species='homo_sapiens',
            tissue=tissue,
            cell_type=cell_type
        )
        if os.path.exists('data/cellxgene'):
            adata.write_h5ad(f"data/cellxgene/adata_{cell_type}_{tissue}.h5ad")
    
    # Calculate the mean expression for each gene
    gene_expression = {gene_id: np.mean(adata[:, idx].X.toarray()) for idx, gene_id in enumerate(adata.var['feature_id'])}
    
    return gene_expression


def get_string_interactions(genes, confidence_threshold=0.7):
    import stringdb
    string_ids = stringdb.get_string_ids(genes)
    interactions = stringdb.get_network(string_ids.preferredName.values.tolist())
    return interactions


def fetch_half_life(gene_symbol):
    import mygene
    mg = mygene.MyGeneInfo()
    result = mg.query(gene_symbol, fields='uniprot')
    if result['hits']:
        return result['hits'][0].get('uniprot', {}).get('half_life')
    return None