import requests
from bs4 import BeautifulSoup
import re

# The URL you want to scrape
URL_TO_SCRAPE = "https://mits.ac.in/university"

def scrape_website_text(url: str) -> str:
    """
    Fetches the content of a URL, parses the HTML, and extracts the main visible text.
    """
    try:
        # 1. Fetch the HTML content
        print(f"Fetching content from: {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return ""

    # 2. Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # 3. Clean the HTML
    # Remove script, style, header, footer, and navigation elements, as they clutter the text data
    for element in soup(["script", "style", "header", "footer", "nav", ".carousel-inner", ".navbar"]):
        element.decompose() # removes the tag and its contents

    # 4. Extract text from common content tags
    # Focus on elements that typically hold valuable text content (paragraphs, headings, list items)
    text_parts = []
    # Use find_all to get all instances of these tags
    for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'td', 'a']):
        # Clean up excessive whitespace, tabs, and newlines
        content = ' '.join(element.get_text().split())
        
        # Only keep content that is significant (e.g., more than 30 characters)
        if content and len(content) > 30:
             text_parts.append(content)
             
    # Combine all cleaned text parts into a single string
    full_text = "\n\n".join(text_parts)
    
    # 5. Final cleanup: remove extra newlines and specific patterns
    full_text = re.sub(r'\n\s*\n', '\n\n', full_text) # Collapse excessive newlines

    return full_text.strip()

# --- Execution ---
if __name__ == "__main__":
    scraped_data = scrape_website_text(URL_TO_SCRAPE)
    
    if scraped_data:
        print("\n--- Scraped Data Summary ---")
        print(f"Total characters extracted: {len(scraped_data)}")
        
        # Print the first 1000 characters of the scraped data for inspection
        print("\n--- First 1000 Characters ---")
        print(scraped_data[:1000] + "...") 
        
        # You can save this to a file for your RAG application:
        with open("home.txt", "w", encoding="utf-8") as f:
             f.write(scraped_data)
        print("\nData saved to ai_ml_faculty.txt")
    else:
        print("Scraping process failed or returned no text.")