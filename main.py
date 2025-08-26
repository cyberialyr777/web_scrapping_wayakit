import pandas as pd
import time
import csv
import config
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from services.ai_service import RelevanceAgent
from scrapers.amazon_scraper import AmazonScraper
from scrapers.mumzworld_scraper import MumzworldScraper
from scrapers.saco_scraper import SacoScraper

def main():
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-notifications')
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument(f"user-agent={config.USER_AGENT}")
    options.add_argument('--log-level=3')

    try:
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Error: {e}")
        return

    try:
        df_instructions = pd.read_csv(config.INSTRUCTIONS_FILE)
        df_instructions = df_instructions.dropna(subset=['Type of product', 'Sub industry'])
    except FileNotFoundError:
        print(f"'{config.INSTRUCTIONS_FILE}' not found.")
        driver.quit()
        return

    ai_agent = RelevanceAgent()
    scrapers = {
        'amazon': AmazonScraper(driver, relevance_agent=ai_agent),
        'mumzworld': MumzworldScraper(driver, relevance_agent=ai_agent),
        'saco': SacoScraper(driver)
    }
    
    all_found_products = []

    for index, row in df_instructions.iterrows():
        industry = row['Industry']
        sub_industry = row['Sub industry']
        original_type_of_product = str(row['Type of product']).lower()
        generic_type_of_product = str(row['Generic product type'])
        search_modifier = str(row['Search Modifiers'])
        
        try:
            base_keyword = original_type_of_product.split('-', 1)[1].strip()
        except IndexError:
            base_keyword = original_type_of_product.strip()

        search_keyword = f"{base_keyword} {search_modifier}" if search_modifier and not pd.isna(row.get('Search Modifiers')) else base_keyword
        
        search_mode = 'units' if any(keyword in original_type_of_product for keyword in ['wipes', 'rags', 'microfiber', 'brush']) else 'volume'

        print(f"\n>> Searching '{search_keyword}' for '{sub_industry}' (Mode: {search_mode})")

        sites_to_scrape = config.TARGET_MAP.get(sub_industry, []).copy()
        
        if base_keyword in config.MUMZWORLD_EXCLUSIONS and 'mumzworld' in sites_to_scrape:
            print(f"   -> Excluding 'mumzworld' for '{base_keyword}' according to rules.")
            sites_to_scrape.remove('mumzworld')

        for site_name in sites_to_scrape:
            scraper = scrapers.get(site_name)
            if scraper:
                found_products = scraper.scrape(search_keyword, search_mode)
                
                for product in found_products:
                    row_data = {
                        'date': time.strftime("%Y-%m-%d"),
                        'industry': industry,
                        'subindustry': sub_industry,
                        'type_of_product': original_type_of_product,
                        'generic_product_type': generic_type_of_product,
                        'product': product.get('Product'),
                        'price_sar': product.get('Price_SAR'),
                        'company': product.get('Company'),
                        'source': site_name,
                        'url': product.get('URL'),
                        'unit_of_measurement': product.get('Unit of measurement'),
                        'total_quantity': product.get('Total quantity')
                    }
                    all_found_products.append(row_data)
                    print(f"    -> SAVED: {product.get('Product', 'N/A')[:60]}... (Source: {site_name})")
            else:
                print(f"   -> Warning: No scraper found for site '{site_name}'.")

    if all_found_products:
        print(f"\n--- 5. SAVING {len(all_found_products)} FOUND PRODUCTS ---")
        try:
            with open(config.OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=config.CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(all_found_products)
            print(f"  -> Success! Data saved to '{config.OUTPUT_CSV_FILE}'.")
        except IOError as e:
            print(f"  -> Error writing to CSV file: {e}")
    else:
        print("\n--- 5. No products found to save. ---")

    print("\n6. Closing the browser.")
    driver.quit()
    print("\n--- PROCESS COMPLETED ---")

if __name__ == "__main__":
    main()