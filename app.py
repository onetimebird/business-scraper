import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
from time import sleep
import random
from yelpapi import YelpAPI
import json
import re

# Streamlit app configuration
st.set_page_config(page_title="Canadian Business Listing Aggregator", layout="wide")

st.title("🇨🇦 Comprehensive Business Listing Aggregator")
st.markdown(
    "Aggregate Canadian business listings using the Yelp API, then scrape each Yelp page for the real business website and phone number."
)

# Configuration: hardcode your Yelp API Key here
yelp_api_key = "EK7jnBCHOO8VFmt7XhNZkCI4SUT6Iwt41rDrr0gYpQZdLBSImqvpAsDew879R7FThsuLxd7GW1SPWiBmHuUYT1H-EK1JVmm0k1ebMOMUjyL-jGTUQ8QXPQ6nXnqGaHYx"

PHONE_REGEX = r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# User inputs
term = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
loc = st.text_input("City or province (e.g. Toronto, Alberta)")
count = st.slider("Number of businesses to list", min_value=10, max_value=200, value=50)
run = st.button("🚀 Generate Listings")

@st.cache_data(show_spinner=False)
def fetch_yelp_detailed(term, loc, limit):
    """Use Yelp API to get business pages, then scrape each page for website and phone."""
    listings = []
    try:
        yelp = YelpAPI(yelp_api_key)
        response = yelp.search_query(term=term, location=loc, limit=min(limit,50))
        for biz in response.get('businesses', []):
            name = biz.get('name', '')
            yelp_url = biz.get('url', '')
            website_url = ''
            phone = ''
            try:
                # Request Yelp page
                r = requests.get(yelp_url, headers=headers, timeout=5)
                s = BeautifulSoup(r.text, 'html.parser')
                # JSON-LD extraction
                for script in s.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        entries = data if isinstance(data, list) else [data]
                        for entry in entries:
                            if entry.get('@type') in ['LocalBusiness','Organization']:
                                # official website
                                url_prop = entry.get('url')
                                if url_prop and 'yelp.com' not in url_prop:
                                    website_url = url_prop
                                # telephone
                                tel = entry.get('telephone')
                                if tel:
                                    phone = tel
                                break
                        if website_url and phone:
                            break
                    except:
                        continue
                # Fallback: extract first external link if no website_url
                if not website_url:
                    for a in s.find_all('a', href=True):
                        href = a['href']
                        if href.startswith('http') and 'yelp.com' not in href:
                            domain = urlparse(href).netloc.lower()
                            if not any(skip in domain for skip in ['facebook.com','instagram.com','twitter.com','google.com']):
                                website_url = href.split('?')[0]
                                break
                # Fallback: extract phone via regex
                if not phone:
                    text = s.get_text()
                    m = re.search(PHONE_REGEX, text)
                    if m:
                        phone = m.group(0)
            except:
                pass
            listings.append({
                "Business Name": name,
                "Yelp URL": yelp_url,
                "Business Website": website_url,
                "Phone": phone
            })
            sleep(random.uniform(0.1,0.3))
    except Exception as e:
        st.error(f"Yelp API error: {e}")
    return listings

if run:
    if not term or not loc:
        st.warning("Please enter both a business type and a location.")
    else:
        with st.spinner("Gathering and scraping Yelp pages..."):
            data = fetch_yelp_detailed(term, loc, count)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} listings with websites and phones!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv,
                    file_name="business_listings.csv", mime="text/csv")
            else:
                st.warning("No listings found. Try adjusting your search.")
