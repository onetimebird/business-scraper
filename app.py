import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
from time import sleep
import random
from yelpapi import YelpAPI

# Streamlit app configuration
st.set_page_config(page_title="Canadian Business Listing Aggregator", layout="wide")

st.title("🇨🇦 Comprehensive Business Listing Aggregator")
st.markdown(
    "Aggregate Canadian business listings using the Yelp API, YellowPages, and Bing for a de-duplicated list, with Canada-wide support optimized for speed."
)

# Configuration: hardcode your Yelp API Key here
yelp_api_key = "EK7jnBCHOO8VFmt7XhNZkCI4SUT6Iwt41rDrr0gYpQZdLBSImqvpAsDew879R7FThsuLxd7GW1SPWiBmHuUYT1H-EK1JVmm0k1ebMOMUjyL-jGTUQ8QXPQ6nXnqGaHYx"

# Helper to sanitize location strings for URL
def sanitize_loc(loc):
    return loc.replace(',', '').replace('&', '').replace(' ', '+')

# User inputs
term = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
canada_wide = st.checkbox("Canada-wide search (include major cities)", value=False)
if not canada_wide:
    loc = st.text_input("City or province (e.g. Toronto, Alberta)")
else:
    loc = None

count_label = (
    "Number of businesses to list per city" if canada_wide 
    else "Number of businesses to list"
)
count = st.slider(count_label, min_value=10, max_value=200, value=50)
use_bing = st.checkbox("Include Bing scraping fallback", value=True)
run = st.button("🚀 Generate Listings")

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch_yelp_detailed(term, loc, limit):
    """Fetch from Yelp API and extract the actual business website via scraping external links"""
    listings = []
    try:
        yelp = YelpAPI(yelp_api_key)
        response = yelp.search_query(term=term, location=loc, limit=min(limit, 50))
        for biz in response.get('businesses', []):
            name = biz.get('name', '')
            yelp_url = biz.get('url', '')
            website_url = ''
            # Scrape Yelp page for external website link
            try:
                r = requests.get(yelp_url, headers=headers, timeout=5)
                s = BeautifulSoup(r.text, 'html.parser')
                ext_links = []
                for a in s.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('http') and 'yelp.com' not in href:
                        domain = urlparse(href).netloc.lower()
                        if not any(skip in domain for skip in [
                            'facebook.com', 'instagram.com', 'twitter.com', 'google.com', 'booking.com'
                        ]):
                            ext_links.append(href.split('?')[0])
                if ext_links:
                    website_url = ext_links[0]
            except:
                pass
            listings.append({
                "Business Name": name,
                "Yelp URL": yelp_url,
                "Business Website": website_url
            })
            sleep(random.uniform(0.05, 0.1))
    except Exception as e:
        st.error(f"Yelp API error: {e}")
    return listings

@st.cache_data(show_spinner=False)
def fetch_yelp_basic(term, loc, limit):
    """Fetch from Yelp API only (fast)"""
    listings = []
    try:
        yelp = YelpAPI(yelp_api_key)
        response = yelp.search_query(term=term, location=loc, limit=min(limit, 50))
        for biz in response.get('businesses', []):
            listings.append({
                "Business Name": biz.get('name', ''),
                "Yelp URL": biz.get('url', ''),
                "Business Website": ''
            })
    except Exception as e:
        st.error(f"Yelp API error: {e}")
    return listings

@st.cache_data(show_spinner=False)
def fetch_yellowpages(term, loc, limit):
    base = "https://www.yellowpages.ca"
    loc_param = sanitize_loc(loc)
    search_url = f"{base}/search/si/1/{term.replace(' ', '+')}/{loc_param}"
    results = []
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        tags = soup.find_all("a", class_="listing__name--link", href=True)
        for tag in tags[:limit]:
            name = tag.get_text(strip=True)
            listing_url = urljoin(base, tag['href'])
            website_url = ''
            # scrape for website link
            try:
                p = requests.get(listing_url, headers=headers, timeout=5)
                sp = BeautifulSoup(p.text, 'html.parser')
                btn = sp.find('a', href=True, string=re.compile('website', re.I))
                if btn:
                    website_url = btn['href']
            except:
                pass
            results.append({
                "Business Name": name,
                "Listing URL": listing_url,
                "Business Website": website_url
            })
            sleep(random.uniform(0.05, 0.1))
    except Exception as e:
        st.error(f"YellowPages scraping error: {e}")
    return results

@st.cache_data(show_spinner=False)
def fetch_bing_scrape(term, loc, limit):
    results = []
    if not use_bing:
        return results
    loc_param = sanitize_loc(loc)
    search_url = f"https://www.bing.com/search?q={term.replace(' ', '+')}+{loc_param}+site:.ca"
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for h2 in soup.find_all("h2"):
            if len(results) >= limit:
                break
            a = h2.find("a", href=True)
            if a and ".ca" in a['href']:
                name = a.get_text(strip=True)
                url = a['href']
                results.append({
                    "Business Name": name,
                    "Business Website": url
                })
                sleep(random.uniform(0.05, 0.1))
    except Exception as e:
        st.error(f"Bing scraping error: {e}")
    return results

@st.cache_data(show_spinner=False)
def aggregate_listings(term, loc, total, detailed=False):
    combined = []
    seen = set()
    # Yelp
    yelp_list = fetch_yelp_detailed(term, loc, total) if detailed else fetch_yelp_basic(term, loc, total)
    for item in yelp_list:
        url = item['Business Website'] or item['Yelp URL']
        if url and url not in seen:
            seen.add(url)
            combined.append(item)
        if len(combined) >= total:
            return combined
    # YellowPages fallback
    for item in fetch_yellowpages(term, loc, total*2):
        url = item['Business Website'] or item['Listing URL']
        if url and url not in seen:
            seen.add(url)
            combined.append(item)
        if len(combined) >= total:
            return combined
    # Bing fallback
    for item in fetch_bing_scrape(term, loc, total*2):
        url = item['Business Website']
        if url and url not in seen:
            seen.add(url)
            combined.append(item)
        if len(combined) >= total:
            return combined
    return combined

@st.cache_data(show_spinner=False)
def aggregate_canada_wide(term, total):
    cities = ["Toronto ON","Montreal QC","Vancouver BC","Calgary AB","Edmonton AB",
              "Ottawa ON","Winnipeg MB","Quebec City QC","Hamilton ON","Victoria BC"]
    combined = []
    seen = set()
    for city in cities:
        items = fetch_yelp_basic(term, city, total)
        for item in items:
            url = item['Yelp URL']
            if url and url not in seen:
                seen.add(url)
                combined.append(item)
    return combined

# Run on button click
if run:
    if not term or (not canada_wide and not loc):
        st.warning("Please enter both a business type and a location (or select Canada-wide).")
    else:
        with st.spinner("Gathering listings with website URLs..."):
            if canada_wide:
                data = aggregate_canada_wide(term, count)
            else:
                data = aggregate_listings(term, loc, count, detailed=True)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} unique listings!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv,
                    file_name="business_listings.csv", mime="text/csv")
            else:
                st.warning("No listings found. Check inputs and retry.")
