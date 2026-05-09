import asyncio
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import pandas as pd

class SkjayaScraper:
    def __init__(self):
        self.base_url = "https://skjaya.id"
        self.login_url = f"{self.base_url}/"
        # Standardized limit to 999999 to get everything
        self.api_endpoints = {
            "inventory": f"{self.base_url}/api/inventory?order=registered&sorting=DESC&limit=999999",
            "deposit": f"{self.base_url}/api/deposit?order=registered&sorting=DESC&limit=999999",
            "restock": f"{self.base_url}/api/transaction/data/restock?order=registered&sorting=DESC&limit=999999",
            "lost_return": f"{self.base_url}/api/transaction/data/po/lost-return/report?order=registered&sorting=DESC&limit=999999",
            "employee": f"{self.base_url}/api/employee?limit=999999",
            "big_query": f"{self.base_url}/api/big-query?order=registered&sorting=DESC&limit=999999",
            "attendance": f"{self.base_url}/api/attendance?limit=999999",
            "customer": f"{self.base_url}/api/customer?limit=999999",
            "customer_movement": f"{self.base_url}/api/customer/movement?limit=999999",
            "product": f"{self.base_url}/api/product?limit=999999",
            "transaction_po": f"{self.base_url}/api/transaction/data/po?limit=999999",
            "transaction_report": f"{self.base_url}/api/transaction/report?limit=999999",
            "branch": f"{self.base_url}/api/branch?limit=999999",
            "category": f"{self.base_url}/api/category?limit=999999"
        }

    async def fetch_all_data(self, username, password, output_file="data.json"):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Apply stealth using the Stealth class
            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            try:
                # 1. Login
                await page.goto(self.login_url)
                # Wait for username field by name attribute which is more stable
                await page.wait_for_selector('input[name="username"]', timeout=15000)
                await page.fill('input[name="username"]', username)
                await page.fill('input[name="password"]', password)
                # Small delay to ensure input is registered
                await asyncio.sleep(0.5)
                await page.click('button:has-text("Sign in"), button[type="submit"]')

                # Wait for navigation or successful login indication
                try:
                    await page.wait_for_url(lambda url: url != self.login_url and self.base_url in url, timeout=10000)
                except:
                    # If URL doesn't change, maybe it's a SPA state change. Check for a common dashboard element.
                    await page.wait_for_load_state("networkidle")
                
                # 2. Fetch all APIs
                all_results = {}
                for key, api_url in self.api_endpoints.items():
                    print(f"Fetching {key}...")
                    try:
                        json_data = await page.evaluate(f"""
                            async () => {{
                                const response = await fetch("{api_url}");
                                return await response.json();
                            }}
                        """)
                        if json_data and "data" in json_data:
                            all_results[key] = json_data["data"]
                        else:
                            all_results[key] = json_data # Fallback to full response
                    except Exception as e:
                        all_results[key] = {"error": str(e)}

                await browser.close()
                
                # 3. Save to data.json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=4, ensure_ascii=False)
                
                return all_results, None

            except Exception as e:
                await browser.close()
                return None, str(e)

async def run_full_fetcher(username, password, output_file="data.json"):
    scraper = SkjayaScraper()
    return await scraper.fetch_all_data(username, password, output_file)
