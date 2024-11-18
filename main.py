
import requests
import re
from bs4 import BeautifulSoup
import json
import base64

# GitHub configuration
GITHUB_USERNAME = "DATABASESK"
GITHUB_REPO = "seriesname"
GITHUB_TOKEN = "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"
GITHUB_FILE_PATH = "db.json"

# Function to fetch movie details from the base URL
def fetch_movies(base_url, pages):
    movie_details = []

    for page in range(1, pages + 1):
        url = f"{base_url}/page/{page}/"  # Adjusted URL for pagination
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to retrieve page {page}. Status code: {response.status_code}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        movie_links = soup.find_all('a', class_='ml-mask')

        for link in movie_links:
            title = link.get('title', '')
            image_tag = link.find('img', class_='thumb mli-thumb lazy')

            if image_tag:
                image_src = image_tag.get('data-original', '')
                next_link = link.get('href', '')
                next_url = f"{next_link[:-1]}/watching/" if next_link.endswith('/') else f"{next_link}/watching/"

                movie_details.append({
                    'title': title,
                    'image': image_src,
                    'next_link': next_url
                })

    return movie_details

# Function to fetch the initial HTML file and find links
def fetch_links(url):
    response = requests.get(url)
    html_content = response.text

    # Use regex to find all matching links
    pattern = r'https://18rule\.com/\d+'
    matches = re.findall(pattern, html_content)

    return matches

# Function to fetch the second link and extract video information
def fetch_video_links(second_link):
    response = requests.get(second_link)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all anchor tags with the specific structure
    video_links = []
    for a in soup.find_all('a', href=True):
        if 'link.php?link=' in a['href']:
            title = a.get_text(strip=True)
            link = a['href'].replace('https://lesmandalas.net/link.php?link=', '')

            # Replace goplayer3.com with videooo.news
            link = link.replace('https://cdn.bewab.co/', 'https://videooo.news/')
            video_links.append({'title': title, 'link': link})

    # Sort video links by episode number
    video_links.sort(key=lambda x: int(re.search(r'(\d+)', x['title']).group()))

    return video_links

# Function to upload the JSON file to GitHub
def upload_to_github(json_data):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

    # Get the current file's SHA (if it exists)
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = response.json().get("sha") if response.status_code == 200 else None

    # Prepare the payload for the API
    content = base64.b64encode(json_data.encode()).decode()
    payload = {
        "message": "Update db.json with Netflix data",
        "content": content
    }
    if sha:
        payload["sha"] = sha

    # Make the API request to create/update the file
    response = requests.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)

    if response.status_code in [200, 201]:
        print("db.json updated successfully on GitHub!")
    else:
        print(f"Failed to update db.json: {response.status_code} - {response.json()}")

# Main function to run the script
def main():
    # Base URL for the movie genre
    base_url = "https://0gomovies.id/genre/watch-tamil-movies/"

    # Step 1: Fetch movie details
    movies = fetch_movies(base_url, 40)

    # Check if movies were found
    if not movies:
        print("No movies found.")
        return

    # Prepare the final output list
    netflix_data = []

    # Loop through each movie and fetch video links
    for movie in movies:
        # Use the next_link to fetch video information
        video_links = fetch_links(movie['next_link'])

        if len(video_links) < 2:
            print(f"Not enough links found for {movie['title']}.")
            continue

        # Use the second link to fetch actual video links
        second_link = video_links[1]
        videos = fetch_video_links(second_link)

        # Append the formatted movie data to the final output
        netflix_data.append({
            "name": movie['title'],
            "uri": movie['image'],
            "videos": videos
        })

    # Step 2: Structure data under the "netflix" key
    final_output = {"netflix": netflix_data}

    # Convert the data to JSON format
    json_data = json.dumps(final_output, indent=4)

    # Step 3: Upload the JSON data to GitHub
    upload_to_github(json_data)

if __name__ == '__main__':
    main()
