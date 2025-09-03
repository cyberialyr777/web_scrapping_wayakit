

class EzorderScraper:
    def __init__(self, driver, relevance_agent):
        self.driver = driver
        self.relevance_agent = relevance_agent
        self.base_url = "https://shop.ezorder.com.sa/"
    
    def _log(self, msg):
        print(msg)

    def scrape(self):
        print("Scraping data from EzOrder...")
        return {"data": "sample data from EzOrder"}