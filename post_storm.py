#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone


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


def main():
    result_file = sys.argv[1] if len(sys.argv) > 1 else 'result.json'

    with open(result_file) as f:
        data = json.load(f)

    new_storms = data.get('new_storms', [])
    if not new_storms:
        print('No new storms to post')
        return

    will_skeet = os.getenv('WILL_SKEET', 'False')

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

        from atproto import Client, models

        client = Client()
        client.login(bluesky_user, bluesky_pass)

        link_text = f'{storm_name} Public Advisory'
        message_text = f'{link_text}\n{gist}'

        os.makedirs('tmp', exist_ok=True)
        urllib.request.urlretrieve(images['5day_cone'], 'tmp/img_5day.png')
        urllib.request.urlretrieve(images['current_wind'], 'tmp/img_wind.png')

        with open('tmp/img_5day.png', 'rb') as f:
            img1_data = f.read()
        with open('tmp/img_wind.png', 'rb') as f:
            img2_data = f.read()

        img1_upload = client.com.atproto.repo.upload_blob(img1_data)
        img2_upload = client.com.atproto.repo.upload_blob(img2_data)

        embed_images = [
            models.AppBskyEmbedImages.Image(alt=image_alts['5day_cone'], image=img1_upload.blob),
            models.AppBskyEmbedImages.Image(alt=image_alts['current_wind'], image=img2_upload.blob),
        ]
        embed = models.AppBskyEmbedImages.Main(images=embed_images)

        facets = [
            {
                'index': {'byteStart': 0, 'byteEnd': len(link_text)},
                'features': [
                    {'$type': 'app.bsky.richtext.facet#link', 'uri': advisory_url}
                ],
            }
        ]

        post = models.AppBskyFeedPost.Main(
            createdAt=datetime.now(timezone.utc).isoformat(),
            text=message_text,
            embed=embed,
            facets=facets,
        )

        client.com.atproto.repo.create_record(
            models.ComAtprotoRepoCreateRecord.Data(
                repo=client.me.did,
                collection=models.ids.AppBskyFeedPost,
                record=post,
            )
        )

        print('  posted!')


if __name__ == '__main__':
    main()
