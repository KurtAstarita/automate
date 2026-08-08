import os
import sys
import glob
import json
from bs4 import BeautifulSoup

def audit_html_file(file_path):
    issues = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # 1. Check Title Tag
    title = soup.find("title")
    if not title or not title.text.strip():
        issues.append("❌ Missing or empty  tag.")
    elif len(title.text) < 20 or len(title.text) > 70:
        issues.append(f"⚠️ Title length ({len(title.text)} chars) outside recommended 20-70 range: '{title.text}'")

    # 2. Check Meta Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not meta_desc or not meta_desc.get("content", "").strip():
        issues.append("❌ Missing or empty meta description.")
    else:
        desc_len = len(meta_desc["content"])
        if desc_len < 50 or desc_len > 160:
            issues.append(f"⚠️ Meta description length ({desc_len} chars) outside 50-160 char range.")

    # 3. Check Image Alt Attributes
    images = soup.find_all("img")
    for img in images:
        src = img.get("src", "unknown")
        alt = img.get("alt")
        if alt is None or not alt.strip():
            issues.append(f"❌ Image missing alt text: {src}")

    # 4. Check JSON-LD Structured Data Syntax
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    if not json_ld_scripts:
        issues.append("⚠️ No JSON-LD structured data found.")
    else:
        for idx, script in enumerate(json_ld_scripts):
            try:
                json.loads(script.string)
            except (json.JSONDecodeError, TypeError) as e:
                issues.append(f"❌ Malformed JSON-LD block #{idx + 1}: {e}")

    # 5. Check Internal Links
    links = soup.find_all("a", href=True)
    for link in links:
        href = link["href"]
        if href == "#" or href == "":
            issues.append(f"❌ Found empty or placeholder anchor link: {link.prettify()}")

    return issues

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    html_files = glob.glob(f"{target_dir}/**/*.html", recursive=True)
    
    if not html_files:
        print(f"No HTML files found in '{target_dir}'. Skipping audit.")
        sys.exit(0)

    total_issues = 0
    print(f"🔍 Auditing {len(html_files)} HTML file(s)...")

    for file_path in html_files:
        print(f"\nScanning: {file_path}")
        issues = audit_html_file(file_path)
        if issues:
            total_issues += len(issues)
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✅ All SEO checks passed!")

    if total_issues > 0:
        print(f"\n❌ SEO Audit Failed with {total_issues} issue(s). Fix errors before merging.")
        sys.exit(1)
    else:
        print("\n🎉 SEO Gate Passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
