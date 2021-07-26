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

# This notebook takes the raw ICTRP COVID-19 registered trials CSV, cuts it down to only the fields we need, and cleans/processes the data using techniques developed for covid19.trialstracker.net

# +
import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# %load_ext autoreload
# %autoreload 2
# -

import pandas as pd
import numpy as np
from datetime import date

df = pd.read_csv(parent + '/data/ictrp_data/COVID19-web_1July2021.csv', dtype={'Phase': str})

# +
from lib.data_cleaning import enrollment_dates, fix_date, fix_errors, d_c

#This is fixes for known broken enrollement dates    
enrollment_errors= {
    'IRCT20200310046736N1': ['14/06/2641', '2020-04-01'],
    'EUCTR2020-001909-22-FR': ['nan', '2020-04-29']
}

reg_date_errors = {
    'RBR-5p8nzk6': ['0', '20201125'],
    'RBR-8tygcz7': ['0', '20201201']}

# +
df = fix_errors(enrollment_errors, df, 'Date enrollement')

df = fix_errors(reg_date_errors, df, 'Date registration3')

# +
df['Date enrollement'] = df['Date enrollement'].apply(enrollment_dates)

df['Date registration'] = pd.to_datetime(df['Date registration3'], format='%Y%m%d', errors='coerce')

# +
from lib.data_cleaning import enroll_extract

#Extracting target enrollment
size = df['Target size'].tolist()

df['target_enrollment'] = enroll_extract(size)

#Creating retrospective registration
df['retrospective_registration'] = np.where(df['Date registration'] > df['Date enrollement'], True, False)

# +
#Taking only what we need right now

cols = ['TrialID', 'Source Register', 'Date registration', 'Date enrollement', 'retrospective_registration', 
        'Primary sponsor', 'Recruitment Status', 'Phase', 'Study type', 'Countries', 'Public title', 
        'Intervention', 'target_enrollment', 'web address', 'results yes no', 'results url link']

df_cond = df[cols].reset_index(drop=True)

#renaming columns to match old format so I don't have to change them throughout
df_cond.columns = ['TrialID', 'Source_Register', 'Date_registration', 'Date_enrollement', 
                   'retrospective_registration', 'Primary_sponsor', 'Recruitment_Status', 'Phase', 'Study_type', 
                   'Countries', 'Public_title', 'Intervention', 'target_enrollment', 'web_address', 
                   'has_results', 'results_url_link']

print(f'The ICTRP shows {len(df_cond)} trials')
# -

df_cond_all = df_cond.copy()

# +
#Data cleaning various fields. 
#One important thing we have to do is make sure there are no nulls or else the data won't properly load onto the website

#semi-colons in the intervention field mess with CSV
df_cond_all['Intervention'] = df_cond_all['Intervention'].str.replace(';', '')

#Study Type
obv_replace = ['Observational [Patient Registry]', 'observational', 'Observational Study']
int_replace = ['interventional', 'Interventional clinical trial of medicinal product', 'Treatment', 
               'INTERVENTIONAL', 'Intervention', 'Interventional Study', 'PMS']
hs_replace = ['Health services reaserch', 'Health Services reaserch', 'Health Services Research']

df_cond_all['Study_type'] = (df_cond_all['Study_type'].str.replace(' study', '')
                             .replace(obv_replace, 'Observational').replace(int_replace, 'Interventional')
                             .replace('Epidemilogical research', 'Epidemiological research')
                             .replace(hs_replace, 'Health services research')
                             .replace('Others,meta-analysis etc', 'Other'))

#phase
df_cond_all['Phase'] = df_cond_all['Phase'].fillna('Not Applicable')
na = ['0', 'Retrospective study', 'Not applicable', 'New Treatment Measure Clinical Study', 'Not selected', 
      'Phase 0', 'Diagnostic New Technique Clincal Study', '0 (exploratory trials)', 'Not Specified']
p1 = ['1', 'Early Phase 1', 'I', 'Phase-1', 'Phase I']
p12 = ['1-2', '2020-02-01 00:00:00', 'Phase I/II', 'Phase 1 / Phase 2', 'Phase 1/ Phase 2', '02-Jan',
       'Human pharmacology (Phase I): yes\nTherapeutic exploratory (Phase II): yes\nTherapeutic confirmatory - (Phase III): no\nTherapeutic use (Phase IV): no\n']
