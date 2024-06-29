import asyncio
import aiohttp
import os
from abc import ABC, abstractmethod
from pyppeteer import launch
import csv

# Abstract base class for any type of scraper
class Scraper(ABC):
    @abstractmethod
    async def scrape(self):
        pass

# Abstract base class for metadata scrapers
class MetadataScraper(Scraper):
    @abstractmethod
    def save_metadata(self):
        pass

# Abstract base class for SBOL document scrapers
class SBOLDocumentScraper(Scraper):
    @abstractmethod
    def read_metadata_csv(self):
        pass

# Concrete implementation for scraping SynBioHub metadata
class SynBioHubMetadataScraper(MetadataScraper):
    def __init__(self, base_url, collection_name, data_dir, batch_size=10, max_items=None):
        self.base_url = base_url
        self.collection_name = collection_name
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.max_items = max_items
        self.browser = None
        self.page = None
        self.all_parts = []
        self.total_items_scraped = 0
        self.metadata_file_path = os.path.join(self.data_dir, f'{self.collection_name}_metadata.csv')

    async def init_browser(self):
        self.browser = await launch(headless=True)
        self.page = await self.browser.newPage()

    async def close_browser(self):
        if self.browser:
            await self.browser.close()

    async def get_available_collections(self):
        return ["igem_collection"]

    async def scrape(self):
        await self.init_browser()
        await self.page.goto(f'{self.base_url}/{self.collection_name}/1', {'waitUntil': 'networkidle2'})
        print("Page loaded")

        while True:
            # Wait for the table to load and ensure it has rows
            try:
                await self.page.waitFor(10000)
                await self.page.waitForSelector('table')
                await self.page.waitForFunction('document.querySelectorAll("table tbody tr").length > 0')
            except Exception as e:
                print(f"Error loading table: {e}")
                break
            
            print("Table loaded and content available")

            # Extract data from the correct table
            parts = await self.page.evaluate('''
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    return Array.from(rows).map(row => {
                        const columns = row.querySelectorAll('td');
                        if (columns.length < 4) return null;
                        return {
                            name: columns[0] ? columns[0].innerText.trim() : '',
                            identifier: columns[1] ? columns[1].innerText.trim() : '',
                            type: columns[2] ? columns[2].innerText.trim() : '',
                            description: columns[3] ? columns[3].innerText.trim() : ''
                        };
                    }).filter(item => item !== null);
                }
            ''')

            print(f"Extracted {len(parts)} parts from the current page")
            print(f"Extracted parts: {parts}")

            self.all_parts.extend(parts)
            self.total_items_scraped += len(parts)

            # Save parts to file in batches
            if len(self.all_parts) >= self.batch_size:
                self.save_metadata()
                self.all_parts = []

            # Check if the maximum number of items has been scraped
            if self.max_items and self.total_items_scraped >= self.max_items:
                print(f"Reached the maximum number of items to scrape: {self.max_items}")
                break

            # Check if there is a next page button and click it
            next_button = await self.page.querySelector('#DataTables_Table_0_next a')
            next_button_disabled = await self.page.evaluate('''
                () => document.querySelector('#DataTables_Table_0_next').classList.contains('disabled')
            ''')
            if next_button and not next_button_disabled:
                await next_button.click()
                print("Clicked next button")
            else:
                break

        await self.close_browser()

        # Save any remaining parts to file
        if self.all_parts:
            self.save_metadata()

    def save_metadata(self):
        os.makedirs(self.data_dir, exist_ok=True)
        csv_file = self.metadata_file_path
        csv_columns = ['name', 'identifier', 'type', 'description']

        with open(csv_file, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            if csvfile.tell() == 0:
                writer.writeheader()
            for part in self.all_parts:
                writer.writerow(part)

        print(f'Saved parts to {csv_file}')

    def get_metadata_file_path(self):
        return self.metadata_file_path

# Concrete implementation for scraping SynBioHub SBOL documents
class SynBioHubSBOLScraper(SBOLDocumentScraper):
    def __init__(self, base_url, metadata_csv, data_dir, file_types=None):
        if file_types is None:
            file_types = ["sbol"]
        self.base_url = base_url
        self.metadata_csv = metadata_csv
        self.data_dir = data_dir
        self.file_types = file_types
        self.sbol_documents = []

    def read_metadata_csv(self):
        with open(self.metadata_csv, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            return [row for row in reader]

    async def scrape(self):
        metadata = self.read_metadata_csv()
        async with aiohttp.ClientSession() as session:
            tasks = []
            for entry in metadata:
                identifier = entry['identifier']
                for file_type in self.file_types:
                    sbol_url = f'{self.base_url}/{identifier}/1/{file_type}'
                    tasks.append(self.download_file(session, sbol_url, identifier, file_type))

            await asyncio.gather(*tasks)
        
        self.save_sbol_documents()

    async def download_file(self, session, url, identifier, file_type):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    file_path = os.path.join(self.data_dir, file_type, f'{identifier}.{file_type}')
                    if not os.path.exists(os.path.dirname(file_path)):
                        os.makedirs(os.path.dirname(file_path))
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    self.sbol_documents.append({'identifier': identifier, 'file_type': file_type, 'url': url})
                    print(f'Successfully downloaded {url}')
                else:
                    print(f'Failed to download {url}')
        except Exception as e:
            print(f'Error downloading {url}: {e}')

    def save_sbol_documents(self):
        os.makedirs(self.data_dir, exist_ok=True)
        csv_file = os.path.join(self.data_dir, 'sbol_documents.csv')
        csv_columns = ['identifier', 'file_type', 'url']

        with open(csv_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for doc in self.sbol_documents:
                writer.writerow(doc)

        print(f'Saved SBOL document URLs to {csv_file}')

async def main():
    base_url = 'https://synbiohub.org/public/igem'
    collection_name = 'igem_collection'
    data_dir = 'data/syn_bio_hub'
    batch_size = 10
    max_items = 30  # Set this to None to scrape all items
    file_types = ["sbol", "gb", "fasta", "gff"]  # Specify the file types to download

    # Scrape metadata
    metadata_scraper = SynBioHubMetadataScraper(base_url, collection_name, data_dir, batch_size, max_items)
    await metadata_scraper.scrape()
    metadata_file_path = metadata_scraper.get_metadata_file_path()

    # Scrape SBOL documents based on metadata
    sbol_scraper = SynBioHubSBOLScraper(base_url, metadata_file_path, data_dir, file_types)
    await sbol_scraper.scrape()

# Run the main function
# asyncio.get_event_loop().run_until_complete(main())
