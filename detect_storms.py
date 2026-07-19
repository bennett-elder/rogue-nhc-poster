#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASIN_RSS_URLS = {
    'ATL':  'https://www.nhc.noaa.gov/index-at.xml',
    'EPAC': 'https://www.nhc.noaa.gov/index-ep.xml',
    'CPAC': 'https://www.nhc.noaa.gov/index-cp.xml',
}

NHC_NS = 'https://www.nhc.noaa.gov'

STORM_GRAPHIC_TYPES = [
    '5day_cone',
    '3day_cone',
    'current_wind',
    'wind_probs_34_F120',
]

GRAPHIC_ALT_TEXT = {
    '5day_cone':          '5-day forecast cone for {name}',
    '3day_cone':          '3-day forecast cone for {name}',
    'current_wind':       'Surface wind field for {name}',
    'wind_probs_34_F120': '34-knot wind speed probability for {name}',
}


def fetch_url(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'rogue-nhc-poster/1.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')


def parse_rss_storms(xml_content):
    root = ET.fromstring(xml_content)
    storms = []

    for item in root.iter('item'):
        cyclone = item.find(f'{{{NHC_NS}}}Cyclone')
        if cyclone is None:
            continue

        def get(tag):
            el = cyclone.find(f'{{{NHC_NS}}}{tag}')
            return el.text.strip() if el is not None and el.text else ''

        atcf = get('atcf')
        if not atcf:
            continue

        link_el = item.find('link')
        link = link_el.text.strip() if link_el is not None and link_el.text else ''

        title_el = item.find('title')
        title = title_el.text.strip() if title_el is not None and title_el.text else ''

        desc_el = item.find('description')
        description = desc_el.text.strip() if desc_el is not None and desc_el.text else ''

        pubdate_el = item.find('pubDate')
        pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ''

        storms.append({
            'name': get('name'),
            'type': get('type'),
            'atcf': atcf,
            'wallet': get('wallet'),
            'link': link,
            'title': title,
            'description': description,
            'pubDate': pubdate,
        })

    return storms


def get_storm_image_urls(atcf):
    basin = atcf[:2]
    storm_num = atcf[2:4]
    base_url = f'https://www.nhc.noaa.gov/storm_graphics/{basin}{storm_num}/{atcf}'
    return {gtype: f'{base_url}_{gtype}.png' for gtype in STORM_GRAPHIC_TYPES}


def get_storm_advisory_url(wallet):
    return f'https://www.nhc.noaa.gov/text/refresh/MIATCP{wallet}+shtml/'


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    known_storms_raw = os.environ.get('KNOWN_STORMS', '')
    if known_storms_raw:
        try:
            return json.loads(known_storms_raw)
        except json.JSONDecodeError:
            pass
    return {}


def save_state(state_file, known_storms):
    os.makedirs(os.path.dirname(state_file) or '.', exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(known_storms, f, indent=2)
        f.write('\n')


def main():
    basins = os.environ.get('BASINS', 'ATL,EPAC,CPAC').split(',')
    state_file = os.environ.get('STATE_FILE', 'known_storms.json')

    known_storms = load_state(state_file)
    active_storms = []

    for basin in basins:
        basin = basin.strip()
        rss_url = BASIN_RSS_URLS.get(basin)
        if rss_url is None:
            print(f'Unknown basin: {basin}', file=sys.stderr)
            continue

        print(f'Checking {basin} RSS feed...', file=sys.stderr)

        try:
            xml_content = fetch_url(rss_url)
        except Exception as e:
            print(f'  ERROR fetching {rss_url}: {e}', file=sys.stderr)
            continue

        try:
            storms = parse_rss_storms(xml_content)
        except ET.ParseError as e:
            print(f'  ERROR parsing XML from {basin}: {e}', file=sys.stderr)
            continue

        print(f'  Found {len(storms)} active storm(s)', file=sys.stderr)

        for storm in storms:
            atcf = storm['atcf']
            storm_name = storm['name'] or '(unnamed)'

            is_new = atcf not in known_storms
            if is_new:
                print(f'  *** NEW STORM: {storm_name} ({atcf}) ***', file=sys.stderr)

            storm['basin'] = basin
            storm['images'] = get_storm_image_urls(atcf)
            storm['advisory_url'] = get_storm_advisory_url(storm['wallet'])
            storm['detected_at'] = datetime.now(timezone.utc).isoformat()
            storm['image_alts'] = {
                gtype: GRAPHIC_ALT_TEXT[gtype].format(name=storm_name)
                for gtype in STORM_GRAPHIC_TYPES
            }

            active_storms.append(storm)

            if is_new:
                known_storms[atcf] = {
                    'name': storm_name,
                    'type': storm['type'],
                    'wallet': storm['wallet'],
                    'first_seen': storm['detected_at'],
                }

    save_state(state_file, known_storms)

    output = {
        'active_storms': active_storms,
        'known_storms': known_storms,
        'last_checked': datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()