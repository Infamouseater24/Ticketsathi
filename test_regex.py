import re

url = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
match = re.search(regex, url)

print(f"URL: {url}")
if match:
    print(f"Extracted ID: {match.group(1)}")
else:
    print("NO MATCH")
