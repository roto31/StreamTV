"""
Documentation and Troubleshooting API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documentation"])

# Get base directory (project root)
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Try to import markdown, fallback to simple conversion if not available
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown library not available, using basic markdown conversion")

def markdown_to_html(markdown_content: str) -> str:
    """Convert markdown to HTML with script link support"""
    if MARKDOWN_AVAILABLE:
        md = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc'])
        html_content = md.convert(markdown_content)
    else:
        # Basic markdown conversion
        import re
        html = markdown_content
        # Headers
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        # Code blocks
        html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
        # Bold
        html = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', html)
        # Lists
        html = re.sub(r'^\* (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        # Paragraphs
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = '<p>' + html + '</p>'
        html_content = html
    
    # Convert script links to interactive buttons
    import re
    # Pattern: [Run Script: script_id](script:script_id) or [script_name](script:script_id)
    script_pattern = r'<a href="script:([^"]+)">([^<]+)</a>'
    def replace_script_link(match):
        script_id = match.group(1)
        link_text = match.group(2)
        return f'<button class="troubleshooting-script-btn" data-script-id="{script_id}" onclick="runTroubleshootingScript(\'{script_id}\')"><span class="material-icons">play_arrow</span>{link_text}</button>'
    
    html_content = re.sub(script_pattern, replace_script_link, html_content)
    
    return html_content

# Documentation files mapping for macOS
DOCS_FILES_MACOS = {
    # Installation Guides
    "beginner": "INSTALL_MACOS.md",
    "installation": "INSTALL_MACOS.md",
    "quick_start": "QUICK_START.md",
    "path_independence": "PATH_INDEPENDENCE.md",
    
    # GUI Installers
    "gui_installer": "GUI_INSTALLER_README.md",
    "swiftui_installer": "SWIFTUI_INSTALLER_README.md",
    "swiftui_readme": "README_SWIFTUI.md",
    "swiftui_quick_start": "QUICK_START_SWIFTUI.md",
    "swiftui_build": "BUILD_SWIFTUI.md",
    
    # Troubleshooting
    "troubleshooting": "docs/TROUBLESHOOTING.md",
}

@router.get("/docs/{doc_type}", response_class=HTMLResponse)
async def get_documentation(doc_type: str, request: Request):
    """Get documentation page"""
    doc_file = DOCS_FILES_MACOS.get(doc_type)
    
    if doc_file:
        doc_path = BASE_DIR / doc_file
        if doc_path.exists():
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                
                html_content = markdown_to_html(markdown_content)
                
                # Get title from first h1 or use doc_type
                title_match = markdown_content.split('\n')[0] if markdown_content else None
                if title_match and title_match.startswith('#'):
                    title = title_match.replace('#', '').strip()
                else:
                    title = doc_type.replace('_', ' ').title()
                
                return templates.TemplateResponse(
                    "documentation.html",
                    {
                        "request": request,
                        "title": title,
                        "content": html_content,
                        "doc_type": doc_type
                    }
                )
            except Exception as e:
                logger.error(f"Error reading documentation file: {e}")
                raise HTTPException(status_code=500, detail=f"Error loading documentation: {str(e)}")
    
    # If not found, return a placeholder
    return templates.TemplateResponse(
        "documentation.html",
        {
            "request": request,
            "title": doc_type.replace('_', ' ').title(),
            "content": f"<h1>{doc_type.replace('_', ' ').title()}</h1><p>Documentation for {doc_type} is coming soon.</p>",
            "doc_type": doc_type
        }
    )

@router.get("/docs", response_class=HTMLResponse)
async def docs_index(request: Request):
    """Documentation index page"""
    return templates.TemplateResponse(
        "documentation.html",
        {
            "request": request,
            "title": "Documentation",
            "content": "<h1>StreamTV Documentation</h1><p>Select a documentation section from the sidebar.</p>",
            "doc_type": "index"
        }
    )

