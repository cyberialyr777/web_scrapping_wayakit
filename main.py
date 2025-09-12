import pandas as pd
import time
import csv
import os  
import re
import config
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from services.ai_service import RelevanceAgent
from scrapers.amazon_scraper import AmazonScraper
from scrapers.mumzworld_scraper import MumzworldScraper
from scrapers.saco_scraper import SacoScraper
from scrapers.fine_scraper import FineScraper
from scrapers.gogreen_scraper import GoGreenScraper 
from scrapers.officesupply_scraper import OfficeSupplyScraper
from scrapers.aerosense_scraper import AeroSenseScraper

def main():
    try:
        df_instructions = pd.read_csv(config.INSTRUCTIONS_FILE)
        df_instructions = df_instructions.dropna(subset=['Type of product', 'Sub industry'])
    except FileNotFoundError:
        print(f"Error: El archivo de instrucciones '{config.INSTRUCTIONS_FILE}' no fue encontrado.")
        return

    write_header = not os.path.exists(config.OUTPUT_CSV_FILE)
    
    with open(config.OUTPUT_CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=config.CSV_COLUMNS)
        if write_header:
            writer.writeheader()

    for industry_to_scrape in config.TARGET_MAP.keys():
        print(f"\n=================================================")
        print(f"  INICIANDO PROCESO PARA LA SUBINDUSTRIA: '{industry_to_scrape}'")
        print(f"=================================================\n")

        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-notifications')
        # options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument(f"user-agent={config.USER_AGENT}")
        options.add_argument('--log-level=3')

        driver = None 
        try:
            driver = webdriver.Chrome(service=service, options=options)
            print("  -> Navegador iniciado correctamente para esta subindustria.\n")
        except Exception as e:
            print(f"  -> Error al iniciar el navegador para '{industry_to_scrape}': {e}")
            continue
        
        df_industry_instructions = df_instructions[df_instructions['Sub industry'] == industry_to_scrape].copy()

        if df_industry_instructions.empty:
            print(f"  -> No se encontraron productos para la subindustria '{industry_to_scrape}'. Saltando a la siguiente.")
            driver.quit()
            continue

        ai_agent = RelevanceAgent()
        scrapers = {
            'amazon': AmazonScraper(driver, relevance_agent=ai_agent),
            'mumzworld': MumzworldScraper(driver, relevance_agent=ai_agent),
            'saco': SacoScraper(driver, relevance_agent=ai_agent),
            'fine': FineScraper(driver, relevance_agent=ai_agent),
            'gogreen': GoGreenScraper(driver, relevance_agent=ai_agent),
            'officesupply': OfficeSupplyScraper(driver, relevance_agent=ai_agent),
            'aerosense': AeroSenseScraper(driver)
        }
        
        all_found_products = []

        for index, row in df_industry_instructions.iterrows():
            sub_industry = row['Sub industry']
            original_type_of_product = str(row['Type of product'])
            original_type_of_product_lower = original_type_of_product.lower() 
            generic_type_of_product = str(row['Generic product type'])
            
            try:
                base_keyword = original_type_of_product_lower.split('-', 1)[1].strip()
            except IndexError:
                base_keyword = original_type_of_product_lower.strip()

            search_modifiers_val = row.get('Search Modifiers')
            site_specific_keywords = {}
            general_modifiers = []

            if pd.notna(search_modifiers_val):
                search_modifiers_str = str(search_modifiers_val)
                modifiers = search_modifiers_str.split(';')
                for mod in modifiers:
                    mod = mod.strip()
                    if ':' in mod:
                        site, keyword = mod.split(':', 1)
                        site = site.strip()
                        keyword = keyword.strip()
                        if site not in site_specific_keywords:
                            site_specific_keywords[site] = []
                        site_specific_keywords[site].append(keyword)
                    elif mod:
                        general_modifiers.append(mod)
            
            general_modifiers_text = " ".join(general_modifiers)
            search_keyword = f"{base_keyword} {general_modifiers_text}".strip()
            
            search_mode = 'units' if any(keyword in original_type_of_product_lower for keyword in ['wipes', 'rags', 'microfiber', 'brush']) else 'volume'

            print(f">> Buscando '{base_keyword}' para '{sub_industry}' (Modo: {search_mode})")
            for site, kword in site_specific_keywords.items():
                print(f"   -> {site.capitalize()} usará el término específico: '{kword}'")

            sites_to_scrape = config.TARGET_MAP.get(sub_industry, []).copy()
            
            if base_keyword in config.MUMZWORLD_EXCLUSIONS and 'mumzworld' in sites_to_scrape:
                sites_to_scrape.remove('mumzworld')
            
            if base_keyword in config.SACO_EXCLUSIONS and 'saco' in sites_to_scrape:
                sites_to_scrape.remove('saco')

            for site_name in sites_to_scrape:
                scraper = scrapers.get(site_name)
                if scraper:
                    keywords_to_use = site_specific_keywords.get(site_name, [search_keyword])

                    for keyword_to_use in keywords_to_use:
                        if site_name in ['fine', 'gogreen', 'officesupply', 'aerosense']:
                             if site_name not in site_specific_keywords:
                                print(f"   -> Saltando '{site_name}' porque no se proveyó una etiqueta específica (ej. '{site_name}:...')")
                                continue
                        
                        print(f"   -> Buscando en '{site_name}' con la palabra clave: '{keyword_to_use}'")
                        found_products = scraper.scrape(keyword_to_use, search_mode)
                        
                        for product in found_products:
                            row_data = {
                                'date': time.strftime("%Y-%m-%d"),
                                'industry': industry_to_scrape,
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
                            print(f"    -> GUARDADO: {product.get('Product', 'N/A')[:60]}... (Fuente: {site_name})")
                else:
                    print(f"   -> Advertencia: No se encontró scraper para el sitio '{site_name}'.")

        if all_found_products:
            print(f"\n--- Guardando {len(all_found_products)} productos encontrados para la industria '{industry_to_scrape}' ---")
            try:
                with open(config.OUTPUT_CSV_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=config.CSV_COLUMNS)
                    writer.writerows(all_found_products)
                print(f"  -> ¡Éxito! Datos añadidos a '{config.OUTPUT_CSV_FILE}'.")
            except IOError as e:
                print(f"  -> Error al escribir en el archivo CSV: {e}")
        else:
            print(f"\n--- No se encontraron productos para guardar en la industria '{industry_to_scrape}'. ---")

        if driver:
            driver.quit()
        print(f"\n  -> Navegador cerrado. Proceso para '{industry_to_scrape}' completado.")
        print("  -> Descansando 10 segundos antes de la siguiente industria...")
        time.sleep(10)

    print("\n\n--- PROCESO COMPLETO PARA TODAS LAS INDUSTRIAS ---")

if __name__ == "__main__":
    main()