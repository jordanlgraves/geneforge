import os
import pandas as pd
import matplotlib.pyplot as plt
import sbol2

from src.data.io import read_sbol_file

def read_sbol_files(directory):
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith('.xml') or filename.endswith('.sbol'):
            file_path = os.path.join(directory, filename)
            doc = read_sbol_file(file_path)
            documents.append(doc)
    return documents

def extract_component_data(documents):
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
            # Add more cases as needed for other SBOL classes
        document_metadata.append({
            'display_id': doc.displayId,
            'name': doc.name,
            'description': doc.description,
            'physical_parts_count': physical_parts_count,
        })
    return pd.DataFrame(object_data), pd.DataFrame(document_metadata)

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

def analyze_component_roles(data, out_dir='.'):
    plot_distribution(data, 'roles', 'Distribution of Component Roles', 'Component Role', 'Count', os.path.join(out_dir, 'component_role_distribution.png'))

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
    step = "scraped"
    
    sbol_dir = f'data/syn_bio_hub/scraped/sbol' if step == 'scraped' else f'data/syn_bio_hub/sbol/{step}/'
    out_dir = f'reports/syn_bio_hub_{step}_sbol'

    # Read and parse SBOL files
    documents = read_sbol_files(sbol_dir)
    
    # Extract component data and document metadata
    component_data, document_metadata = extract_component_data(documents)
    
    # Analyze and plot distributions
    analyze_component_types(component_data, out_dir)
    analyze_component_roles(component_data, out_dir)
    analyze_component_counts(component_data, out_dir)
    analyze_document_metadata(document_metadata, out_dir)

if __name__ == '__main__':
    main()
