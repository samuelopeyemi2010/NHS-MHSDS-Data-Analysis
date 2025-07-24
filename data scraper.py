import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime
from git import Repo

# Target website URL
base_url = "https://digital.nhs.uk/data-and-information/publications/statistical/mental-health-services-monthly-statistics"


def find_data_files():
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links containing "MHSDS Monthly: Performance" and "Referral Spells"
    data_links = []
    for link in soup.find_all('a'):
        href = link.get('href')
        text = link.get_text()
        if "MHSDS Monthly: Performance" in text and "Referral Spells" in text:
            full_url = f"https://digital.nhs.uk{href}" if href.startswith('/') else href
            data_links.append((text.strip(), full_url))
    
    return data_links


def download_new_files(data_links):
    downloaded_files = []
    
    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')
    
    for name, url in data_links:
        # Extract month/year from filename
        # Example: "MHSDS Monthly: Performance April 2024 Referral Spells"
        try:
            month_year = ' '.join(name.split()[3:5])  # Gets "April 2024"
            file_date = datetime.strptime(month_year, "%B %Y")
            filename = f"data/mental_health_{file_date.strftime('%m-%Y')}.csv"
            
            # Only download if file doesn't exist
            if not os.path.exists(filename):
                print(f"Downloading {name}...")
                data = requests.get(url)
                with open(filename, 'wb') as f:
                    f.write(data.content)
                downloaded_files.append(filename)
        except Exception as e:
            print(f"Error processing {name}: {e}")
    
    return downloaded_files


def update_github():
    repo = Repo('.')  # Assumes script is in repo root
    repo.git.add('data/')
    repo.index.commit(f"Automated update: {datetime.now().strftime('%d-%m-%Y')}")
    origin = repo.remote(name='origin')
    origin.push()


if __name__ == "__main__":
    print("Starting automated data collection...")
    data_files = find_data_files()
    new_files = download_new_files(data_files)
    
    if new_files:
        print(f"Downloaded {len(new_files)} new files")
        update_github()
        print("GitHub repository updated")
    else:
        print("No new files found")    