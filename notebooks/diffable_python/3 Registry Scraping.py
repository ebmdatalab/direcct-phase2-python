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

# This is a collection of webscrapers used to get data we need from registries
#
# For now, this is only certain registries as others have so few trials they can be easily manually screened.
#
# This doesn't really need to be a notebook but for organisation, disply, and if you are running than all at once, ease. Any of the specific scrapers could be copied into a .py file and run that way if preferred.

# To add for July scrape:
#
# -Contact info
# -last updated date

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

save_path = parent + '/data/raw_scraping_output/'
# -

# The trials these were run on are those in the ICTRP dataset after the initial inclusions/exclusions were made (observational, pre-2020 trials, trials that are withdrawn/cancelled). This code assumes you read in that dataset to a DataFrame below and work from there.

df = pd.read_csv(parent + '/data/scrape_df_jul21.csv')
df.source_register.unique()

df.columns

# # ClinicalTrials.gov

# +
nct_urls = df[df.source_register == 'ClinicalTrials.gov'].web_address.to_list()
pubmed_res_str = 'Publications automatically indexed to this study by ClinicalTrials.gov Identifier (NCT Number):'

ctgov_list = []


for nct in tqdm(nct_urls):
    soup = get_url(nct)
    trial_dict = {}
    
    trial_dict['trial_id'] = nct[-11:]
    
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
#on the day of the scrape and

# +
ctgov_results = pd.DataFrame(ctgov_list)

ctgov_results['pcd'] = pd.to_datetime(ctgov_results['pcd'])
ctgov_results['scd'] = pd.to_datetime(ctgov_results['scd'])
ctgov_results['last_updated'] = pd.to_datetime(ctgov_results['last_updated'])

ctgov_results.to_csv(save_path + 'ctgov_results_11jul2021.csv')
# -

# # ISRCTN

isrctn_ids = df[df.source_register == 'ISRCTN'].trialid.to_list()

# +
#ISRCTN

isrctn_urls = df[df.source_register == 'ISRCTN'].trialid.to_list()

isrctn_list = []

for i in tqdm(isrctn_urls[0:10]):

    trial_dict = {}
    soup = get_url(f'https://www.isrctn.com/{i}')

    #Trial ID
    trial_dict['trial_id'] = i

    #Trial Status
    if soup.find('dt', text='Overall trial status'):
        trial_dict['overall_status'] = soup.find('dt', text='Overall trial status').find_next().text.strip()
    else:
        trial_dict['overall_status'] = None
        
    trial_dict['recruitment_status'] = soup.find('dt', text='Recruitment status').find_next().text.strip()

    #Dates
    trial_dict['trial_start_date'] = soup.find('h3', text='Overall trial start date').find_next().text.strip()

    #Dates
    trial_dict['trial_end_date'] = soup.find('h3', text='Overall trial end date').find_next().text.strip()
    
    #Other IDs
    sid_dict={}
    if soup.find('h3', text='EudraCT number').find_next().text.strip():
        sid_dict['eudract_number'] = soup.find('h3', text='EudraCT number').find_next().text.strip()
    else:
        sid_dict['eudract_number'] = None
    if soup.find('h3', text='ClinicalTrials.gov number').find_next().text.strip():
        sid_dict['ctgov_number'] = soup.find('h3', text='ClinicalTrials.gov number').find_next().text.strip()
    else:
        sid_dict['ctgov_number'] = None
    if soup.find('h3', text='Protocol/serial number').find_next().text.strip():
        sid_dict['other_id'] = soup.find('h3', text='Protocol/serial number').find_next().text.strip()
    else:
        sid_dict['other_id'] = None
    trial_dict['secondary_ids'] = sid_dict

    #Results stuff
    if soup.find('h3', text='Basic results (scientific)').find_next():
        trial_dict['basic_results'] = soup.find('h3', text='Basic results (scientific)').find_next().text.strip()
    else:
        trial_dict['basic_results'] = None
    if soup.find('h3', text='Publication list').find_next().text.strip():
        trial_dict['pub_list'] = soup.find('h3', text='Publication list').find_next().text.strip()
    else:
        trial_dict['pub_list'] = None
        
    if soup.find('dt', text='Last edited'):
        trial_dict['last_updated'] = soup.find('dt', text='Overall trial status').find_next().text.strip()
    else:
        trial_dict['last_updated'] = None
    
    emails = []
    for x in soup.select('a[href^=mailto]'):
        emails.append(x.text)
    trial_dict['emails'] = emails
    
    isrctn_list.append(trial_dict)
# -

pd.DataFrame(isrctn_list).to_csv(save_path + 'isrctn_11jul_2021.csv')

# +
#The above doesn't work great anymore because ISRCTN switched to an API but easier to just download the 
#full isrctn and just filter it and grab the IDs we want than fiddle with the API.
# -

