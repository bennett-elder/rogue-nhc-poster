#!/usr/bin/env python3

# of course borrowing bits and pieces from 
# https://github.com/bluesky-social/cookbook/blob/main/python-bsky-post/create_bsky_post.py
# for the proper URLs and request content schema

from datetime import datetime, timezone
import os
from time import sleep
from atproto import Client, models
import urllib.request

from typing import Dict, List
from datetime import datetime, timezone
import json
import sys

import requests

class Poster:
    def __init__(self, pds_url: str, handle: str, password: str) -> None:
        self.pds_url = pds_url
        self.session = self.bsky_login_session(handle, password)

    def bsky_login_session(self, handle: str, password: str) -> Dict:
        resp = requests.post(
            self.pds_url + "/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    def upload_file(self, filename, img_bytes) -> Dict:
        suffix = filename.split(".")[-1].lower()
        mimetype = "application/octet-stream"
        if suffix in ["png"]:
            mimetype = "image/png"
        elif suffix in ["jpeg", "jpg"]:
            mimetype = "image/jpeg"
        elif suffix in ["webp"]:
            mimetype = "image/webp"

        # WARNING: a non-naive implementation would strip EXIF metadata from JPEG files here by default
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

    def add_image(self, input_image_array:List, filename:str, alt_text:str) -> List:
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

def load_json_config(filename: str):
    with open(filename, 'r') as f:
        contents = f.read()
        output = json.loads(contents)
        return output

def main():
    do_uploads = True
    do_post = True
    pds_url = os.getenv('PDS_URL', 'https://bsky.social')

    bluesky_user = os.environ.get('BLUESKY_USER')
    bluesky_pass = os.environ.get('BLUESKY_PASS')
    two_region = os.environ.get('TWO_REGION')

    config = load_json_config('two_config.json')
    region_config = config[two_region]
    two_txt_html_url = region_config['report_html_url']
    two_txt_html_report_linebreaker = region_config['report_html_line_breaker']
    two_2d0_url = region_config['two_2d0_url']
    two_7d0_url = region_config['two_7d0_url']
    ocean_name = region_config['ocean_name']
 
    contents = urllib.request.urlopen(two_txt_html_url).read().decode("utf-8") 
    print(contents)
    clean_left = contents.partition("<pre>")[2]
    clean_right = clean_left.partition("</pre>")[0]

    message = clean_right
    temp_split_message = message.split(two_txt_html_report_linebreaker)

    full_split_message = temp_split_message[4:]
    full_message = os.linesep.join(full_split_message)

    if "1." in full_message:
        partial_message = full_message.partition("1.")[0]
    else:
        partial_message = full_message

    print(partial_message)
    print(f'partial_message length: {len(partial_message)}')
    print(f'full_message length: {len(full_message)}')

    if len(partial_message) > 300:
        partial_message = partial_message[0:300]
   
    urllib.request.urlretrieve(two_2d0_url, "two_2d0.png")
    urllib.request.urlretrieve(two_7d0_url, "two_7d0.png")

    poster = Poster(pds_url, bluesky_user, bluesky_pass)

    two_2d0_filename = 'two_2d0.png'
    two_7d0_filename = 'two_7d0.png'

    two_2d0_alt_text = f'tropical weather outlook over the next 2 days greyscale satellite image of {ocean_name} Ocean for\n{full_message}'
    two_7d0_alt_text = f'tropical weather outlook over the next 7 days color illustrated image of {ocean_name} Ocean for\n{full_message}'

    images = []

    if do_uploads:
        images = poster.add_image(images, two_2d0_filename, two_2d0_alt_text)
        images = poster.add_image(images, two_7d0_filename, two_7d0_alt_text)

    if do_post:
        resp = poster.create_post(partial_message, images)

        print("createRecord response:", file=sys.stderr)
        print(json.dumps(resp.json(), indent=2))

if __name__ == '__main__':
    main()
