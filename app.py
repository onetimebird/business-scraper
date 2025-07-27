import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from time import sleep
import random

# Streamlit app configuration
st.set_page_config(page_title="Canadian Business Listing Scraper", layout="wide")

st.title("🇨🇦 Canadian Business Listing Scraper")
st.markdown(
    "Generate a comprehensive list of businesses based on your search term and location, "
    "so you can manually collect contact information."
)

# User inputs
query = st.text_input("Business type or keywords (e.g. dentist, marketing agency)")
location = st.text_input("City or province (e.g. Toronto, Alberta)")
num_listings = st.slider("Number of businesses to list", min_value=10, max_value=200, value=50)
run_scrape = st.button("🚀 Get Listings")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

@st.cache_data(show_spinner=False)
def fetch_listings(query, location, limit):
    """
    Scrape YellowPages.ca for business listings and return a list of
    {'Business Name', 'Listing URL'} dictionaries.
    """
    base_url = "https://www.yellowpages.ca"
    search_url = (
        f"{base_url}/search/si/1/"
        f"{query.replace(' ', '+')}/{location.replace(' ', '+')}"
    )
    listings = []
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Find listing links and names
        link_tags = soup.find_all(
            "a", class_="listing__name--link", href=True
        )
        for tag in link_tags[:limit]:
            name = tag.get_text(strip=True)
            href = tag['href']
            full_url = urljoin(base_url, href)
            listings.append({
                "Business Name": name,
                "Listing URL": full_url
            })
            # polite delay
            sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass
    return listings

# Run scraping
if run_scrape:
    if query and location:
        with st.spinner("Fetching business listings, please wait..."):
            data = fetch_listings(query, location, num_listings)
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Retrieved {len(df)} business listings!")
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download CSV", csv,
                    file_name="business_listings.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No listings found for the given search.")
    else:
        st.warning("Please enter both a business type and a location.")
