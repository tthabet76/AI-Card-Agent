import time
import re
import sqlite3
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- CONFIGURATION ---
database_file = 'card_inventory.db'
chromedriver_path = "chromedriver.exe" 

# Full list of banks restored, but we will test one at a time.
bank_listing_urls = {
    "Mashreq Bank": "https://www.mashreq.com/en/uae/neo/cards/",
    # "ADCB": "https://www.adcb.com/en/personal/cards/credit-cards/",
    # "RAKBANK": "https://www.rakbank.ae/en",
    # "Emirates NBD": "https://www.emiratesnbd.com/en/cards/credit-cards/",
    # "FAB (First Abu Dhabi Bank)": "https://www.bankfab.com/en-ae/personal/credit-cards",
    # "HSBC": "https://www.hsbc.ae/credit-cards/products/",
    # "DIB": "https://www.dib.ae/personal/cards/?cardType=All-Cards&income=Any&cardBenefit=All-Benefits&visible=24"
}

# --- DATABASE SETUP ---
def setup_database():
    """Initializes the database and creates the table if it doesn't exist."""
    print("--- Setting up database ---")
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    # Using the more robust schema from your previous work
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_inventory (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            bank_name TEXT,
            first_discovered_date TEXT,
            last_verified_date TEXT,
            is_active BOOLEAN,
            card_name TEXT,
            annual_fee TEXT,
            minimum_salary TEXT
        );
    ''')
    conn.commit()
    conn.close()
    print(f"  Database '{database_file}' is ready.\n")

# --- DISCOVERY AGENT LOGIC ---
def discover_card_urls_from_listing(bank_name, listing_url):
    """Uses Selenium with explicit waits to find credit card URLs."""
    print(f"--- Running Discovery for: {bank_name} ---")
    service = Service(executable_path=chromedriver_path)
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(listing_url)
        
        # Use explicit wait for robustness
        print("  Waiting for page content to load...")
        wait = WebDriverWait(driver, 10)
        
        # CORRECTED LINE: This is the line that caused the error.
        # Ensure it is exactly like this, with no extra quotes.
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='card-item_card-item__']")))
        
        print("  Card containers have loaded. Parsing page...")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        found_urls = []
        card_containers = soup.find_all('div', class_=re.compile('card-item_card-item__'))
        
        for container in card_containers:
            card_type_element = container.find('p', class_=re.compile('card-item_card-type__'))
            link_element = container.find('a', href=True)
            
            if card_type_element and "credit card" in card_type_element.text.strip().lower():
                full_url = urljoin(listing_url, link_element['href'])
                found_urls.append(full_url)
        
        print(f"  Found {len(found_urls)} credit card URLs.")
        return found_urls

    except Exception as e:
        print(f"  An error occurred: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def update_database_with_urls(bank_name, urls):
    """Saves or updates discovered URLs in the database using the advanced ON CONFLICT method."""
    if not urls:
        print("  No new URLs to update in the database.")
        return
        
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for url in urls:
        # Using the superior ON CONFLICT...DO UPDATE logic from your backup file
        cursor.execute('''
            INSERT INTO card_inventory (url, bank_name, first_discovered_date, last_verified_date, is_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                last_verified_date = excluded.last_verified_date,
                is_active = 1
        ''', (url, bank_name, current_datetime, current_datetime, 1))
    
    conn.commit()
    conn.close()
    print(f"  Database updated for {bank_name}.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    setup_database()
    for bank_name, url in bank_listing_urls.items():
        discovered_urls = discover_card_urls_from_listing(bank_name, url)
        update_database_with_urls(bank_name, discovered_urls)
        # We can add the polite delay back in when we run on all banks
    print("\n--- Discovery Agent has finished its run. ---")