isrctn_data = pd.read_csv(parent + '/data/registry_data/ISRCTN search results_11july.csv')

isrctn_data[isrctn_data.ISRCTN.isin(isrctn_ids)].to_csv(save_path + 'isrctn_11jul_2021.csv')



# # EUCTR
# IDs will be injested in form of EUCTR2020-000890-25-FR
# We need to kill the EUCTR and the -FR part

# +
euctr_urls = df[df.source_register == 'EU Clinical Trials Register'].web_address.to_list()

euctr_ids = df[df.source_register == 'EU Clinical Trials Register'].trialid.to_list()

euctr_trials = []

for i in tqdm(euctr_ids):

    euctr_id = re.search('(.*\d)', i.replace('EUCTR',''))[0]

    search_url = 'https://www.clinicaltrialsregister.eu/ctr-search/search?query={}'
    #First blank is the trial number, 2nd is the abbreviation for the protocol country
    protocol_url = 'https://www.clinicaltrialsregister.eu/ctr-search/trial/{}/{}'

    soup=get_url(search_url.format(euctr_id))

    trial_dict = {}

    #trial id
    trial_dict['trial_id'] = euctr_id

    #Results status
    trial_dict['results_status'] = soup.find('span', {'class':'label'}, text='Trial results:').find_next().text

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

pd.DataFrame(euctr_trials).to_csv(save_path + 'euctr_12jul_2021.csv')


# # DRKS
# We can get DRKS trials via the URL in the ICTRP dataset like:
# https://www.drks.de/drks_web/navigate.do?navigationId=trial.HTML&TRIAL_ID=DRKS00021186

# +
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

drks_urls = df[df.source_register == 'German Clinical Trials Register'].web_address.to_list()

drks_trials = []

for d in tqdm(drks_urls): 
    
    soup = get_url(d)

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
# -

pd.DataFrame(drks_trials).to_csv(save_path + 'drks_trials_12jul_2021.csv')

# # CTRI
#
# We can get right to a trial registration with a URL from the ICTRP like:
# http://www.ctri.nic.in/Clinicaltrials/pmaindet2.php?trialid=43553

ctri_urls = df[df.source_register == 'CTRI'].web_address.to_list()


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


ctri_urls[406]

ctri_list[-1]

# +
ctri_list = []

for c in tqdm(ctri_urls):

    soup = get_ctri(c)

    trial_dict = {}

    trial_dict['trial_id'] = soup.find('td', text = re.compile('CTRI Number\s*')).find_next('b').find_next('b').text.strip()
    
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
    from time import sleep
    sleep(1)
# -

pd.DataFrame(ctri_list).to_csv(save_path + 'ctri_12jul2021.csv')

# # ANZCTR

# +
anzctr_urls = df[df.source_register == 'ANZCTR'].web_address.to_list()

anzctr_trials = []

for u in tqdm(anzctr_urls):

    soup = get_url(u)

    trial_dict = {}

    trial_dict['trial_id'] = soup.find('span', {'id': 'ctl00_body_CXACTRNUMBER'}).text.replace('p','')

    trial_dict['last_updated'] = soup.find('span', {'id': 'ctl00_body_CXUPDATEDATE'}).text

    trial_dict['trial_status'] = soup.find('span', {'id': 'ctl00_body_CXRECRUITMENTSTATUS'}).text

    anticipated_end_date = soup.find('span', {'id': 'ctl00_body_CXANTICIPATEDENDDATE'}).text

    actual_end_date = soup.find('span', {'id': 'ctl00_body_CXACTUALENDDATE'}).text

    if anticipated_end_date:
        trial_dict['completion_date'] = anticipated_end_date
    else:
        trial_dict['completion_date'] = actual_end_date

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

    trial_dict['results'] = results_dict
    
    trial_dict['last_updated'] = pd.to_datetime(soup.find('span', {'id': 'ctl00_body_CXUPDATEDATE'}).text, format='%d/%m/%Y')
    
    emails = []
    for x in soup.select('span[id$=_CXEMAIL]'):
        if x.text and 'Email [' not in x.text:
            emails.append(x.text)
    trial_dict['emails'] = list(set(emails))
    
    anzctr_trials.append(trial_dict)
# -

anzctr_df = pd.DataFrame(anzctr_trials)
anzctr_df.to_csv(save_path + 'anzctr_trials_12jul2021.csv.csv')

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

ntr_ids = df[df.source_register == 'Netherlands Trial Register'].trialid.to_list()

ntr_df = pd.read_csv(save_path + 'ntr - 2021-07-12.csv')

covid_ntr = ntr_df[ntr_df.idFull.isin(ntr_ids)]

covid_ntr[['idFull', 'status', 'dateStop', 'publications', 'idSource', 'isrctn', 'contact']].to_csv(save_path + 'ntr_covid_12jul.csv')
# -

# # IRCT

s = get_url('https://www.irct.ir/trial/53653')

