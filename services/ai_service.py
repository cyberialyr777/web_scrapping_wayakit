import os
import json
import requests
import time 
from dotenv import load_dotenv

class RelevanceAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("API KEY not found")

        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={self.api_key}"
        self.headers = {'Content-Type': 'application/json'}

    def _get_prompt(self, product_name, search_query):
        return f"""
        You are a highly precise expert shopping assistant. Your task is to determine if a product title is a relevant and specific match for a user's search query. Your decisions must be strict.

        --- RULES ---

        ## General Rules:
        1.  **Tools vs. Cleaners:** If the query is for a liquid/spray cleaner (e.g., "glass cleaner"), you MUST REJECT cleaning tools (cloths, wipes, brushes). Only accept tools if the query explicitly asks for one (e.g., "disinfectant wipes").
        2.  **Context of Use:** If the query specifies an application (e.g., "for furniture"), you MUST REJECT products for a different application (e.g., "laundry," "dishes").

        ## Specificity Rules:
        3.  **Specialized Surfaces:** If the query asks for a cleaner for a specific surface (e.g., "hardwood floor cleaner"), you MUST REJECT general-purpose or multi-surface cleaners. The product must be explicitly for that surface.
        4.  **Specialized Products:** If the query is for a specialized product (e.g., "wax and floor polish," "waterless car wash"), you MUST REJECT general cleaners. The product title must clearly indicate it performs that specific function.
        5.  **Automotive Focus:** If the query is for a car cleaning product (e.g., "microfiber for vehicle," "car disinfectant rags"), you MUST REJECT general-purpose products. The product must be explicitly marketed for automotive use.

        ## Final Instruction:
        Respond with only "Yes" or "No".

        --- EXAMPLES ---

        # Example (Tools vs. Cleaner)
        User Search Query: "glass cleaner"
        Product Title: "Microfiber cloth for glass"
        Is the product a relevant match for the query?
        No

        # Example (Context of Use)
        User Search Query: "fabric freshener for furnitures"
        Product Title: "Loyal Fabric Softener & Freshener for Laundry"
        Is the product a relevant match for the query?
        No

        # Example (Specialized Surface)
        User Search Query: "hardwood floor cleaner"
        Product Title: "Mr. Clean Multi-Purpose Floor Cleaner"
        Is the product a relevant match for the query?
        No
        
        # Example (Specialized Product)
        User Search Query: "wax and floor polish"
        Product Title: "Pledge Floor Gloss, Polish and Wax"
        Is the product a relevant match for the query?
        Yes

        # Example (Automotive Focus)
        User Search Query: "car surface disinfectant wet rags"
        Product Title: "Lysol Disinfecting Wipes, Multi-Surface Lemon Scent"
        Is the product a relevant match for the query?
        No

        # Example (Automotive Focus)
        User Search Query: "microfiber for vehicle cleaning"
        Product Title: "Armor All Car Cleaning Microfiber Towel"
        Is the product a relevant match for the query?
        Yes
        
        # Example (Waterless Product)
        User Search Query: "waterless car wash"
        Product Title: "Meguiar's Gold Class Car Wash Shampoo & Conditioner"
        Is the product a relevant match for the query?
        No

        --- END EXAMPLES ---

        --- CURRENT TASK ---
        User Search Query: "{search_query}"
        Product Title: "{product_name}"

        Is the product a relevant match for the query?
        """

    def is_relevant(self, product_name, search_query):
        if not self.api_key:
            return False 

        prompt = self._get_prompt(product_name, search_query)
        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": chat_history}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=self.headers, data=json.dumps(payload))
                
                if response.status_code == 429:
                    print("      -> Rate limit hit. Waiting for 60 seconds to reset...")
                    time.sleep(60)
                    continue 

                response.raise_for_status()
                result = response.json()

                if result.get('candidates'):
                    decision = result['candidates'][0]['content']['parts'][0]['text'].strip().lower()
                    print(f"      -> IA decision: {decision}")
                    return "yes" in decision
                else:
                    print("      -> No candidates found in AI response.")
                    return False

            except requests.exceptions.RequestException as e:
                print(f"      -> Network error contacting AI agent: {e}")
                if attempt < max_retries - 1:
                    print(f"      -> Retrying in 10 seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(10)
                else:
                    return False 
            except Exception as e:
                print(f"      -> Unexpected error processing AI response: {e}")
                return False
        
        print("      -> Failed to get a valid response from AI after multiple retries.")
        return False