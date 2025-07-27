import streamlit as st
import pandas as pd
import requests
import googlemaps
from yelpapi import YelpAPI
from urllib.parse import urlparse
from time import sleep
import random

# -- Streamlit App Configuration --
st.set_page_config(page_title="Business Listing Aggregator", layout="wide")

st.title("🇨🇦 Comprehensive Business Listing Aggregator")
st.markdown(
    "Use the Yelp Fusion API, Google Places API, and optional Bing scraping to build a de-duplicated list "
    "of Canadian businesses for your outreach."
)

# -- API Key Inputs --
yelp_api_key = st.text_input("Yelp API Key", type="password")
google_api_key = st.text_input("Google API Key", type="password")
use_bing = st.checkbox("Include Bing scraping fallback", value=False)

# -- Search Inputs --
query = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
location = st.text_input("City or province (e.g. Toronto, Alberta)")
num_listings = st.slider("Total businesses to list", 10, 500, 100)
run = st.button("🚀 Generate Listings")

# -- Functions --
@st.cache_data(show_spinner=False)
def fetch_yelp(api_key, term, loc, limit):
    listings = []
    try:
        yelp = YelpAPI(api_key)
        response = yelp.search_query(term=term, location=loc, limit=min(limit,50))
        for biz in response.get('businesses', []):
            listings.append({
                "Business Name": biz.get('name', ''),
                "Listing URL": biz.get('url', '')
            })
    except Exception as e:
        st.error(f"Yelp API error: {e}")
    return listings

@st.cache_data(show_spinner=False)
def fetch_google(api_key, term, loc, limit):
    listings = []
    try:
        gmaps = googlemaps.Client(key=api_key)
        geocode = gmaps.geocode(loc)
        if not geocode:
            return listings
        coords = geocode[0]['geometry']['location']
        places = gmaps.places_nearby(location=(coords['lat'], coords['lng']),
                                     keyword=term, rank_by='distance')
        for place in places.get('results', [])[:limit]:
            name = place.get('name')
            pid = place.get('place_id')
            details = gmaps.place(place_id=pid, fields=['website'])
            url = details.get('result', {}).get('website', '')
            listings.append({"Business Name": name, "Listing URL": url})
    except Exception as e:
        st.error(f"Google Places API error: {e}")
    return listings

@st.cache_data(show_spinner=False)
def fetch_bing(term, loc, limit):
    # Simple Bing scraping fallback
    listings = []
    headers = {"User-Agent": "Mozilla/5.0"}
    search_url = f"https://www.bing.com/search?q={term.replace(' ','+')}+{loc.replace(' ','+')}+site:.ca"
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for h2 in soup.find_all('h2'):
            if len(listings) >= limit:
                break
            a = h2.find('a', href=True)
            if a:
                url = a['href']
                name = a.get_text(strip=True)
                listings.append({"Business Name": name, "Listing URL": url})
                sleep(random.uniform(0.2, 0.5))
    except:
        pass
    return listings

# -- Aggregation Logic --
@st.cache_data(show_spinner=False)
def aggregate(term, loc, total):
    combined = []
    seen = set()
    # Yelp
    if yelp_api_key:
        for item in fetch_yelp(yelp_api_key, term, loc, total):
            if item['Listing URL'] not in seen:
                seen.add(item['Listing URL']); combined.append(item)
            if len(combined) >= total: return combined
    # Google
    if google_api_key:
        for item in fetch_google(google_api_key, term, loc, total):
            if item['Listing URL'] not in seen:
                seen.add(item['Listing URL']); combined.append(item)
            if len(combined) >= total: return combined
    # Bing
    if use_bing:
        for item in fetch_bing(term, loc, total):
            if item['Listing URL'] not in seen:
                seen.add(item['Listing URL']); combined.append(item)
            if len(combined) >= total: return combined
    return combined

# -- Run On Button Click --
if run:
    if not (query and location):
        st.warning("Please enter both a business type and a location.")
    else:
        with st.spinner("Gathering listings from APIs..."):
            data = aggregate(query, location, num_listings)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} unique listings!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv,
                    file_name="business_listings.csv", mime="text/csv")
            else:
                st.warning("No listings found. Check your API keys and input.")
