
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from utils import parse_volume_string, parse_count_string

def safe_get_text(element):
    return element.get_text(strip=True) if element else None

def extract_from_table(soup, table_id, fields):
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

def log(msg):
    print(msg)


def extract_details_from_product_page(soup, search_mode='volume'):
    details = {
        'Product': 'Not found',
        'Price_SAR': '0.00',
        'Company': 'Company not found',
        'Unit of measurement': 'units',
        'Total quantity': 0,
        'Validation_Status': 'Not Found'
    }

    details['Product'] = safe_get_text(soup.find('span', id='productTitle')) or details['Product']
    brand_row = soup.find('tr', class_='po-brand')
    details['Company'] = safe_get_text(brand_row.find('span', class_='po-break-word')) if brand_row else details['Company']
    price_whole = soup.find('span', class_='a-price-whole')
    price_fraction = soup.find('span', class_='a-price-fraction')
    if price_whole:
        price_str = price_whole.get_text(strip=True).replace(',', '').rstrip('.')
        if price_fraction:
            price_str += '.' + price_fraction.get_text(strip=True)
        details['Price_SAR'] = price_str

    raw_title = details.get('Product')
    tech_fields = extract_from_table(soup, 'productDetails_techSpec_section_1', ['volume', 'weight'])
    raw_volume = tech_fields['volume']
    raw_weight = tech_fields['weight']
    item_volume_row = soup.find('tr', class_='po-item_volume')
    raw_item_volume = safe_get_text(item_volume_row.find('span', class_='po-break-word')) if item_volume_row else None

    log(f"     [Debug] -> Title: '{raw_title is not None}', title: {raw_title}, Vol: '{raw_volume}', ItemVol: '{raw_item_volume}', Weight: '{raw_weight}'")

    p_title = p_volume = p_item_volume = p_weight = None
    if search_mode == 'units':
        log("     [Validator] Search mode: units")
        p_title = parse_count_string(raw_title)
    else:
        log("     [Validator] Search mode: volume")
        p_title = parse_volume_string(raw_title)
        p_volume = parse_volume_string(raw_volume)
        p_item_volume = parse_volume_string(raw_item_volume)
        p_weight = parse_volume_string(raw_weight)

    final_data = None
    validation_status = 'Not Found'

    volume_fields = [p_title, p_volume, p_item_volume, p_weight]
    volume_values = [v for v in volume_fields if v is not None]
    if search_mode != 'units' and len(volume_values) < 2:
        log("     [Validator] ❌ Not enough volume values found.")
        return details

    if search_mode != 'units':
        for i, vi in enumerate(volume_fields):
            if vi is None:
                continue
            for j in range(i+1, len(volume_fields)):
                vj = volume_fields[j]
                if vj is None:
                    continue
                if abs(vi['normalized'] - vj['normalized']) < 1:
                    final_data = vi
                    validation_status = f"Confirmed by {['title','volume','item_volume','weight'][i].capitalize()} & {['title','volume','item_volume','weight'][j].capitalize()}"
                    break
            if final_data:
                break
        if not final_data:
            log("     [Validator] ❌ Not enough volume values found.")
            return details
    else:
        if p_title:
            final_data = p_title
            validation_status = 'From Title'

    if final_data:
        details['Total quantity'] = final_data['quantity']
        details['Unit of measurement'] = final_data['unit']
        details['Validation_Status'] = validation_status
        log(f"     [Validator] ✅ Final Decision: {final_data['quantity']} {final_data['unit']} (Source: {validation_status})")
    else:
        log(f"     [Validator] ❌ No valid data found for mode '{search_mode}'.")

    return details

def scrape_amazon(keyword, driver, search_mode):
    log(f"  Searching '{keyword}'")
    base_url = "https://www.amazon.sa"
    found_products = []
    products_to_find = 2
    search_url = f"{base_url}/s?k={keyword.replace(' ', '+')}&language=en_AE"

    try:
        driver.get(search_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})

        if not product_containers:
            log("    ! Warning: No product containers found.")
            return []

        for container in product_containers:
            if len(found_products) >= products_to_find:
                log(f"    > Target of {products_to_find} valid products reached.")
                break

            link_tag = container.find('a', class_='a-link-normal')
            if not link_tag or 'spons' in link_tag.get('href', ''):
                continue

            product_url = urljoin(base_url, link_tag['href'])
            log(f"    > Visiting product page: {product_url[:250]}...")

            driver.get(product_url)
            try:
                WebDriverWait(driver, 10).until(EC.any_of(
                    EC.presence_of_element_located((By.ID, "productDetails_techSpec_section_1")),
                    EC.presence_of_element_located((By.ID, "detailBullets_feature_div")),
                    EC.presence_of_element_located((By.CLASS_NAME, "po-item_volume")),
                    EC.presence_of_element_located((By.ID, "centerCol"))
                ))
            except Exception:
                log(f"    ! No details section found for {product_url[:250]}. Skipping.")
                continue

            product_soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_details = extract_details_from_product_page(product_soup, search_mode)

            if product_details.get('Total quantity', 0) > 0:
                product_details['URL'] = product_url
                found_products.append(product_details)
                log(f"    -> Valid product found: {product_details.get('Product')[:50]}...")
            else:
                log(f"    -> Discarded product (no valid data): {product_details.get('Product')[:50]}...")

    except Exception as e:
        log(f"    ! Unexpected error occurred in Selenium scraper: {e}")

    return found_products