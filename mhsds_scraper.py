import os
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import subprocess

# Directory for storing data
DATA_DIR = "mhsds_data"
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://digital.nhs.uk/data-and-information/publications/statistical/mental-health-services-monthly-statistics"

def get_all_monthly_pages():
    res = requests.get(BASE_URL)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href.startswith("/data-and-information/publications/statistical/mental-health-services-monthly-statistics/"):
            if any(year in href for year in ["2024", "2025"]):
                full_url = "https://digital.nhs.uk" + href
                links.append(full_url)

    return list(set(links))

def is_relevant_filename(filename):
    name = filename.lower()
    return (
        ("mhsds" in name and "4ww" in name and "perf" in name)
        and ("2024" in name or "2025" in name)
        and (name.endswith(".csv") or name.endswith(".zip"))
    )

def get_data_links_from_monthly_page(url):
    links = []
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            filename = href.split("/")[-1]
            if is_relevant_filename(filename):
                if href.startswith("/"):
                    href = "https://digital.nhs.uk" + href
                links.append(href)
    except Exception as e:
        print(f"❌ Failed to parse {url} | Error: {e}")
    return links

def download_and_extract(link):
    filename = link.split("/")[-1]
    filepath = os.path.join(DATA_DIR, filename)

    if os.path.exists(filepath) or any(filename.replace(".zip", ".csv") in f for f in os.listdir(DATA_DIR)):
        print(f"⏩ Already downloaded or extracted: {filename}")
        return

    try:
        response = requests.get(link)
        if link.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                for zip_info in z.infolist():
                    if zip_info.filename.endswith(".csv"):
                        extracted_name = os.path.basename(zip_info.filename)
                        out_path = os.path.join(DATA_DIR, extracted_name)
                        with open(out_path, "wb") as f:
                            f.write(z.read(zip_info))
                        print(f"📦 Extracted: {extracted_name}")
        else:
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"✅ Saved: {filepath}")
    except Exception as e:
        print(f"❌ Failed: {filename} | {e}")

def cleanup_zips():
    for file in os.listdir(DATA_DIR):
        if file.endswith(".zip"):
            try:
                os.remove(os.path.join(DATA_DIR, file))
                print(f"🗑️ Deleted ZIP: {file}")
            except Exception as e:
                print(f"❌ Couldn't delete {file}: {e}")

def remove_merged_data():
    merged_path = os.path.join(DATA_DIR, "merged_data.csv")
    if os.path.exists(merged_path):
        os.remove(merged_path)
        print("🧹 Removed old 'merged_data.csv'")

def git_commit_push():
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "🔁 Auto update: Removed merge file and updated dataset"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Changes pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")

def main():
    remove_merged_data()
    monthly_pages = get_all_monthly_pages()

    all_download_links = []
    for page_url in monthly_pages:
        all_download_links.extend(get_data_links_from_monthly_page(page_url))

    all_download_links = list(set(all_download_links))
    print(f"🔗 Total unique relevant files to download: {len(all_download_links)}")

    for link in all_download_links:
        download_and_extract(link)

    cleanup_zips()
    git_commit_push()

if __name__ == "__main__":
    main()