p2 = ['2', 'II', 'Phase II', 'IIb', 'Phase-2', 'Phase2',
      'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): yes\nTherapeutic confirmatory - (Phase III): no\nTherapeutic use (Phase IV): no\n']
p23 = ['Phase II/III', '2020-03-02 00:00:00', 'II-III', 'Phase 2 / Phase 3', 'Phase 2/ Phase 3', '2-3', '03-Feb',
       'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): yes\nTherapeutic confirmatory - (Phase III): yes\nTherapeutic use (Phase IV): no\n']
p3 = ['3', 'Phase III', 'Phase-3', 'III',
      'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): no\nTherapeutic confirmatory - (Phase III): yes\nTherapeutic use (Phase IV): no\n']
p34 = ['Phase 3/ Phase 4', 'Phase III/IV',
       'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): no\nTherapeutic confirmatory - (Phase III): yes\nTherapeutic use (Phase IV): yes\n']
p4 = ['4', 'IV', 'Post Marketing Surveillance', 'Phase IV', 'PMS',
      'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): no\nTherapeutic confirmatory - (Phase III): no\nTherapeutic use (Phase IV): yes\n']

df_cond_all['Phase'] = (df_cond_all['Phase'].replace(na, 'Not Applicable').replace(p1, 'Phase 1')
                        .replace(p12, 'Phase 1/Phase 2').replace(p2, 'Phase 2')
                        .replace(p23, 'Phase 2/Phase 3').replace(p3, 'Phase 3').replace(p34, 'Phase 3/Phase 4')
                        .replace(p4, 'Phase 4'))

#Fixing Observational studies incorrectly given a Phase in ICTRP data
m = ((df_cond_all.Phase.str.contains('Phase')) & (df_cond_all.Study_type == 'Observational'))
df_cond_all['Phase'] = df_cond_all.Phase.where(~m, 'Not Applicable')

#Recruitment Status
df_cond_all['Recruitment_Status'] = df_cond_all['Recruitment_Status'].replace('Not recruiting', 'Not Recruiting')
df_cond_all['Recruitment_Status'] = df_cond_all['Recruitment_Status'].fillna('No Status Given')

#Get rid of messy accents
from lib.data_cleaning import norm_names
    
df_cond_all['Primary_sponsor'] = df_cond_all.Primary_sponsor.apply(norm_names)
df_cond_all['Primary_sponsor'] = df_cond_all['Primary_sponsor'].replace('NA', 'No Sponsor Name Given')
df_cond_all['Primary_sponsor'] = df_cond_all['Primary_sponsor'].replace('nan', 'No Sponsor Name Given')

# +
#Countries
df_cond_all['Countries'] = df_cond_all['Countries'].fillna('No Country Given').replace('??', 'No Country Given')

china_corr = ['Chian', 'China?', 'Chinese', 'Wuhan', 'Chinaese', 'china', 'Taiwan, Province Of China', 
              "The People's Republic of China"]

country_values = df_cond_all['Countries'].tolist()

new_list = []

