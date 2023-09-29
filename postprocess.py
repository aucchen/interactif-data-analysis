# TODO: load interact-IF results
import datetime
import time
import traceback

import urllib.request
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

import pandas as pd

df = pd.read_csv('intro_posts_3.tsv', sep='\t')
#df_2 = pd.read_csv('intro_posts_2.tsv', sep='\t')

#options = Options()
#options.headless = True
#driver = webdriver.Firefox(options=options)

# TODO: use the tumblr API instead?
with open('consumer_key') as f:
    consumer_key = f.read().strip()
with open('secret_key') as f:
    consumer_secret = f.read().strip()
with open('oauth_token') as f:
    oauth_token = f.read().strip()
with open('oauth_verifier') as f:
    oauth_verifier = f.read().strip()

import pytumblr
client = pytumblr.TumblrRestClient(consumer_key, consumer_secret, oauth_token, oauth_verifier)


def process_url(url):
    "Converts an x.tumblr.com url to a blogname and an id"
    components = url.split('/')
    post_id = components[-1]
    username = components[2].split('.')[0]
    return username, post_id

def get_origin_data(url, client):
    "Gets the original post date, and the date of the last update"
    username, post_id = process_url(url)
    target_post = client.posts(username, id=int(post_id))
    if 'errors' in target_post:
        print('Error:', target_post)
        return target_post
    if 'meta' in target_post and 'status' in target_post['meta']:
        status = target_post['meta']['status']
        if status == 403:
            print('Error: post cannot be read.')
            return target_post
    intro_date = target_post['posts'][0]['date']
    first_post = client.posts(username, limit=1)
    last_update_date = first_post['posts'][0]['date']
    intro_date = datetime.datetime.strptime(intro_date, '%Y-%m-%d %X %Z')
    last_update_date = datetime.datetime.strptime(last_update_date, '%Y-%m-%d %X %Z')
    return intro_date, last_update_date, target_post, first_post

def get_origin_update_dates(df, new_rows=None, df_2=None):
    if new_rows is None:
        new_rows = []
    can_use_client = True
    for i, row in df.iterrows():
        url = row['Intro_URL']
        if_url = row['Interact_IF_URL']
        new_row = row.copy()
        if df_2 is not None:
            if if_url in df_2['Interact_IF_URL']:
                new_row = df_2[df_2['Interact_IF_URL']==if_url].iloc[0].copy()
        if not isinstance(url, str):
            new_rows.append(new_row)
            continue
        if can_use_client and (not row['Intro_date'] or pd.isna(row['Intro_date'])) and pd.isna(row['Current_status']):
            print(url)
            try:
                intro_date, last_update_date, target_post, first_post = get_origin_data(url, client)
            except Exception as e:
                if type(e) == ValueError:
                    print(e)
                    new_rows.append(new_row)
                    continue
                error = get_origin_data(url, client)
                print(error)
                if error['meta']['status'] == 429:
                    can_use_client = False
                elif error['meta']['status'] == 404:
                    new_row['Current_status'] = 'not available'
                else:
                    pass
                traceback.print_tb(e.__traceback__)
                #new_row['Demo_url'] = ''
                new_rows.append(new_row)
                continue
            new_row['Intro_date'] = intro_date.strftime('%m/%d/%Y')
            new_row['Last_update_date'] = last_update_date.strftime('%m/%d/%Y')
            print(new_row['Game_name'], new_row['Intro_date'], new_row['Last_update_date'])
            if not row['Current_status'] or pd.isna(row['Current_status']):
                # TODO: get demo link (itch.io or dashingdon)
                try:
                    post_body = target_post['posts'][0]['body']
                    soup = BeautifulSoup(post_body, 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        href = link.attrs['href']
                        if 'dashingdon' in href or 'itch.io' in href:
                            new_row['Demo_url'] = href
                            new_row['Current_status'] = 'demo'
                            print('demo:', href)
                        if 'forum.choiceofgames.com' in href:
                            new_row['Forum_url'] = href
                            print('forum url:', href)
                except Exception as e:
                    print(e)
                    traceback.print_tb(e.__traceback__)
        if 'Demo_url' not in new_row:
            new_row['Demo_url'] = ''
        if 'Forum_url' not in new_row:
            new_row['Forum_url'] = ''
        new_rows.append(new_row)
    new_df = pd.DataFrame(new_rows)
    return new_df

def update_df_local(df):
    "Updates a dataframe without doing client calls."
    new_df = df.copy()
    for i, row in df.iterrows():
        if not pd.isna(row['Intro_date']) and pd.isna(row['Current_status']):
            # if there is no demo link, assume that there's no change in status
            new_df.loc[i, 'Current_status'] = row['Intro_status']
        if isinstance(row['Demo_url'], str) and 'href.li' in row['Demo_url']:
            new_df.loc[i, 'Demo_url'] = row['Demo_url'].split('?')[1]
        if isinstance(row['Forum_url'], str) and 'href.li' in row['Forum_url']:
            new_df.loc[i, 'Forum_url'] = row['Forum_url'].split('?')[1]
    return new_df

if __name__ == '__main__':
    new_rows = []
    #df_2.index = df_2['Interact_IF_URL']
    new_df = get_origin_update_dates(df, new_rows)#, df_2)
    new_df_2 = pd.DataFrame(new_rows)
    new_df_2 = update_df_local(new_df_2)
    new_df_2.to_csv('intro_posts_3.tsv', sep='\t', index=None)

