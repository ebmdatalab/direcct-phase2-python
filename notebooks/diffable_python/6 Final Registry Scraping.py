# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# +
from requests import get
from requests import post
from bs4 import BeautifulSoup
import re
from time import time
import csv
import pandas as pd
from tqdm.auto import tqdm

def get_url(url, parse='html'):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    response = get(url, verify = False, headers=headers)
    html = response.content
    if parse == 'html':
        soup = BeautifulSoup(html, "html.parser")
    elif parse == 'xml':
        soup = BeautifulSoup(html, "xml")
    return soup

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

save_path = parent + '/data/final_registry_data_apr2022/'
# -

df = pd.read_csv(parent + '/data/2022-03-01_registrations.csv')
df.registry.unique()

df.registry.value_counts()

df.columns

# # ClinicalTrials.gov

# +
ncts = df[df.registry == 'ClinicalTrials.gov'].trn.to_list()
pubmed_res_str = 'Publications automatically indexed to this study by ClinicalTrials.gov Identifier (NCT Number):'
url_str = 'https://clinicaltrials.gov/show/{}'

ctgov_list = []


for nct in tqdm(ncts):
    soup = get_url(url_str.format(nct))
    trial_dict = {}
    
    trial_dict['trial_id'] = nct
    
    #Completion Dates
    if soup.find('span', {'data-term': "Primary Completion Date"}):
        trial_dict['pcd'] = soup.find('span', {'data-term': "Primary Completion Date"}).find_next('td').text
    else:
        trial_dict['pcd'] = None
    if soup.find('span', {'data-term': "Study Completion Date"}):
        trial_dict['scd'] = soup.find('span', {'data-term': "Study Completion Date"}).find_next('td').text
    else:
        trial_dict['scd'] = None

    #Tabular Results Status
    if soup.find('li', {'id':'results'}):
        trial_dict['tab_results'] = soup.find('li', {'id':'results'}).text.strip()
    else:
        trial_dict['tab_results'] = None

    #Auto-linked results via PubMed
    if soup.find('span', text=pubmed_res_str):
        pm_linked = []
        for x in soup.find('span', text=pubmed_res_str).find_next('div').find_all('div'):
            pm_linked.append(x.text.strip())
        trial_dict['linked_pubs'] = pm_linked
    else:
        trial_dict['linked_pubs'] = None

    #Results citations provided by sponsor
    if soup.find('span', text='Publications of Results:'):
        spon_pubs = []
        for x in soup.find('span', text='Publications of Results:').find_next('div').find_all('div'):
            spon_pubs.append(x.text.strip())
        trial_dict['spon_pubs'] = spon_pubs
    else:
        trial_dict['spon_pubs'] = None

    #Trial Status:
    if soup.find('span', {'data-term': 'Recruitment Status'}):
        trial_dict['trial_status'] = soup.find('span', {'data-term': 'Recruitment Status'}).next_sibling.replace(':','').strip()
    else:
        trial_dict['trial_status'] = None

    #Secondary IDs:
    if soup.find('td', text='Other Study ID Numbers:'):
        ids = []
        for a in soup.find('td', text='Other Study ID Numbers:').find_next('td').text.split('\n'):
            if a.strip():
                ids.append(a.strip())
        trial_dict['secondary_ids'] = ids
        
    #Last updated date:
    if soup.find('span', {'data-term': 'Last Update Posted'}):
        trial_dict['last_updated'] = soup.find('span', {'data-term': 'Last Update Posted'}).next_sibling.replace(':','').strip()
    else:
        trial_dict['last_updated'] = None
        
    emails = []
    for x in soup.select('a[href^=mailto]'):
        emails.append(x.text)
    trial_dict['emails'] = emails
    
    ctgov_list.append(trial_dict)
    
#Can be expanded for some covariates as needed but also can archive our full copy from the FDAAA TT 
#on the day of the scrape

# +
ctgov_results = pd.DataFrame(ctgov_list)

ctgov_results['pcd'] = pd.to_datetime(ctgov_results['pcd'])
ctgov_results['scd'] = pd.to_datetime(ctgov_results['scd'])
ctgov_results['last_updated'] = pd.to_datetime(ctgov_results['last_updated'])
# -

ctgov_results.to_csv(save_path + 'ctgov_results_03apr2022.csv')

# # ISRCTN
#
# The ISRCTN doesn't allow scraping anymore and the API doesn't reliably return completion status so I downloaded the relevant fields for the entire ISRCTN in CSV format and will process from that.

isrctn_ids = df[df.registry == 'ISRCTN'].trn.to_list()

