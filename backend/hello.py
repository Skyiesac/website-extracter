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
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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

class GeminiResponse(BaseModel):
    html: str
    message: str

def get_base_url(url: str) -> str:
    """Extract base URL from the given URL"""
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def extract_css_from_style(style_content: str, base_url: str) -> str:
    """Extract CSS rules from style content and return as a single string"""
    try:
        # Extract @import rules first
        import_pattern = r'@import\s+url\([\'"]?([^\'"]+)[\'"]?\)'
        imports = re.findall(import_pattern, style_content)
        css_content = []
        
        for import_url in imports:
            if not import_url.startswith(('http://', 'https://')):
                import_url = urllib.parse.urljoin(base_url, import_url)
            try:
                response = requests.get(import_url)
                if response.status_code == 200:
                    css_content.append(response.text)
            except Exception as e:
                print(f"Error fetching imported CSS from {import_url}: {str(e)}")

        # Add the original style content
        css_content.append(style_content)
        
        # Join all CSS content
        return '\n'.join(css_content)
    except Exception as e:
        print(f"Error parsing CSS: {str(e)}")
        return style_content

def extract_css_from_file(css_url: str, base_url: str) -> str:
    """Extract CSS from external CSS file and return as a string"""
    try:
        if not css_url.startswith(('http://', 'https://')):
            css_url = urllib.parse.urljoin(base_url, css_url)
        
        response = requests.get(css_url)
        if response.status_code == 200:
            return response.text
        return ""
    except Exception as e:
        print(f"Error fetching CSS from {css_url}: {str(e)}")
        return ""

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
        
        # Extract structure elements
        for tag in ['header', 'nav', 'main', 'footer']:
            element = soup.find(tag)
            if element:
                content["structure"][tag] = str(element)
        
        # If no main content found, use body
        if not content["structure"].get("main"):
            body = soup.find("body")
            if body:
                content["structure"]["main"] = str(body)
        
        # Extract inline styles
        for style in soup.find_all("style"):
            if style.string:
                css_content = extract_css_from_style(style.string, base_url)
                if css_content:
                    content["styles"].append(css_content)
        
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
                    if css_content:
                        content["css_files"].append({
                            "url": css_url,
                            "content": css_content
                        })
                except Exception as e:
                    print(f"Error processing CSS file {css_url}: {str(e)}")
        
        # Extract assets
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(base_url, src)
            content["assets"]["images"].append({
                "src": src,
                "alt": img.get("alt", ""),
                "class": img.get("class", []),
                "id": img.get("id", ""),
                "style": img.get("style", "")
            })
        
        # Extract icons
        for link in soup.find_all("link", rel=lambda x: x and "icon" in x.lower()):
            if link.get("href"):
                href = link["href"]
                if not href.startswith(('http://', 'https://')):
                    href = urllib.parse.urljoin(base_url, href)
                content["assets"]["icons"].append({
                    "href": href,
                    "type": link.get("type", ""),
                    "sizes": link.get("sizes", "")
                })
        
        # Extract scripts
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(base_url, src)
            content["assets"]["scripts"].append(src)
        
        # Extract font families from CSS
        font_pattern = r'font-family:\s*([^;]+)'
        for style in content["styles"]:
            fonts = re.findall(font_pattern, style)
            content["assets"]["fonts"].extend(fonts)
        
        # Remove duplicates
        content["assets"]["fonts"] = list(set(content["assets"]["fonts"]))
        
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting website content: {str(e)}")

def initialize_gemini():
    """Initialize Gemini API only when needed"""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        # Use gemini-1.5-flash which has better rate limits
        return genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Error configuring Google Gemini: {str(e)}")
        raise

def optimize_content_for_gemini(content: Dict) -> Dict:
    """Optimize content while preserving all styling"""
    optimized = {
        "title": content.get("title", ""),
        "meta": content.get("meta", {}),
        "structure": content.get("structure", {}),
        "assets": content.get("assets", {}),
        "styles": [],
        "css_files": []
    }
    
    # Process all styles
    for style in content.get("styles", []):
        if style:  # Only add non-empty styles
            optimized["styles"].append(style)
    
    # Process all CSS files
    for css_file in content.get("css_files", []):
        if css_file.get("content"):  # Only add files with content
            optimized["css_files"].append(css_file)
    
    return optimized

