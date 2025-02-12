import requests

# NASA API Key (Get your own from https://api.nasa.gov/)
NASA_API_KEY = "DEMO_KEY"

def test_nasa_apod():
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
    response = requests.get(url)
    print("NASA APOD API Response:")
    print(response.json())

def test_ads_api():
    # Requires an ADS API Key (Get it from https://ui.adsabs.harvard.edu/user/settings/token)
    ADS_API_KEY = "YOUR_ADS_API_KEY"
    url = "https://api.adsabs.harvard.edu/v1/search/query?q=cosmology&fl=title,abstract"
    headers = {"Authorization": f"Bearer {ADS_API_KEY}"}
    response = requests.get(url, headers=headers)
    print("\nADS API Response:")
    print(response.json())

def test_arxiv_api():
    url = "http://export.arxiv.org/api/query?search_query=cosmology&start=0&max_results=3"
    response = requests.get(url)
    print("\nArXiv API Response:")
    print(response.text)

def test_spaceflight_news_api():
    url = "https://api.spaceflightnewsapi.net/v3/articles"
    response = requests.get(url)
    print("\nSpaceflight News API Response:")
    print(response.json())

if __name__ == "__main__":
    test_nasa_apod()
    test_arxiv_api()
    test_spaceflight_news_api()

    # Uncomment the line below after getting an ADS API Key
    # test_ads_api()
