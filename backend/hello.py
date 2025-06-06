import concurrent.futures
import json
import logging
import os
import re
import tempfile
import time
import urllib.parse
import uuid
from typing import Dict, List, Optional
import google.generativeai as genai
import requests
import uvicorn
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, HttpUrl
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI instance
app = FastAPI(
    title="Website Cloner API",
    description="API for cloning websites using BeautifulSoup and Playwright",
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
    is_small: bool = True

class WebsiteCloneResponse(BaseModel):
    html: str
    message: str
    preview_id: str

class GeminiResponse(BaseModel):
    html: str
    message: str

# Store generated HTML content with unique IDs
html_store = {}

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
        Generate complete HTML replicating this website. Minimize whitespace but preserve all functionality:

        Website: {json.dumps(content, indent=2)}
        CSS: {combined_css}

        Output: Complete standalone HTML file with inline CSS, absolute URLs, exact styling.
        Start with <!DOCTYPE html>, include full <head> and <body> sections.
        """
        # logger.info(prompt)
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

async def clone_with_playwright(url: str) -> str:
    """Clone website using Playwright with full resource capture"""
    try:
        async with async_playwright() as p:
            # Launch browser with specific settings
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            
            # Create context with specific settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                java_script_enabled=True
            )
            
            # Set default timeout
            context.set_default_timeout(60000)
            
            # Create a new page
            page = await context.new_page()
            
            try:
                # Enable request interception
                await page.route("**/*", lambda route: route.continue_())
                
                # Navigate to the URL and wait for network to be idle
                await page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Wait for the page to be fully loaded
                await page.wait_for_load_state('load', timeout=30000)
                
                # Wait for any lazy-loaded images
                await page.wait_for_load_state('domcontentloaded')
                
                # Inject script to capture all styles
                styles = await page.evaluate("""() => {
                    const styles = [];
                    // Get all stylesheets
                    for (const sheet of document.styleSheets) {
                        try {
                            const rules = sheet.cssRules || sheet.rules;
                            for (const rule of rules) {
                                styles.push(rule.cssText);
                            }
                        } catch (e) {
                            // Handle CORS errors
                            console.log('Could not access stylesheet:', e);
                        }
                    }
                    return styles;
                }""")
                
                # Get all inline styles
                inline_styles = await page.evaluate("""() => {
                    const styles = [];
                    const styleElements = document.getElementsByTagName('style');
                    for (const style of styleElements) {
                        styles.push(style.textContent);
                    }
                    return styles;
                }""")
                
                # Get all images and convert to base64
                images = await page.evaluate("""() => {
                    const images = [];
                    const imgElements = document.getElementsByTagName('img');
                    for (const img of imgElements) {
                        if (img.src) {
                            images.push({
                                src: img.src,
                                alt: img.alt,
                                style: img.getAttribute('style'),
                                class: img.className
                            });
                        }
                    }
                    return images;
                }""")
                
                # Get the final HTML content
                html_content = await page.content()
                
                # Create a BeautifulSoup object to modify the HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Add all captured styles to the head
                head = soup.find('head') or soup.new_tag('head')
                if not soup.find('head'):
                    soup.html.insert(0, head)
                
                # Add external stylesheets
                for style in styles:
                    style_tag = soup.new_tag('style')
                    style_tag.string = style
                    head.append(style_tag)
                
                # Add inline styles
                for style in inline_styles:
                    style_tag = soup.new_tag('style')
                    style_tag.string = style
                    head.append(style_tag)
                
                # Update image sources to be absolute
                for img in soup.find_all('img'):
                    if img.get('src'):
                        if not img['src'].startswith(('http://', 'https://')):
                            img['src'] = urllib.parse.urljoin(url, img['src'])
                
                # Add base styles to ensure proper rendering
                base_style = soup.new_tag('style')
                base_style.string = """
                    * { box-sizing: border-box; }
                    body { margin: 0; padding: 0; }
                    img { max-width: 100%; height: auto; }
                """
                head.append(base_style)
                
                # Convert back to string
                final_html = str(soup)
                
                return final_html
                
            except Exception as e:
                logger.error(f"Error during page navigation: {str(e)}")
                # If navigation fails, try to get whatever content is available
                try:
                    html_content = await page.content()
                    if html_content:
                        return html_content
                except:
                    pass
                raise
                
            finally:
                # Clean up
                await context.close()
                await browser.close()
                
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(
                status_code=504,
                detail="Website took too long to load. Please try again or use a different URL."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error cloning website with Playwright: {error_msg}"
        )

@app.post("/clone-website", response_model=WebsiteCloneResponse)
async def clone_website(request: WebsiteCloneRequest):
    """Endpoint to clone a website"""
    try:
        logger.info(f"Received request to clone website: {request.url} (is_small: {request.is_small})")
        
        if request.is_small:
            # For small websites, use Gemini
            logger.info("Using Gemini for small website")
            content = extract_website_content(str(request.url))
            html_code = generate_html_with_gemini(content)
        else:
            # For large websites, use Playwright
            logger.info("Using Playwright for large website")
            try:
                html_code = await clone_with_playwright(str(request.url))
            except HTTPException as he:
                # If Playwright fails, fall back to Gemini
                logger.warning(f"Playwright failed, falling back to Gemini: {str(he)}")
                content = extract_website_content(str(request.url))
                html_code = generate_html_with_gemini(content)
        
        # Generate a unique ID for this HTML content
        html_id = str(uuid.uuid4())
        html_store[html_id] = html_code
        
        # Create a temporary file to store the HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_code)
            temp_file_path = f.name
        
        logger.info(f"Successfully cloned website. HTML saved to: {temp_file_path}")
        
        return WebsiteCloneResponse(
            html=html_code,
            message=f"Website cloned successfully. HTML saved to: {temp_file_path}",
            preview_id=html_id
        )
    except HTTPException as he:
        logger.error(f"HTTP Exception in clone_website: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in clone_website: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

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

@app.get("/preview/{html_id}", response_class=HTMLResponse)
async def preview_html(html_id: str):
    """Endpoint to preview generated HTML"""
    if html_id not in html_store:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    html_content = html_store[html_id]
    
    # Check if the HTML content is empty or just contains basic structure
    soup = BeautifulSoup(html_content, 'html.parser')
    body_content = soup.body.get_text().strip() if soup.body else ""
    
    if not body_content:
        # Add a warning message to the HTML
        warning_div = soup.new_tag('div')
        warning_div['style'] = 'position: fixed; top: 0; left: 0; right: 0; background: #ff4444; color: white; padding: 1rem; text-align: center; z-index: 9999;'
        warning_div.string = 'Warning: The page appears to be empty. Try using the other website size option.'
        soup.body.insert(0, warning_div)
        html_content = str(soup)
    
    return HTMLResponse(content=html_content)

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
