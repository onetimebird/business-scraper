import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from time import sleep
import random
from yelpapi import YelpAPI

# Streamlit app configuration
st.set_page_config(page_title="Canadian Business Listing Aggregator", layout="wide")

st.title("🇨🇦 Comprehensive Business Listing Aggregator")
st.markdown(
    "Aggregate Canadian business listings using the Yelp API, YellowPages, and Bing for a de-duplicated list without requiring manual API key input each search."
)

# Configuration: hardcode your Yelp API Key here
yelp_api_key = "EK7jnBCHOO8VFmt7XhNZkCI4SUT6Iwt41rDrr0gYpQZdLBSImqvpAsDew879R7FThsuLxd7GW1SPWiBmHuUYT1H-EK1JVmm0k1ebMOMUjyL-jGTUQ8QXPQ6nXnqGaHYx"

# User inputs
term = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
loc = st.text_input("City or province (e.g. Toronto, Alberta)")
count = st.slider("Number of businesses to list", min_value=10, max_value=500, value=100)
use_bing = st.checkbox("Include Bing scraping fallback", value=True)
run = st.button("🚀 Generate Listings")

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

@st.cache_data(show_spinner=False)
def fetch_yelp_api(term, loc, limit):
    listings = []
    try:
        yelp = YelpAPI(yelp_api_key)
        response = yelp.search_query(term=term, location=loc, limit=min(limit,50))
        for biz in response.get('businesses', []):
            name = biz.get('name', '')
            url = biz.get('url', '')
            if url:
                listings.append({"Business Name": name, "Listing URL": url})
    except Exception as e:
        st.error(f"Yelp API error: {e}")
    return listings

@st.cache_data(show_spinner=False)
def fetch_yellowpages(term, loc, limit):
    base = "https://www.yellowpages.ca"
    search_url = f"{base}/search/si/1/{term.replace(' ', '+')}/{loc.replace(' ', '+')}"
    results = []
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        tags = soup.find_all("a", class_="listing__name--link", href=True)
        for tag in tags[:limit]:
            name = tag.get_text(strip=True)
            url = urljoin(base, tag['href'])
            results.append({"Business Name": name, "Listing URL": url})
            sleep(random.uniform(0.2, 0.5))
    except:
        pass
    return results

@st.cache_data(show_spinner=False)
def fetch_bing_scrape(term, loc, limit):
    results = []
    if not use_bing:
        return results
    search_url = f"https://www.bing.com/search?q={term.replace(' ', '+')}+{loc.replace(' ', '+')}+site:.ca"
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for h2 in soup.find_all("h2"):
            if len(results) >= limit:
                break
            a = h2.find("a", href=True)
            if a and ".ca" in a['href']:
                name = a.get_text(strip=True)
                results.append({"Business Name": name, "Listing URL": a['href']})
                sleep(random.uniform(0.2, 0.5))
    except:
        pass
    return results

@st.cache_data(show_spinner=False)
def aggregate_listings(term, loc, total):
    combined = []
    seen = set()
    # Yelp API
    for item in fetch_yelp_api(term, loc, total):
        url = item['Listing URL']
        if url and url not in seen:
            seen.add(url)
            combined.append(item)
        if len(combined) >= total:
            return combined
    # YellowPages fallback
    for item in fetch_yellowpages(term, loc, total*2):
        url = item['Listing URL']
        if url and url not in seen:
            seen.add(url)
            combined.append(item)
        if len(combined) >= total:
            return combined
    # Bing fallback
    for item in fetch_bing_scrape(term, loc, total*2):
        url = item['Listing URL']
        if url and url not in seen:
            seen.add(url)
            combined.append(item)
        if len(combined) >= total:
            return combined
    return combined

if run:
    if term and loc:
        with st.spinner("Gathering listings using Yelp, YellowPages, and Bing..."):
            data = aggregate_listings(term, loc, count)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} unique listings!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv,
                    file_name="business_listings.csv", mime="text/csv")
            else:
                st.warning("No listings found. Check inputs and retry.")
    else:
        st.warning("Please enter both a business type and a location.")
