import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urlparse
from time import sleep
import random

st.set_page_config(page_title="Canadian Business Scraper", layout="wide")

st.title("🇨🇦 Canadian Business Scraper")
st.markdown("Extract emails and contact info from Canadian business websites for outreach.")

query = st.text_input("Enter business type or keywords (e.g. marketing agency, dentist)")
location = st.text_input("Enter city or province (e.g. Toronto, Alberta)")
num_sites = st.slider("Number of websites to scan", 5, 50, 10)
run_scrape = st.button("Run Scrape")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(\\(?\\d{3}\\)?[\\s.-]?\\d{3}[\\s.-]?\\d{4})"

@st.cache_data(show_spinner=False)
def get_search_results(query, location, limit):
    results = []
    search_query = f"{query} {location} site:.ca"
    url = f"https://www.bing.com/search?q={search_query.replace(' ', '+')}"
    try:
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link['href']
            if href.startswith("http") and ".ca" in href:
                domain = urlparse(href).netloc
                if not any(d in domain for d in ["bing.com", "microsoft.com"]):
                    clean = href.split("?")[0]
                    results.append(clean)
                    if len(results) >= limit:
                        break
    except:
        pass
    return list(set(results))

def extract_info_from_site(url):
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        title = soup.title.string if soup.title else urlparse(url).netloc
        emails = re.findall(EMAIL_REGEX, text)
        phones = re.findall(PHONE_REGEX, text)
        emails = list(set([e for e in emails if not e.endswith(".png") and "@" in e and not any(bad in e for bad in [".jpg", ".css", ".svg"])]))
        phones = list(set(phones))
        return {
            "Business Name": title.strip(),
            "Website": url,
            "Email(s)": ", ".join(emails),
            "Phone(s)": ", ".join(phones)
        }
    except:
        return None

if run_scrape and query and location:
    with st.spinner("Scraping the web, please wait..."):
        urls = get_search_results(query, location, num_sites)
        results = []
        for i, site in enumerate(urls):
            st.text(f"Scanning: {site}")
            info = extract_info_from_site(site)
            if info and (info['Email(s)'] or info['Phone(s)']):
                results.append(info)
            sleep(random.uniform(1, 2.5))

        if results:
            df = pd.DataFrame(results)
            st.success(f"Found contact info from {len(df)} businesses.")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "business_contacts.csv", "text/csv")
        else:
            st.warning("No contact info found from scanned websites.")

elif run_scrape:
    st.warning("Please enter both a search query and a location.")
