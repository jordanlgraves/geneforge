import os
import pandas as pd
import matplotlib.pyplot as plt
import sbol2

from geneforge.data.io import read_sbol_file

def read_sbol_files_from_directory(directory):
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith('.xml') or filename.endswith('.sbol'):
            file_path = os.path.join(directory, filename)
            doc = read_sbol_file(file_path)
            documents.append(doc)
    return documents

def extract_component_data_from_sbol_documents(documents):
    object_data = []
    document_metadata = []
    for doc in documents:
        physical_parts_count = 0
        for key, obj in doc.SBOLObjects.items():
            if isinstance(obj, sbol2.ComponentDefinition):
                # Extract information from ComponentDefinition
                for component in obj.components:
                    physical_parts_count += 1
                    object_data.append({
                        'name': component.name,
                        'display_id': component.displayId,
                        'description': component.description,
                        'types': [_.split('/')[-1] for _ in obj.types] if obj.types else ['unknown'],
                        'roles': [_.split('/')[-1] for _ in obj.roles] if obj.roles else ['unknown'],
                    })
                # for sequence in obj.sequences:                    
                    # physical_parts_count += 1
                    # object_data.append({
                    #     'name': sequence.name,
                    #     'display_id': sequence.displayId,
                    #     'description': sequence.description,
                    #     'types': [_.split('/')[-1] for _ in sequence.types] if sequence.types else ['unknown'],
                    #     'roles': [_.split('/')[-1] for _ in sequence.roles] if sequence.roles else ['unknown'],
                    # })
            elif isinstance(obj, sbol2.ModuleDefinition):
                # Extract information from ModuleDefinition
                for fc in obj.functionalComponents:
                    physical_parts_count += 1
                    object_data.append({
                        'name': fc.definition.name,
                        'display_id': fc.definition.displayId,
                        'description': fc.definition.description,
                        'types': [_.split('/')[-1] for _ in fc.definition.types] if fc.definition.types else ['unknown'],
                        'roles': [_.split('/')[-1] for _ in fc.definition.roles] if fc.definition.roles else ['unknown'],
                    })
            elif isinstance(obj, sbol2.Component):
                # Extract information from Component
                physical_parts_count += 1
                object_data.append({
                    'name': obj.name,
                    'display_id': obj.displayId,
                    'description': obj.description,
                    'types': [_.split('/')[-1] for _ in obj.types] if obj.types else ['unknown'],
                    'roles': [_.split('/')[-1] for _ in obj.roles] if obj.roles else ['unknown'],
                })
            elif isinstance(obj, sbol2.FunctionalComponent):
                # Extract information from FunctionalComponent
                physical_parts_count += 1
                object_data.append({
                    'name': obj.definition.name,
                    'display_id': obj.definition.displayId,
                    'description': obj.definition.description,
                    'types': [_.split('/')[-1] for _ in obj.definition.types] if obj.definition.types else ['unknown'],
                    'roles': [_.split('/')[-1] for _ in obj.definition.roles] if obj.definition.roles else ['unknown'],
                })
            elif isinstance(obj, sbol2.Sequence):
                # Extract information from Sequence
                object_data.append({
                    'name': obj.displayId,
                    'display_id': obj.displayId,
                    'description': 'Sequence',
                    'types': ['sequence'],
                    'roles': ['sequence'],
                })
            elif isinstance(obj, sbol2.SequenceAnnotation):
                # Extract information from SequenceAnnotation
                object_data.append({
                    'name': obj.component.name,
                    'display_id': obj.component.displayId,
                    'description': obj.component.description,
                    'types': [_.split('/')[-1] for _ in obj.component.types] if obj.component.types else ['unknown'],
                    'roles': [_.split('/')[-1] for _ in obj.component.roles] if obj.component.roles else ['unknown'],
                })
            elif isinstance(obj, sbol2.Range):
                # Extract information from Range
                object_data.append({
                    'name': obj.displayId,
                    'display_id': obj.displayId,
                    'description': 'Range',
                    'types': ['range'],
                    'roles': ['range'],
                })
            elif isinstance(obj, sbol2.Location):
                # Extract information from Location
                object_data.append({
                    'name': obj.displayId,
                    'display_id': obj.displayId,
                    'description': 'Location',
                    'types': ['location'],
                    'roles': ['location'],
                })
            
        document_metadata.append(physical_parts_count)
        
    return pd.DataFrame(object_data), document_metadata

def plot_distribution(data, column, title, xlabel, ylabel, output_file):
    # Explode the lists into individual rows
    exploded_data = data[column].explode()
    
    plt.figure(figsize=(10, 6))
    exploded_data.value_counts().plot(kind='bar')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file)
    # plt.show()


def analyze_component_types(data, out_dir='.'):
    plot_distribution(data, 'types', 'Distribution of Component Types', 'Component Type', 'Count', os.path.join(out_dir, 'component_type_distribution.png'))
    # Save list of unique types and their counts to CSV
    types = data['types'].explode().value_counts().reset_index()
    types.columns = ['type', 'count']
    types.to_csv(os.path.join(out_dir, 'component_types.csv'), index=False)

def analyze_component_roles(data, out_dir='.'):
    plot_distribution(data, 'roles', 'Distribution of Component Roles', 'Component Role', 'Count', os.path.join(out_dir, 'component_role_distribution.png'))
    # Save list of unique roles and their counts to CSV
    roles = data['roles'].explode().value_counts().reset_index()
    roles.columns = ['role', 'count']
    roles.to_csv(os.path.join(out_dir, 'component_roles.csv'), index=False)

def analyze_component_counts(data, out_dir='.'):
    component_counts = data['name'].value_counts()
    plt.figure(figsize=(10, 6))
    component_counts.plot(kind='hist', bins=20)
    plt.title('Distribution of Number of Components per Part')
    plt.xlabel('Number of Components')
    plt.ylabel('Count')
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_dir), exist_ok=True)
    plt.savefig(os.path.join(out_dir, 'component_count_distribution.png'))
    # plt.show()

def analyze_document_metadata(metadata, out_dir='.'):
    plt.figure(figsize=(10, 6))
    metadata['physical_parts_count'].plot(kind='hist', bins=20)
    plt.title('Distribution of Physical Parts Count in Documents')
    plt.xlabel('Number of Physical Parts')
    plt.ylabel('Count')
    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    plt.savefig(os.path.join(out_dir, 'physical_parts_count_distribution.png'))
    # plt.show()

def main():
    step = "normalized"
    
    sbol_dir = f'data/syn_bio_hub/scraped/sbol' if step == 'scraped' else f'data/syn_bio_hub/sbol/{step}/'
    out_dir = f'reports/syn_bio_hub_{step}_sbol'

    # Read and parse SBOL files
    filenames = os.listdir(sbol_dir)
    documents = read_sbol_files_from_directory(sbol_dir)

    # Extract component data and document metadata
    component_data, num_parts_per_document = extract_component_data_from_sbol_documents(documents)
    # document_metadata = pd.DataFrame({'physical_parts_count': num_parts_per_document,
                                    #   'file_names': filenames})
    
    # Analyze and plot distributions
    analyze_component_types(component_data, out_dir)
    analyze_component_roles(component_data, out_dir)
    analyze_component_counts(component_data, out_dir)
    # analyze_document_metadata(document_metadata, out_dir)

    # Save dataframes to CSV
    os.makedirs(out_dir, exist_ok=True)
    component_data.to_csv(os.path.join(out_dir, 'component_data.csv'), index=False)
    # document_metadata.to_csv(os.path.join(out_dir, 'document_metadata.csv'), index=False)
    
if __name__ == '__main__':
    main()
