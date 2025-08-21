import os
import json
import requests
from dotenv import load_dotenv

class RelevanceAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Api KEY not found")

        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={self.api_key}"
        self.headers = {'Content-Type': 'application/json'}

    def _get_prompt(self, product_name, search_query):
        return f"""
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

    def is_relevant(self, product_name, search_query):
        if not self.api_key:
            return False 

        prompt = self._get_prompt(product_name, search_query)
        chat_history = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {"contents": chat_history}

        try:
            response = requests.post(self.api_url, headers=self.headers, data=json.dumps(payload))
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
            return False
        except Exception as e:
            print(f"      -> Unexpected error processing AI response: {e}")
            return False