for c in country_values:
    country_list = []
    if isinstance(c, float):
        country_list.append('No Sponsor Name Given')
    elif c == 'No Sponsor Name Given':
        country_list.append('No Sponsor Name Given')
    elif c in china_corr:
        country_list.append('China')
    elif c in ['Iran (Islamic Republic of)', 'Iran, Islamic Republic of']:
        country_list.append('Iran')
    elif c in ['Viet nam', 'Viet Nam']:
        country_list.append('Vietnam')
    elif c in ['Korea, Republic of', 'Korea, Republic Of', 'KOREA'] :
        country_list.append('South Korea')
    elif c in ['USA', 'United States of America', 'U.S.']:
        country_list.append('United States')
    elif c == 'Japan,Asia(except Japan),Australia,Europe':
        country_list = ['Japan', 'Australia', 'Asia', 'Europe']
    elif c == 'Japan,Asia(except Japan),North America,South America,Australia,Europe,Africa':
        country_list = ['Japan, Asia(except Japan), North America, South America, Australia, Europe, Africa']
    elif c == 'The Netherlands':
        country_list.append('Netherlands')
    elif c == 'England':
        country_list.append('United Kingdom')
    elif c == 'Japan,North America':
        country_list = ['Japan', 'North America']
    elif c == 'Czechia':
        country_list.append('Czech Republic')
    elif c == 'ASIA':
        country_list.append('Asia')
    elif c == 'EUROPE':
        country_list.append('Europe')
    elif c == 'MALAYSIA':
        country_list.append('Malaysia')
    elif c in ['Congo', 'Congo, Democratic Republic', 'Congo, The Democratic Republic of the']:
        country_list.append('Democratic Republic of Congo')
    elif c in ["C√¥te D'Ivoire", 'Cote Divoire', "CÃ´te D'Ivoire"]:
        country_list.append("Cote d'Ivoire")
    elif c in ['Türkiye', 'TÃ¼rkiye', 'TÃƒÂ¼rkiye']:
        country_list.append('Turkey')
    elif c == 'SOUTH AMERICA':
        country_list.append('South America')
    elif c == 'AFRICA':
        country_list.append('Africa')
    elif c == 'italy':
        country_list.append('Italy')
    elif ';' in c:
        c_list = c.split(';')
        unique_values = list(set(c_list))
        for v in unique_values:
            if v in china_corr:
                country_list.append('China')
            elif v in ['Iran (Islamic Republic of)', 'Iran, Islamic Republic of']:
                country_list.append('Iran')
            elif v in ['Korea, Republic of', 'Korea, Republic Of', 'KOREA']:
                country_list.append('South Korea')
            elif v in ['Viet nam', 'Viet Nam']:
                country_list.append('Vietnam')
            elif v in ['USA', 'United States of America']:
                country_list.append('United States')
            elif v == 'The Netherlands':
                country_list.append('Netherlands')
            elif v == 'England':
                country_list.append('United Kingdom')
            elif v == 'Czechia':
                country_list.append('Czech Republic')
            elif v == 'ASIA':
                country_list.append('Asia')
            elif v == 'EUROPE':
                country_list.append('Europe')
            elif v == 'MALAYSIA':
                country_list.append('Malaysia')
            elif v in ['Congo', 'Congo, Democratic Republic', 'Congo, The Democratic Republic of the']:
                country_list.append('Democratic Republic of Congo')
            elif v in ["C√¥te D'Ivoire", 'Cote Divoire', "CÃ´te D'Ivoire"]:
                country_list.append("Cote d'Ivoire")
            elif v in ['Türkiye', 'TÃ¼rkiye', 'TÃƒÂ¼rkiye']:
                country_list.append('Turkey')
            elif v == 'SOUTH AMERICA':
                country_list.append('South America')
            elif v == 'AFRICA':
                country_list.append('Africa')
            elif v == 'italy':
                country_list.append('Italy')
            else:
                country_list.append(v)
    else:
        country_list.append(c.strip())
    new_list.append(', '.join(country_list))

df_cond_all['Countries'] = new_list

# +
#Final organising

col_names = []

for col in list(df_cond_all.columns):
    col_names.append(col.lower())
    
df_cond_all.columns = col_names

reorder = ['trialid', 'source_register', 'date_registration', 'date_enrollement', 'retrospective_registration', 
           'recruitment_status', 'phase', 'study_type', 'countries', 'public_title', 
            'target_enrollment', 'web_address']

df_intermediate = df_cond_all[reorder].reset_index(drop=True).drop_duplicates().reset_index(drop=True)

# +
print(f'There are {len(df_intermediate)} total unique registered studies on the ICTRP')

non_int = df_intermediate[((df_intermediate.study_type == 'Interventional') | (df_intermediate.study_type == 'Prevention'))].reset_index(drop=True)

print(f'{len(non_int)} are Interventional or on Prevention. We exclude {len(df_intermediate) - len(non_int)} at this setp')

in_2020 = non_int[(non_int.date_registration >= pd.Timestamp(2020,1,1))].reset_index(drop=True)

print(f'{len(in_2020)} started since 1 Jan 2020. We exclude {len(non_int) - len(in_2020)} at this step')

withdrawn = in_2020[~(in_2020.public_title.str.contains('Cancelled') | in_2020.public_title.str.contains('Retracted due to'))].reset_index(drop=True)

print(f'{len(withdrawn)} are not listed as cancelled/withdrawn. We exclude {len(in_2020) - len(withdrawn)} at this step but will exclude additional trials after scraping the registries')
# -

df_for_scrape = withdrawn.copy()

df_for_scrape.to_csv(parent + '/data/scrape_df_jul21.csv')

df_intermediate.to_csv(parent + '/data/cleaned_ictrp_1jul2021.csv')





















