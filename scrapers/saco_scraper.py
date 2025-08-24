import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from bs4 import BeautifulSoup
from urllib.parse import quote

class SacoScraper:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://www.saco.sa/en/"

    def _log(self, msg):
        print(msg)

    # MODIFICADO: Función para manejar el banner de cookies
    def _handle_overlays(self):
        try:
            # Esperamos un máximo de 7 segundos por el botón "Accept" de las cookies
            cookie_accept_button = WebDriverWait(self.driver, 7).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            self._log("    > Cookie banner detected. Clicking 'Accept'.")
            cookie_accept_button.click()
            time.sleep(2) # Pausa para que el banner desaparezca
        except TimeoutException:
            self._log("    > No cookie banner detected. Continuing.")
            pass

    def scrape(self, keyword, search_mode):
        self._log(f"  [Saco Scraper] Searching: '{keyword}'")
        search_keyword = quote(keyword)
        search_url = f"{self.base_url}search/{search_keyword}"
        
        all_product_urls = []
        page_num = 1
        current_search_page_url = search_url # Guardamos la URL de búsqueda

        while True:
            if page_num == 1:
                self._log(f"    > Navigating to: {search_url}")
                self.driver.get(search_url)
            
            self._handle_overlays()

            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.product-inner-container"))
                )
                self._log(f"    > Page {page_num} loaded. Analyzing products...")
                time.sleep(3)

                product_links_selectors = "p.product-name a"
                num_products = len(self.driver.find_elements(By.CSS_SELECTOR, product_links_selectors))
                if num_products == 0:
                    self._log("    ! No products found on this page.")
                    break

                for i in range(num_products):
                    # MODIFICADO: Guardamos la URL de la página de resultados antes de hacer clic
                    current_search_page_url = self.driver.current_url
                    try:
                        product_link = self.driver.find_elements(By.CSS_SELECTOR, product_links_selectors)[i]
                        self._log(f"      -> Processing product {i+1}/{num_products}...")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", product_link)
                        time.sleep(1)
                        product_link.click()

                        WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.name")))
                        
                        product_url = self.driver.current_url
                        all_product_urls.append(product_url)
                        self._log(f"      -> SUCCESS: Found URL: {product_url}")

                        self.driver.get(current_search_page_url) # MODIFICADO: Volvemos a la URL de búsqueda

                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.product-inner-container"))
                        )
                        time.sleep(2)

                    except (StaleElementReferenceException, TimeoutException, ElementClickInterceptedException) as e:
                        self._log(f"      -> WARNING: Could not process product {i+1}. Skipping. Reason: {type(e).__name__}")
                        # MODIFICADO: Volvemos a la página de búsqueda si algo falla
                        self.driver.get(current_search_page_url)
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.product-inner-container"))
                        )
                
                next_page_button = self.driver.find_elements(By.CSS_SELECTOR, "li.pagination-next:not(.disabled) a")

                if next_page_button:
                    self._log("    > Next page found. Clicking...")
                    page_num += 1
                    self.driver.execute_script("arguments[0].click();", next_page_button[0])
                    time.sleep(3)
                else:
                    self._log("    > No more pages found. Ending pagination.")
                    break

            except TimeoutException:
                self._log("    ! Warning: No product containers found or page timed out.")
                break
            except Exception as e:
                self._log(f"    ! An unexpected error occurred: {e}")
                break

        self._log(f"\n  [Saco Scraper] Found a total of {len(all_product_urls)} product URLs.")
        print(all_product_urls)
        
        return []

