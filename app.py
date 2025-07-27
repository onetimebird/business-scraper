import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
from time import sleep
import random

# Streamlit app configuration
st.set_page_config(page_title="Canadian Business Listing Aggregator", layout="wide")

st.title("🇨🇦 Canadian Business Listing Aggregator")
st.markdown(
    "Aggregate business listings from YellowPages, Yelp, and Bing for your search term and location, "
    "and remove duplicates for a comprehensive CSV you can work with."
)

# User inputs
query = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
location = st.text_input("City or province (e.g. Toronto, Alberta)")
num_listings = st.slider("Number of businesses to list", min_value=10, max_value=300, value=50)
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
        for tag in tags:
            if len(listings) >= limit:
                break
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
        links = soup.find_all("a", href=True, attrs={"class": "css-1m051bw"}) or \
                [a for a in soup.find_all("a", href=True) if a["href"].startswith("/biz/")]
        for a in links:
            if len(listings) >= limit:
                break
            href = a['href']
            url = urljoin(base, href.split('?')[0])
            name = a.get_text(strip=True)
            if name:
                listings.append({"Business Name": name, "Listing URL": url})
                sleep(random.uniform(0.2, 0.5))
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
        items = soup.find_all("li", class_="b_algo")
        for li in items:
            if len(listings) >= limit:
                break
            a = li.find("a", href=True)
            if a:
                url = a['href']
                name = a.get_text(strip=True)
                if ".ca" in url:
                    listings.append({"Business Name": name, "Listing URL": url})
                    sleep(random.uniform(0.2, 0.5))
    except:
        pass
    return listings

@st.cache_data(show_spinner=False)
def aggregate_listings(query, location, limit):
    combined = []
    seen = set()
    # fetch double limit from each source to ensure diversity
    sources = [fetch_yellowpages(query, location, limit*2),
               fetch_yelp(query, location, limit*2),
               fetch_bing(query, location, limit*2)]
    for source in sources:
        for item in source:
            url = item["Listing URL"]
            if url not in seen:
                seen.add(url)
                combined.append(item)
            if len(combined) >= limit:
                return combined
    return combined

# Run aggregation when button clicked
if run_scrape:
    if query and location:
        with st.spinner("Aggregating listings from YellowPages, Yelp, and Bing..."):
            data = aggregate_listings(query, location, num_listings)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} unique listings!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download CSV", csv,
                    file_name="aggregated_listings.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No listings found for the given search.")
    else:
        st.warning("Please enter both a business type and a location.")
