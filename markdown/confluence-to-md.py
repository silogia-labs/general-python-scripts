#!/usr/bin/env python3
"""
Confluence Space -> Markdown exporter

Requirements:
  pip install -r requirements.txt
  pandoc installed (preferred) or pypandoc

Run:
  python confluence-to-md.py --space <SPACE_KEY>
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
import time
import urllib.parse
from typing import Dict, List, Optional

import requests
import yaml
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

# Attempt to import pypandoc
try:
    import pypandoc
except ImportError:
    pypandoc = None

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

class ConfluenceExporter:
    def __init__(self, base_url: str, space_key: str, username: str, token: str, output_dir: str, use_pypandoc: bool = False):
        self.base_url = base_url.rstrip("/")
        self.space_key = space_key
        self.output_dir = output_dir
        self.use_pypandoc = use_pypandoc
        
        # Configuration
        self.page_fetch_limit = 50
        self.sleep_between_requests = 0.1
        
        # Session setup
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, token)
        self.session.headers.update({"Accept": "application/json"})

    def ensure_dir(self, path: str):
        os.makedirs(path, exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """Sanitize filename to prevent directory traversal and invalid characters."""
        name = name.strip()
        # Remove invalid chars
        name = re.sub(r'[\\/*?:"<>|]', "_", name)
        # Remove control chars
        name = "".join(c for c in name if c.isprintable())
        # Truncate
        return name[:200]

    def fetch_all_pages(self) -> List[Dict]:
        pages = []
        start = 0
        logger.info(f"Fetching pages for space: {self.space_key}")
        while True:
            url = f"{self.base_url}/rest/api/content"
            params = {
                "spaceKey": self.space_key,
                "type": "page",
                "limit": self.page_fetch_limit,
                "start": start,
                "expand": "ancestors"
            }
            try:
                r = self.session.get(url, params=params)
                r.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Failed to fetch pages listing: {e}")
                raise

            data = r.json()
            results = data.get("results", [])
            pages.extend(results)
            logger.info(f"Fetched {len(results)} pages (Total: {len(pages)})...")
            
            if data.get("_links", {}).get("next"):
                start += self.page_fetch_limit
                time.sleep(self.sleep_between_requests)
            else:
                break
        return pages

    def fetch_page_details(self, page_id: str) -> Dict:
        url = f"{self.base_url}/rest/api/content/{page_id}"
        params = {"expand": "body.storage,version,ancestors,metadata.labels"}
        try:
            r = self.session.get(url, params=params)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch page details {page_id}: {e}")
            raise

    def fetch_attachments(self, page_id: str) -> List[Dict]:
        atts = []
        start = 0
        while True:
            url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment"
            params = {"limit": 50, "start": start}
            try:
                r = self.session.get(url, params=params)
                r.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch attachments for page {page_id}: {e}")
                break

            j = r.json()
            atts.extend(j.get("results", []))
            
            if j.get("_links", {}).get("next"):
                start += 50
                time.sleep(self.sleep_between_requests)
            else:
                break
        return atts

    def download_attachment(self, att: Dict, save_dir: str) -> Optional[str]:
        dl_path = att.get("_links", {}).get("download")
        if not dl_path:
            return None
        
        full_url = urllib.parse.urljoin(self.base_url, dl_path)
        filename = self.sanitize_filename(att.get("title") or os.path.basename(dl_path))
        
        self.ensure_dir(save_dir)
        final_path = os.path.join(save_dir, filename)
        
        # Path traversal check
        if not os.path.abspath(final_path).startswith(os.path.abspath(save_dir)):
            logger.warning(f"Skipping attachment with unsafe filename: {filename}")
            return None

        try:
            with self.session.get(full_url, stream=True) as r:
                r.raise_for_status()
                with open(final_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return final_path
        except Exception as e:
            logger.error(f"Attachment download failed ({full_url}): {e}")
            return None

    def convert_html_to_markdown(self, html_text: str, dest_path: str):
        # Temp file
        tmp_html = dest_path + ".tmp.html"
        self.ensure_dir(os.path.dirname(dest_path))
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_text)

        # 1. Try system pandoc
        pandoc_cmd = ["pandoc", tmp_html, "-f", "html", "-t", "gfm", "-o", dest_path]
        success = False
        try:
            subprocess.run(pandoc_cmd, check=True, capture_output=True)
            success = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 2. Try pypandoc if enabled/available
            if self.use_pypandoc and pypandoc:
                try:
                    pypandoc.convert_text(html_text, "gfm", format="html", outputfile=dest_path)
                    success = True
                except Exception as e:
                    logger.warning(f"pypandoc conversion failed: {e}")
            
        if not success:
            logger.warning(f"Pandoc unavailable/failed for {dest_path}. Falling back to strip-tags.")
            text = BeautifulSoup(html_text, "html.parser").get_text("\n\n")
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(text)
        
        if os.path.exists(tmp_html):
            os.remove(tmp_html)

    def build_id_to_path_map(self, all_pages: List[Dict]) -> Dict[str, str]:
        mapping = {}
        # First pass: map ID to its simple title-based filename
        # Confluence ancestors list is usually complete if expand=ancestors was used
        
        for p in all_pages:
            pid = p["id"]
            ancestors = p.get("ancestors", [])
            
            # Build relative directory path based on ancestors
            parts = [self.sanitize_filename(a.get("title", "")) for a in ancestors if a.get("title")]
            title = self.sanitize_filename(p.get("title", f"page_{pid}"))
            
            rel_dir = os.path.join(*parts) if parts else ""
            rel_path = os.path.join(rel_dir, f"{title}.md")
            
            # Simple conflict resolution
            if rel_path in mapping.values():
                rel_path = os.path.join(rel_dir, f"{title}-{pid}.md")
            
            mapping[pid] = rel_path
            
        return mapping

    def rewrite_content(self, html_content: str, page_id: str, id_to_path: Dict[str, str], attachments_dirname: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Images
        # <ac:image><ri:attachment ri:filename="..."/></ac:image>
        for ac_image in soup.find_all('ac:image'):
            ri = ac_image.find('ri:attachment')
            if ri and ri.get('ri:filename'):
                filename = self.sanitize_filename(ri['ri:filename'])
                new_img = soup.new_tag("img", src=os.path.join(attachments_dirname, filename))
                ac_image.replace_with(new_img)
            else:
                ri_url = ac_image.find('ri:url')
                if ri_url and ri_url.get('ri:value'):
                    new_img = soup.new_tag("img", src=ri_url['ri:value'])
                    ac_image.replace_with(new_img)

        # 2. Internal Page Links
        # <ac:link><ri:page ri:page-id="..."/></ac:link>
        for ac_link in soup.find_all('ac:link'):
            ri_page = ac_link.find('ri:page')
            if ri_page:
                target_pid = ri_page.get('ri:page-id') or ri_page.get('ri:content-title')
                text = ac_link.get_text()
                
                if target_pid and target_pid in id_to_path:
                    # Calculate relative path from current page to target
                    curr_path = id_to_path.get(page_id)
                    target_path = id_to_path[target_pid]
                    
                    if curr_path:
                        rel = os.path.relpath(target_path, start=os.path.dirname(curr_path))
                    else:
                        rel = os.path.basename(target_path)
                        
                    if not text.strip():
                        # Fallback title if text empty
                        text = os.path.splitext(os.path.basename(target_path))[0]
                        
                    new_a = soup.new_tag("a", href=rel)
                    new_a.string = text
                    ac_link.replace_with(new_a)
                else:
                    ac_link.replace_with(text)

        # 3. Standard Links (href="/wiki/...")
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Page ID links
            m_pid = re.search(r'pageId=(\d+)', href)
            if m_pid:
                target_pid = m_pid.group(1)
                if target_pid in id_to_path:
                    curr_path = id_to_path.get(page_id)
                    target_path = id_to_path[target_pid]
                    rel = os.path.relpath(target_path, start=os.path.dirname(curr_path)) if curr_path else target_path
                    a['href'] = rel
            
            # Attachment links
            m_att = re.search(r'/download/attachments/[^/]+/([^/?#]+)', href)
            if m_att:
                filename = self.sanitize_filename(m_att.group(1))
                a['href'] = os.path.join(attachments_dirname, filename)

        # 4. Standard Images pointing to attachments
        for img in soup.find_all('img', src=True):
            src = img['src']
            m = re.search(r'/download/attachments/[^/]+/([^/?#]+)', src)
            if m:
                filename = self.sanitize_filename(m.group(1))
                img['src'] = os.path.join(attachments_dirname, filename)

        # 5. Clean Macros
        for macro in soup.find_all(re.compile(r'^ac:')):
            try:
                text = macro.get_text(separator=" ")
                macro.replace_with(text)
            except Exception:
                macro.decompose()
                
        return str(soup)

    def add_front_matter(self, md_path: str, meta: Dict):
        fm = {
            "title": meta.get("title"),
            "id": meta.get("id"),
            "labels": meta.get("labels", []),
            "version": meta.get("version"),
            # "created": meta.get("created"),
        }
        yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
        
        with open(md_path, "r+", encoding="utf-8") as f:
            content = f.read()
            f.seek(0, 0)
            f.write("---\n" + yaml_text + "\n---\n\n" + content)

    def run(self):
        self.ensure_dir(self.output_dir)
        
        # 1. Fetch List
        all_pages = self.fetch_all_pages()
        logger.info(f"Total pages to process: {len(all_pages)}")
        
        # 2. Map IDs to Paths
        id_to_relpath = self.build_id_to_path_map(all_pages)
        
        # 3. Process Pages
        for idx, p in enumerate(all_pages, 1):
            pid = p["id"]
            title = p.get("title", "Untitled")
            logger.info(f"[{idx}/{len(all_pages)}] Processing: {title} ({pid})")
            
            try:
                # Fetch full content
                full = self.fetch_page_details(pid)
                storage = full.get("body", {}).get("storage", {}).get("value", "")
                
                # Metadata
                lbls = full.get("metadata", {}).get("labels", {}).get("results", [])
                labels = [l.get("name") for l in lbls if l.get("name")]
                
                # Paths
                rel_md_path = id_to_relpath.get(pid, f"{pid}.md")
                abs_md_path = os.path.join(self.output_dir, rel_md_path)
                page_dir_abs = os.path.dirname(abs_md_path)
                self.ensure_dir(page_dir_abs)
                
                # Attachments
                # We store attachments in a subfolder named "_attachments/{pid}" relative to the page's directory
                att_rel_dir = f"_attachments/{pid}" 
                att_abs_path = os.path.join(page_dir_abs, "_attachments", pid)
                
                page_attachments = self.fetch_attachments(pid)
                if page_attachments:
                    self.ensure_dir(att_abs_path)
                    for att in page_attachments:
                        self.download_attachment(att, att_abs_path)
                
                # Rewrite HTML
                rewritten_html = self.rewrite_content(storage, pid, id_to_relpath, att_rel_dir)
                
                # Wrap for pandoc stability
                wrapped_html = f"<div>\n{rewritten_html}\n</div>"
                
                # Convert
                self.convert_html_to_markdown(wrapped_html, abs_md_path)
                
                # Front matter
                meta = {
                    "title": title,
                    "id": pid,
                    "labels": labels,
                    "version": full.get("version", {}).get("number"),
                }
                self.add_front_matter(abs_md_path, meta)
                
                time.sleep(self.sleep_between_requests)
                
            except Exception as e:
                logger.error(f"Error processing page {pid} ({title}): {e}", exc_info=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Export Confluence Space to Markdown")
    parser.add_argument("--url", default=os.getenv("CONFLUENCE_URL"), help="Confluence Base URL")
    parser.add_argument("--space", required=True, help="Space Key to export")
    parser.add_argument("--email", default=os.getenv("CONFLUENCE_EMAIL"), help="Auth Email (default: env CONFLUENCE_EMAIL)")
    parser.add_argument("--token", default=os.getenv("CONFLUENCE_API_TOKEN"), help="API Token (default: env CONFLUENCE_API_TOKEN)")
    parser.add_argument("--output", default="confluence_export", help="Output directory")
    parser.add_argument("--pypandoc", action="store_true", help="Use pypandoc library instead of pandoc CLI")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    if not args.email or not args.token:
        # Check if running interactively or print help
        logger.error("Email and Token are required. Set via arguments or CONFLUENCE_EMAIL / CONFLUENCE_API_TOKEN env vars.")
        sys.exit(1)
        
    exporter = ConfluenceExporter(
        base_url=args.url,
        space_key=args.space,
        username=args.email,
        token=args.token,
        output_dir=args.output,
        use_pypandoc=args.pypandoc
    )
    
    exporter.run()

if __name__ == "__main__":
    main()
