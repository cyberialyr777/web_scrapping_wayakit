
import time
import random
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import quote


class CleanDishesScraper:
    def __init__(self, driver, relevance_agent=None):
        self.driver = driver
        self.relevance_agent = relevance_agent
        self.base_url = "https://cleandishes1.com/"
        # Configure anti-bot detection measures
        self._configure_anti_bot_measures()

    def _log(self, msg):
        print(msg)

    def _configure_anti_bot_measures(self):
        """Configure the browser to avoid bot detection"""
        try:
            # Execute JavaScript to remove webdriver property and other bot indicators
            self.driver.execute_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Add languages property
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'ar'],
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock permissions
                const originalQuery = window.navigator.permissions.query;
                return window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Set additional headers to appear more human-like
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "acceptLanguage": "en-US,en;q=0.9,ar;q=0.8",
                "platform": "Win32"
            })
            
            self._log("    -> Anti-bot measures configured")
            
        except Exception as e:
            self._log(f"    -> Warning: Could not configure all anti-bot measures: {e}")

    def _human_like_delay(self, min_seconds=1, max_seconds=3):
        """Add random human-like delay"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def _simulate_human_behavior(self):
        """Simulate human-like behavior on the page"""
        try:
            # Random mouse movements and scrolling
            self.driver.execute_script("""
                // Simulate mouse movement
                const event = new MouseEvent('mousemove', {
                    clientX: Math.random() * window.innerWidth,
                    clientY: Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
                
                // Random scroll
                window.scrollTo({
                    top: Math.random() * 200,
                    behavior: 'smooth'
                });
            """)
            
            # Random small delay
            self._human_like_delay(0.5, 2)
            
        except Exception as e:
            self._log(f"    -> Could not simulate human behavior: {e}")

    def _translate_to_arabic(self, text):
        """Translate English text to Arabic using Google Translate API"""
        try:
            # Using Google Translate API via requests
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': 'en',  # source language (English)
                'tl': 'ar',  # target language (Arabic)
                'dt': 't',   # return translation
                'q': text
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated_text = result[0][0][0]
                self._log(f"    -> Translated '{text}' to '{translated_text}'")
                return translated_text
            else:
                self._log(f"    -> Translation API returned empty result for '{text}'")
                return text
                
        except requests.RequestException as e:
            self._log(f"    -> Translation API error: {e}")
            return self._fallback_translation(text)
        except Exception as e:
            self._log(f"    -> Unexpected translation error: {e}")
            return self._fallback_translation(text)

    def _fallback_translation(self, text):
        """Fallback translations for common cleaning product terms from analysis.csv"""
        translations = {
            'all purpose cleaner': 'منظف متعدد الأغراض',
            'glass cleaner': 'منظف زجاج',
            'kitchen degreaser': 'مزيل الدهون للمطبخ',
            'oven and grill cleaner': 'منظف أفران وشواء',
            'stainless steel cleaner': 'منظف ستانلس ستيل',
            'general sanitizer for vegetable and salad washing': 'معقم عام لغسل الخضروات والسلطة',
            'toilet bowl cleaner': 'منظف مرحاض',
            'shower and tub cleaner': 'منظف حمام وبانيو',
            'mold and mildew remover': 'مزيل العفن والفطريات',
            'tile and grout cleaner': 'منظف بلاط وفواصل',
            'hardwood floor cleaner': 'منظف أرضيات خشبية',
            'tile and laminate cleaner': 'منظف بلاط ولامينيت',
            'wax and floor polish': 'شمع وملمع أرضيات',
            'marble cleaner': 'منظف رخام',
            'wood polish for furniture': 'ملمع خشب للأثاث',
            'leather cleaner': 'منظف جلد',
            'carpet shampoo': 'شامبو سجاد',
            'spot remover for carpets': 'مزيل البقع للسجاد',
            'fabric freshener for furnitures': 'معطر أقمشة للأثاث',
            'surface disinfectant spray': 'رذاذ مطهر للأسطح'
        }
        
        # Try direct mapping first
        text_lower = text.lower().strip()
        if text_lower in translations:
            arabic_text = translations[text_lower]
            self._log(f"    -> Used fallback translation for '{text}' -> '{arabic_text}'")
            return arabic_text
        
        # Try to find partial matches
        for eng, arab in translations.items():
            if eng in text_lower:
                self._log(f"    -> Used fallback partial match for '{text}' -> '{arab}'")
                return arab
        
        # If no mapping found, return original text with a warning
        self._log(f"    -> Warning: No translation found for '{text}', using original text")
        return text

    def _translate_page_to_english(self):
        """Use browser translation to translate the page from Arabic to English"""
        try:
            self._log("    -> Attempting to translate page to English using browser translator")
            
            current_url = self.driver.current_url
            
            # Method 1: Try to find Google Translate widget or browser translate bar
            try:
                translate_selectors = [
                    "//button[contains(text(), 'Translate') or contains(text(), 'ترجم')]",
                    "//div[@id='google_translate_element']//select",
                    "//button[contains(@class, 'translate')]"
                ]
                
                for selector in translate_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        element.click()
                        self._log("    -> Found and clicked translate element")
                        # Wait for translation to complete
                        WebDriverWait(self.driver, 10).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                        return True
                    except TimeoutException:
                        continue
                        
            except Exception as e:
                self._log(f"    -> No automatic translate option found")
            
            # Method 2: Try Chrome's translate bar (usually appears automatically for Arabic pages)
            try:
                # Check if page language is detected as Arabic
                page_lang = self.driver.execute_script("return document.documentElement.lang || document.body.lang || 'unknown'")
                self._log(f"    -> Page language detected as: {page_lang}")
                
                # Wait for Chrome translate bar to potentially appear
                try:
                    translate_bar = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'translate') or contains(@id, 'translate')]"))
                    )
                    self._log("    -> Chrome translate bar detected")
                except TimeoutException:
                    self._log("    -> No Chrome translate bar found")
                
            except Exception as e:
                self._log(f"    -> Could not detect page language: {e}")
            
            # Method 3: Add language parameter to URL if supported
            if "lang=" not in current_url and "language=" not in current_url:
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}lang=en"
                self._log(f"    -> Trying language parameter: {new_url}")
                self.driver.get(new_url)
                
                # Wait for page to load with language parameter
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            
            self._log("    -> Translation attempts completed. Page should be translated by browser if Arabic content detected.")
            return True
            
        except Exception as e:
            self._log(f"    -> Translation attempt failed: {e}")
            return False

    def _wait_for_page_load(self, timeout=60):
        """Wait for the page to fully load, avoiding the loading screen and bot detection"""
        try:
            self._log(f"    -> Waiting for page to load completely (timeout: {timeout}s)...")
            
            # Simulate human behavior while waiting
            self._simulate_human_behavior()
            
            # Wait for the bot detection/loading message to disappear
            bot_detection_messages = [
                "//*[contains(text(), 'يرجي الانتظار')]",
                "//*[contains(text(), 'لحظات وسيتم تحويلك')]",
                "//*[contains(text(), 'Please wait')]",
                "//*[contains(text(), 'Loading')]",
                "//*[contains(text(), 'Checking your browser')]",
                "//*[contains(text(), 'Just a moment')]",
                ".loading, .spinner, .loader, .cf-browser-verification",
                "#loading, #spinner, #loader, #cf-wrapper"
            ]
            
            # First, check if we're stuck on a bot detection page
            for attempt in range(3):
                try:
                    # Check current page content
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    
                    if any(phrase in page_text for phrase in ['يرجي الانتظار', 'please wait', 'checking your browser', 'just a moment']):
                        self._log(f"    -> Bot detection page detected (attempt {attempt + 1}/3)")
                        
                        # Try refreshing the page
                        if attempt < 2:
                            self._log("    -> Refreshing page to bypass bot detection...")
                            self._human_like_delay(2, 5)  # Wait before refresh
                            self.driver.refresh()
                            self._human_like_delay(3, 8)  # Wait after refresh
                            self._simulate_human_behavior()
                            continue
                        else:
                            self._log("    -> Bot detection persists after retries")
                            
                    else:
                        self._log("    -> No bot detection message found, proceeding...")
                        break
                        
                except Exception as e:
                    self._log(f"    -> Error checking for bot detection: {e}")
                    break
            
            # Wait for actual content to appear
            content_selectors = [
                "nav, header, .header, .navigation, .navbar",
                ".content, .main, .container, .wrapper, .page-content",
                ".product, .search, .category, .menu, .footer",
                "input[type='search'], .search-box, .search-input",
                "a[href*='search'], a[href*='category']"
            ]
            
            content_found = False
            for selector in content_selectors:
                try:
                    # Use shorter timeout for each selector
                    WebDriverWait(self.driver, min(15, timeout // 4)).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self._log(f"    -> Content loaded (found: {selector})")
                    content_found = True
                    
                    # Simulate human interaction with the content
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        self._human_like_delay(0.5, 1.5)
                    except:
                        pass
                    
                    break
                    
                except TimeoutException:
                    continue
            
            if not content_found:
                self._log("    -> No recognizable content found, but continuing...")
            
            # Final check: wait for document to be ready
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                self._log("    -> Document ready state is complete")
            except TimeoutException:
                self._log("    -> Document ready state timeout, but continuing...")
            
            # Final human simulation
            self._simulate_human_behavior()
            
            return True
            
        except TimeoutException:
            self._log(f"    -> Page load timeout ({timeout}s exceeded)")
            return False
        except Exception as e:
            self._log(f"    -> Error waiting for page load: {e}")
            return False

    def _handle_popups(self):
        """Handle cookie popups and other overlays"""
        try:
            cookie_selectors = [
                "//button[contains(text(), 'Accept') or contains(text(), 'قبول') or contains(text(), 'موافق')]",
                "//button[contains(@class, 'cookie')]",
                "//a[contains(text(), 'Accept')]",
                ".cookie-accept",
                "#cookie-accept"
            ]
            
            for selector in cookie_selectors:
                try:
                    if selector.startswith("//"):
                        button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    button.click()
                    self._log("    -> Cookie popup handled")
                    
                    # Wait for popup to disappear
                    WebDriverWait(self.driver, 5).until_not(
                        EC.presence_of_element_located((By.XPATH, selector) if selector.startswith("//") else (By.CSS_SELECTOR, selector))
                    )
                    return True
                except TimeoutException:
                    continue
            
            self._log("    -> No popups found")
            return False
            
        except Exception as e:
            self._log(f"    -> Error handling popups: {e}")
            return False

    def scrape(self, search_keyword, search_mode):
        """
        Simplified scraping method - only navigate, translate page, and perform search
        """
        self._log(f"  [Clean Dishes Scraper] Testing navigation and translation for: '{search_keyword}'")
        
        try:
            # Step 1: Navigate to the main page with human-like behavior
            self._log("    -> Navigating to Clean Dishes homepage")
            self.driver.get(self.base_url)
            
            # Immediate human simulation after navigation
            self._human_like_delay(2, 5)
            self._simulate_human_behavior()
            
            # Step 2: Wait for page to load completely (with anti-bot measures)
            if not self._wait_for_page_load(timeout=90):
                self._log("    -> Warning: Page may not have loaded completely")
                # Try one more refresh if page didn't load
                self._log("    -> Attempting final page refresh...")
                self._human_like_delay(3, 7)
                self.driver.refresh()
                self._human_like_delay(5, 10)
                self._simulate_human_behavior()
            
            # Step 3: Handle popups
            self._handle_popups()
            
            # Step 4: More human behavior before proceeding
            self._human_like_delay(2, 4)
            self._simulate_human_behavior()
            
            # Step 5: Try to translate the page
            self._translate_page_to_english()
            
            # Step 6: Translate search keyword to Arabic
            arabic_keyword = self._translate_to_arabic(search_keyword)
            
            # Step 7: Human-like delay before search
            self._human_like_delay(3, 6)
            
            # Step 8: Navigate to search page with human-like behavior
            search_url = f"{self.base_url}search?q={quote(arabic_keyword)}"
            self._log(f"    -> Navigating to search URL: {search_url}")
            
            self.driver.get(search_url)
            
            # Step 9: Human behavior after navigation
            self._human_like_delay(2, 5)
            self._simulate_human_behavior()
            
            # Step 10: Wait for search page to load completely
            if not self._wait_for_page_load(timeout=60):
                self._log("    -> Warning: Search page may not have loaded completely")
            
            # Step 11: Handle popups on search page
            self._handle_popups()
            
            # Step 12: Human behavior before translation
            self._human_like_delay(1, 3)
            
            # Step 13: Try to translate the search results page
            self._translate_page_to_english()
            
            # Step 14: Log page information and check for bot detection
            try:
                page_title = self.driver.title
                current_url = self.driver.current_url
                page_text = self.driver.find_element(By.TAG_NAME, "body").text[:300]  # First 300 chars
                
                self._log(f"    -> Page Analysis:")
                self._log(f"         Title: '{page_title}'")
                self._log(f"         URL: {current_url}")
                self._log(f"         Content preview: '{page_text[:200]}...'")
                
                # Check if we're still blocked
                if any(phrase in page_text.lower() for phrase in ['يرجي الانتظار', 'please wait', 'checking', 'moment']):
                    self._log("    -> ⚠️  WARNING: Still appears to be on bot detection page")
                    self._log("    -> Site may have strong anti-bot protection")
                else:
                    self._log("    -> ✅ Successfully bypassed loading/detection screen")
                
            except Exception as e:
                self._log(f"    -> Could not analyze page content: {e}")
            
            # Step 15: Keep page open for manual inspection with periodic human behavior
            self._log("    -> Keeping page open for 45 seconds for manual inspection...")
            for i in range(3):  # 3 intervals of 15 seconds each
                time.sleep(15)
                if i < 2:  # Don't simulate on last iteration
                    self._simulate_human_behavior()
                    self._log(f"    -> Human behavior simulation {i+1}/3")
            
            self._log("  [Clean Dishes Scraper] Navigation and translation test completed")
            return []  # Return empty list for now since we're not extracting products yet
            
        except Exception as e:
            self._log(f"    -> Error in Clean Dishes scraper: {e}")
            return []