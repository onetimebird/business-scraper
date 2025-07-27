import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urlparse, urljoin
from time import sleep
import random

st.set_page_config(page_title="Smart Canadian Business Scraper", layout="wide")

st.title("🇨🇦 Smart Canadian Business Scraper")
st.markdown("Find and extract emails + contact info from Canadian business websites, using YellowPages-powered crawling and filters.")

query = st.text_input("Business type or keywords (e.g. marketing agency, electrician)")
location = st.text_input("City or province (e.g. Toronto, Alberta)")
num_sites = st.slider("Number of businesses to scan", 5, 50, 10)
filter_business_emails = st.checkbox("✅ Only include business emails (no Gmail/Yahoo/etc.)", value=True)
require_email = st.checkbox("✅ Only show results with email address", value=True)
run_scrape = st.button("🚀 Run Smart Scrape")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})"
FREE_EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com', 'outlook.com']

@st.cache_data(show_spinner=False)
def get_search_results(query, location, limit):
    """
    Use YellowPages to find business listing pages.
    Returns a list of YellowPages business URLs.
    """
    results = []
    base_url = "https://www.yellowpages.ca"
    search_url = f"{base_url}/search/si/1/{query.replace(' ', '+')}/{location.replace(' ', '+')}"
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Find listing links
        for a in soup.find_all('a', class_='listing__name--link', href=True):
            if len(results) >= limit:
                break
            href = a['href']
            full_url = urljoin(base_url, href)
            results.append(full_url)
    except Exception:
        pass
    return list(dict.fromkeys(results))


def get_contact_pages(soup, base_url):
    """Find and return contact/about pages from a site soup"""
    contact_links = []
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        if any(x in href for x in ["contact", "about", "team", "staff"]):
            full = urljoin(base_url, href)
            contact_links.append(full)
    return list(set(contact_links))


def extract_info_from_site(url):
    """Extract emails and phones from homepage and contact subpages"""
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        base = urlparse(url).scheme + "://" + urlparse(url).netloc
        pages = [url] + get_contact_pages(soup, base)

        emails, phones = set(), set()
        for p in pages:
            try:
                r = requests.get(p, headers=headers, timeout=5)
                txt = BeautifulSoup(r.text, "html.parser").get_text()
                emails.update(re.findall(EMAIL_REGEX, txt))
                phones.update(re.findall(PHONE_REGEX, txt))
            except:
                continue
        # Clean and filter emails
        emails = [e for e in emails if '@' in e]
        if filter_business_emails:
            emails = [e for e in emails if e.split('@')[-1].lower() not in FREE_EMAIL_DOMAINS]

        title = soup.title.string.strip() if soup.title else urlparse(url).netloc
        return {
            "Business Name": title,
            "Website": url,
            "Email(s)": ", ".join(sorted(emails)),
            "Phone(s)": ", ".join(sorted(phones))
        }
    except:
        return None

if run_scrape and query and location:
    with st.spinner("Crawling YellowPages listings, then websites — please wait..."):
        biz_urls = get_search_results(query, location, num_sites)
        results = []
        for site in biz_urls:
            st.text(f"Scanning: {site}")
            info = extract_info_from_site(site)
            if info and (not require_email or info['Email(s)']):
                results.append(info)
            sleep(random.uniform(1, 2))

        if results:
            df = pd.DataFrame(results)
            st.success(f"✅ Found contact info for {len(df)} businesses!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "business_contacts.csv", "text/csv")
        else:
            st.warning("No contact info found for the given search.")
elif run_scrape:
    st.warning("Please enter both a business type and a location to begin.")
