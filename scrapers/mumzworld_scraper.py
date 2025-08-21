import time
import os
from dotenv import load_dotenv
import re
import json
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from utils import parse_volume_string, parse_count_string

class MumzworldScraper:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://www.mumzworld.com/sa-en/"

    def _log(self, msg):
        print(msg)

    def _safe_get_text(self, element):
        return element.get_text(strip=True) if element else None

    def _parse_mumzworld_count_string(self, text_string):
        if not text_string:
            return None
        match = re.search(r'(\d+)\s*(wipes|count|sheets|sachets|pack|pcs|pieces|pc|s)\b', text_string, re.I)
        if not match:
            return None
        quantity = int(match.group(1))
        return {'quantity': quantity, 'unit': 'units', 'normalized': quantity}

    def _is_product_relevant_gemini(self, product_name, search_query):
        prompt = f"""
        You are an expert shopping assistant. Your task is to determine if a product title is a relevant match for a user's search query.
        You must follow these rules:
        1.  If the user's query is for a liquid or spray cleaner (e.g., "glass cleaner", "all purpose cleaner"), you MUST reject products that are cleaning tools like cloths, wipes, microfibers, or brushes.
        2.  You should only accept cleaning tools if the user's query explicitly asks for one (e.g., "disinfectant wipes", "microfiber cloth").
        3.  Pay close attention to the context of use. If the query specifies an application (e.g., "for furniture", "for floors"), you MUST reject products designed for a different application (e.g., "laundry", "dishes"), even if they share keywords like 'cleaner' or 'freshener'.

        Respond with only "Yes" or "No".

        --- EXAMPLES ---
        User Search Query: "glass cleaner"
        Product Title: "Microfiber cloth for glass"
        Is the product a relevant match for the query?
        No

        User Search Query: "disinfectant wipes"
        Product Title: "Dettol disinfectant wipes"
        Is the product a relevant match for the query?
        Yes

        User Search Query: "fabric freshener for furnitures"
        Product Title: "Loyal Fabric Softener & Freshener"
        Is the product a relevant match for the query?
        No
        --- END EXAMPLES ---

        --- CURRENT TASK ---
        User Search Query: "{search_query}"
        Product Title: "{product_name}"

        Is the product a relevant match for the query?
        """
        try:
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                self._log("      -> ERROR: GEMINI_API_KEY no encontrada.")
                return False

            chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
            payload = {"contents": chat_history}
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()

            if result.get('candidates'):
                decision = result['candidates'][0]['content']['parts'][0]['text'].strip().lower()
                self._log(f"      -> IA decision: {decision}")
                return "yes" in decision
            else:
                self._log("      -> No candidates found in AI response.")
                return False
        except requests.exceptions.RequestException as e:
            self._log(f"      -> Network error contacting AI agent: {e}")
            return False
        except Exception as e:
            self._log(f"      -> Unexpected error processing AI response: {e}")
            return False

    def _extract_product_details(self, product_url, search_mode):
        details = {
            'Product': 'Not found', 'Price_SAR': '0.00', 'Company': 'Not found',
            'URL': product_url, 'Unit of measurement': 'units', 'Total quantity': 0
        }
        try:
            self.driver.get(product_url)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ProductDetails_productName__lcVK_")))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            product_name_tag = soup.find('h1', class_='ProductDetails_productName__lcVK_')
            product_name = self._safe_get_text(product_name_tag)
            if product_name:
                details['Product'] = product_name
                details['Company'] = product_name.split(' - ')[0].strip() if ' - ' in product_name else product_name.split(' ')[0].strip()

                parsed_data = self._parse_mumzworld_count_string(product_name) if search_mode == 'units' else parse_volume_string(product_name)
                if parsed_data:
                    base_quantity = parsed_data['quantity']
                    multiplier_match = re.search(r'(?:pack of|x|of)\s*(\d+)', product_name, re.IGNORECASE)
                    if multiplier_match:
                        multiplier = int(multiplier_match.group(1))
                        details['Total quantity'] = base_quantity * multiplier
                        self._log(f"      -> Multiplier found: {base_quantity} * {multiplier} = {details['Total quantity']}")
                    else:
                        details['Total quantity'] = base_quantity
                    details['Unit of measurement'] = parsed_data['unit']
                    self._log(f"      -> Extracted amount: {details['Total quantity']} {parsed_data['unit']}")

            price_tag = soup.find('span', class_='Price_integer__3ngZQ')
            if price_tag:
                details['Price_SAR'] = self._safe_get_text(price_tag).replace(',', '')
        except Exception as e:
            self._log(f"      ! Error extracting details from {product_url}: {e}")
        return details

    def scrape(self, keyword, search_mode):
        self._log(f"  [Mumzworld Scraper] Searching: '{keyword}' (Mode: {search_mode})")
        search_url = f"{self.base_url}search?q={quote(keyword)}"
        valid_products_found = []
        products_to_find = 5

        try:
            self._log(f"    > Navigating to: {search_url}")
            self.driver.get(search_url)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProductCard_productCard__kFgss")))
            self._log("    > Search results page loaded. Analyzing products...")
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            product_containers = soup.select("div.ProductCard_productCard__kFgss")

            if not product_containers:
                self._log("    ! Warning: No product containers found.")
                return []

            for container in product_containers:
                if len(valid_products_found) >= products_to_find:
                    self._log(f"    > Limit of {products_to_find} VALID products reached.")
                    break

                link_tag = container.find('a', class_='ProductCard_productName__Dz1Yx')
                if link_tag and link_tag.has_attr('href'):
                    product_url = urljoin(self.base_url, link_tag['href'])
                    self._log(f"      -> Visiting: {product_url[:80]}...")
                    product_details = self._extract_product_details(product_url, search_mode)

                    if product_details.get('Total quantity', 0) > 0:
                        is_relevant = self._is_product_relevant_gemini(product_details.get('Product'), keyword)
                        if is_relevant:
                            valid_products_found.append(product_details)
                            self._log(f"      -> VALID. Extracted: {product_details['Product'][:60]}...")
                        else:
                            self._log(f"      -> DISCARDED (Not relevant by AI): {product_details['Product'][:60]}...")
                    else:
                        self._log(f"      -> DISCARDED (no quantity): {product_details['Product'][:60]}...")
        except Exception as e:
            self._log(f"    ! Unexpected error occurred in Mumzworld scraper: {e}")

        return valid_products_found