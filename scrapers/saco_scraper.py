import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException, InvalidSessionIdException, NoSuchElementException
from bs4 import BeautifulSoup
from urllib.parse import quote
from utils import parse_volume_string, parse_count_string, parse_saco_count_string

class SacoScraper:
    def __init__(self, driver, relevance_agent):
        self.driver = driver
        self.relevance_agent = relevance_agent
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
        self._log(f"        -> Extracting details from: {product_url}")
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        details = {
            'Product': 'Not found', 'Price_SAR': '0.00', 'Company': 'Brand not found',
            'URL': product_url, 'Unit of measurement': 'units', 'Total quantity': 0
        }

        title_tag = soup.select_one("h1.product-title")
        product_name = title_tag.get_text(strip=True) if title_tag else "Not found"
        details['Product'] = product_name

        price_tag = soup.select_one("span.discount-price")
        if price_tag:
            price_text = price_tag.get_text(separator='.', strip=True)
            details['Price_SAR'] = price_text

        additional_info_items = soup.select("ul.details-box li")
        for item in additional_info_items:
            label_tag = item.find("label")
            if label_tag and "Brand:" in label_tag.get_text():
                brand_span = label_tag.find_next_sibling("span")
                if brand_span:
                    details['Company'] = brand_span.get_text(strip=True)
                    break

        if product_name != "Not found":
            if search_mode == 'units':
                parsed_data = parse_saco_count_string(product_name)
                if not parsed_data:
                    parsed_data = parse_count_string(product_name)
            else:
                parsed_data = parse_volume_string(product_name)

            if parsed_data:
                details['Total quantity'] = parsed_data['quantity']
                details['Unit of measurement'] = parsed_data['unit']
                self._log(f"        -> Extracted amount: {details['Total quantity']} {details['Unit of measurement']}")

        return details

    def scrape(self, keyword, search_mode):
        self._log(f"  [Saco Scraper] Searching: '{keyword}'")
        search_keyword = quote(keyword)
        search_url = f"{self.base_url}search/{search_keyword}"
        
        all_found_products = []
        page_num = 1
        products_to_find_limit = 2

        self.driver.get(search_url)
        self._handle_overlays()

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-inner-container"))
            )
        except TimeoutException:
            self._log("    > No product containers found on the initial page. Skipping keyword.")
            return []

        while len(all_found_products) < products_to_find_limit:
            self._log(f"--- Analyzing Page {page_num} ---")
            
            search_page_url = self.driver.current_url
            time.sleep(5)

            
            product_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.product-inner-container")
            num_containers = len(product_containers)

            if num_containers == 0:
                self._log("    ! No products containers found on this page.")
                break

            self._log(f"    > Found {num_containers} product containers on this page.")

            
            for i in range(num_containers):
                if len(all_found_products) >= products_to_find_limit:
                    break
                try:
                    
                    current_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.product-inner-container")
                    if i >= len(current_containers):
                        break
                    
                    container = current_containers[i]

                    
                    try:
                        product_link = container.find_element(By.CSS_SELECTOR, "p.product-name a")
                        if not product_link.text.strip():
                            self._log(f"      -> Skipping empty product container #{i+1}.")
                            continue 
                    except NoSuchElementException:
                        self._log(f"      -> Skipping container #{i+1} (no product link found inside).")
                        continue 

                    self._log(f"      -> Processing product {i+1}/{num_containers}...")
                    
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", product_link)
                    time.sleep(1)
                    product_link.click()

                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-title"))
                    )
                    
                    product_url = self.driver.current_url
                    product_details = self._extract_product_details(product_url, search_mode)
                    
                    if product_details and product_details.get('Total quantity', 0) > 0:
                        is_relevant = self.relevance_agent.is_relevant(product_details.get('Product'), keyword)
                        if is_relevant:
                            all_found_products.append(product_details)
                            self._log(f"      -> AI VALIDATED. Product saved: {product_details['Product'][:60]}...")
                        else:
                            self._log(f"      -> DISCARDED BY AI (Not relevant): {product_details['Product'][:60]}...")
                    else:
                        self._log(f"      -> DISCARDED (no quantity): {product_details.get('Product', 'N/A')[:60]}...")

                    self.driver.get(search_page_url)
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-inner-container"))
                    )
                    time.sleep(2)

                except (TimeoutException, StaleElementReferenceException, ElementClickInterceptedException) as e:
                    self._log(f"      -> WARNING: Could not process product {i+1}. Skipping. Reason: {type(e).__name__}")
                    self.driver.get(search_page_url)
                    WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-inner-container")))
                    continue
                except InvalidSessionIdException:
                    self._log(f"      -> FATAL ERROR: Browser session lost. Aborting scrape for '{keyword}'.")
                    return all_found_products
            
            if len(all_found_products) >= products_to_find_limit:
                self._log(f"    > Target of {products_to_find_limit} products reached.")
                break
            
            try:
                current_page_url = self.driver.current_url
                next_page_button = self.driver.find_element(By.CSS_SELECTOR, "a.next")
                self._log("    > Next page button found. Attempting to navigate...")
                
                self.driver.execute_script("arguments[0].click();", next_page_button)
                time.sleep(3)

                if self.driver.current_url == current_page_url:
                    self._log("    > URL did not change. Reached the last page.")
                    break
                else:
                    page_num += 1
                    self._log("    > Successfully navigated to the next page.")

            except:
                self._log("    > No more pages found. Ending pagination.")
                break

        self._log(f"\n  [Saco Scraper] Finished scraping. Found data for {len(all_found_products)} products.")
        return all_found_products