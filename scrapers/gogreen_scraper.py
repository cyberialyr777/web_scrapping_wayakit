import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from utils import parse_volume_with_multiplier, parse_count_string

class GoGreenScraper:
    def __init__(self, driver, relevance_agent):
        self.driver = driver
        self.relevance_agent = relevance_agent
        self.base_url = "https://gogreen.com.sa/"
        self.products_to_find_limit = 2

    def _log(self, msg):
        print(msg)

    def _safe_get_text(self, soup_element):
        return soup_element.get_text(strip=True) if soup_element else None

    def _set_language_to_english(self):
        try:
            html_tag = self.driver.find_element(By.TAG_NAME, "html")
            if html_tag.get_attribute("lang") == "en":
                return True
            self._log("    -> Cambiando idioma a inglés...")
            lang_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.js-language-shipping"))
            )
            lang_button.click()
            language_select_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "floatingSelectLanguage"))
            )
            select = Select(language_select_element)
            select.select_by_value("en")
            save_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.js-button-save"))
            )
            save_button.click()
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//html[@lang='en']"))
            )
            self._log("    -> ¡ÉXITO! Idioma verificado correctamente.")
            return True
        except Exception as e:
            self._log(f"    -> ERROR: No se pudo establecer el idioma a inglés. Error: {e}")
            return False

    def _extract_product_details(self, product_url, search_mode):
        details = {
            'Product': 'Not found', 'Price_SAR': '0.00', 'Company': 'GoGreen',
            'URL': product_url, 'Unit of measurement': 'units', 'Total quantity': 0
        }
        try:
            self.driver.get(product_url)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.h5")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            name_tag = soup.select_one("h1.h5")
            product_name = self._safe_get_text(name_tag)
            details['Product'] = product_name

            price_tag = soup.select_one("span.js-product-price")
            if price_tag:
                price_text = re.search(r'([\d,]+\.\d{2})', price_tag.get_text())
                if price_text:
                    details['Price_SAR'] = price_text.group(1).replace(',', '')

            if product_name:
                parsed_data = None
                if search_mode == 'units':
                    parsed_data = parse_count_string(product_name)
                else: 
                    parsed_data = parse_volume_with_multiplier(product_name)

                if parsed_data:
                    details['Total quantity'] = parsed_data['quantity']
                    details['Unit of measurement'] = parsed_data['unit']
                    self._log(f"        -> Cantidad extraída: {details['Total quantity']} {details['Unit of measurement']}")

        except Exception as e:
            self._log(f"      ! Error extrayendo detalles de {product_url}: {e}")
        
        return details

    def scrape(self, keyword, search_mode):
        self._log(f"  [GoGreen Scraper] Buscando: '{keyword}' (Modo: {search_mode})")
        all_found_products = []
        try:
            self.driver.get(self.base_url)
            if not self._set_language_to_english():
                return []
            
            search_url = urljoin(self.base_url, f"products?search={quote(keyword)}")
            self.driver.get(search_url)

            WebDriverWait(self.driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card.card-product")))
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            product_containers = soup.select("div.card.card-product")
            self._log(f"    -> Encontrados {len(product_containers)} productos en la página de resultados.")

            for container in product_containers:
                if len(all_found_products) >= self.products_to_find_limit:
                    break

                link_tag = container.select_one("a.css-thumbnail")
                if not link_tag or not link_tag.has_attr('href'):
                    continue
                
                product_url = urljoin(self.base_url, link_tag['href'])
                self._log(f"      -> Procesando: {product_url[:80]}...")
                
                product_details = self._extract_product_details(product_url, search_mode)
                
                if product_details.get('Total quantity', 0) > 0:
                    if self.relevance_agent.is_relevant(product_details.get('Product'), keyword):
                        all_found_products.append(product_details)
                        self._log(f"      -> PRODUCTO VÁLIDO GUARDADO: {product_details['Product'][:60]}...")
                    else:
                        self._log(f"      -> DESCARTADO (No relevante por IA): {product_details['Product'][:60]}...")
                else:
                    self._log(f"      -> DESCARTADO (Sin cantidad válida): {product_details['Product'][:60]}...")
            
        except TimeoutException:
            self._log("    -> No se encontraron productos o la página tardó demasiado en cargar.")
        except Exception as e:
            self._log(f"    ! Ocurrió un error inesperado en GoGreen scraper: {e}")

        return all_found_products