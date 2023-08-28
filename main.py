#!/usr/bin/env python3

from datetime import datetime, timezone
import os
from time import sleep
from atproto import Client, models
import urllib.request

def main():
    # two_txt_html_url = 'https://www.nhc.noaa.gov/xgtwo/two_atl_txt.html'
    two_txt_html_url = os.environ.get('REPORT_HTML_URL')
    contents = urllib.request.urlopen(two_txt_html_url).read().decode("utf-8") 
    clean_left = contents.partition("<pre>")[2]
    clean_right = clean_left.partition("</pre>")[0]

    message = clean_right
    temp_split_message = message.splitlines()

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

    # two_2d0_url = 'https://www.nhc.noaa.gov/xgtwo/two_atl_2d0.png'
    # two_7d0_url = 'https://www.nhc.noaa.gov/xgtwo/two_atl_7d0.png'
    two_2d0_url = os.environ.get('TWO_2D0_URL')
    two_7d0_url = os.environ.get('TWO_7D0_URL')
    ocean_name = os.environ.get('OCEAN_NAME')
    
    urllib.request.urlretrieve(two_2d0_url, "two_2d0.png")
    urllib.request.urlretrieve(two_7d0_url, "two_7d0.png")

    bluesky_user = os.environ.get('BLUESKY_USER')
    bluesky_pass = os.environ.get('BLUESKY_PASS')
    will_skeet = os.getenv('WILL_SKEET', False)

    client = Client()
    client.login(bluesky_user, bluesky_pass)

    print(f'will_skeet: {will_skeet}')

    if will_skeet == 'True' or will_skeet == 'true':
        print('skeetin')

        with open('two_2d0.png', 'rb') as f2:
            two_2d0_img_data = f2.read()
        with open('two_7d0.png', 'rb') as f7:
            two_7d0_img_data = f7.read()

        two_2d0_upload = client.com.atproto.repo.upload_blob(two_2d0_img_data)
        two_7d0_upload = client.com.atproto.repo.upload_blob(two_7d0_img_data)
        images = [
            models.AppBskyEmbedImages.Image(alt='tropical weather outlook over the next 2 days greyscale satellite image of ' + ocean_name + ' Ocean for\n', image=two_2d0_upload.blob),
            models.AppBskyEmbedImages.Image(alt='tropical weather outlook over the next 7 days color illustrated image of ' + ocean_name + ' Ocean for\n', image=two_7d0_upload.blob),
        ]
        embed = models.AppBskyEmbedImages.Main(images=images)

        client.com.atproto.repo.create_record(
            models.ComAtprotoRepoCreateRecord.Data(
                repo=client.me.did,
                collection=models.ids.AppBskyFeedPost,
                record=models.AppBskyFeedPost.Main(
                    createdAt=datetime.now().isoformat(), text=partial_message, embed=embed
                ),
            )
        )

    else:
        print('no skeetin')
    


if __name__ == '__main__':
    main()