def generate_html_with_gemini(content: Dict) -> str:
    """Generate HTML code using Google Gemini"""
    try:
        logger.info("Initializing Gemini")
        model = initialize_gemini()
        
        # Prepare CSS content
        css_content = []
        
        # Add inline styles
        for style in content.get("styles", []):
            css_content.append(style)
        
        # Add external CSS files
        for css_file in content.get("css_files", []):
            css_content.append(f"/* CSS from {css_file['url']} */\n{css_file['content']}")
        
        # Combine all CSS
        combined_css = "\n".join(css_content)
        
        # Prepare the prompt for Gemini
        prompt = f"""
        You are an expert web developer. Your task is to generate a complete HTML code that is EXACTLY the same as the original website.
        The website must look 100% identical, including all styles, layout, and functionality.
        
        Website Data:
        {json.dumps(content, indent=2)}
        
        CSS Content:
        {combined_css}
        
        Requirements:
        1. Create a pixel-perfect clone of the original website
        2. Include ALL CSS exactly as provided above
        3. Maintain the EXACT structure and layout
        4. Include ALL assets (images, scripts, icons) with their original attributes
        5. Preserve ALL styling, including:
           - Colors
           - Fonts
           - Spacing
           - Animations
           - Transitions
           - Media queries
           - Custom properties
        6. Use absolute URLs for all resources
        7. Include all meta tags, title, and other head elements
        8. Preserve all JavaScript functionality
        9. Maintain responsive design
        10. Keep all original classes and IDs
        
        Important:
        - The output must be a complete, standalone HTML file
        - Start with <!DOCTYPE html> and end with </html>
        - Include all CSS in a <style> tag in the head section
        - Link to all external CSS files
        - Include all necessary scripts
        - Make sure all URLs are absolute
        - Preserve all original attributes and values
        - The website must look EXACTLY the same as the original
        - Do not add any extra newlines or formatting
        """

        logger.info("Sending request to Gemini")
        response = model.generate_content(
            prompt,
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ],
            generation_config={
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        
        if not response or not response.text:
            raise ValueError("Empty response from Gemini")
            
        logger.info("Received response from Gemini")
        
        # Extract the HTML code from the response
        html_code = response.text
        
        # Clean up the response
        html_code = re.sub(r'```html\n|```', '', html_code)
        html_code = re.sub(r'\n{3,}', '\n\n', html_code)  # Replace multiple newlines with double newlines
        
        if not html_code.strip():
            raise ValueError("Generated HTML code is empty")
            
        # Validate that the response is proper HTML
        if not html_code.strip().startswith('<!DOCTYPE html>'):
            raise ValueError("Generated code is not valid HTML")
            
        logger.info("Successfully generated HTML code")
        return html_code.strip()
        
    except Exception as e:
        logger.error(f"Error in generate_html_with_gemini: {str(e)}")
        if "quota" in str(e).lower() or "rate" in str(e).lower():
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again in a few minutes or upgrade your API plan at https://ai.google.dev/gemini-api/docs/rate-limits"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating HTML with Gemini: {str(e)}"
        )

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

@app.post("/generate-html", response_model=GeminiResponse)
async def generate_html(request: WebsiteCloneRequest):
    """Endpoint to generate HTML code using Gemini"""
    try:
        logger.info(f"Received request to generate HTML for URL: {request.url}")
        
        # First, get the website content using the existing endpoint
        logger.info("Extracting website content")
        content = extract_website_content(str(request.url))
        
        if not content:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract website content"
            )
            
        logger.info("Successfully extracted website content")
        
        # Generate HTML using Gemini
        logger.info("Generating HTML with Gemini")
        html_code = generate_html_with_gemini(content)
        
        logger.info("Successfully generated HTML code")
        return GeminiResponse(
            html=html_code,
            message="HTML code generated successfully"
        )
    except HTTPException as he:
        logger.error(f"HTTP Exception in generate_html: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_html: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

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
