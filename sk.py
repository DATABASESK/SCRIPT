import requests
from bs4 import BeautifulSoup
import json
import re
from github import Github  # Install using `pip install PyGithub`

# GitHub configuration
GITHUB_TOKEN = "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"
REPO_NAME = "DATABASESK/FINAL"
DB_JSON_PATH = "db.json"

# Base URLs for different movie genres
urls = {
    'hollywood': 'https://0gomovies.id/genre/hollywood/',
    'multi': 'https://0gomovies.id/genre/multi-language/',
    'tamil': 'https://0gomovies.id/genre/watch-tamil-movies/',
    'netflix': 'https://0gomovies.mov/genre/watch-tamil-movies/'  # Adjust as per your requirement
}

# Function to scrape data for a given genre URL
def scrape_data(base_url, genre):
    poster_links = []
    movie_links = []
    page_number = 1
    max_pages = 50

    while page_number <= max_pages:
        if page_number == 5:
            print(f"Skipping page {page_number}")
            page_number += 1
            continue

        url = f'{base_url}page/{page_number}/'
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to retrieve page {page_number}, status code:", response.status_code)
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find_all('img', class_='thumb mli-thumb lazy')
        for img in images:
            img_url = img.get('data-original') or img.get('src')
            if img_url:
                poster_links.append(img_url)

        items = soup.find_all('div', class_='ml-item')
        if not items:
            print(f"No more items found for {genre}, ending pagination.")
            break

        for div in items:
            a_tag = div.find('a', class_='ml-mask')
            if a_tag:
                movie_url = a_tag.get('href')
                if movie_url:
                    movie_links.append(movie_url)

        print(f"Fetched page {page_number} for {genre} with {len(images)} images and {len(items)} items.")
        page_number += 1

    return poster_links, movie_links

# Function to fetch movie details from the movie links
def fetch_movie_details(movie_links, poster_links):
    movie_details = []

    for index, movie_url in enumerate(movie_links):
        print(f"\nFetching details from: {movie_url}")
        response = requests.get(movie_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        movie_name = soup.find('h3').text.strip() if soup.find('h3') else "Unknown"
        video_url_player1 = None
        video_url_player2 = None

        button_tags = soup.find_all('button', {'class': 'chbtn'})
        for button_tag in button_tags:
            if "WATCH ON PLAYER 2" in button_tag.text:
                onclick_attr = button_tag['onclick']
                start = onclick_attr.find("('") + 2
                end = onclick_attr.find("')", start)
                if start != -1 and end != -1:
                    external_link = onclick_attr[start:end]
                    if "cdn.bewab.co" in external_link:
                        video_url_player2 = external_link[external_link.find("https://cdn.bewab.co"):]

        if not video_url_player2:
            for button_tag in button_tags:
                if "WATCH ON PLAYER 1" in button_tag.text:
                    onclick_attr = button_tag['onclick']
                    start = onclick_attr.find("('") + 2
                    end = onclick_attr.find("')", start)
                    if start != -1 and end != -1:
                        video_url_player1 = onclick_attr[start:end]

        if index < len(poster_links):
            if video_url_player2 or video_url_player1:
                movie_detail = {
                    'name': movie_name,
                    'uri': poster_links[index]
                }
                if video_url_player2:
                    movie_detail['link'] = video_url_player2.replace(
                        "https://cdn.bewab.co/", "https://videooo.news/"
                    )
                elif video_url_player1:
                    movie_detail['link'] = video_url_player1.replace(
                        "https://cdn.bewab.co/", "https://videooo.news/"
                    )
                movie_details.append(movie_detail)

    return movie_details

# Function to fetch and merge movie data with existing JSON
def merge_data(existing_data, new_data, genre):
    if genre not in existing_data:
        existing_data[genre] = []
    existing_names = {movie['name'] for movie in existing_data[genre]}
    for movie in new_data:
        if movie['name'] not in existing_names:
            existing_data[genre].append(movie)

# Function to update the db.json file on GitHub
def update_github_db(json_data):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    try:
        # Get the current file content
        contents = repo.get_contents(DB_JSON_PATH)
        repo.update_file(
            path=DB_JSON_PATH,
            message="Updated db.json with new movie data",
            content=json.dumps(json_data, indent=4),
            sha=contents.sha
        )
        print("db.json successfully updated on GitHub.")
    except Exception as e:
        print("Error updating db.json:", e)

# Main function
def main():
    try:
        # Fetch existing db.json from GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(DB_JSON_PATH)
        existing_data = json.loads(contents.decoded_content.decode())

    except Exception as e:
        print("Error fetching existing db.json from GitHub. Creating new file.")
        existing_data = {}

    # Fetch new data and merge with existing data
    for genre, base_url in urls.items():
        print(f"Fetching data for {genre}")
        if genre in ['hollywood', 'multi', 'tamil']:
            poster_links, movie_links = scrape_data(base_url, genre)
            new_data = fetch_movie_details(movie_links, poster_links)
            merge_data(existing_data, new_data, genre)

    # Save updated data locally and on GitHub
    with open('db.json', 'w') as json_file:
        json.dump(existing_data, json_file, indent=4)
    print("Local db.json updated.")

    # Update db.json on GitHub
    update_github_db(existing_data)

if __name__ == '__main__':
    main()
