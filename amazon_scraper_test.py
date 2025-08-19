# import pandas as pd
# import time
# import csv
# import re
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# # ==============================================================================
# # 1. FUNCIONES DE PARSEO (EXTRACCIÓN DE DATOS)
# # ==============================================================================

# def parse_volume_string(text_string):
#     """
#     [VERSIÓN 2]
#     Busca volumen/peso (ml, L, g, kg, oz).
#     El orden de las comprobaciones ha sido corregido para evitar falsos positivos.
#     """
#     if not text_string:
#         return None
    
#     match = re.search(r'(\d+\.?\d*)\s*(ml|l|g|kg|liter|litre|liters|milliliters|grams|kilograms|oz|ounce|fluid\sounces?)\b', text_string, re.I)
#     if not match:
#         return None
        
#     quantity = float(match.group(1))
#     unit = match.group(2).lower().strip()
#     normalized_value = quantity
    
#     if 'milliliter' in unit or unit == 'ml':
#         unit = 'ml'
#     elif 'liter' in unit or unit == 'l':
#         normalized_value = quantity * 1000
#         unit = 'L'
#     elif 'gram' in unit or unit == 'g':
#         unit = 'g'
#     elif 'kilogram' in unit or unit == 'kg':
#         normalized_value = quantity * 1000
#         unit = 'kg'
#     elif 'oz' in unit or 'ounce' in unit:
#         normalized_value = quantity * 29.5735
#         unit = 'fl oz'

#     return {'quantity': quantity, 'unit': unit, 'normalized': normalized_value}

# def parse_count_string(text_string):
#     """
#     [NUEVA FUNCIÓN]
#     Busca un conteo de unidades/piezas (wipes, count, pack, etc.).
#     """
#     if not text_string:
#         return None

#     match = re.search(r'(\d+)(?:\s+\w+){0,2}\s*(wipes|count|sheets|sachets|pack|pcs|pieces|pc)\b|\b(wipes|count|sheets|sachets|pack|pcs|pieces|pc)(?:\s+\w+){0,2}\s*(\d+)', text_string, re.I)
#     if not match:
#         return None
#     if match.group(1) and match.group(2):
#         quantity = int(match.group(1))
#     elif match.group(3) and match.group(4):
#         quantity = int(match.group(4))
#     else:
#         return None
#     return {'quantity': quantity, 'unit': 'units', 'normalized': quantity}


# # ==============================================================================
# # 2. FUNCIÓN DE EXTRACCIÓN DE LA PÁGINA DEL PRODUCTO
# # ==============================================================================

# def extract_details_from_product_page(soup, search_mode='volume'):
#     """
#     [VERSIÓN 3 - HÍBRIDA]
#     Extrae detalles de la página, decidiendo si buscar volumen o conteo
#     basado en el search_mode.
#     """
#     details = {
#         'Product': 'No encontrado', 'Price_SAR': '0.00', 'Company': 'Company not found',
#         'Unit of measurement': 'units', 'Total quantity': 0, 'Validation_Status': 'Not Found'
#     }

#     title_tag = soup.find('span', id='productTitle')
#     if title_tag:
#         details['Product'] = title_tag.get_text(strip=True)
#     # Extraer la marca
#     brand_row = soup.find('tr', class_='po-brand')
#     if brand_row:
#         brand_span = brand_row.find('span', class_='po-break-word')
#         if brand_span:
#             details['Company'] = brand_span.get_text(strip=True)
#     # Extraer precio con decimales
#     price_whole = soup.find('span', class_='a-price-whole')
#     price_fraction = soup.find('span', class_='a-price-fraction')
#     if price_whole:
#         price_str = price_whole.get_text(strip=True).replace(',', '')
#         price_str = price_str.rstrip('.')
#         if price_fraction:
#             price_str += '.' + price_fraction.get_text(strip=True)
#         details['Price_SAR'] = price_str

#     raw_title = details.get('Product')
#     raw_volume, raw_item_volume, raw_weight = None, None, None

#     tech_spec_table = soup.find('table', id='productDetails_techSpec_section_1')
#     if tech_spec_table:
#         for row in tech_spec_table.find_all('tr'):
#             header = row.find('th')
#             if header:
#                 header_text = header.get_text(strip=True).lower()
#                 value_cell = row.find('td')
#                 if 'volume' in header_text:
#                     raw_volume = value_cell.get_text(strip=True) if value_cell else None
#                 elif 'weight' in header_text:
#                     raw_weight = value_cell.get_text(strip=True) if value_cell else None
    
#     item_volume_row = soup.find('tr', class_='po-item_volume')
#     if item_volume_row:
#         value_span = item_volume_row.find('span', class_='po-break-word')
#         raw_item_volume = value_span.get_text(strip=True) if value_span else None

#     print(f"     [Debug] Pistas Crudas -> Título: '{raw_title is not None}', title: {raw_title}, Vol: '{raw_volume}', ItemVol: '{raw_item_volume}', Peso: '{raw_weight}'")


