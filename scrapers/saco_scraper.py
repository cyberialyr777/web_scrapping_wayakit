import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from bs4 import BeautifulSoup
from urllib.parse import quote
# Asegúrate de que este import funcione según la estructura de tu proyecto
from utils import parse_volume_string, parse_count_string

class SacoScraper:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://www.saco.sa/en/"

    def _log(self, msg):
        print(msg)

    def _handle_overlays(self):
        try:
            cookie_accept_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            self._log("    > Cookie banner detected. Clicking 'Accept'.")
            self.driver.execute_script("arguments[0].click();", cookie_accept_button)
            time.sleep(2)
        except TimeoutException:
            self._log("    > No cookie banner detected. Continuing.")
            pass

    def _extract_product_details(self, product_url, search_mode):
        """
        Extrae los detalles (nombre, precio, marca, cantidad) de la página de un producto.
        """
        self._log(f"        -> Extracting details from: {product_url}")
        
        # Espera a que el título del producto sea visible para asegurar que la página cargó
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-title"))
        )
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        details = {
            'Product': None, 'Price_SAR': '0.00', 'Company': None,
            'URL': product_url, 'Unit of measurement': 'units', 'Total quantity': 0
        }

        # 1. Extraer nombre del producto
        title_tag = soup.select_one("h1.product-title")
        product_name = title_tag.get_text(strip=True) if title_tag else "Not found"
        details['Product'] = product_name

        # 2. Extraer precio (manejando el formato con <sup>)
        price_tag = soup.select_one("span.discount-price")
        if price_tag:
            # .get_text() junta el texto principal y el del <sup>
            price_text = price_tag.get_text(separator='.', strip=True)
            details['Price_SAR'] = price_text

        # 3. Extraer marca
        # Buscamos todas las etiquetas 'li' en la caja de detalles
        additional_info_items = soup.select("ul.details-box li")
        for item in additional_info_items:
            label_tag = item.find("label")
            if label_tag and "Brand:" in label_tag.get_text():
                # Si la etiqueta es "Brand:", obtenemos el texto del siguiente <span>
                brand_span = label_tag.find_next_sibling("span")
                if brand_span:
                    details['Company'] = brand_span.get_text(strip=True)
                    break # Salimos del bucle una vez encontrada

        # 4. Extraer cantidad usando las funciones de utils.py
        if product_name != "Not found":
            parser_func = parse_count_string if search_mode == 'units' else parse_volume_string
            parsed_data = parser_func(product_name)
            if parsed_data:
                details['Total quantity'] = parsed_data['quantity']
                details['Unit of measurement'] = parsed_data['unit']
                self._log(f"        -> Extracted amount: {details['Total quantity']} {details['Unit of measurement']}")

        return details

    def scrape(self, keyword, search_mode):
        self._log(f"  [Saco Scraper] Searching: '{keyword}'")
        search_keyword = quote(keyword)
        search_url = f"{self.base_url}search/{search_keyword}"
        
        all_found_products = [] # Aquí guardaremos los datos de los productos
        page_num = 1
        
        # Límite para evitar scraping infinito durante las pruebas
        products_to_find_limit = 20

        self.driver.get(search_url)

        while len(all_found_products) < products_to_find_limit:
            self._log(f"--- Analyzing Page {page_num} ---")
            self._handle_overlays()

            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-inner-container"))
                )
                self._log(f"    > Page {page_num} loaded. Analyzing products...")
                time.sleep(3)

                product_links_selector = "p.product-name a"
                num_products = len(self.driver.find_elements(By.CSS_SELECTOR, product_links_selector))
                if num_products == 0:
                    self._log("    ! No products found on this page.")
                    break

                self._log(f"    > Found {num_products} products on this page.")

                for i in range(num_products):
                    if len(all_found_products) >= products_to_find_limit:
                        break # Salimos si ya alcanzamos el límite
                    try:
                        product_links = self.driver.find_elements(By.CSS_SELECTOR, product_links_selector)
                        if i >= len(product_links):
                            break
                        
                        product_link = product_links[i]
                        
                        self._log(f"      -> Processing product {i+1}/{num_products}...")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", product_link)
                        time.sleep(1)
                        product_link.click()

                        # --- LLAMADA A LA FUNCIÓN DE EXTRACCIÓN ---
                        product_details = self._extract_product_details(self.driver.current_url, search_mode)
                        
                        # Guardamos el producto si la extracción fue exitosa
                        if product_details and product_details.get('Total quantity', 0) > 0:
                            all_found_products.append(product_details)
                            self._log(f"      -> SUCCESS: Product data saved: {product_details['Product'][:60]}...")
                        else:
                            self._log(f"      -> DISCARDED (no quantity): {product_details.get('Product', 'N/A')[:60]}...")

                        self.driver.back()
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-inner-container"))
                        )
                        time.sleep(2)

                    except Exception as e:
                        self._log(f"      -> WARNING: Could not process product {i+1}. Skipping. Reason: {type(e).__name__}")
                        self.driver.get(self.driver.current_url) # Recargar para estabilizar
                        WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-inner-container")))
                        continue
                
                if len(all_found_products) >= products_to_find_limit:
                    self._log(f"    > Target of {products_to_find_limit} products reached.")
                    break

                try:
                    next_page_button = self.driver.find_element(By.CSS_SELECTOR, "li.pagination-next:not(.disabled) a")
                    self._log("    > Next page found. Clicking...")
                    page_num += 1
                    self.driver.execute_script("arguments[0].click();", next_page_button)
                    time.sleep(3)
                except:
                    self._log("    > No more pages found. Ending pagination.")
                    break

            except Exception as e:
                self._log(f"    ! An unexpected error occurred: {e}")
                break

        self._log(f"\n  [Saco Scraper] Finished scraping. Found data for {len(all_found_products)} products.")
        
        return all_found_products