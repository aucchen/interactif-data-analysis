import datetime
import time

import urllib.request
from bs4 import BeautifulSoup

keys = ['Game_name',
        'Intro_URL',
        'Interact_IF_URL',
        'Intro_date',
        'Interact_IF_date',
        'notes',
        'Last_update_date',
        'Intro_status',
        'Current_status',
        'Demo_deactivation_completion_date',
        'Platform',
        'num_ratings',
        'rating',
        'genres'
        ]

new_url = 'https://interact-if.tumblr.com/tagged/if%3A%20intro'

def process_url(new_url):
    with urllib.request.urlopen(new_url) as fp:
        data = fp.read()
        html = data.decode("utf8")
    soup = BeautifulSoup(html, 'html.parser')
    posts = soup.find_all('article')
    processed_posts = []
    for post in posts:
        new_row = {x: '' for x in keys}
        # get tags - 'status: wip' must be in tags. and 'if: visual novel' must not be in tags.
        # if 'status: demo' in tags, it's a demo
        tags_div = post.find('div', attrs={'class': 'tags'})
        all_tags = [tag.contents[0] for tag in tags_div.children]
        new_row['Game_name'] = all_tags[0]
        all_tags = set(all_tags)
        if 'if: visual novel' in all_tags or 'visual novels' in all_tags or 'renpy game' in all_tags:
            continue
        if 'status: completed' in all_tags or 'status: complete' in all_tags:
            continue
        if 'twine game' in all_tags:
            new_row['Platform'] = 'twine'
        if 'cscript game' in all_tags:
            new_row['Platform'] = 'choicescript'
        if 'status: demo' in all_tags:
            new_row['Intro_status'] = 'demo'
        if 'status: no demo' in all_tags:
            new_row['Intro_status'] = 'no demo'
        if 'status: discontinued' in all_tags or 'discontinued' in all_tags:
            new_row['Current_status'] = 'discontinued'
        if 'status: hiatus' in all_tags or 'hiatus' in all_tags:
            new_row['Current_status'] = 'hiatus'
        genres = all_tags.difference(['if: intro', 'twine game', 'cscript game', 'status: demo', 'status: no demo', 'status: wip', 'interactive fiction', new_row['Game_name']])
        genres = ','.join(list(genres))
        new_row['genres'] = genres
        # get URLs
        try:
            intro_url = post.find('a', attrs={'class': 'user'}).attrs['href']
            new_row['Intro_URL'] = intro_url
        except:
            intro_url = 'N/A'
        print(intro_url)
        if intro_url == 'N/A':
            new_row['Current_status'] = 'deactivated?'
        base_url_date = post.find('a', attrs={'class': 'dt'})
        new_row['Interact_IF_URL'] = base_url_date.attrs['href']
        # get dates
        interact_if_date = base_url_date.contents[0]
        interact_if_date = datetime.datetime.strptime(interact_if_date, '%d %b %y')
        new_row['Interact_IF_date'] = interact_if_date.strftime('%m/%d/%Y')
        # get notes
        notes = post.find('a', attrs={'class': 'notecount'}).contents[0]
        notes = int(notes.split()[0].replace(',', ''))
        new_row['notes'] = notes
        print(new_row['Game_name'])
        processed_posts.append(new_row)
    try:
        next_url = soup.find('a', attrs={'title': 'next page'})
        next_url = next_url.attrs['href']
    except:
        next_url = None
    return processed_posts, next_url


if __name__ == '__main__':
    all_processed_posts = []
    processed_posts, next_url = process_url(new_url)
    all_processed_posts += processed_posts
    while next_url:
        new_url = 'https://interact-if.tumblr.com' + next_url
        processed_posts, next_url = process_url(new_url)
        all_processed_posts += processed_posts
        time.sleep(0.5)
    import pandas as pd
    df = pd.DataFrame(all_processed_posts)
    print(df.head())
    df.to_csv('intro_posts.tsv', index=None, sep='\t')
