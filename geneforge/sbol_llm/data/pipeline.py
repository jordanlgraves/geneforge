import os
import asyncio
from geneforge.data.scraper import SynBioHubMetadataScraper, SynBioHubSBOLScraper
from geneforge.data.simplify import simplify_json_files
from geneforge.data.structure import convert_sbol_files_to_json
from geneforge.data.validation import validate_sbol_directory
from geneforge.data.normalization import normalize_sbol_directory
from geneforge.data.annotation import annotate_sbol_directory

def run_synbiohub_scraper(data_dir, 
                base_url="https://synbiohub.org/public/igem",
                collection_name="igem_collection",
                file_types=["sbol", "gb", "fasta"],
                batch_size=10,
                max_items=1000):
    """
    Scrape metadata and SBOL documents from the SynBioHub iGEM collection.
    set max_items to None to scrape all items.
    """
    # Scrape metadata
    metadata_scraper = SynBioHubMetadataScraper(base_url, collection_name, data_dir, batch_size, max_items)
    asyncio.get_event_loop().run_until_complete(metadata_scraper.scrape())
    metadata_file_path = metadata_scraper.get_metadata_file_path()

    # Scrape SBOL documents based on metadata
    sbol_scraper = SynBioHubSBOLScraper(base_url, metadata_file_path, data_dir, file_types)
    asyncio.get_event_loop().run_until_complete(sbol_scraper.scrape())

def run_validation(input_dir, output_dir):
    validate_sbol_directory(input_dir, output_dir)

def run_normalization(input_dir, output_dir):
    normalize_sbol_directory(input_dir, output_dir)

def run_annotation(input_dir, output_dir):
    annotate_sbol_directory(input_dir, output_dir)

def run_structure(input_dir, output_dir):
    convert_sbol_files_to_json(input_dir, output_dir)

def run_simplification(input_dir, output_dir):
    simplify_json_files(input_dir, output_dir)

def main():
    root = 'data/syn_bio_hub'
    scraped_dir = f'{root}/scraped'
    scraped_sbol_dir = f'{root}/scraped/sbol'
    validated_dir = f'{root}/validated/sbol'
    normalized_dir = f'{root}/sbol/normalized'
    annotated_dir = f'{root}/sbol/annotated'
    structured_dir = f'{root}/sbol/structured'
    simplified_dir = f'{root}/sbol/simplified'
    
    # Step 1: Run Scraper
    run_synbiohub_scraper(scraped_dir)

    # Step 2: Run Validation
    # run_validation(scraped_sbol_dir, validated_dir)

    # Step 3: Run Normalization
    run_normalization(scraped_sbol_dir, normalized_dir)

    # Step 4: Run Structuring
    run_structure(normalized_dir, structured_dir)

    # Step 5: Run Simplification
    run_simplification(structured_dir, simplified_dir)
    

if __name__ == '__main__':
    main()
