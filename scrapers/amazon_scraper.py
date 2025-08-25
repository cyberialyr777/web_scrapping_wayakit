import time 
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from utils import parse_volume_string, parse_count_string

class AmazonScraper:
    def __init__(self, driver, relevance_agent):
        self.driver = driver
        self.relevance_agent = relevance_agent 
        self.base_url = "https://www.amazon.sa"

    def _log(self, msg):
        print(msg)

    def _safe_get_text(self, element):
        return element.get_text(strip=True) if element else None

    def _extract_from_table(self, soup, table_id, fields):
        results = {field: None for field in fields}
        table = soup.find('table', id=table_id)
        if table:
            for row in table.find_all('tr'):
                header = row.find('th')
                value_cell = row.find('td')
                if header and value_cell:
                    header_text = header.get_text(strip=True).lower()
                    for field in fields:
                        if field in header_text:
                            results[field] = value_cell.get_text(strip=True)
        return results

    def _extract_details_from_product_page(self, soup, search_mode='volume'):
        details = {
            'Product': 'Not found', 'Price_SAR': '0.00', 'Company': 'Company not found',
            'Unit of measurement': 'units', 'Total quantity': 0, 'Validation_Status': 'Not Found'
        }

        details['Product'] = self._safe_get_text(soup.find('span', id='productTitle')) or details['Product']
        brand_row = soup.find('tr', class_='po-brand')
        details['Company'] = self._safe_get_text(brand_row.find('span', class_='po-break-word')) if brand_row else details['Company']
        price_whole = self._safe_get_text(soup.find('span', class_='a-price-whole'))
        price_fraction = self._safe_get_text(soup.find('span', class_='a-price-fraction'))
        
        if price_whole:
            price_str = price_whole.replace(',', '').rstrip('.')
            details['Price_SAR'] = f"{price_str}.{price_fraction}" if price_fraction else price_str
        raw_title = details.get('Product')
        tech_fields = self._extract_from_table(soup, 'productDetails_techSpec_section_1', ['volume', 'weight'])
        item_volume_row = soup.find('tr', class_='po-item_volume')
        raw_item_volume = self._safe_get_text(item_volume_row.find('span', class_='po-break-word')) if item_volume_row else None
        self._log(f"     [Debug] -> Title: '{raw_title is not None}', Vol: '{tech_fields['volume']}', ItemVol: '{raw_item_volume}'")

        if search_mode == 'units':
            self._log("     [Validator] Search mode: units")
            p_title = parse_count_string(raw_title)
            if p_title:
                details['Total quantity'] = p_title['quantity']
                details['Unit of measurement'] = p_title['unit']
                details['Validation_Status'] = 'From Title'
                self._log(f"     [Validator] ✅ Final Decision: {p_title['quantity']} {p_title['unit']} (Source: From Title)")
        else:
            self._log("     [Validator] Search mode: volume")
            p_title = parse_volume_string(raw_title)
            p_volume = parse_volume_string(tech_fields['volume'])
            p_item_volume = parse_volume_string(raw_item_volume)
            volume_sources = {'title': p_title, 'volume': p_volume, 'item_volume': p_item_volume}
            valid_sources = {k: v for k, v in volume_sources.items() if v}

            if len(valid_sources) >= 2:
                source_keys = list(valid_sources.keys())
                final_data = None
                for i in range(len(source_keys)):
                    for j in range(i + 1, len(source_keys)):
                        key1, key2 = source_keys[i], source_keys[j]
                        val1, val2 = valid_sources[key1], valid_sources[key2]
                        if abs(val1['normalized'] - val2['normalized']) < 1:
                            final_data = val1
                            validation_status = f"Confirmed by {key1.capitalize()} & {key2.capitalize()}"
                            details['Total quantity'] = final_data['quantity']
                            details['Unit of measurement'] = final_data['unit']
                            details['Validation_Status'] = validation_status
                            self._log(f"     [Validator] Final Decision: {final_data['quantity']} {final_data['unit']} (Source: {validation_status})")
                            break
                    if final_data:
                        break
            if not details.get('Total quantity'):
                self._log("     [Validator] ❌ Not enough matching volume values found.")
        return details

    def scrape(self, keyword, search_mode):
        self._log(f"  [Amazon Scraper] Searching: '{keyword}' (Mode: {search_mode})")
        found_products = []
        products_to_find = 40
        search_url = f"{self.base_url}/s?k={keyword.replace(' ', '+')}&language=en_AE"

        try:
            self.driver.get(search_url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})

            if not product_containers:
                self._log("    ! Warning: No product containers found.")
                return []

            for container in product_containers:
                if len(found_products) >= products_to_find:
                    self._log(f"    > Target of {products_to_find} valid products reached.")
                    break

                link_tag = container.find('a', class_='a-link-normal')
                if not link_tag or 'spons' in link_tag.get('href', ''):
                    continue

                product_url = urljoin(self.base_url, link_tag['href'])
                self._log(f"    > Visiting product page: {product_url[:120]}...")
                self.driver.get(product_url)
                
                try:
                    WebDriverWait(self.driver, 10).until(EC.any_of(
                        EC.presence_of_element_located((By.ID, "productDetails_techSpec_section_1")),
                        EC.presence_of_element_located((By.ID, "detailBullets_feature_div")),
                        EC.presence_of_element_located((By.CLASS_NAME, "po-item_volume"))
                    ))
                except Exception:
                    self._log(f"    ! No details section found for product. Skipping.")
                    continue
                
                product_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                product_details = self._extract_details_from_product_page(product_soup, search_mode)
                product_details['URL'] = product_url

                if product_details.get('Total quantity', 0) > 0:
                    is_relevant = self.relevance_agent.is_relevant(product_details.get('Product'), keyword)
                    
                    self._log(f"      -> Waiting 4.5 seconds before next request...")
                    time.sleep(5)

                    if is_relevant:
                        found_products.append(product_details)
                        self._log(f"    -> VALID product found: {product_details.get('Product')[:60]}...")
                    else:
                        self._log(f"    -> DISCARDED (Not relevant by AI): {product_details.get('Product')[:60]}...")
                else:
                    self._log(f"    -> DISCARDED (no valid data): {product_details.get('Product')[:60]}...")
        except Exception as e:
            self._log(f"    ! Unexpected error occurred in Amazon scraper: {e}")

        return found_products