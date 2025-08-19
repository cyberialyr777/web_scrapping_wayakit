import pandas as pd
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from scrapers.amazon_scraper import scrape_amazon

service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
options.add_argument('--log-level=3') 
driver = webdriver.Chrome(service=service, options=options)

TARGET_MAP = { 'Home': ['amazon'], 'Automotive': ['amazon'], 'Pets': ['amazon'], }
SCRAPER_FUNCTIONS = { 'amazon': scrape_amazon, }

try:
    df_instructions = pd.read_csv('analysis.csv')
    df_instructions = df_instructions.dropna(subset=['Type of product', 'Sub industry'])
except FileNotFoundError:
    print("Error: El archivo CSV de instrucciones 'analysis.csv' no fue encontrado.")
    driver.quit()
    exit()

output_csv_file = 'resultados_finales_clasificados_v6.csv'
csv_columns = ['date', 'industry', 'subindustry', 'type_of_product', 'generic_product_type', 
               'product', 'price_sar', 'company', 'source', 'url',
               'unit_of_measurement', 'total_quantity']
with open(output_csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()

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

    if search_modifier and not pd.isna(row.get('Search Modifiers')):
        search_keyword = f"{base_keyword} {search_modifier}"
    else:
        search_keyword = base_keyword

    search_mode = 'volume'
    units_keywords = ['wipes', 'rags', 'microfiber', 'brush']
    if any(keyword in original_type_of_product for keyword in units_keywords):
        search_mode = 'units'

    print(f"\n>> Searching '{search_keyword}' for '{sub_industry}' (Mode: {search_mode})")
    sites_to_scrape = TARGET_MAP.get(sub_industry, [])
    
    for site_name in sites_to_scrape:
        if site_name in SCRAPER_FUNCTIONS:
            scraper_function = SCRAPER_FUNCTIONS[site_name]
            found_products = scraper_function(search_keyword, driver, search_mode)
            
            for product in found_products:
                row_data = {
                    'date': time.strftime("%Y-%m-%d"),
                    'industry': industry, 'subindustry': sub_industry,
                    'type_of_product': original_type_of_product,
                    'generic_product_type': generic_type_of_product,
                    'product': product.get('Product'), 'price_sar': product.get('Price_SAR'),
                    'company': product.get('Company'), 'source': site_name, 'url': product.get('URL'),
                    'unit_of_measurement': product.get('Unit of measurement'),
                    'total_quantity': product.get('Total quantity')
                }
                with open(output_csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=csv_columns)
                    writer.writerow(row_data)
                print(f"Saved: {product.get('Product')[:60]}...")
        else:
            print(f"No web scraper for that site")
driver.quit()