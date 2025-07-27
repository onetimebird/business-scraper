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
    "Aggregate Canadian business listings using the Yelp API, YellowPages, and Bing, with optional Canada-wide search across major cities."
)

# Configuration: hardcode your Yelp API key here
YELP_API_KEY = "EK7jnBCHOO8VFmt7XhNZkCI4SUT6Iwt41rDrr0gYpQZdLBSImqvpAsDew879R7FThsuLxd7GW1SPWiBmHuUYT1H-EK1JVmm0k1ebMOMUjyL-jGTUQ8QXPQ6nXnqGaHYx"

# Helper to build search URL param
def sanitize(query):
    return query.replace(' ', '+')

# User inputs
term = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
canada_wide = st.checkbox("Canada-wide search (include major cities)", value=False)
if not canada_wide:
    loc = st.text_input("City or province (e.g. Toronto, Alberta)")
else:
    loc = None
count_label = (
    "Number of businesses to list per city" if canada_wide else "Number of businesses to list"
)
count = st.slider(count_label, 10, 500, 50)
use_bing = st.checkbox("Include Bing scraping fallback", value=True)
run = st.button("🚀 Generate Listings")

headers = {"User-Agent": "Mozilla/5.0"}

def fetch_yelp(term, loc, limit):
    listings = []
    try:
        client = YelpAPI(YELP_API_KEY)
        response = client.search_query(term=term, location=loc, limit=min(limit,50))
        for biz in response.get('businesses', []):
            name = biz.get('name')
            url = biz.get('url')
            if url:
                listings.append({'Business Name': name, 'Listing URL': url})
    except Exception as e:
        st.error(f"Yelp API error: {e}")
    return listings

@st.cache_data(show_spinner=False)
def fetch_yellowpages(term, loc, limit):
    base = 'https://www.yellowpages.ca'
    search_url = f"{base}/search/si/1/{sanitize(term)}/{sanitize(loc)}"
    listings = []
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup.find_all('a', class_='listing__name--link', href=True)[:limit]:
            name = tag.get_text(strip=True)
            url = urljoin(base, tag['href'])
            listings.append({'Business Name': name, 'Listing URL': url})
            sleep(random.uniform(0.2,0.5))
    except Exception:
        pass
    return listings

@st.cache_data(show_spinner=False)
def fetch_bing(term, loc, limit):
    listings = []
    if not use_bing:
        return listings
    search_url = f"https://www.bing.com/search?q={sanitize(term)}+{sanitize(loc)}+site:.ca"
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for h2 in soup.find_all('h2'):
            if len(listings) >= limit:
                break
            a = h2.find('a', href=True)
            if a and '.ca' in a['href']:
                name = a.get_text(strip=True)
                url = a['href']
                listings.append({'Business Name': name, 'Listing URL': url})
                sleep(random.uniform(0.2,0.5))
    except Exception:
        pass
    return listings

@st.cache_data(show_spinner=False)
def aggregate_single(term, loc, limit):
    combined = []
    seen = set()
    # Yelp
    for item in fetch_yelp(term, loc, limit):
        if item['Listing URL'] not in seen:
            seen.add(item['Listing URL']); combined.append(item)
        if len(combined) >= limit: return combined
    # YellowPages
    for item in fetch_yellowpages(term, loc, limit*2):
        if item['Listing URL'] not in seen:
            seen.add(item['Listing URL']); combined.append(item)
        if len(combined) >= limit: return combined
    # Bing
    for item in fetch_bing(term, loc, limit*2):
        if item['Listing URL'] not in seen:
            seen.add(item['Listing URL']); combined.append(item)
        if len(combined) >= limit: return combined
    return combined

@st.cache_data(show_spinner=False)
def aggregate_canada(term, limit):
    cities = [
        'Toronto ON','Montreal QC','Vancouver BC','Calgary AB','Edmonton AB',
        'Ottawa ON','Winnipeg MB','Quebec City QC','Hamilton ON','Victoria BC'
    ]
    combined = []
    seen = set()
    for city in cities:
        for item in fetch_yelp(term, city, limit):
            if item['Listing URL'] not in seen:
                seen.add(item['Listing URL']); combined.append(item)
    return combined

if run:
    if not term or (not canada_wide and not loc):
        st.warning('Please enter both a business type and a location (or select Canada-wide).')
    else:
        with st.spinner('Aggregating listings...'):
            if canada_wide:
                data = aggregate_canada(term, count)
            else:
                data = aggregate_single(term, loc, count)
            if data:
                df = pd.DataFrame(data)
                st.success(f'✅ Retrieved {len(df)} listings!')
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button('📥 Download CSV', csv,
                    file_name='business_listings.csv', mime='text/csv')
            else:
                st.warning('No listings found.')
