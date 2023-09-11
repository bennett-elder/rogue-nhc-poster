#!/usr/bin/env python3

from datetime import datetime, timezone
import os
from time import sleep
from atproto import Client, models
import urllib.request

def main():
    storm_name = os.environ.get('STORM_NAME')

    link_url = os.environ.get('LINK_URL')

    img1_url = os.environ.get('IMG1_URL')
    img1_alt = os.environ.get('IMG1_ALT')
    img2_url = os.environ.get('IMG2_URL')
    img2_alt = os.environ.get('IMG2_ALT')
    img3_url = os.environ.get('IMG3_URL')
    img3_alt = os.environ.get('IMG3_ALT')
    img4_url = os.environ.get('IMG4_URL')
    img4_alt = os.environ.get('IMG4_ALT')
    
    bluesky_user = os.environ.get('BLUESKY_USER')
    bluesky_pass = os.environ.get('BLUESKY_PASS')
    will_skeet = os.getenv('WILL_SKEET', False)


    contents = urllib.request.urlopen(link_url).read().decode("utf-8") 
    clean_left = contents.partition("<pre>")[2]
    clean_right = clean_left.partition("</pre>")[0]

    header_stripped = clean_right.partition("...")[2]
    gist = header_stripped.partition("SUMMARY")[0]

    cleaned_gist = gist.replace("""...
...""", ". ").replace("""
""", " ").replace("...", "")

    print(cleaned_gist)

    client = Client()
    client.login(bluesky_user, bluesky_pass)

    print(f'will_skeet: {will_skeet}')

    if will_skeet == 'True' or will_skeet == 'true':
        print('skeetin')

        link_text = storm_name + ' Public Advisory'
        length_of_link_text = len(link_text)

        message_text = link_text + """
""" + cleaned_gist

        urllib.request.urlretrieve(img1_url, "img1")
        urllib.request.urlretrieve(img2_url, "img2")
        # urllib.request.urlretrieve(img3_url, "img3")
        # urllib.request.urlretrieve(img4_url, "img4")

        with open('img1', 'rb') as f1:
            img1_data = f1.read()
        with open('img2', 'rb') as f2:
            img2_data = f2.read()
        # with open('img3', 'rb') as f3:
        #     img3_data = f3.read()
        # with open('img4', 'rb') as f4:
        #     img4_data = f4.read()
        
        img1_upload = client.com.atproto.repo.upload_blob(img1_data)
        img2_upload = client.com.atproto.repo.upload_blob(img2_data)
        # img3_upload = client.com.atproto.repo.upload_blob(img3_data)
        # img4_upload = client.com.atproto.repo.upload_blob(img4_data)
        
        images = [
            models.AppBskyEmbedImages.Image(alt=img1_alt, image=img1_upload.blob),
            models.AppBskyEmbedImages.Image(alt=img2_alt, image=img2_upload.blob),
            # models.AppBskyEmbedImages.Image(alt=img3_alt, image=img3_upload.blob),
            # models.AppBskyEmbedImages.Image(alt=img4_alt, image=img4_upload.blob),
        ]
        embed = models.AppBskyEmbedImages.Main(images=images)

        facets = []
        facets.append(
            {
                "index": {
                    "byteStart": 0,
                    "byteEnd": length_of_link_text,
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        # NOTE: URI ("I") not URL ("L")
                        "uri": link_url,
                    }
                ],
            }
        )

        post = models.AppBskyFeedPost.Main(
                    createdAt=datetime.now().isoformat(), text=message_text, embed=embed, facets=facets
                )
        
        client.com.atproto.repo.create_record(
            models.ComAtprotoRepoCreateRecord.Data(
                repo=client.me.did,
                collection=models.ids.AppBskyFeedPost,
                record=post,
            )
        )
    else:
        print('no skeetin')

if __name__ == '__main__':
    main()


