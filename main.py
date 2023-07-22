#!/usr/bin/env python3

from datetime import datetime, timezone
import os
from time import sleep
from atproto import Client
import urllib.request

def main():
    two_atl_txt_html_url = 'https://www.nhc.noaa.gov/xgtwo/two_atl_txt.html'
    contents = urllib.request.urlopen(two_atl_txt_html_url).read().decode("utf-8") 
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

    two_atl_2d0_url = 'https://www.nhc.noaa.gov/xgtwo/two_atl_2d0.png'
    two_atl_7d0_url = 'https://www.nhc.noaa.gov/xgtwo/two_atl_7d0.png'
    
    urllib.request.urlretrieve(two_atl_2d0_url, "two_atl_2d0.png")
    urllib.request.urlretrieve(two_atl_7d0_url, "two_atl_7d0.png")

    bluesky_user = os.environ.get('BLUESKY_USER')
    bluesky_pass = os.environ.get('BLUESKY_PASS')
    will_skeet = os.getenv('WILL_SKEET', False)

    client = Client()
    client.login(bluesky_user, bluesky_pass)

    print(will_skeet)

    if will_skeet == 'True' or will_skeet == 'true':
        print('skeetin')
        with open('two_atl_2d0.png', 'rb') as f:
            img_data = f.read()

            client.send_image(
                text=partial_message, image=img_data, image_alt='2 day outlook greyscale representation of Atlantic Ocean for\n' + full_message
            )
        with open('two_atl_7d0.png', 'rb') as f:
            img_data = f.read()

            client.send_image(
                text=partial_message, image=img_data, image_alt='7 day outlook color representation of Atlantic Ocean for\n' + full_message
            )
    else:
        print('no skeetin')
    


if __name__ == '__main__':
    main()


