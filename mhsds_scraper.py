import os
import requests
from bs4 import BeautifulSoup
import zipfile
import io
import subprocess
import pandas as pd
import glob

# Folder to store CSVs
DATA_DIR = "mhsds_data"
os.makedirs(DATA_DIR, exist_ok=True)

# NHS index page
BASE_URL = "https://digital.nhs.uk/data-and-information/publications/statistical/mental-health-services-monthly-statistics"

def get_all_monthly_pages():
    print("🔍 Fetching all monthly publication page URLs...")
    res = requests.get(BASE_URL)
    soup = BeautifulSoup(res.text, "html.parser")

    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href.startswith("/data-and-information/publications/statistical/mental-health-services-monthly-statistics/"):
            if any(year in href for year in ["2024", "2025"]):
                full_url = "https://digital.nhs.uk" + href
                links.append(full_url)

    links = list(set(links))
    print(f"✅ Found {len(links)} monthly pages from 2024 onward.")
    return links

def is_relevant_filename(filename):
    name = filename.lower()
    return (
        ("mhsds" in name and "4ww" in name and "perf" in name)
        and ("2024" in name or "2025" in name)
        and (name.endswith(".csv") or name.endswith(".zip"))
    )

def get_data_links_from_monthly_page(url):
    print(f"🔎 Checking page: {url}")
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
        print(f"❌ Failed to parse {url}: {e}")
    return links

def download_and_extract(link):
    filename = link.split("/")[-1]
    filepath = os.path.join(DATA_DIR, filename)

    if os.path.exists(filepath) or any(filename.replace(".zip", ".csv") in f for f in os.listdir(DATA_DIR)):
        print(f"⏩ Already downloaded or extracted: {filename}")
        return

    print(f"⬇️ Downloading: {filename}")
    try:
        response = requests.get(link)
        if link.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                for zip_info in z.infolist():
                    if zip_info.filename.endswith(".csv"):
                        print(f"📦 Extracting: {zip_info.filename}")
                        z.extract(zip_info, DATA_DIR)
        else:
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"✅ Saved: {filepath}")
    except Exception as e:
        print(f"❌ Failed to download or extract {filename}: {e}")

def cleanup_zips():
    for file in os.listdir(DATA_DIR):
        if file.endswith(".zip"):
            path = os.path.join(DATA_DIR, file)
            try:
                os.remove(path)
                print(f"🗑️ Deleted ZIP: {file}")
            except Exception as e:
                print(f"❌ Failed to delete ZIP {file}: {e}")

def merge_csvs(output_path):
    print("🔄 Merging all CSVs into one file...")

    # Recursively find all CSVs in subfolders too
    csv_files = glob.glob(os.path.join(DATA_DIR, "**", "*.csv"), recursive=True)
    merged_data = []

    for file in csv_files:
        if os.path.basename(file).lower() == "merged_data.csv":
            continue  # Avoid merging the merged file
        try:
            df = pd.read_csv(file)
            df["source_file"] = os.path.relpath(file, DATA_DIR)
            merged_data.append(df)
        except Exception as e:
            print(f"⚠️ Skipped {file} due to error: {e}")

    if merged_data:
        final_df = pd.concat(merged_data, ignore_index=True)
        final_df.to_csv(output_path, index=False)
        print(f"✅ Merged {len(csv_files)} files into: {output_path}")
    else:
        print("⚠️ No valid CSVs to merge.")

def git_commit_push():
    try:
        subprocess.run(["git", "add", DATA_DIR], check=True)
        subprocess.run(["git", "commit", "-m", "🔁 Auto update: MHSDS data files"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Auto pushed updates to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")

def main():
    monthly_pages = get_all_monthly_pages()
    all_download_links = []
    for page_url in monthly_pages:
        links = get_data_links_from_monthly_page(page_url)
        all_download_links.extend(links)

    all_download_links = list(set(all_download_links))
    print(f"🔗 Total unique relevant files to download: {len(all_download_links)}")

    for link in all_download_links:
        download_and_extract(link)

    cleanup_zips()
    merge_csvs(os.path.join(DATA_DIR, "merged_data.csv"))
    git_commit_push()

if __name__ == "__main__":
    main()
