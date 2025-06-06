from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional
import uvicorn
import requests
from bs4 import BeautifulSoup
import re
import json
import urllib.parse
import concurrent.futures

# Create FastAPI instance
app = FastAPI(
    title="Website Cloner API",
    description="API for cloning websites using BeautifulSoup",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class WebsiteCloneRequest(BaseModel):
    url: HttpUrl

class WebsiteCloneResponse(BaseModel):
    html: str
    css: List[Dict]
    assets: Dict
    message: str

def get_base_url(url: str) -> str:
    """Extract base URL from the given URL"""
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def extract_css_from_style(style_content: str, base_url: str) -> Dict:
    """Extract CSS rules from style content"""
    css_rules = {}
    try:
        # Extract @import rules first
        import_pattern = r'@import\s+url\([\'"]?([^\'"]+)[\'"]?\)'
        imports = re.findall(import_pattern, style_content)
        for import_url in imports:
            if not import_url.startswith(('http://', 'https://')):
                import_url = urllib.parse.urljoin(base_url, import_url)
            try:
                response = requests.get(import_url)
                if response.status_code == 200:
                    imported_rules = extract_css_from_style(response.text, base_url)
                    css_rules.update(imported_rules)
            except Exception as e:
                print(f"Error fetching imported CSS from {import_url}: {str(e)}")

        # Extract @keyframes
        keyframes_pattern = r'@keyframes\s+([^{]+){([^}]+)}'
        keyframes = re.finditer(keyframes_pattern, style_content)
        for match in keyframes:
            name = match.group(1).strip()
            content = match.group(2).strip()
            css_rules[f"@keyframes {name}"] = content

        # Extract regular CSS rules
        rule_pattern = r'([^{]+){([^}]+)}'
        matches = re.finditer(rule_pattern, style_content)
        
        for match in matches:
            selectors = match.group(1).strip()
            properties = match.group(2).strip()
            
            # Handle URLs in properties
            if 'url(' in properties:
                url_pattern = r'url\([\'"]?([^\'"]+)[\'"]?\)'
                urls = re.findall(url_pattern, properties)
                for url in urls:
                    if not url.startswith(('http://', 'https://', 'data:')):
                        properties = properties.replace(url, urllib.parse.urljoin(base_url, url))
            
            css_rules[selectors] = properties

    except Exception as e:
        print(f"Error parsing CSS: {str(e)}")
    
    return css_rules

def extract_css_from_file(css_url: str, base_url: str) -> Dict:
    """Extract CSS from external CSS file"""
    try:
        if not css_url.startswith(('http://', 'https://')):
            css_url = urllib.parse.urljoin(base_url, css_url)
        
        response = requests.get(css_url)
        if response.status_code == 200:
            return extract_css_from_style(response.text, base_url)
        return {}
    except Exception as e:
        print(f"Error fetching CSS from {css_url}: {str(e)}")
        return {}

def fetch_url(url: str) -> Optional[str]:
    """Fetch URL content with error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

def clean_empty_content(content: Dict) -> Dict:
    """Remove empty lists and dictionaries from content"""
    if isinstance(content, dict):
        return {
            k: clean_empty_content(v)
            for k, v in content.items()
            if v and (not isinstance(v, (list, dict)) or clean_empty_content(v))
        }
    elif isinstance(content, list):
        return [clean_empty_content(item) for item in content if item and (not isinstance(item, (list, dict)) or clean_empty_content(item))]
    return content

def extract_website_content(url: str) -> Dict:
    """Extract essential content from website"""
    try:
        # Fetch the webpage
        html_content = fetch_url(url)
        if not html_content:
            raise HTTPException(status_code=500, detail="Failed to fetch website content")
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        base_url = get_base_url(url)
        
        # Extract essential elements
        content = {
            "title": soup.title.string if soup.title else "",
            "meta": {
                "description": soup.find("meta", {"name": "description"})["content"] if soup.find("meta", {"name": "description"}) else "",
                "viewport": soup.find("meta", {"name": "viewport"})["content"] if soup.find("meta", {"name": "viewport"}) else "",
                "charset": soup.find("meta", {"charset": True})["charset"] if soup.find("meta", {"charset": True}) else "UTF-8"
            },
            "styles": [],
            "css_files": [],
            "structure": {},
            "assets": {
                "images": [],
                "background_images": [],
                "scripts": [],
                "fonts": [],
                "icons": []
            }
        }
        
        # Extract structure elements only if they exist and have content
        header = soup.find("header")
        if header and header.get_text(strip=True):
            content["structure"]["header"] = str(header)
            
        nav = soup.find("nav")
        if nav and nav.get_text(strip=True):
            content["structure"]["nav"] = str(nav)
            
        main = soup.find("main") or soup.find("body")
        if main and main.get_text(strip=True):
            content["structure"]["main"] = str(main)
            
        footer = soup.find("footer")
        if footer and footer.get_text(strip=True):
            content["structure"]["footer"] = str(footer)
        
        # Extract inline styles
        for style in soup.find_all("style"):
            if style.string:
                css_rules = extract_css_from_style(style.string, base_url)
                if css_rules:  # Only add non-empty CSS rules
                    content["styles"].append(css_rules)
                    
                    # Extract background images from CSS
                    for rules in css_rules.values():
                        bg_pattern = r'url\([\'"]?([^\'"]+)[\'"]?\)'
                        bg_images = re.findall(bg_pattern, rules)
                        for img in bg_images:
                            if not img.startswith(('http://', 'https://', 'data:')):
                                img = urllib.parse.urljoin(base_url, img)
                            content["assets"]["background_images"].append(img)
        
        # Extract external CSS files
        css_links = soup.find_all("link", rel="stylesheet")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_css = {
                executor.submit(extract_css_from_file, link["href"], base_url): link["href"]
                for link in css_links if link.get("href")
            }
            for future in concurrent.futures.as_completed(future_to_css):
                css_url = future_to_css[future]
                try:
                    css_content = future.result()
                    if css_content:  # Only add non-empty CSS content
                        content["css_files"].append({
                            "url": css_url,
                            "rules": css_content
                        })
                except Exception as e:
                    print(f"Error processing CSS file {css_url}: {str(e)}")
        
        # Extract assets
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(base_url, src)
            img_data = {
                "src": src,
                "alt": img.get("alt", ""),
                "class": img.get("class", []),
                "id": img.get("id", ""),
                "style": img.get("style", "")
            }
            # Only add image if it has meaningful data
            if any(v for v in img_data.values() if v):
                content["assets"]["images"].append(img_data)
        
        # Extract icons
        for link in soup.find_all("link", rel=lambda x: x and "icon" in x.lower()):
            if link.get("href"):
                href = link["href"]
                if not href.startswith(('http://', 'https://')):
                    href = urllib.parse.urljoin(base_url, href)
                icon_data = {
                    "href": href,
                    "type": link.get("type", ""),
                    "sizes": link.get("sizes", "")
                }
                # Only add icon if it has meaningful data
                if any(v for v in icon_data.values() if v):
                    content["assets"]["icons"].append(icon_data)
        
        # Extract scripts
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(base_url, src)
            content["assets"]["scripts"].append(src)
        
        # Extract font families from CSS
        font_pattern = r'font-family:\s*([^;]+)'
        for style in content["styles"]:
            for rules in style.values():
                fonts = re.findall(font_pattern, rules)
                content["assets"]["fonts"].extend(fonts)
        
        # Remove duplicates
        content["assets"]["fonts"] = list(set(content["assets"]["fonts"]))
        content["assets"]["background_images"] = list(set(content["assets"]["background_images"]))
        
        # Clean up empty content
        cleaned_content = clean_empty_content(content)
        
        # Remove empty meta fields
        if "meta" in cleaned_content:
            cleaned_content["meta"] = {k: v for k, v in cleaned_content["meta"].items() if v}
            if not cleaned_content["meta"]:
                del cleaned_content["meta"]
        
        return cleaned_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting website content: {str(e)}")

@app.post("/clone-website", response_model=WebsiteCloneResponse)
async def clone_website(request: WebsiteCloneRequest):
    """Endpoint to clone a website"""
    try:
        # Extract website content
        content = extract_website_content(str(request.url))
        
        # Only include non-empty structure
        structure = content.get("structure", {})
        if not structure:
            structure = {"main": str(BeautifulSoup(fetch_url(str(request.url)), 'html.parser').find("body"))}
        
        return WebsiteCloneResponse(
            html=json.dumps(structure, indent=2),
            css=content.get("styles", []) + content.get("css_files", []),
            assets=content.get("assets", {}),
            message="Website content extracted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "website-cloner-api"}

def main():
    """Run the application"""
    uvicorn.run(
        "hello:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
