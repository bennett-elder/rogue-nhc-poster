#!/usr/bin/env python3

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASIN_RSS_URLS = {
    'ATL':  'https://www.nhc.noaa.gov/index-at.xml',
    'ATL-ES': 'https://www.nhc.noaa.gov/index-at-sp.xml',
    'EPAC': 'https://www.nhc.noaa.gov/index-ep.xml',
    'EPAC-ES': 'https://www.nhc.noaa.gov/index-ep-sp.xml',
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


def parse_rss_storms(xml_content, basin=''):
    root = ET.fromstring(xml_content)
    storms = []

    for item in root.iter('item'):
        title_el = item.find('title')
        title = title_el.text.strip() if title_el is not None and title_el.text else ''

        # Check if this is a Spanish feed item (no nhc:Cyclone element)
        cyclone = item.find(f'{{{NHC_NS}}}Cyclone')
        
        if cyclone is not None:
            # English feed format - has nhc:Cyclone element
            def get(tag):
                el = cyclone.find(f'{{{NHC_NS}}}{tag}')
                return el.text.strip() if el is not None and el.text else ''

            atcf = get('atcf')
            if not atcf:
                continue

            link_el = item.find('link')
            link = link_el.text.strip() if link_el is not None and link_el.text else ''

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
        else:
            # Spanish feed format - parse from title and description
            # Title format: "Depresión Tropical Six-E Aviso Publico* Numero 1"
            # Link format: "https://www.nhc.noaa.gov/text/refresh/MIATASEP1+shtml/..."
            # Description contains: "SNM Miami FL  EP062026"
            
            # Only process "Aviso Publico" (Public Advisory) items
            if 'Aviso Publico' not in title:
                continue
            
            # Extract storm name from title (e.g., "Six-E" from "Depresión Tropical Six-E Aviso Publico* Numero 1")
            name_match = re.search(r'(?:Depresión Tropical|Tropical Depression|Tormenta Tropical|Tropical Storm|Huracán|Hurricane)\s+([A-Za-z]+-[A-Za-z]+|[A-Za-z]+)', title)
            if not name_match:
                continue
            storm_name = name_match.group(1)
            
            # Extract ATC code from description (e.g., "EP062026" from "SNM Miami FL  EP062026")
            atcf_match = re.search(r'SNM Miami FL\s+([A-Z]{2}\d{6})', title + ' ' + (item.find('description').text if item.find('description') is not None else ''))
            if not atcf_match:
                continue
            atcf = atcf_match.group(1)
            
            # Extract link
            link_el = item.find('link')
            link = link_el.text.strip() if link_el is not None and link_el.text else ''

            # Extract wallet from atcf AL022026 or EP052026 or EP062026
            wallet_suffix = atcf[2:4]
            wallet_prefix = atcf[:2]
            if wallet_prefix == 'AL':
                wallet_prefix = 'AT'
            wallet = wallet_prefix + wallet_suffix
            
            # Determine storm type from title
            if 'Depresión Tropical' in title or 'Tropical Depression' in title:
                storm_type = 'Tropical Depression'
            elif 'Tormenta Tropical' in title or 'Tropical Storm' in title:
                storm_type = 'Tropical Storm'
            elif 'Huracán' in title or 'Hurricane' in title:
                storm_type = 'Hurricane'
            else:
                storm_type = ''
            
            desc_el = item.find('description')
            description = desc_el.text.strip() if desc_el is not None and desc_el.text else ''

            pubdate_el = item.find('pubDate')
            pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ''

            storms.append({
                'name': storm_name,
                'type': storm_type,
                'atcf': atcf,
                'wallet': wallet,
                'link': link,
                'title': title,
                'description': description,
                'pubDate': pubdate,
            })

    return storms


def get_storm_image_urls(wallet, atcf):
    storm_num = atcf[2:4]
    basin = wallet[:2]
    base_url = f'https://www.nhc.noaa.gov/storm_graphics/{basin}{storm_num}/{atcf}'
    return {gtype: f'{base_url}_{gtype}.png' for gtype in STORM_GRAPHIC_TYPES}


def get_storm_advisory_url(wallet, basin=''):
    # Spanish advisory URLs use different prefixes:
    # - Atlantic: MIATASEP{wallet}+shtml/
    # - Eastern Pacific: MIATASEP{wallet}+shtml/
    if basin == 'ATL-ES':
        return f'https://www.nhc.noaa.gov/text/refresh/MIATAS{wallet}+shtml/'
    elif basin == 'EPAC-ES':
        return f'https://www.nhc.noaa.gov/text/refresh/MIATAS{wallet}+shtml/'
    else:
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
    basins = os.environ.get('BASINS', 'ATL,ATL-ES,EPAC,CPAC,EPAC-ES').split(',')
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
            storms = parse_rss_storms(xml_content, basin)
        except ET.ParseError as e:
            print(f'  ERROR parsing XML from {basin}: {e}', file=sys.stderr)
            continue

        print(f'  Found {len(storms)} active storm(s)', file=sys.stderr)

        for storm in storms:
            atcf = storm['atcf']
            wallet = storm['wallet']
            storm_name = storm['name'] or '(unnamed)'

            is_new = atcf not in known_storms
            if is_new:
                print(f'  *** NEW STORM: {storm_name} ({atcf}) ***', file=sys.stderr)

            storm['basin'] = basin
            # storm['advisory_url'] = get_storm_advisory_url(storm['wallet'], basin)
            images = get_storm_image_urls(wallet, atcf)
            if '-ES' in basin:
                images['5day_cone'] = images['5day_cone'].replace('_5day_cone.png', '_5day_cone_es.png')
                images['3day_cone'] = images['3day_cone'].replace('_3day_cone.png', '_3day_cone_es.png')
            storm['images'] = images
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