#     p_title, p_volume, p_item_volume, p_weight = None, None, None, None

#     # --- LÓGICA HÍBRIDA: Decide qué parser usar ---
#     if search_mode == 'units':
#         print("     [Validator] Modo de búsqueda: Unidades/Conteo")
#         p_title = parse_count_string(raw_title)
#     else:
#         print("     [Validator] Modo de búsqueda: Volumen/Peso")
#         p_title = parse_volume_string(raw_title)
#         p_volume = parse_volume_string(raw_volume)
#         p_item_volume = parse_volume_string(raw_item_volume)
#         p_weight = parse_volume_string(raw_weight)

#     final_data = None
#     validation_status = 'Not Found'

#     # --- Nueva lógica: solo aceptar si hay al menos dos valores de volumen verificados ---
#     volume_fields = [p_title, p_volume, p_item_volume, p_weight]
#     volume_values = [v for v in volume_fields if v is not None]

#     # Si hay menos de 2 valores de volumen, descartar el producto
#     if search_mode != 'units' and len(volume_values) < 2:
#         print("     [Validator] ❌ Producto descartado: solo se encontró un valor de volumen.")
#         return details

#     # Verificación cruzada entre los valores
#     if search_mode != 'units':
#         # Buscar dos valores que sean aproximadamente iguales
#         for i in range(len(volume_fields)):
#             vi = volume_fields[i]
#             if vi is None:
#                 continue
#             for j in range(i+1, len(volume_fields)):
#                 vj = volume_fields[j]
#                 if vj is None:
#                     continue
#                 if abs(vi['normalized'] - vj['normalized']) < 1:
#                     final_data = vi
#                     validation_status = f"Confirmed by {['title','volume','item_volume','weight'][i].capitalize()} & {['title','volume','item_volume','weight'][j].capitalize()}"
#                     break
#             if final_data:
#                 break
#         if not final_data:
#             print("     [Validator] ❌ Producto descartado: los valores de volumen no coinciden.")
#             return details
#     else:
#         # Modo unidades: lógica original
#         if p_title:
#             final_data = p_title
#             validation_status = 'From Title'
#     # --- LÓGICA DE VALIDACIÓN BASADA EN MODOS ---

#     # --- ASIGNACIÓN FINAL DE DATOS --- (Esta parte no cambia)
#     if final_data:
#         details['Total quantity'] = final_data['quantity']
#         details['Unit of measurement'] = final_data['unit']
#         details['Validation_Status'] = validation_status
#         print(f"     [Validator] ✅ Decisión Final: {final_data['quantity']} {final_data['unit']} (Fuente: {validation_status})")
#     else:
#         print(f"     [Validator] ❌ No se encontró ningún dato válido para el modo '{search_mode}'.")

#     return details

#     # --- Lógica de Validación Flexible (Versión Mejorada) ---


# # ==============================================================================
# # 3. FUNCIÓN PRINCIPAL DEL SCRAPER DE AMAZON
# # ==============================================================================

# def scrape_amazon(keyword, driver, search_mode):
#     print(f"  [Trabajador de Amazon con Selenium] Buscando: '{keyword}'")
#     base_url = "https://www.amazon.sa"
#     found_products = []
#     products_to_find = 2
#     search_url = f"{base_url}/s?k={keyword.replace(' ', '+')}&language=en_AE"
    
#     try:
#         driver.get(search_url)
#         WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']")))
#         soup = BeautifulSoup(driver.page_source, 'html.parser')
#         product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})
        
#         if not product_containers:
#             print("    ! Advertencia: No se encontraron contenedores de productos.")
#             return []

#         for container in product_containers:
#             if len(found_products) >= products_to_find:
#                 print(f"    > Objetivo de {products_to_find} productos válidos alcanzado.")
#                 break

#             link_tag = container.find('a', class_='a-link-normal')
#             if not link_tag or 'spons' in link_tag.get('href', ''):
#                 continue
            
#             product_url = urljoin(base_url, link_tag['href'])
#             print(f"    > Visitando página de producto: {product_url[:70]}...")
            
#             driver.get(product_url)
            
#             try:
#                 WebDriverWait(driver, 10).until(EC.any_of(
#                     EC.presence_of_element_located((By.ID, "productDetails_techSpec_section_1")),
#                     EC.presence_of_element_located((By.ID, "detailBullets_feature_div")),
#                     EC.presence_of_element_located((By.CLASS_NAME, "po-item_volume")),
#                     EC.presence_of_element_located((By.ID, "centerCol"))
#                 ))
#             except Exception:
#                 print(f"    ! No se encontró una sección de detalles para {product_url[:70]}. Saltando.")
#                 continue
            
#             product_soup = BeautifulSoup(driver.page_source, 'html.parser')
#             product_details = extract_details_from_product_page(product_soup, search_mode)
            
