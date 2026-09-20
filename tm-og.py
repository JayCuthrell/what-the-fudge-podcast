import subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def get_open_chrome_urls():
    """
    Uses macOS AppleScript to get the URL of every open tab in Google Chrome.
    """
    applescript = """
    set urlList to ""
    tell application "Google Chrome"
        set window_list to every window
        repeat with the_window in window_list
            set tab_list to every tab in the_window
            repeat with the_tab in tab_list
                set the_url to the URL of the_tab
                set urlList to urlList & the_url & "\\n"
            end repeat
        end repeat
    end tell
    return urlList
    """
    
    # Run the AppleScript using the command line
    result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error communicating with Chrome: {result.stderr}")
        return []
        
    # Split the result by newlines and remove any empty lines
    urls = [url.strip() for url in result.stdout.split('\n') if url.strip()]
    return urls

def extract_techmeme_item(tm_url):
    """
    Fetches a Techmeme permalink and extracts the OG tags 
    and the primary linked article using Techmeme's specific 'ourh' class.
    """
    parsed_url = urlparse(tm_url)
    anchor_id = parsed_url.fragment

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(tm_url, headers=headers, timeout=10)
        response.raise_for_status() 
        
        # Record the clean URL for the Markdown formatting
        final_url_clean = response.url
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # Pick up the OG Title
        og_title_tag = soup.find("meta", property="og:title")
        og_title = og_title_tag["content"] if og_title_tag else None

        # Pick up the URL and Title for the linked article
        linked_article_url = None

        if anchor_id:
            anchor_element = soup.find(id=anchor_id) or soup.find("a", attrs={"name": anchor_id})
            
            if anchor_element:
                headline_link = anchor_element.find_next("a", class_="ourh")
                if headline_link:
                    linked_article_url = headline_link.get('href')

        return {
            "2_og_title": og_title,
            "4_linked_article_url": linked_article_url,
            "6_final_url": final_url_clean
        }

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("Fetching open tabs from Google Chrome...\n")
    all_urls = get_open_chrome_urls()
    
    # Filter to only grab Techmeme permalinks (must contain techmeme.com and a fragment identifier '#')
    techmeme_urls = [url for url in all_urls if 'techmeme.com' in url and '#' in url]
    
    print(f"Found {len(techmeme_urls)} Techmeme permalink(s) in your open Chrome tabs.")
    print("Extracting data... (this will take a few seconds)\n")
    
    markdown_output = []
    
    # Loop through all found tabs
    for url in techmeme_urls:
        item = extract_techmeme_item(url)
        
        if "error" in item:
            print(f"  [!] Skipped {url} due to error: {item['error']}")
            continue
            
        # Fallbacks just in case the scrape misses something
        og_title = item.get("2_og_title") or "Title not found"
        linked_url = item.get("4_linked_article_url") or "#"
        meta_url = item.get("6_final_url") or url
        
        # Build the exact string you requested
        markdown_line = f"* [{og_title}]({linked_url}) and [meta coverage]({meta_url})"
        markdown_output.append(markdown_line)
        
    print("--- Final Markdown Output ---\n")
    for line in markdown_output:
        print(line)
    print("\n-----------------------------")