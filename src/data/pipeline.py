import os
import asyncio
from src.data.scraper import SynBioHubMetadataScraper, SynBioHubSBOLScraper
from src.data.structure import convert_sbol_files_to_json
from src.data.validation import validate_sbol_directory
from src.data.normalization import normalize_sbol_directory
from src.data.annotation import annotate_sbol_directory

def run_scraper(data_dir, file_types=["sbol", "gb", "fasta"]):
    base_url = 'https://synbiohub.org/public/igem'
    collection_name = 'igem_collection'
    batch_size = 10
    max_items = 1000  # Set this to None to scrape all items

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

def main():
    root = 'data/syn_bio_hub'
    scraped_dir = f'{root}/scraped'
    scraped_sbol_dir = f'{root}/scraped/sbol'
    validated_dir = f'{root}/validated/sbol'
    normalized_dir = f'{root}/sbol/normalized'
    annotated_dir = f'{root}/sbol/annotated'
    structured_dir = f'{root}/sbol/structured'
    
    # Step 1: Run Scraper
    #run_scraper(scraped_dir)

    # Step 2: Run Validation
    # run_validation(scraped_sbol_dir, validated_dir)

    # Step 3: Run Normalization
    # run_normalization(scraped_sbol_dir, normalized_dir)

    # Step 4: Run Structuring
    
    run_structure(normalized_dir, structured_dir)
    

if __name__ == '__main__':
    main()
