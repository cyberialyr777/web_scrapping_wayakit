#!/usr/bin/env python3
"""
Simple test script for Clean Dishes scraper only
"""
import config
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from services.ai_service import RelevanceAgent
from scrapers.cleandishes_scraper import CleanDishesScraper

def test_cleandishes_only():
    print("=== Testing Clean Dishes Scraper Only (Anti-Bot Version) ===")
    
    # Setup Chrome driver with enhanced anti-detection
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    
    # Anti-detection options
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-images')  # Load faster
    options.add_argument('--disable-javascript-harmony-shipping')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument(f"user-agent={config.USER_AGENT}")
    options.add_argument('--log-level=3')
    
    # Additional headers and preferences
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "geolocation": 2,
        },
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2,  # Block images for speed
        "profile.password_manager_enabled": False,
        "credentials_enable_service": False,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        print("✓ Chrome driver started successfully with anti-bot configuration")
        
        # Additional stealth measures
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined,
                });
                
                // Mock the plugins property
                Object.defineProperty(navigator, 'plugins', {
                  get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                  get: () => ['en-US', 'en', 'ar'],
                });
                
                // Chrome runtime
                window.chrome = {
                  runtime: {}
                };
                
                // Permissions
                const originalQuery = window.navigator.permissions.query;
                return window.navigator.permissions.query = (parameters) => (
                  parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
            """
        })
        
        # Initialize AI agent and scraper
        ai_agent = RelevanceAgent()
        scraper = CleanDishesScraper(driver, relevance_agent=ai_agent)
        
        # Test with a simple keyword from your analysis.csv
        test_keyword = 'glass cleaner'  # This should be in your CSV
        
        print(f"\n--- Testing with keyword: '{test_keyword}' (Anti-Bot Mode) ---")
        results = scraper.scrape(test_keyword, 'volume')
        
        print(f"✓ Scraping completed. Found {len(results)} products.")
        
        for i, product in enumerate(results, 1):
            print(f"  Product {i}:")
            print(f"    Name: {product.get('Product', 'N/A')}")
            print(f"    Price: {product.get('Price_SAR', 'N/A')} SAR")
            print(f"    Brand: {product.get('Company', 'N/A')}")
            print(f"    Quantity: {product.get('Total quantity', 'N/A')} {product.get('Unit of measurement', 'N/A')}")
            print(f"    URL: {product.get('URL', 'N/A')}")
            print("")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("✓ Driver closed")

if __name__ == "__main__":
    test_cleandishes_only()