isrctn_df_full = pd.read_csv(save_path + 'ISRCTN_search_results_03apr2022_full.csv')

isrctn_df_covid = isrctn_df[isrctn_df.ISRCTN.isin(isrctn_ids)].reset_index(drop=True)

isrctn_df_covid.to_csv(save_path + 'isrctn_03apr_2022.csv')

# # EUCTR
# IDs will be injested in form of EUCTR2020-000890-25
# We need to kill the EUCTR part

euctr_ids = [x[5:].replace('-Outside/EEA','') for x in df[df.registry == 'EudraCT'].trn.to_list()]

# +
euctr_trials = []

for euctr_id in tqdm(euctr_ids):


    search_url = 'https://www.clinicaltrialsregister.eu/ctr-search/search?query={}'
    #First blank is the trial number, 2nd is the abbreviation for the protocol country
    protocol_url = 'https://www.clinicaltrialsregister.eu/ctr-search/trial/{}/{}'

    soup=get_url(search_url.format(euctr_id))

    trial_dict = {}

    #trial id
    trial_dict['trial_id'] = euctr_id

    #Results status
    if soup.find('span', {'class':'label'}, text='Trial results:'):
        trial_dict['results_status'] = soup.find('span', {'class':'label'}, text='Trial results:').find_next().text
    else:
        euctr_trials.append(trial_dict)
        continue

    #Countries
    country_list = []
    for x in soup.find('span', text='Trial protocol:').parent.find_all('a'):
        country_list.append(x.text)
    trial_dict['countries'] = country_list

    #Individual Protocol Data
    #Completion dates
    comp_dates = []
    status_list = []
    emails = []
    for c in country_list:
        psoup = get_url(protocol_url.format(euctr_id, c))
        if psoup.find('td', text='Date of the global end of the trial'):
            comp_dates.append(psoup.find('td', text='Date of the global end of the trial').find_next().text)
        else:
            comp_dates.append(None)
    
    #Trial status
        if psoup.find('td', text='Trial Status:'):
            status_list.append(psoup.find('td', text='Trial Status:').find_next('td').text.strip())
        else:
            status_list.append(None)

    #secondary_ids
        sid_dict = {}
        if psoup.find('td', text='ISRCTN (International Standard Randomised Controlled Trial) Number'):
            sid_dict['isrctn'] = psoup.find('td', text='ISRCTN (International Standard Randomised Controlled Trial) Number').find_next().text.strip()
        if psoup.find('td', text='US NCT (ClinicalTrials.gov registry) number'):
            sid_dict['nct_id'] = psoup.find('td', text='US NCT (ClinicalTrials.gov registry) number').find_next().text.strip()
        if psoup.find('td', text="Sponsor's protocol code number"):
            sid_dict['spon_id'] = psoup.find('td', text="Sponsor's protocol code number").find_next().text.strip()
            
    #emails
        if psoup.find('td', text='E-mail'):
            for x in psoup.find_all('td', text='E-mail'):
                emails.append(x.find_next().text)
            
    
    trial_dict['global_trial_end_dates'] =  comp_dates
    trial_dict['status_list'] = status_list
    trial_dict['emails'] = emails
    if len(sid_dict) > 0:
        trial_dict['secondary_ids'] = sid_dict
    else:
        trial_dict['secondary_ids'] = None
    
    euctr_trials.append(trial_dict)
# -

pd.DataFrame(euctr_trials).to_csv(save_path + 'euctr_03apr_2022.csv')


# # DRKS
# We can get DRKS trials via the URL in the ICTRP dataset like:
# https://www.drks.de/drks_web/navigate.do?navigationId=trial.HTML&TRIAL_ID=DRKS00021186

def does_it_exist(soup, element, e_class, n_e=False):
    if not n_e:
        location = soup.find(element, class_=e_class).text.strip()
    elif n_e:
        location = soup.find(element, class_=e_class).next_element.next_element.next_element.next_element.strip()
    if location == '[---]*':
        field = None
    else:
        field = location
    return field


# +
drks_url = 'https://www.drks.de/drks_web/navigate.do?navigationId=trial.HTML&TRIAL_ID={}'

drks_ids = df[df.registry == 'DRKS'].trn.to_list()

drks_trials = []
# -

