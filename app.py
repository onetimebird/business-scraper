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
st.markdown("Find and extract emails + contact info from Canadian business websites, with smart crawling and filters.")

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

def get_contact_pages(soup, base_url):
    contact_links = []
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        if any(x in href for x in ["contact", "about", "team", "staff"]):
            full_url = urljoin(base_url, href)
            contact_links.append(full_url)
    return list(set(contact_links))

def extract_info_from_site(url):
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
        all_pages = [url] + get_contact_pages(soup, base_url)

        emails, phones = set(), set()
        for page in all_pages:
            try:
                r = requests.get(page, headers=headers, timeout=5)
                s = BeautifulSoup(r.text, "html.parser")
                text = s.get_text()
                new_emails = re.findall(EMAIL_REGEX, text)
                new_phones = re.findall(PHONE_REGEX, text)
                for e in new_emails:
                    if not e.endswith(('.png', '.jpg', '.css', '.svg')):
                        emails.add(e)
                for p in new_phones:
                    phones.add(p)
            except:
                continue

        # Clean emails
        emails = [e for e in emails if '@' in e and '.' in e.split('@')[-1]]
        if filter_business_emails:
            emails = [e for e in emails if e.split('@')[-1].lower() not in FREE_EMAIL_DOMAINS]

        title = soup.title.string if soup.title else urlparse(url).netloc
        return {
            "Business Name": title.strip(),
            "Website": url,
            "Email(s)": ", ".join(sorted(emails)),
            "Phone(s)": ", ".join(sorted(phones))
        }
    except:
        return None

if run_scrape and query and location:
    with st.spinner("Crawling websites, hang tight..."):
        urls = get_search_results(query, location, num_sites)
        results = []
        for i, site in enumerate(urls):
            st.text(f"Scanning: {site}")
            info = extract_info_from_site(site)
            if info:
                if require_email and not info['Email(s)']:
                    continue
                results.append(info)
            sleep(random.uniform(1.2, 2.5))

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