for x in s.find_all('strong', text='Email'):
    print(x.find_next())

re.findall(r'\d{4}-\d{2}-\d{2}', s.find('span', text='Last update:').find_next().text)[0]

# +

trial_dict['last_updated'] = re.findall(r'\d{4}-\d{2}-\d{2}', soup.find('span', text='Last update:').find_next().text)[0]


# +
irct_urls = df[df.source_register == 'IRCT'].web_address.to_list()

irct_list = []

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
        trial_dict['last_updated'] = re.findall(r'\d{4}-\d{2}-\d{2}', soup.find('span', text='Last update:').find_next().text)[0]
    else:
        trial_dict['last_updated'] = None
    
    emails = []
    for x in soup.find_all('strong', text='Email'):
        emails.append(x.find_next().text.strip())
    trial_dict['emails'] = list(set(emails))
    
    irct_list.append(trial_dict)
# -

pd.DataFrame(irct_list).to_csv(save_path + 'irct_12jul_2021.csv')

# # ChiCTR
#
# This scraper works poorly. You only get between 10-30 trials scraped before you run into the anti-dos blocks. I ran it multiple times over about a day and a half to gather the data on ChiCTR trials.

# +
chictr_urls = df[df.source_register == 'ChiCTR'].web_address.to_list()

chictr_trials = []

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

pd.DataFrame(chictr_trials).to_csv(save_path + 'chictr_jul21.csv')

# # jRCT

# +
jrct_urls = df[(df.source_register == 'JPRN') & (df.trialid.str.contains('jRCT'))].web_address.to_list()

jrct_urls_eng = []

for j in jrct_urls:
    jrct_urls_eng.append(j[:24] + 'en-' + j[24:])
# -


jrct_urls_eng[0]

# +
jrct_trials = []

for j in tqdm(jrct_urls_eng):
    j_dict = {}
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

pd.DataFrame(jrct_trials).to_csv(save_path + 'jrct_13jul21.csv')

# # REBEC

# +
rebec_ids = df[df.source_register == 'REBEC'].trialid.to_list()

rebec_url = 'https://ensaiosclinicos.gov.br/rg/{}'
# -

s = get_url(rebec_url.format(rebec_ids[0]))

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

pd.DataFrame(rebec_trials).to_csv(save_path + 'rebec_13jul_2021.csv')

# # PACTR

pactr_urls = df[df.source_register == 'PACTR'].web_address.to_list()

# +
pactr_trials = []
id_regex = re.compile(r'PACTR\d{15}')

for p in tqdm(pactr_urls):
    soup = get_url(p)
    p_dict = {}
    
    p_dict['trial_id'] = soup.find('td', text=re.compile(id_regex)).text
    
    p_dict['anticipated_comp'] = pd.to_datetime(soup.find('td', text='Anticipated date of last follow up').find_next('td').text)
    
    p_dict['actual_comp'] = pd.to_datetime(soup.find('td', text='Actual Last follow-up date').find_next('td').text)
    
    p_dict['trial_status'] = soup.find('td', text='Recruitment status').find_next('td').text
    
    if s.find('td', text='Changes to trial information').find_next('tr'):
        p_dict['last_updated'] = pd.to_datetime(soup.find('td', text='Changes to trial information').find_next('tr').find_next('tr').find_all('td')[2].text)
    else:
        p_dict['last_updated'] = pd.to_datetime(soup.find('td', text='\r\n                  Date of Approval:\r\n                ').find_next('td').text)
        
    emails = []
    for e in soup.find('td', text='CONTACT PEOPLE').parent.parent.find_all('b',text='Email'):
        emails.append(e.find_next('tr').find_all('td')[2].text)
    p_dict['emails'] = emails
    
    pactr_trials.append(p_dict)
# -

pd.DataFrame(pactr_trials).to_csv(save_path + 'pactr_16jul_2021.csv')

# # Cris

cris_urls = df[df.source_register == 'CRIS'].web_address.to_list()

# +
cris_trials = []

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
# -

pd.DataFrame(cris_trials).to_csv(save_path + 'cris_16jul_2021.csv')

# # JPRN UMIN

umin_urls = df[(df.source_register == 'JPRN') & (df.trialid.str.contains('UMIN'))].web_address.to_list()

umin_urls[0]

# +
umin_trials = []

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
    
# -

pd.DataFrame(umin_trials).to_csv(save_path + 'umin_trials18jul21.csv')



# # RPCEC

rpcec_urls = df[df.source_register == 'RPCEC'].web_address.to_list()

# +
rpcec_trials = []

for rp in tqdm(rpcec_urls):
    rp_dict = {}
    soup = get_url(rp)
    sopa = get_url(rp.replace('En', 'Sp').replace('en/trials', 'ensayos'))
    
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
# -

pd.DataFrame(rpcec_trials).to_csv(save_path + 'rpcec_18jul21.csv')