for d in tqdm(drks_ids): 
    
    soup = get_url(drks_url.format(d))

    trial_dict = {}

    trial_dict['trial_id'] = soup.find('li', class_='drksId').next_element.next_element.next_element.next_element.strip()

    history = get_url(f'https://www.drks.de/drks_web/navigate.do?navigationId=trial.history&TRIAL_ID={trial_dict["trial_id"]}')
    
    st_class = ['state', 'deadline']
    st_labels = ['recruitment_status', 'study_closing_date']
    for lab, s_class in zip(st_labels, st_class):
        trial_dict[lab] = does_it_exist(soup, 'li', s_class, n_e=True)

    s_id_list = []
    ul = soup.find('ul', class_='secondaryIDs').find_all('li')
    if ul[0].text == '[---]*':
        s_id_list = None
    else:
        for u in ul:
            s_id_dict = {}
            s_id_dict['id_type'] = u.next_element.next_element.next_element.strip().replace(':','')
            li_t = u.next_element.next_element.next_element.next_element.strip()
            li_t = re.sub('\n', '|', li_t)
            li_t = re.sub('\s+', '', li_t).replace('(','').replace(')','')
            id_info = li_t.split('|')
            if len(id_info) > 1:   
                s_id_dict['registry'] = id_info[1]
                s_id_dict['secondary_id'] = id_info[0]
            else:
                s_id_dict['registry'] = None
                s_id_dict['secondary_id'] = id_info[0]
            s_id_list.append(s_id_dict)

    trial_dict['secondary_ids'] = s_id_list

    docs_list = []
    ul = soup.find('ul', class_='publications').find_all('li')
    if ul[0].text == '[---]*':
        docs_list = None
    else:
        for u in ul:
            doc_dict = {}
            doc_dict['document_type'] = u.next_element.next_element.next_element.strip().replace(':','')
            if u.find('a'):
                doc_dict['link_to_document'] = u.find('a').get('href')
            else:
                doc_dict['link_to_document'] = None
            docs_list.append(doc_dict)
    trial_dict['results_publications_documents'] = docs_list
    
    trial_dict['last_updated'] = pd.to_datetime(history.find('tbody').find_next('td').text, format='%m-%d-%Y')
    
    emails = []
    for x in soup.select('a[href^=mailto]'):
        emails.append(x.text.replace(' at ', '@'))
    trial_dict['emails'] = emails
    
    drks_trials.append(trial_dict)

pd.DataFrame(drks_trials).to_csv(save_path + 'drks_trials_03apr_2022.csv')

# # CTRI
#
# Since CTRI URLs aren't linked to the trial id we need to join them in from the current ICTRP covid database.

# +
ctri_trials = df[df.registry == 'CTRI']

ictrp = pd.read_csv(parent + '/data/COVID19-web_31mar_2022.csv')
# -

ctri_merged = ctri_trials.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

ctri_merged.at[71, 'web address'] = 'http://ctri.nic.in/Clinicaltrials/pmaindet2.php?trialid=45442'
ctri_merged.at[72, 'web address'] = 'http://ctri.nic.in/Clinicaltrials/pmaindet2.php?trialid=11463'
ctri_merged.at[73, 'web address'] = 'http://ctri.nic.in/Clinicaltrials/pmaindet2.php?trialid=16467'
ctri_merged.at[819, 'web address'] = 'http://ctri.nic.in/Clinicaltrials/pmaindet2.php?trialid=49102'

ctri_urls = ctri_merged['web address'].to_list()
ctri_ids = ctri_merged['trn'].to_list()


