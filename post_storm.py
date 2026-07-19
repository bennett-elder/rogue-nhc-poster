#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
import requests


def fetch_advisory_text(advisory_url):
    contents = urllib.request.urlopen(advisory_url).read().decode('utf-8')
    clean_left = contents.partition('<pre>')[2]
    clean_right = clean_left.partition('</pre>')[0]

    header_stripped = clean_right.partition('...')[2]
    gist = header_stripped.partition('SUMMARY')[0]

    cleaned_gist = gist.replace("""...
...""", '. ').replace("""
""", ' ').replace('...', '')
    return cleaned_gist


class Poster:
    def __init__(self, pds_url: str, handle: str, password: str) -> None:
        self.pds_url = pds_url
        self.session = self.bsky_login_session(handle, password)

    def bsky_login_session(self, handle: str, password: str) -> dict:
        resp = requests.post(
            self.pds_url + "/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, filename, img_bytes) -> dict:
        suffix = filename.split(".")[-1].lower()
        mimetype = "application/octet-stream"
        if suffix in ["png"]:
            mimetype = "image/png"
        elif suffix in ["jpeg", "jpg"]:
            mimetype = "image/jpeg"
        elif suffix in ["webp"]:
            mimetype = "image/webp"

        access_token = self.session["accessJwt"]
        resp = requests.post(
            self.pds_url + "/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Content-Type": mimetype,
                "Authorization": "Bearer " + access_token,
            },
            data=img_bytes,
        )
        resp.raise_for_status()
        return resp.json()["blob"]

    def create_post(self, post_text, images=[]):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        post = {
            "$type": "app.bsky.feed.post",
            "text": post_text,
            "createdAt": now,
        }

        post["embed"] = {
            "$type": "app.bsky.embed.images",
            "images": images,
        }

        response = requests.post(
            self.pds_url + "/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": "Bearer " + self.session["accessJwt"]},
            json={
                "repo": self.session["did"],
                "collection": "app.bsky.feed.post",
                "record": post,
            },
        )

        return response

    def add_image(self, input_image_array: list, filename: str, alt_text: str) -> list:
        with open(filename, 'rb') as f:
            img_data = f.read()
        blob = self.upload_file(filename, img_data)

        input_image_array.append(
            {
                "alt": alt_text,
                "image": blob
            }
        )
        return input_image_array


def main():
    result_file = sys.argv[1] if len(sys.argv) > 1 else 'result.json'

    with open(result_file) as f:
        data = json.load(f)

    new_storms = data.get('new_storms', [])
    if not new_storms:
        print('No new storms to post')
        return

    will_skeet = os.getenv('WILL_SKEET', 'False')
    pds_url = os.getenv('PDS_URL', 'https://bsky.social')

    for storm in new_storms:
        storm_name = storm['name']
        atcf = storm['atcf']
        basin = storm['basin']
        advisory_url = storm['advisory_url']
        images = storm['images']
        image_alts = storm['image_alts']

        bluesky_user = os.environ[f'BLUESKY_USER_{basin}']
        bluesky_pass = os.environ[f'BLUESKY_PASS_{basin}']

        print(f'Account ({basin}): {bluesky_user}')
        print(f'\nPosting {storm_name} ({atcf})...')

        gist = fetch_advisory_text(advisory_url)
        print(gist)

        if will_skeet not in ('True', 'true'):
            print('  no skeetin')
            continue

        link_text = f'{storm_name} Public Advisory'
        message_text = f'{link_text}\n{gist}'

        os.makedirs('tmp', exist_ok=True)
        urllib.request.urlretrieve(images['5day_cone'], 'tmp/img_5day.png')
        urllib.request.urlretrieve(images['current_wind'], 'tmp/img_wind.png')

        poster = Poster(pds_url, bluesky_user, bluesky_pass)

        image_list = []
        image_list = poster.add_image(image_list, 'tmp/img_5day.png', image_alts['5day_cone'])
        image_list = poster.add_image(image_list, 'tmp/img_wind.png', image_alts['current_wind'])

        response = poster.create_post(message_text, image_list)

        print("createRecord response:", file=sys.stderr)
        print(json.dumps(response.json(), indent=2))

        print('  posted!')


if __name__ == '__main__':
    main()