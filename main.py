# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:20:02 2020

@author: aliha
@twitter: rockingAli5 
"""

import warnings
import time
import pandas as pd
pd.options.mode.chained_assignment = None
import json
from bs4 import BeautifulSoup as soup
import re 
from collections import OrderedDict
from datetime import datetime as dt
import itertools
import numpy as np
try:
    from tqdm import trange
except ModuleNotFoundError:
    pass


from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By

# options = webdriver.FirefoxOptions()

# options.add_experimental_option('excludeSwitches', ['enable-logging'])


TRANSLATE_DICT = {'Jan': 'Jan',
                 'Feb': 'Feb',
                 'Mac': 'Mar',
                 'Apr': 'Apr',
                 'Mei': 'May',
                 'Jun': 'Jun',
                 'Jul': 'Jul',
                 'Ago': 'Aug',
                 'Sep': 'Sep',
                 'Okt': 'Oct',
                 'Nov': 'Nov',
                 'Des': 'Dec',
                 'Jan': 'Jan',
                 'Feb': 'Feb',
                 'Mar': 'Mar',
                 'Apr': 'Apr',
                 'May': 'May',
                 'Jun': 'Jun',
                 'Jul': 'Jul',
                 'Aug': 'Aug',
                 'Sep': 'Sep',
                 'Oct': 'Oct',
                 'Nov': 'Nov',
                 'Dec': 'Dec'}

main_url = 'https://1xbet.whoscored.com/'



def getLeagueUrls(minimize_window=True):
    
    driver = webdriver.Firefox()

    if minimize_window:
        driver.minimize_window()

    driver.get(main_url)
    league_names = []
    league_urls = []
    try:
        cookie_button = driver.find_element(By.XPATH, '//*[@class=" css-gweyaj"]').click()
    except NoSuchElementException:
        pass
    tournaments_btn = driver.find_element(By.XPATH, '//*[@id="All-Tournaments-btn"]').click()
    n_button = soup(driver.find_element(By.XPATH, '//*[@id="header-wrapper"]/div/div/div/div[4]/div[2]/div/div/div/div[1]/div/div').get_attribute('innerHTML')).find_all('button')
    n_tournaments = []
    for button in n_button:
        id_button = button.get('id')
        driver.find_element(By.ID, id_button).click()
        n_country = soup(driver.find_element(By.XPATH, '//*[@id="header-wrapper"]/div/div/div/div[4]/div[2]/div/div/div/div[2]').get_attribute('innerHTML')).find_all('div', {'class':'TournamentsDropdownMenu-module_countryDropdownContainer__I9P6n'})

        for country in n_country:
            country_id = country.find('div', {'class': 'TournamentsDropdownMenu-module_countryDropdown__8rtD-'}).get('id')

            # Trouver l'élément avec Selenium et cliquer dessus
            country_element = driver.find_element(By.ID, country_id)
            country_element.click()

            html_tournaments_list = driver.find_element(By.XPATH, '//*[@id="header-wrapper"]/div/div/div/div[4]/div[2]/div/div/div/div[2]').get_attribute('innerHTML')

            # Parse le HTML avec BeautifulSoup pour trouver les liens des tournois
            soup_tournaments = soup(html_tournaments_list, 'html.parser')
            tournaments = soup_tournaments.find_all('a')

            # Ajouter les tournois à la liste n_tournaments
            n_tournaments.extend(tournaments)

            driver.execute_script("arguments[0].click();", country_element)


    for tournament in n_tournaments:
        league_name = tournament.get('href').split('/')[-1]
        league_link = main_url[:-1]+tournament.get('href')
        league_names.append(league_name)
        league_urls.append(league_link)

    leagues = {}
    for name,link in zip(league_names,league_urls):
        leagues[name] = link

    driver.close()
    return leagues


def getMatchUrls(comp_urls, competition, season, maximize_window=True):

    driver = webdriver.Firefox()
    
    if maximize_window:
        driver.maximize_window()
    
    comp_url = comp_urls[competition]
    driver.get(comp_url)
    time.sleep(5)
    
    seasons = driver.find_element(By.XPATH, '//*[@id="seasons"]').get_attribute('innerHTML').split(sep='\n')
    seasons = [i for i in seasons if i]
    
    
    for i in range(1, len(seasons)+1):
        if driver.find_element(By.XPATH, '//*[@id="seasons"]/option['+str(i)+']').text == season:
            driver.find_element(By.XPATH, '//*[@id="seasons"]/option['+str(i)+']').click()
            
            time.sleep(5)
            try:
                stages = driver.find_element(By.XPATH, '//*[@id="stages"]').get_attribute('innerHTML').split(sep='\n')
                stages = [i for i in stages if i]
                
                all_urls = []
            
                for i in range(1, len(stages)+1):
                    print(driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').text)
                    if competition == 'Champions League' or competition == 'Europa League':
                        if 'Grp' in driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').text or 'Final Stage' in driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').text:
                            driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').click()
                            time.sleep(5)
                            
                            driver.execute_script("window.scrollTo(0, 400)") 
                            
                            match_urls = getFixtureData(driver)
                            
                            match_urls = getSortedData(match_urls)
                            
                            match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                            
                            all_urls += match_urls2
                        else:
                            continue
                    
                    elif competition == 'Major League Soccer':
                        if 'Grp. ' not in driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').text: 
                            driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').click()
                            time.sleep(5)
                        
                            driver.execute_script("window.scrollTo(0, 400)")
                            
                            match_urls = getFixtureData(driver)
                            
                            match_urls = getSortedData(match_urls)
                            
                            match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                            
                            all_urls += match_urls2
                        else:
                            continue
                        
                    else:
                        driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').click()
                        time.sleep(5)
                    
                        driver.execute_script("window.scrollTo(0, 400)")
                        
                        match_urls = getFixtureData(driver)
                        
                        match_urls = getSortedData(match_urls)
                        
                        match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                        
                        all_urls += match_urls2
                
            except NoSuchElementException:
                all_urls = []
                
                driver.execute_script("window.scrollTo(0, 400)")
                
                match_urls = getFixtureData(driver)
                
                match_urls = getSortedData(match_urls)
                
                match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                
                all_urls += match_urls2
            
            
            remove_dup = [dict(t) for t in {tuple(sorted(d.items())) for d in all_urls}]
            all_urls = getSortedData(remove_dup)
            
            driver.close() 
    
            return all_urls
     
    season_names = [re.search(r'\>(.*?)\<',season).group(1) for season in seasons]
    driver.close() 
    print('Seasons available: {}'.format(season_names))
    raise('Season Not Found.')
    




def getTeamUrls(team, match_urls):
    
    team_data = []
    for fixture in match_urls:
        if fixture['home'] == team or fixture['away'] == team:
            team_data.append(fixture)
    team_data = [a[0] for a in itertools.groupby(team_data)]
                
    return team_data


def getMatchesData(match_urls, minimize_window=True):
    
    matches = []
    
    driver = webdriver.Firefox()
    if minimize_window:
        driver.minimize_window()
    
    try:
        for i in trange(len(match_urls), desc='Getting Match Data'):
            # recommended to avoid getting blocked by incapsula/imperva bots
            time.sleep(7)
            match_data = getMatchData(driver, main_url+match_urls[i]['url'], display=False, close_window=False)
            matches.append(match_data)
    except NameError:
        print('Recommended: \'pip install tqdm\' for a progress bar while the data gets scraped....')
        time.sleep(7)
        for i in range(len(match_urls)):
            match_data = getMatchData(driver, main_url+match_urls[i]['url'], display=False, close_window=False)
            matches.append(match_data)
    
    driver.close()
    
    return matches




def getFixtureData(driver):
    matches_ls = []
    while True:
        initial = driver.page_source
        all_fixtures = driver.find_elements(By.CLASS_NAME, 'Accordion-module_accordion__UuHD0')
        for dates in all_fixtures:
            fixtures = dates.find_elements(By.CLASS_NAME, 'Match-module_row__zwBOn')
            date_row = dates.find_element(By.CLASS_NAME, 'Accordion-module_header__HqzWD')
            for row in fixtures:
                url = row.find_element(By.TAG_NAME, 'a')
                if 'live' in url.get_attribute('href'):
                    # print(url.get_attribute('href'))
                    match_dict = {}
                    element = soup(row.get_attribute('innerHTML'), features='lxml')
                    teams_tag = element.find("div", {"class":"Match-module_teams__sGVeq"})
                    link_tag = element.find("a")
                    match_dict['date'] = date_row.text
                    match_dict['home'] = teams_tag.find_all('a')[0].text
                    match_dict['away'] = teams_tag.find_all('a')[1].text
                    match_dict['score'] = ':'.join([t.text for t in link_tag.find_all('span')])
                    match_dict['url'] = link_tag['href']
                    # print(match_dict)
                    matches_ls.append(match_dict)
        prev_btn = driver.find_element(By.ID, 'dayChangeBtn-prev')
        prev_btn.click()
        time.sleep(1)
        final = driver.page_source
        if initial == final:
            break

    return matches_ls






def translateDate(data):
    
    unwanted = []
    for match in data:
        date = match['date'].split()
        if '?' not in date[0]:
            try:
                match['date'] = ' '.join([TRANSLATE_DICT[date[0]], date[1], date[2]])
            except KeyError:
                print(date)
        else:
            unwanted.append(data.index(match))
    
    # remove matches that got suspended/postponed
    for i in sorted(unwanted, reverse = True):
        del data[i]
    
    return data


def getSortedData(data):
    data = sorted(data, key = lambda i: dt.strptime(i['date'], '%A, %b %d %Y'))
    return data
    



def getMatchData(driver, url, display=True, close_window=True):
    try:
        driver.get(url)
    except WebDriverException:
        driver.get(url)

    time.sleep(5)
    # get script data from page source
    script_content = driver.find_element(By.XPATH, '//*[@id="layout-wrapper"]/script[1]').get_attribute('innerHTML')


    # clean script content
    script_content = re.sub(r"[\n\t]*", "", script_content)
    script_content = script_content[script_content.index("matchId"):script_content.rindex("}")]


    # this will give script content in list form 
    script_content_list = list(filter(None, script_content.strip().split(',            ')))
    metadata = script_content_list.pop(1) 


    # string format to json format
    match_data = json.loads(metadata[metadata.index('{'):])
    keys = [item[:item.index(':')].strip() for item in script_content_list]
    values = [item[item.index(':')+1:].strip() for item in script_content_list]
    for key,val in zip(keys, values):
        match_data[key] = json.loads(val)


    # get other details about the match
    region = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/span[1]').text
    league = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')[0]
    season = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')[1]
    if len(driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')) == 2:
        competition_type = 'League'
        competition_stage = ''
    elif len(driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - '))== 3:
        competition_type = 'Knock Out'
        competition_stage = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')[-1]
    else:
        print('Getting more than 3 types of information about the competition.')

    match_data['region'] = region
    match_data['league'] = league
    match_data['season'] = season
    match_data['competitionType'] = competition_type
    match_data['competitionStage'] = competition_stage


    # sort match_data dictionary alphabetically
    match_data = OrderedDict(sorted(match_data.items()))
    match_data = dict(match_data)
    if display:
        print('Region: {}, League: {}, Season: {}, Match Id: {}'.format(region, league, season, match_data['matchId']))
    
    
    if close_window:
        driver.close()
        
    return match_data





def createEventsDF(data):
    events = data['events']
    for event in events:
        event.update({'matchId' : data['matchId'],
                        'startDate' : data['startDate'],
                        'startTime' : data['startTime'],
                        'score' : data['score'],
                        'ftScore' : data['ftScore'],
                        'htScore' : data['htScore'],
                        'etScore' : data['etScore'],
                        'venueName' : data['venueName'],
                        'maxMinute' : data['maxMinute']})
    events_df = pd.DataFrame(events)

    # clean period column
    events_df['period'] = pd.json_normalize(events_df['period'])['displayName']

    # clean type column
    events_df['type'] = pd.json_normalize(events_df['type'])['displayName']

    # clean outcomeType column
    events_df['outcomeType'] = pd.json_normalize(events_df['outcomeType'])['displayName']

    # clean outcomeType column
    try:
        x = events_df['cardType'].fillna({i: {} for i in events_df.index})
        events_df['cardType'] = pd.json_normalize(x)['displayName'].fillna(False)
    except KeyError:
        events_df['cardType'] = False

    eventTypeDict = data['matchCentreEventTypeJson']  
    events_df['satisfiedEventsTypes'] = events_df['satisfiedEventsTypes'].apply(lambda x: [list(eventTypeDict.keys())[list(eventTypeDict.values()).index(event)] for event in x])

    # clean qualifiers column
    try:
        for i in events_df.index:
            row = events_df.loc[i, 'qualifiers'].copy()
            if len(row) != 0:
                for irow in range(len(row)):
                    row[irow]['type'] = row[irow]['type']['displayName']
    except TypeError:
        pass


    # clean isShot column
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        if 'isShot' in events_df.columns:
            events_df['isShot'] = events_df['isShot'].replace(np.nan, False).infer_objects(copy=False)
        else:
            events_df['isShot'] = False

        # clean isGoal column
        if 'isGoal' in events_df.columns:
            events_df['isGoal'] = events_df['isGoal'].replace(np.nan, False).infer_objects(copy=False)
        else:
            events_df['isGoal'] = False

    # add player name column
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        events_df.loc[events_df.playerId.notna(), 'playerId'] = events_df.loc[events_df.playerId.notna(), 'playerId'].astype(int).astype(str)    
    player_name_col = events_df.loc[:, 'playerId'].map(data['playerIdNameDictionary']) 
    events_df.insert(loc=events_df.columns.get_loc("playerId")+1, column='playerName', value=player_name_col)

    # add home/away column
    h_a_col = events_df['teamId'].map({data['home']['teamId']:'h', data['away']['teamId']:'a'})
    events_df.insert(loc=events_df.columns.get_loc("teamId")+1, column='h_a', value=h_a_col)


    # adding shot body part column
    events_df['shotBodyType'] =  np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        for i in events_df.loc[events_df.isShot==True].index:
            for j in events_df.loc[events_df.isShot==True].qualifiers.loc[i]:
                if j['type'] == 'RightFoot' or j['type'] == 'LeftFoot' or j['type'] == 'Head' or j['type'] == 'OtherBodyPart':
                    events_df.loc[i, 'shotBodyType'] = j['type']


    # adding shot situation column
    events_df['situation'] =  np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        for i in events_df.loc[events_df.isShot==True].index:
            for j in events_df.loc[events_df.isShot==True].qualifiers.loc[i]:
                if j['type'] == 'FromCorner' or j['type'] == 'SetPiece' or j['type'] == 'DirectFreekick':
                    events_df.loc[i, 'situation'] = j['type']
                if j['type'] == 'RegularPlay':
                    events_df.loc[i, 'situation'] = 'OpenPlay' 

    event_types = list(data['matchCentreEventTypeJson'].keys())
    event_type_cols = pd.DataFrame({event_type: pd.Series([event_type in row for row in events_df['satisfiedEventsTypes']]) for event_type in event_types})
    events_df = pd.concat([events_df, event_type_cols], axis=1)


    return events_df
    



def createMatchesDF(data):
    columns_req_ls = ['matchId', 'attendance', 'venueName', 'startTime', 'startDate',
                      'score', 'home', 'away']
    matches_df = pd.DataFrame(columns=columns_req_ls)
    if type(data) == dict:
        matches_dict = dict([(key,val) for key,val in data.items() if key in columns_req_ls])
        matches_df = pd.DataFrame(matches_dict, columns=columns_req_ls).reset_index(drop=True)
        matches_df[['home', 'away']] = np.nan  
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            matches_df['home'].iloc[0] = [data['home']]
            matches_df['away'].iloc[0] = [data['away']]
    else:
        for match in data:
            matches_dict = dict([(key,val) for key,val in match.items() if key in columns_req_ls])
            matches_df = pd.DataFrame(matches_dict, columns=columns_req_ls).reset_index(drop=True)
    
    matches_df = matches_df.set_index('matchId')        
    return matches_df


import numpy as np
import joblib

FEATURES = ["x", "y", "distance_to_goal", "shot_angle",
            "body_part", "situation", "first_touch", "shot_technique"]

CAT_COLS = ["body_part", "situation", "first_touch", "shot_technique"]

# ---------- Coordinate + feature engineering (WhoScored -> StatsBomb space) ----------

def whoscored_to_statsbomb_xy(x_pct, y_pct):
    # WhoScored: 0-100 (%), StatsBomb: 120x80
    return (x_pct / 100.0) * 120.0, (y_pct / 100.0) * 80.0

def add_distance_and_angle(df):
    goal_x = 120.0
    goal_y = 40.0

    dx = goal_x - df["x"]
    dy = df["y"] - goal_y
    df["distance_to_goal"] = np.sqrt(dx**2 + dy**2)

    # approximate posts on 80-scale
    left_post_y = 36.34
    right_post_y = 43.66

    a1 = np.arctan2(right_post_y - df["y"], goal_x - df["x"])
    a2 = np.arctan2(left_post_y - df["y"], goal_x - df["x"])
    df["shot_angle"] = np.abs(a1 - a2)

    return df

def _qualifier_set(q):
    if not isinstance(q, list):
        return set()
    return set([d.get("type") for d in q if isinstance(d, dict) and "type" in d])

def map_body_part(shotBodyType):
    # StatsBomb encoder classes: Head, Left Foot, Other, Right Foot
    if shotBodyType == "RightFoot":
        return "Right Foot"
    if shotBodyType == "LeftFoot":
        return "Left Foot"
    if shotBodyType in ["Head", "Header", "Headed"]:
        return "Head"
    return "Other"

def map_situation(s):
    # StatsBomb encoder classes: Corner, Free Kick, Kick Off, Open Play, Penalty
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return "Open Play"
    s = str(s)

    if s.lower() in ["openplay", "open_play", "open play"]:
        return "Open Play"
    if "Penalty" in s or s.lower() == "penalty":
        return "Penalty"
    if "Corner" in s:
        return "Corner"
    if "FreeKick" in s or "Free Kick" in s or "Freekick" in s:
        return "Free Kick"
    if "KickOff" in s or "Kick Off" in s:
        return "Kick Off"
    return "Open Play"

def map_first_touch(qset):
    # StatsBomb encoder classes: 'None', 'True'
    return "True" if "FirstTouch" in qset else "None"

def map_shot_technique(qset):
    # StatsBomb encoder classes: Backheel, Diving Header, Half Volley, Lob, Normal, Overhead Kick, Volley
    if "Backheel" in qset:
        return "Backheel"
    if "DivingHeader" in qset or "Diving Header" in qset:
        return "Diving Header"
    if "HalfVolley" in qset or "Half Volley" in qset:
        return "Half Volley"
    if "Lob" in qset:
        return "Lob"
    if "OverheadKick" in qset or "Overhead Kick" in qset:
        return "Overhead Kick"
    if "Volley" in qset:
        return "Volley"
    return "Normal"

def build_xg_features_from_whoscored(df_shots):
    """
    Input: df with WhoScored shots only (isShot==True)
    Output: dataframe with FEATURES columns in StatsBomb feature space (strings for categoricals)
    """
    df = df_shots.copy()

    # x,y -> StatsBomb
    xy = df.apply(lambda r: whoscored_to_statsbomb_xy(r["x"], r["y"]), axis=1, result_type="expand")
    df["x"], df["y"] = xy[0], xy[1]

    qsets = df["qualifiers"].apply(_qualifier_set)

    # categoricals
    df["body_part"] = df["shotBodyType"].apply(map_body_part)
    df["situation"] = df["situation"].apply(map_situation)
    df["first_touch"] = qsets.apply(map_first_touch)
    df["shot_technique"] = qsets.apply(map_shot_technique)

    # numericals
    df = add_distance_and_angle(df)

    return df[FEATURES].copy()

# ---------- Encoding (safe) ----------

def apply_label_encoders_safe(X, label_encoders):
    """
    Uses training label_encoders but safely handles unseen categories by mapping to a fallback
    that DOES exist in the encoder classes.
    """
    X = X.copy()
    fallback = {
        "body_part": "Other",
        "situation": "Open Play",
        "first_touch": "None",
        "shot_technique": "Normal",
    }

    for col, le in label_encoders.items():
        X[col] = X[col].astype(str)

        known = set(le.classes_)
        fb = fallback.get(col, list(le.classes_)[0])
        X[col] = X[col].apply(lambda v: v if v in known else fb)

        X[col] = le.transform(X[col])

    return X

# ---------- Main function to add xG to shots ----------

def add_xg_to_shots_whoscored(df_events, model_path, encoders_path, xg_col="xG_model"):
    """
    Adds xG to all shot events and skips all non-shots.
    Returns df_shots (only shot rows) with xG column.
    """
    model = joblib.load(model_path)
    label_encoders = joblib.load(encoders_path)

    # only shots (skip the rest)
    df_shots = df_events[df_events.get("isShot", False) == True].copy()
    if df_shots.empty:
        return df_shots

    # build features -> encode -> predict
    X = build_xg_features_from_whoscored(df_shots)
    X_enc = apply_label_encoders_safe(X, label_encoders)

    df_shots[xg_col] = model.predict_proba(X_enc)[:, 1]

    return df_shots

def add_xg_to_all_events_whoscored(df_events, model_path, encoders_path, xg_col="xG_model"):
    """
    Voegt een xG-kolom toe aan ALLE events.
    - shots (isShot==True) krijgen model xG
    - rest krijgt 0.0
    """
    df_out = df_events.copy()
    df_out[xg_col] = 0.0  # default: non-shots = 0

    # mask shots
    shot_mask = df_out["isShot"] == True
    if shot_mask.sum() == 0:
        return df_out

    # load model + encoders
    model = joblib.load(model_path)
    label_encoders = joblib.load(encoders_path)

    # build + encode only for shots
    df_shots = df_out.loc[shot_mask].copy()
    X = build_xg_features_from_whoscored(df_shots)
    X_enc = apply_label_encoders_safe(X, label_encoders)

    # predict + write back
    df_out.loc[shot_mask, xg_col] = model.predict_proba(X_enc)[:, 1]

    return df_out

def load_EPV_grid(fname='EPV_grid.csv'):
    """ load_EPV_grid(fname='EPV_grid.csv')
    
    # load pregenerated EPV surface from file. 
    
    Parameters
    -----------
        fname: filename & path of EPV grid (default is 'EPV_grid.csv' in the curernt directory)
        
    Returns
    -----------
        EPV: The EPV surface (default is a (32,50) grid)
    
    """
    epv = np.loadtxt(fname, delimiter=',')
    return epv






def get_EPV_at_location(position,EPV,attack_direction,field_dimen=(106.,68.)):
    """ get_EPV_at_location
    
    Returns the EPV value at a given (x,y) location
    
    Parameters
    -----------
        position: Tuple containing the (x,y) pitch position
        EPV: tuple Expected Possession value grid (loaded using load_EPV_grid() )
        attack_direction: Sets the attack direction (1: left->right, -1: right->left)
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
            
    Returrns
    -----------
        EPV value at input position
        
    """
    
    x,y = position
    if abs(x)>field_dimen[0]/2. or abs(y)>field_dimen[1]/2.:
        return 0.0 # Position is off the field, EPV is zero
    else:
        if attack_direction==-1:
            EPV = np.fliplr(EPV)
        ny,nx = EPV.shape
        dx = field_dimen[0]/float(nx)
        dy = field_dimen[1]/float(ny)
        ix = (x+field_dimen[0]/2.-0.0001)/dx
        iy = (y+field_dimen[1]/2.-0.0001)/dy
        return EPV[int(iy),int(ix)]



                

def to_metric_coordinates_from_whoscored(data,field_dimen=(106.,68.) ):
    '''
    Convert positions from Whoscored units to meters (with origin at centre circle)
    '''
    x_columns = [c for c in data.columns if c[-1].lower()=='x'][:2]
    y_columns = [c for c in data.columns if c[-1].lower()=='y'][:2]
    x_columns_mod = [c+'_metrica' for c in x_columns]
    y_columns_mod = [c+'_metrica' for c in y_columns]
    data[x_columns_mod] = (data[x_columns]/100*106)-53
    data[y_columns_mod] = (data[y_columns]/100*68)-34
    return data

def addEpvToDataFrame(data):

    # loading EPV data
    EPV = load_EPV_grid('EPV_grid.csv')

    # converting opta coordinates to metric coordinates
    data = to_metric_coordinates_from_whoscored(data)

    # calculating EPV for events
    EPV_difference = []
    for i in data.index:
        if data.loc[i, 'type'] == 'Pass' and data.loc[i, 'outcomeType'] == 'Successful':
            start_pos = (data.loc[i, 'x_metrica'], data.loc[i, 'y_metrica'])
            start_epv = get_EPV_at_location(start_pos, EPV, attack_direction=1)
            
            end_pos = (data.loc[i, 'endX_metrica'], data.loc[i, 'endY_metrica'])
            end_epv = get_EPV_at_location(end_pos, EPV, attack_direction=1)
            
            diff = end_epv - start_epv
            EPV_difference.append(diff)
            
        else:
            EPV_difference.append(np.nan)
    
    data = data.assign(EPV_difference = EPV_difference)
    
    
    # dump useless columns
    drop_cols = ['x_metrica', 'endX_metrica', 'y_metrica',
                 'endY_metrica']
    data.drop(drop_cols, axis=1, inplace=True)
    data.rename(columns={'EPV_difference': 'EPV'}, inplace=True)
    
    return data

team_id_to_name = {
    876: "FC Volendam",
    116: "NEC Nijmegen",
    758: "FC Groningen",
    868: "PEC Zwolle",
    130: "Ajax",
    242: "Fortuna Sittard",
    783: "NAC Breda",
    113: "FC Twente",
    303: "Sparta Rotterdam",
    874: "Go Ahead Eagles",
    129: "PSV",
    243: "AZ",
    867: "Excelsior",
    287: "SC Heerenveen",
    762: "FC Emmen",
    256: "Feyenoord",
    128: "FC Utrecht",
    870: "Heracles Almelo",
}










