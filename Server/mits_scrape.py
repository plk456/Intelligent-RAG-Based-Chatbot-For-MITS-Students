import os
import requests
from bs4 import BeautifulSoup
import re

def url_to_filename(url: str) -> str:
    """
    Generates a safe filename based on the URL, preserving fragment identifiers.
    """
    temp = url.replace("https://mits.ac.in/", "").replace("http://mits.ac.in/", "")
    filename = temp.replace("#", "_").replace("/", "_").rstrip('_')
    if not filename or url in ("https://mits.ac.in", "http://mits.ac.in", "https://mits.ac.in/"):
        return "home.txt"
    filename = filename + ".txt"
    # sanitize filename
    filename = "".join(c for c in filename if c.isalnum() or c in ('_', '.', '-'))
    return filename

def scrape_website_text(url: str) -> str:
    """
    Fetches the content of a URL, parses the HTML, and extracts the main visible text.
    """
    try:
        print(f"Fetching content from: {url}")
        # Add User-Agent header to resemble a standard browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return ""

    soup = BeautifulSoup(response.content, 'html.parser')

    # Remove script, style, header, footer, and navigation elements, as they clutter the text data
    for element in soup(["script", "style", "header", "footer", "nav", ".carousel-inner", ".navbar"]):
        element.decompose()

    text_parts = []
    # Use find_all to get all instances of these tags
    for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'li', 'td', 'a']):
        content = ' '.join(element.get_text().split())
        
        # Only keep content that is significant (e.g., more than 20 characters to keep shorter list elements and headings)
        if content and len(content) > 20:
             text_parts.append(content)
             
    full_text = "\n\n".join(text_parts)
    full_text = re.sub(r'\n\s*\n', '\n\n', full_text) # Collapse excessive newlines

    return full_text.strip()

def main():
    # Find project root directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(script_dir, "newmits_dataset", "links.txt")):
        root_dir = script_dir
    elif os.path.exists(os.path.join(os.path.dirname(script_dir), "newmits_dataset", "links.txt")):
        root_dir = os.path.dirname(script_dir)
    else:
        root_dir = script_dir

    links_file_path = os.path.join(root_dir, "newmits_dataset", "links.txt")
    dataset_dir = os.path.join(root_dir, "newmits_dataset")
    os.makedirs(dataset_dir, exist_ok=True)

    if not os.path.exists(links_file_path):
        print(f"Error: links.txt not found at {links_file_path}")
        return

    # Read links and clean them
    urls = []
    with open(links_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            urls.append(line)

    # Scrape all URLs listed in links.txt (without base URL deduplication)
    print(f"Found {len(urls)} URLs to scrape.")

    all_scraped_contents = []

    for index, url in enumerate(urls, 1):
        print(f"\n[{index}/{len(urls)}] Processing {url}...")
        scraped_data = scrape_website_text(url)
        
        if scraped_data:
            filename = url_to_filename(url)
            output_file_path = os.path.join(dataset_dir, filename)
            
            with open(output_file_path, "w", encoding="utf-8") as out_f:
                out_f.write(scraped_data)
            print(f"Saved {len(scraped_data)} characters to {output_file_path}")
            
            # Keep trace for combined file
            all_scraped_contents.append(f"=== Source: {url} ===\n\n{scraped_data}\n\n")
        else:
            print(f"Failed to scrape content for {url}")

    # Save combined dataset file for RAG application
    if all_scraped_contents:
        combined_file_path = os.path.join(dataset_dir, "combined_scraped_data.txt")
        with open(combined_file_path, "w", encoding="utf-8") as comb_f:
            comb_f.writelines(all_scraped_contents)
        print(f"\nSuccessfully saved combined data to {combined_file_path}")

if __name__ == "__main__":
    main()