#Need a slightly more robust function to fetch trial data from the CTRI
def get_ctri(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    tries=3
    for i in range(tries):
        try:
            response = get(url, verify = False, headers=headers)
        except ConnectionError as e:
            if i < tries - 1:
                sleep(2)
                continue
            else:
                raise
    html = response.content
    soup = BeautifulSoup(html, "html.parser")
    return soup


ctri_list = []

# +
from time import sleep

for c,i in zip(tqdm(ctri_urls), ctri_ids):
    try:
        if c:
            soup = get_ctri(c)

            trial_dict = {}

            trial_dict['trial_id'] = i

            trial_dict['completion_date_india'] = soup.find('td', text = 'Date of Study Completion (India)').find_next('td').text.strip()

            trial_dict['completion_date_global'] = soup.find('td', text = 'Date of Study Completion (Global)').find_next('td').text.strip()

            trial_dict['recruitment_status_india'] = soup.find('b', text='Recruitment Status of Trial (India)').find_next('td').text.strip()

            trial_dict['recruitment_status_global'] = soup.find('b', text='Recruitment Status of Trial (Global)').find_next('td').text.strip()

            trial_dict['publication_details'] = soup.find('b', text='Publication Details').find_next('td').text.strip()

            if soup.find('b', text = re.compile('Secondary IDs if Any')):
                trial_dict['secondary_ids'] = soup.find('b', text = re.compile('Secondary IDs if Any')).parent.parent.find_all('tr')
            else:
                trial_dict['secondary_ids'] = None

            trial_dict['last_updated'] = soup.find('b', text='Last Modified On:').find_next('td').text.strip()

            emails = []
            for x in soup.find_all('td', text='Email '):
                emails.append(x.find_next('td').text.strip())
            trial_dict['emails'] = list(set(emails))

            ctri_list.append(trial_dict)

            sleep(1)
        else:
            trial_dict = {}
            trial_dict['trial_id'] = i
            ctri_list.append(trial_dict)
            continue
    #Excuse the blind except here but was getting some weird errors. Easier to just check those by hand.
    except:
        trial_dict = {}
        trial_dict['trial_id'] = i
        ctri_list.append(trial_dict)
        continue
    
# -

pd.DataFrame(ctri_list).to_csv(save_path + 'ctri_04jul2022.csv')

# # ANZCTR

# +
anzctr_url = 'https://anzctr.org.au/{}.aspx'

anzctr_ids = df[df.registry == 'ANZCTR'].trn.to_list()

anzctr_trials = []
# -

for u in tqdm(anzctr_ids):

    soup = get_url(anzctr_url.format(u))

    trial_dict = {}

    try:
        trial_dict['trial_id'] = soup.find('span', {'id': 'ctl00_body_CXACTRNUMBER'}).text.replace('p','')
    except AttributeError:
        continue
        

    trial_dict['last_updated'] = soup.find('span', {'id': 'ctl00_body_CXUPDATEDATE'}).text

    trial_dict['trial_status'] = soup.find('span', {'id': 'ctl00_body_CXRECRUITMENTSTATUS'}).text  
    
    anticipated_end_date = soup.find('span', {'id': 'ctl00_body_CXANTICIPATEDLASTVISITDATE'}).text

    actual_end_date = soup.find('span', {'id': 'ctl00_body_CXACTUALLASTVISITDATE'}).text

    if actual_end_date:
        trial_dict['completion_date'] = actual_end_date
    else:
        trial_dict['completion_date'] = anticipated_end_date

    secondary_ids = []

    for x in soup.find_all('span', text=re.compile('Secondary ID \[\d*\]')):
        secondary_ids.append(x.find_next('div').span.text.strip())

    trial_dict['secondary_ids'] = secondary_ids

    results_dict = {}

    if soup.find('div', {'id': 'ctl00_body_divNoResultsANZCTR'}):
        trial_dict['results'] = None
    else:
        citations = []
        for x in soup.find_all('span', text=re.compile('Publication date and citation/details \[\d*\]')):
            citations.append(x.find_next('div').span.text)

        results_dict['citations'] = citations

        if soup.find('a', {'id': 'ctl00_body_hyperlink_CXRESULTATTACHMENT'}):
            results_dict['basic_reporting_doc'] = soup.find('a', {'id': 'ctl00_body_hyperlink_CXRESULTATTACHMENT'}).text

    if results_dict:
        trial_dict['results'] = results_dict
    else:
        trial_dict['results'] = None
    
    trial_dict['last_updated'] = pd.to_datetime(soup.find('span', {'id': 'ctl00_body_CXUPDATEDATE'}).text, format='%d/%m/%Y')
    
    emails = []
    for x in soup.select('span[id$=_CXEMAIL]'):
        if x.text and 'Email [' not in x.text:
            emails.append(x.text)
    trial_dict['emails'] = list(set(emails))
    
    anzctr_trials.append(trial_dict)

anzctr_df = pd.DataFrame(anzctr_trials)
anzctr_df.to_csv(save_path + 'anzctr_trials_03apr2022.csv')

# # NTR

# +
#Easiest to just to this query and then filter

rsp = post(
    "https://api.trialregister.nl/trials/public.trials/_msearch?",
    headers={"Content-Type": "application/x-ndjson", "Accept": "application/json"},
    data='{"preference":"results"}\n{"query":{"match_all":{}},"size":10000,"_source":{"includes":["*"],"excludes":[]},"sort":[{"id":{"order":"desc"}}]}\n',
)
results = rsp.json()
hits = results["responses"][0]["hits"]["hits"]
records = [hit["_source"] for hit in hits]

all_keys = set().union(*(record.keys() for record in records))

# +
labels = list(all_keys)

from datetime import date
import csv

def ntr_csv(save_path):
    with open(save_path + 'ntr - ' + str(date.today()) + '.csv','w', newline = '', encoding='utf-8') as ntr_csv:
        writer=csv.DictWriter(ntr_csv,fieldnames=labels)
        writer.writeheader()
        writer.writerows(records)


# -

ntr_csv(save_path)

# +
#Only what we need from the NTR

ntr_ids = df[df.registry == 'NTR'].trn.to_list()

ntr_df = pd.read_csv(save_path + 'ntr - 2022-04-04.csv')

covid_ntr = ntr_df[ntr_df.idFull.isin(ntr_ids)]

covid_ntr[['idFull', 'status', 'dateStop', 'publications', 'idSource', 'isrctn', 'contact']].to_csv(save_path + 'ntr_covid_03apr_2022.csv')
# -

# # IRCT
#
# As with the CTRI, we need to pull in web adresses from the ICTRP as the URLS are not based on the trial ids

irct_trials = df[df.registry == 'IRCT']

irct_merged = irct_trials.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

#Fixing missing urls
irct_merged.at[0, 'web address'] = 'https://www.irct.ir/trial/46667'
irct_merged.at[237, 'web address'] = 'https://www.irct.ir/trial/15589'
irct_merged.at[239, 'web address'] = 'https://www.irct.ir/trial/38534'
irct_merged.at[414, 'web address'] = 'https://www.irct.ir/trial/51802'

# +
irct_urls = irct_merged['web address'].to_list()

irct_list = []
# -

for url in tqdm(irct_urls):

    soup=get_url(url)

    trial_dict = {}
    
    if soup.find('span', text='IRCT registration number:'):
        trial_dict['trial_id'] = soup.find('span', text='IRCT registration number:').find_next('strong').text.strip()
    else:
        trial_dict['trial_id'] = None

    if soup.find('dt', text=re.compile('\sRecruitment status\s')):
        trial_dict['trial_status'] = soup.find('dt', text=re.compile('\sRecruitment status\s')).find_next('dd').text.strip()
    else:
        trial_dict['trial_status'] = None

    if not soup.find('dt', text=re.compile('\sTrial completion date\s')) or soup.find('dt', text=re.compile('\sTrial completion date\s')).find_next('dd').text.strip() == 'empty':
        trial_dict['completion_date'] = None
    else:
        trial_dict['completion_date'] = re.findall(re.compile('\d{4}-\d{2}-\d{2}'), soup.find('dt', text=re.compile('\sTrial completion date\s')).find_next('dd').text.strip())[0]

    if soup.find('h3', text=re.compile('Secondary Ids')):
        trial_dict['secondary_ids'] = soup.find('h3', text=re.compile('Secondary Ids')).parent
    else:
        trial_dict['secondary_ids'] = None
    
    if soup.find('span', text='Last update:'):
        try:
            trial_dict['last_updated'] = re.findall(r'\d{4}-\d{2}-\d{2}', soup.find('span', text='Last update:').find_next().text)[0]
        except IndexError:
            trial_dict['last_updated'] = None
    else:
        trial_dict['last_updated'] = None
    
    emails = []
    for x in soup.find_all('strong', text='Email'):
        emails.append(x.find_next().text.strip())
    trial_dict['emails'] = list(set(emails))
    
    irct_list.append(trial_dict)

pd.DataFrame(irct_list).to_csv(save_path + 'irct_03apr_2022.csv')

# # jRCT

jrct_trials = df[df.registry == 'jRCT']

jrct_merged = jrct_trials.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

jrct_merged[jrct_merged['web address'].isna()]

#Fixing missing urls
jrct_merged.at[31, 'web address'] = 'https://jrct.niph.go.jp/latest-detail/jRCT2031200174'

# +
jrct_urls = jrct_merged['web address'].to_list()

jrct_urls_eng = []

for j in jrct_urls:
    if isinstance(j, float):
        jrct_urls_eng.append(None)
    else:
        jrct_urls_eng.append(j[:24] + 'en-' + j[24:])

# +
jrct_trials = []

for j in tqdm(jrct_urls_eng):
    j_dict = {}
    
    if not j:
        j_dict['trial_id'] = 'JPRN-JRCT2031200252'
        jrct_trials.append(j_dict)
    else:
        soup = get_url(j)

        j_dict['trial_id'] = 'JPRN-' + j[-14:]

        j_dict['status'] = soup.find('label', text='Recruitment status').find_next().find_next().text

        j_dict['secondary_ids'] = soup.find('label', text='Secondary ID(s)').find_next().text

        j_dict['last_updated'] = pd.to_datetime(soup.find('label', text='Last modified on').find_next().text)

        emails = []
        for x in soup.find_all('label', text='E-mail'):
            emails.append(x.find_next().text.strip())
        j_dict['emails'] = list(set(emails))

        jrct_trials.append(j_dict)
# -

pd.DataFrame(jrct_trials).to_csv(save_path + 'jrct_04apr_2022.csv')

# # REBEC

# +
rebec_ids = df[df.registry == 'ReBec'].trn.to_list()

rebec_url = 'https://ensaiosclinicos.gov.br/rg/{}'

# +
rebec_trials = []

for r in tqdm(rebec_ids):
    soup = get_url(rebec_url.format(r))
    
    r_t = {}
    
    r_t['trial_id'] = r
    
    try:
        r_t['trial_status'] = soup.find('span', text="Study status:").find_next().text.strip()
    except AttributeError:
        r_t['trial_status'] = None
    
    try:
        r_t['last_enrollment'] = soup.find('span', text='Date last enrollment:').find_next().text.strip()
    except AttributeError:
        r_t['last_enrollment'] = None
        
    try:
        r_t['last_updated'] = pd.to_datetime(soup.find('span', text='Last approval date\xa0:').find_next('span').text.strip()[:10])
    except AttributeError:
        r_t['last_updated'] = None
        
    try:
        emails = []
        for x in soup.find_all('span', {'class':'email'}):
            emails.append(x.text.strip())
        r_t['emails'] = list(set(emails))
    except AttributeError:
        r_t['emails'] = None
    
    rebec_trials.append(r_t)
# -

pd.DataFrame(rebec_trials).to_csv(save_path + 'rebec_04apr_2022.csv')

# # PACTR

pactr_ids = df[df.registry == 'PACTR']

pactr_merged = pactr_ids.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

# +
pactr_urls = pactr_merged['web address'].to_list()

pactr_trials = []

# +
id_regex = re.compile(r'PACTR\d{15}')

for p in tqdm(pactr_urls):
    soup = get_url(p)
    p_dict = {}
    
    p_dict['trial_id'] = soup.find('td', text=re.compile(id_regex)).text
    
    p_dict['anticipated_comp'] = pd.to_datetime(soup.find('td', text='Anticipated date of last follow up').find_next('td').text)
    
    p_dict['actual_comp'] = pd.to_datetime(soup.find('td', text='Actual Last follow-up date').find_next('td').text)
    
    p_dict['trial_status'] = soup.find('td', text='Recruitment status').find_next('td').text
    
    if soup.find('td', text='Changes to trial information').find_next('tr'):
        p_dict['last_updated'] = pd.to_datetime(soup.find('td', text='Changes to trial information').find_next('tr').find_next('tr').find_all('td')[2].text)
    else:
        p_dict['last_updated'] = pd.to_datetime(soup.find('td', text='\r\n                  Date of Approval:\r\n                ').find_next('td').text)
        
    emails = []
    for e in soup.find('td', text='CONTACT PEOPLE').parent.parent.find_all('b',text='Email'):
        emails.append(e.find_next('tr').find_all('td')[2].text)
    p_dict['emails'] = emails
    
    pactr_trials.append(p_dict)
# -

pd.DataFrame(pactr_trials).to_csv(save_path + 'pactr_04apr_2022.csv')

# # CRIS

cris_ids = df[df.registry == 'CRiS']
cris_merged = cris_ids.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

#Fixing missing urls
cris_merged.at[4, 'web address'] = 'http://cris.nih.go.kr/cris/en/search/search_result_st01.jsp?seq=12657'
cris_merged.at[5, 'web address'] = 'http://cris.nih.go.kr/cris/en/search/search_result_st01.jsp?seq=11087'
cris_merged.at[6, 'web address'] = 'http://cris.nih.go.kr/cris/en/search/search_result_st01.jsp?seq=7441'
cris_merged.at[7, 'web address'] = 'http://cris.nih.go.kr/cris/en/search/search_result_st01.jsp?seq=16278'

# +
cris_urls = cris_merged['web address'].to_list()

cris_trials = []
# -

for c in tqdm(cris_urls):
    soup = get_url(c)
    c_dict = {}
    
    c_dict['trial_id'] = soup.find('th', text='\r\n\t\t\t\t\t\t\t\t1. Background\r\n\t\t\t\t\t\t\t').find_next('th').find_next('td').text.strip()
    
    c_dict['last_updated'] = pd.to_datetime(soup.find('p', {'class':'page_title_info'}).find_all('span')[-1].text)
    
    c_dict['trial_status'] = soup.find('th', text='\r\n\t\t\t\t\t\t\t\t4. Status\r\n\t\t\t\t\t\t\t').find_next('th').find_next('th').find_next('td').text.strip()
    
    if soup.find('th', text='Primary Completion Date').find_next('td'):
        c_dict['pcd'] = pd.to_datetime(soup.find('th', text='Primary Completion Date').find_next('td').text.strip()[:10])
    else:
        c_dict['pcd'] = None
    
    if soup.find('th', text='Study Completion Date').find_next('td'):
        c_dict['scd'] = pd.to_datetime(soup.find('th', text='Study Completion Date').find_next('td').text.strip()[:10])
    else:
        c_dict['scd'] = None
        
    c_dict['results_status'] = soup.find('th', text='\r\n\t\t\t\t\t\t\t\t11. Study Results and Publication\r\n\t\t\t\t\t\t\t').find_next('th').find_next('td').text.strip()
    
    cris_trials.append(c_dict)

pd.DataFrame(cris_trials).to_csv(save_path + 'cris_05apr_2022.csv')

# # JPRN UMIN

umin_ids = df[df.registry == 'UMIN-CTR']
umin_merged = umin_ids.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

#Fixing missing urls
umin_merged.at[38, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000004846'
umin_merged.at[39, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000006464'
umin_merged.at[40, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000008394'
umin_merged.at[41, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000024177'
umin_merged.at[42, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000026773'
umin_merged.at[43, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000030949'
umin_merged.at[44, 'web address'] = 'https://upload.umin.ac.jp/cgi-open-bin/ctr_e/ctr_view.cgi?recptno=R000044045'

# +
umin_urls = umin_merged['web address'].to_list()

umin_trials = []
# -

for u in tqdm(umin_urls):
    u_dict = {}
    soup=get_url(u)
    
    u_dict['trial_id'] = 'JPRN-' + soup.find('font', text='Unique ID issued by UMIN').find_next('td').text
    
    u_dict['trial_status'] = soup.find('font', text='Recruitment status').find_next('td').text
    
    u_dict['comp_date'] = pd.to_datetime(soup.find('font', text='Date trial data considered complete').find_next('td').text, errors='coerce')
    
    u_dict['last_updated'] = pd.to_datetime(soup.find('font', text='Last modified on').find_next('td').text, errors='coerce')
    
    emails = []
    emails.append(soup.find('font', text='Research contact person').parent.parent.parent.parent.find('font', text='Email').find_next('td').text)
    emails.append(soup.find('font', text='Public contact ').parent.parent.parent.parent.find('font', text='Email').find_next('td').text)
    u_dict['emails'] = list(set(emails))
    
    results = []
    results_sec = soup.find('font', text='Result').parent.parent.parent.parent
    
    results.append(results_sec.find('font', text='Results').find_next('td'))

    results.append(results_sec.find('font', text='URL related to results and publications').find_next('td'))
    u_dict['results'] = results
    
    umin_trials.append(u_dict)

pd.DataFrame(umin_trials).to_csv(save_path + 'umin_trials05apr_2022.csv')

# # RPCEC

# +
rpcec_ids = df[df.registry == 'RPCEC'].trn.to_list()

rpcec_url_format = 'https://rpcec.sld.cu/en/trials/{}-En'
# -

rpcec_trials = []

for rp in tqdm(rpcec_ids):
    rp_dict = {}
    soup = get_url(rpcec_url_format.format(rp))
    sopa = get_url(rpcec_url_format.format(rp).replace('En', 'Sp').replace('en/trials', 'ensayos'))
    
    rp_dict['trial_id'] = soup.find('div', text=re.compile(r'\s*Unique ID number:\s*')).find_next().text.strip()
    
    rp_dict['trial_status'] = soup.find('div', text=re.compile(r'\s*Recruitment status:\s*')).find_next().text.strip()
    
    rp_dict['comp_date'] = pd.to_datetime(soup.find('div', text=re.compile(r'\s*Study completion date:\s*')).find_next().text.strip())
    
    rp_dict['last_updated'] = pd.to_datetime(soup.find('div', text = re.compile(r'\s*Record Verification Date\s*:\s*')).find_next().text.strip())
    
    emails = []
    for e in soup.find_all('div', text = re.compile(r'\s*Email\s*:\s*')):
        emails.append(e.find_next().text.strip())
    rp_dict['emails'] = list(set(emails))
    
    rp_dict['results'] = sopa.find('div', text=re.compile(r'\s*Referencias:\s*')).find_next().text.strip()
    
    rpcec_trials.append(rp_dict)

pd.DataFrame(rpcec_trials).to_csv(save_path + 'rpcec_05apr_2022.csv')

# # ChiCTR
#
# This scraper works poorly. You only get between 10-30 trials scraped before you run into the anti-dos blocks. I ran it multiple times over about a day and a half to gather the data on ChiCTR trials.

# +
chictr_ids = df[df.registry == 'ChiCTR']

chictr_merged = chictr_ids.merge(ictrp[['TrialID', 'web address']], how='left', left_on='trn', right_on='TrialID').drop('TrialID', axis=1)

# +
chictr_urls = chictr_merged['web address'].to_list()

chictr_trials = []
# -

tracker = 0

# +
from time import sleep

for u in tqdm(chictr_urls[tracker:]):
    
    soup=get_url(u)
    
    trial_dict = {}
    
    try:
        test = soup.find('p', text = re.compile('\w*Registration number\w*'))
    except AttributeError:
        trial_dict['error'] = u
        chictr_trials.append(trial_dict)
        continue
    
    trial_dict['trial_id'] = soup.find('p', text = re.compile('\w*Registration number\w*')).find_next('td').text.strip()
    
    if len(re.findall(re.compile('\d{4}-\d{2}-\d{2}'), soup.find('span', text='To').parent.text)) > 1:
        trial_dict['comp_date'] = re.findall(re.compile('\d{4}-\d{2}-\d{2}'), soup.find('span', text='To').parent.text)[1]
    else:
        trial_dict['comp_date'] = None
            

    trial_dict['trial_status'] = soup.find('p', text = re.compile('\w*Recruiting status\w*')).find_next('p').find_next('p').text.strip()
    
    trial_dict['last_updated'] = soup.find('p', text = re.compile('Date of Last Refreshed on\w*')).find_next('td').text.strip()
    
    email_identifiers = [r'\w*Applicant E-mail\w*', r"\w*Study leader's fax\w*"]
    
    emails = []
    for e in email_identifiers:
        emails.append(soup.find('p', text=re.compile(e)).find_next('td').text.strip())
    trial_dict['emails'] = list(set(emails))
    
    
    chictr_trials.append(trial_dict)
    tracker +=1
    sleep(10)
# -

print(len(chictr_trials), tracker)

pd.DataFrame(chictr_trials).to_csv(save_path + 'chictr_07apr_2022.csv')

# # TCTR

import json

tctr_ids = df[df.registry == 'TCTR'].trn.to_list()

tctr_url = 'http://www.thaiclinicaltrials.org/show/{}'
tctr_api = 'https://www.thaiclinicaltrials.org/api/control/records/previews/{}?RID={}'

files = ['getRecordInfo.php', 'getRecordStatus.php', 'getRecordPubStudy.php', 'getRecordTitleSid.php', 'getRecordLocationA.php']

tctr_trials = []

for t in tqdm(tctr_ids):
    t_dict = {}
    t_dict['trial_id'] = t
    
    get_id = re.search('PV_REC:\d{4}', str(get_url(tctr_url.format(t))))[0][-4:]
    
    info = json.loads(get_url(tctr_api.format(files[0], get_id)).text)
    t_dict['last_updated'] = info['records'][0]['last_update']
    t_dict['trial_status'] = info['records'][0]['OverallStatusDesc']
    
    status = json.loads(get_url(tctr_api.format(files[1], get_id)).text)
    t_dict['pcd'] = status['records'][0]['completion_date']
    t_dict['scd'] = status['records'][0]['study_completion_date']
    
    pub = get_url(tctr_api.format(files[2], get_id)).text
    if pub:
        pub_d = json.loads(pub)
        t_dict['linked_pubs'] = pub_d['records'][0]['url_link']
    else:
        t_dict['linked_pubs'] = None
    
    sid = get_url(tctr_api.format(files[3], get_id)).text
    if sid:
        sid_d = json.loads(sid)
        
        sids = []
        for x in sid_d['records']:
            sids.append(x['secondary_ids'])
        
        t_dict['secondary_ids'] = sids

    else:
        t_dict['secondary_ids'] = None
        
    contact = json.loads(get_url(tctr_api.format(files[4], get_id)).text)
    contacts = []
    try:
        contacts.append(contact['records'][0]['sec_a_email'])
    except KeyError:
        pass
    try:
        contacts.append(contact['records'][0]['sec_a_bak_email'])
    except KeyError:
        pass
    t_dict['emails'] = contacts
    
    tctr_trials.append(t_dict)

pd.DataFrame(tctr_trials).to_csv(save_path + 'tctr_22apr_2022.csv')

# # Pulling the trials from the registries that are either not easily scraped or very small

# +
registries = ['SLCTR', 'LBCTR', 'JapicCTI', 'REPEC']

manual_trials = df[df.registry.isin(registries)]
# -

manual_trials.to_csv(save_path + 'manual_data.csv')