#             if product_details.get('Total quantity', 0) > 0:
#                 product_details['URL'] = product_url
#                 found_products.append(product_details)
#                 print(f"    -> Producto VÁLIDO encontrado: {product_details.get('Product')[:50]}...")
#             else:
#                 print(f"    -> Producto DESCARTADO (sin datos válidos): {product_details.get('Product')[:50]}...")

#     except Exception as e:
#         print(f"    ! Ocurrió un error inesperado en el scraper de Selenium: {e}")

#     return found_products


# # ==============================================================================
# # 4. CONFIGURACIÓN Y EJECUCIÓN PRINCIPAL DEL SCRIPT
# # ==============================================================================

# print("Configurando el navegador de Selenium...")
# service = Service(ChromeDriverManager().install())
# options = webdriver.ChromeOptions()
# options.add_argument('--headless')
# options.add_argument('--disable-gpu')
# options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
# options.add_argument('--log-level=3') 
# driver = webdriver.Chrome(service=service, options=options)
# print("Navegador listo (ejecutándose en segundo plano).")

# TARGET_MAP = { 'Home': ['amazon'], 'Automotive': ['amazon'], 'Pets': ['amazon'], }
# SCRAPER_FUNCTIONS = { 'amazon': scrape_amazon, }

# try:
#     df_instructions = pd.read_csv('analysis.csv')
#     df_instructions = df_instructions.dropna(subset=['Type of product', 'Sub industry'])
# except FileNotFoundError:
#     print("Error: El archivo CSV de instrucciones 'analysis.csv' no fue encontrado.")
#     driver.quit()
#     exit()

# output_csv_file = 'resultados_finales_clasificados_v6.csv'
# csv_columns = ['Date', 'Industry', 'Sub industry', 'Type of product', 'Generic product type', 
#                'Product', 'Price_SAR', 'Company', 'Source', 'URL',
#                'Unit of measurement', 'Total quantity']
# with open(output_csv_file, 'w', newline='', encoding='utf-8') as f:
#     writer = csv.DictWriter(f, fieldnames=csv_columns)
#     writer.writeheader()

# print("\n--- INICIANDO PROCESO DE SCRAPING CON SELENIUM (Lógica Híbrida) ---")

# for index, row in df_instructions.iterrows():
#     industry = row['Industry']
#     sub_industry = row['Sub industry']
#     original_type_of_product = str(row['Type of product'])
#     generic_type_of_product = str(row['Generic product type'])
#     search_modifier = str(row['Search Modifiers'])
#     try:
#         base_keyword = original_type_of_product.split('-', 1)[1].strip()
#     except IndexError:
#         base_keyword = original_type_of_product.strip()

#     # --- LÓGICA MEJORADA PARA CONSTRUIR LA BÚSQUEDA ---
#     # Si hay un modificador, lo añadimos a la palabra clave base
#     if search_modifier and not pd.isna(row.get('Search Modifiers')):
#         search_keyword = f"{base_keyword} {search_modifier}"
#     else:
#         search_keyword = base_keyword

#     # --- LÓGICA DE DECISIÓN CORREGIDA ---
#     # Se basa en la columna 'Type of product' como solicitaste.
#     search_mode = 'volume'
#     type_lower = original_type_of_product.lower()
#     if 'wipes' in type_lower or 'rags' in type_lower or 'microfiber' in type_lower or 'brush' in type_lower:
#         search_mode = 'units'

#     # Si no coincide con ninguno, se queda como 'volume' por defecto.

#     print(f"\n>> Tarea: Buscar '{search_keyword}' para '{sub_industry}' (Modo: {search_mode})")
#     sites_to_scrape = TARGET_MAP.get(sub_industry, [])
    
#     for site_name in sites_to_scrape:
#         if site_name in SCRAPER_FUNCTIONS:
#             scraper_function = SCRAPER_FUNCTIONS[site_name]
#             found_products = scraper_function(search_keyword, driver, search_mode)
            
#             for product in found_products:
#                 row_data = {
#                     'Date': time.strftime("%Y-%m-%d"),
#                     'Industry': industry, 'Sub industry': sub_industry,
#                     'Type of product': original_type_of_product,
#                     'Generic product type': generic_type_of_product,
#                     'Product': product.get('Product'), 'Price_SAR': product.get('Price_SAR'),
#                     'Company': product.get('Company'), 'Source': site_name, 'URL': product.get('URL'),
#                     'Unit of measurement': product.get('Unit of measurement'),
#                     'Total quantity': product.get('Total quantity')
#                 }
#                 with open(output_csv_file, 'a', newline='', encoding='utf-8') as f:
#                     writer = csv.DictWriter(f, fieldnames=csv_columns)
#                     writer.writerow(row_data)
#                 print(f"    -> Guardado (Selenium): {product.get('Product')[:60]}...")
#         else:
#             print(f"  ! Advertencia: No tengo un trabajador para el sitio '{site_name}'")

# driver.quit()
# print("\n--- PROCESO COMPLETADO ---")