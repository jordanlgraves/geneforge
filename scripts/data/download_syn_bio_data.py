import asyncio
from pyppeteer import launch
import csv

async def main():
    # Launch the browser
    browser = await launch(headless=True)
    page = await browser.newPage()

    # Navigate to the SynBioHub collection page
    await page.goto('https://synbiohub.org/public/igem/igem_collection/1', {'waitUntil': 'networkidle2'})
    print("Page loaded")

    all_parts = []

    while True:
        # Wait for the table to load and ensure it has rows
        try:
            await page.waitFor(10000)
            await page.waitForSelector('table')
            await page.waitForFunction('document.querySelectorAll("table tbody tr").length > 0')
        except:
            print("Table not loaded or no content available")
            break
        
        print("Table loaded and content available")

        # Extract the HTML of the table rows for debugging
        table_html = await page.evaluate('''
            () => {
                const rows = document.querySelectorAll('table tbody tr');
                return Array.from(rows).map(row => row.innerHTML);
            }
        ''')
        print(f"Table rows HTML: {table_html}")

        # Extract data from the correct table
        parts = await page.evaluate('''
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

        all_parts.extend(parts)

        # Debugging: List all paginate buttons and their classes
        paginate_buttons = await page.evaluate('''
            () => {
                const buttons = document.querySelectorAll('a.paginate_button');
                return Array.from(buttons).map(button => ({
                    text: button.innerText,
                    classes: button.className
                }));
            }
        ''')
        print(f"Paginate buttons: {paginate_buttons}")

        # Check if there is a next page button and click it
        next_button = await page.querySelector('#DataTables_Table_0_next a')
        next_button_disabled = await page.evaluate('''
            () => document.querySelector('#DataTables_Table_0_next').classList.contains('disabled')
        ''')
        if next_button and not next_button_disabled:
            await next_button.click()
            print("Clicked next button")

            # # Wait for the table to reload with new content
            # await page.waitForSelector('table')
            # await page.waitForFunction('document.querySelectorAll("table tbody tr").length > 0')
            print("Navigated to next page")
        else:
            break


    # Close the browser
    await browser.close()

    # Save the data to a CSV file
    csv_file = 'igem_parts.csv'
    csv_columns = ['name', 'identifier', 'type', 'description']

    with open(csv_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for part in all_parts:
            writer.writerow(part)

    print(f'Saved {len(all_parts)} parts to {csv_file}')

# Run the main function
asyncio.get_event_loop().run_until_complete(main())