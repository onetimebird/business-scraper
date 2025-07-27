import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from time import sleep
import random

# Streamlit app configuration
st.set_page_config(page_title="Canadian Business Listing Aggregator", layout="wide")

st.title("🇨🇦 Canadian Business Listing Aggregator")
st.markdown(
    "Aggregate business listings from YellowPages, Yelp, and Bing for your search term and location, "
    "with deduplication for a comprehensive list you can manually extract emails from."
)

# User inputs
query = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
location = st.text_input("City or province (e.g. Toronto, Alberta)")
num_listings = st.slider("Number of businesses to list", min_value=10, max_value=500, value=100)
run_scrape = st.button("🚀 Get Aggregated Listings")

# HTTP headers
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

@st.cache_data(show_spinner=False)
def fetch_yellowpages(query, location, limit):
    base = "https://www.yellowpages.ca"
    search_url = f"{base}/search/si/1/{query.replace(' ', '+')}/{location.replace(' ', '+')}"
    listings = []
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        tags = soup.find_all("a", class_="listing__name--link", href=True)
        for tag in tags[:limit]:
            name = tag.get_text(strip=True)
            href = tag['href']
            url = urljoin(base, href)
            listings.append({"Business Name": name, "Listing URL": url})
            sleep(random.uniform(0.2, 0.5))
    except:
        pass
    return listings

@st.cache_data(show_spinner=False)
def fetch_yelp(query, location, limit):
    base = "https://www.yelp.ca"
    search_url = f"{base}/search?find_desc={query.replace(' ', '+')}&find_loc={location.replace(' ', '+')}"
    listings = []
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        biz_paths = set()
        for a in soup.find_all("a", href=True):
            href = a['href']
            if href.startswith("/biz/"):
                biz_paths.add(href.split('?')[0])
        for path in list(biz_paths)[:limit]:
            url = urljoin(base, path)
            try:
                page = requests.get(url, headers=headers, timeout=5)
                page_soup = BeautifulSoup(page.text, "html.parser")
                h1 = page_soup.find("h1")
                name = h1.get_text(strip=True) if h1 else url
            except:
                name = url
            listings.append({"Business Name": name, "Listing URL": url})
            sleep(random.uniform(0.3, 0.7))
    except:
        pass
    return listings

@st.cache_data(show_spinner=False)
def fetch_bing(query, location, limit):
    search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}+{location.replace(' ', '+')}+site:.ca"
    listings = []
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for h2 in soup.find_all("h2"):
            if len(listings) >= limit:
                break
            a = h2.find("a", href=True)
            if a:
                url = a['href']
                if ".ca" in url:
                    name = a.get_text(strip=True)
                    listings.append({"Business Name": name, "Listing URL": url})
                    sleep(random.uniform(0.2, 0.6))
    except:
        pass
    return listings

@st.cache_data(show_spinner=False)
def aggregate_listings(query, location, limit):
    combined = []
    seen = set()
    sources = [
        fetch_yellowpages(query, location, limit*2),
        fetch_yelp(query, location, limit*2),
        fetch_bing(query, location, limit*2),
    ]
    for source in sources:
        for item in source:
            url = item["Listing URL"]
            if url not in seen:
                seen.add(url)
                combined.append(item)
            if len(combined) >= limit:
                return combined
    return combined

if run_scrape:
    if query and location:
        with st.spinner("Aggregating listings from YellowPages, Yelp, and Bing..."):
            data = aggregate_listings(query, location, num_listings)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} unique listings!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download CSV", csv,
                    file_name="aggregated_listings.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No listings found for the given search.")
    else:
        st.warning("Please enter both a business type and a location.")
