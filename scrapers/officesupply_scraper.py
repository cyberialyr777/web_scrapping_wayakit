import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from utils import parse_volume_with_multiplier, parse_count_string

class OfficeSupplyScraper:
    def __init__(self, driver, relevance_agent):
        self.driver = driver
        self.relevance_agent = relevance_agent
        self.base_url = "https://officesupply.sa/en/"
        self.products_to_find_limit = 2

    def _log(self, msg):
        """Función para registrar mensajes en la consola."""
        print(msg)

    def _extract_product_details(self, product_url, search_mode):
        """
        Extrae los detalles de la página de un producto individual.
        """
        self._log(f"        -> Extrayendo detalles de: {product_url}")
        details = {
            'Product': 'Not found', 'Price_SAR': '0.00', 'Company': 'Brand not found',
            'URL': product_url, 'Unit of measurement': 'units', 'Total quantity': 0
        }

        try:
            self.driver.get(product_url)
            
            self._log("        -> Esperando a que cargue el precio del producto...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.ty-price-num"))
            )
            self._log("        -> ¡Precio encontrado! Extrayendo datos.")
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            name_tag = soup.select_one("h1 bdi")
            if name_tag:
                product_title = name_tag.get_text(strip=True)
                details['Product'] = product_title
                
                # --- INICIO DEL CAMBIO ---
                # Log para depurar el título extraído
                self._log(f"        -> TÍTULO EXTRAÍDO: '{product_title}'")
                # --- FIN DEL CAMBIO ---

            price_tag = soup.select_one("span.ty-price-num")
            if price_tag:
                price_text = price_tag.get_text(strip=True).replace('', '').strip()
                details['Price_SAR'] = re.sub(r'\s+', '.', price_text)

            if details['Product'] != 'Not found':
                parsed_data = None
                if search_mode == 'units':
                    parsed_data = parse_count_string(details['Product'])
                else: 
                    parsed_data = parse_volume_with_multiplier(details['Product'])

                if parsed_data:
                    details['Total quantity'] = parsed_data['quantity']
                    details['Unit of measurement'] = parsed_data['unit']
                    self._log(f"        -> Cantidad extraída: {details['Total quantity']} {details['Unit of measurement']}")
                else:
                    # Log para indicar que el parseo falló
                    self._log("        -> ALERTA: La función de parseo no encontró una cantidad válida.")


        except TimeoutException:
            self._log("      ! Error: El precio no se encontró en la página después de 15 segundos.")
        except Exception as e:
            self._log(f"      ! Error inesperado extrayendo detalles: {e}")
        
        return details


    def scrape(self, keyword, search_mode):
        self._log(f"  [OfficeSupply Scraper] Buscando: '{keyword}' (Modo: {search_mode})")
        
        search_keyword = quote(keyword)
        search_url = (
            f"{self.base_url}?match=all&subcats=Y&pcode_from_q=Y&pshort=Y&pfull=Y"
            f"&pname=Y&pkeywords=Y&search_performed=Y&dispatch=products.search&q={search_keyword}"
        )
        
        all_found_products = []
        
        try:
            self.driver.get(search_url)

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.ut2-gl__body"))
            )
            
            self._log("    > Página de resultados de búsqueda cargada.")
            
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            product_containers = soup.select("div.ut2-gl__body")
            self._log(f"    > Encontrados {len(product_containers)} productos en la página.")

            product_urls = []
            for container in product_containers:
                link_tag = container.select_one("a.product_icon_lnk")
                if link_tag and link_tag.has_attr('href'):
                    product_urls.append(urljoin(self.base_url, link_tag['href']))

            self._log(f"    > Se encontraron {len(product_urls)} URLs de productos para procesar.")

            for product_url in product_urls:
                if len(all_found_products) >= self.products_to_find_limit:
                    self._log(f"    > Límite de {self.products_to_find_limit} productos alcanzado.")
                    break
                
                product_details = self._extract_product_details(product_url, search_mode)
                
                if product_details.get('Total quantity', 0) > 0:
                    is_relevant = self.relevance_agent.is_relevant(product_details.get('Product'), keyword)
                    if is_relevant:
                        all_found_products.append(product_details)
                        self._log(f"      -> PRODUCTO VÁLIDO GUARDADO: {product_details['Product'][:60]}...")
                    else:
                        self._log(f"      -> DESCARTADO (No relevante por IA): {product_details['Product'][:60]}...")
                else:
                    self._log(f"      -> DESCARTADO (Sin cantidad válida): {product_details.get('Product', 'N/A')[:60]}...")

        except TimeoutException:
            self._log("    > No se encontraron productos o la página tardó demasiado en cargar.")
        except Exception as e:
            self._log(f"    ! Ocurrió un error inesperado durante la búsqueda en OfficeSupply: {e}")

        return all_found_products