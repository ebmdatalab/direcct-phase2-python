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

# This notebook performs the searches of PubMed and the CORD-19 Database for text representing trial registrations.

# # Setup

# +
import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# %load_ext autoreload
# %autoreload 2

# +
import os
from tqdm.auto import tqdm
import re
import json
import pandas as pd
import numpy as np
import xmltodict
import tarfile
import pickle

from bs4 import BeautifulSoup
from xml.etree.ElementTree import tostring

#Our searching function and lists of our regular expressions
from lib.id_searches import search_text, ids_exact, prefixes, registry_names
# -

# # PubMed Search

# +
#If the archive exists, load it in.
try:
    from lib.id_searches import zip_load
    archive_df = zip_load(parent + '/data/pubmed/pubmed_archive_1Jan_2021.csv.zip', 
                  'pubmed_archive_1Jan_2021.csv', index_col = 0)

#If it doesn't exist, you can do a new PubMed search
except FileNotFoundError:
    from pymed import PubMed
    from lib.credentials import email
    from lib.id_searches import query, create_pubmed_archive
    print('Archive file not found, conduting new PubMed search.')
    pubmed = PubMed(tool="Pymed", email=email)
    results = pubmed.query(query, max_results=150000)
    results_length = pubmed.getTotalResultsCount(query)
    print(f'There are {results_length} results')
          
    print('Transforming results. This may take a few minutes.')
    #results_list = list(results) #This can take a while
    #print(f'Transformed {len(results_list)} results')
    
    #archive_df = create_pubmed_archive(results_list)
    archive_df = create_pubmed_archive(results, results_length)
    archive_df.to_csv(parent + '/data/pubmed/pubmed_archive_1Jan_2021.csv')
    print('Archive created')
    
# -

pubmed_data = archive_df.xml_json.tolist()

# +
pubmed_dicts = []
for rec in tqdm(pubmed_data):
    pm_dict = json.loads(rec)['PubmedArticle']
    entry_dict = {}
    art_ids = pm_dict['PubmedData']['ArticleIdList']['ArticleId']
    entry_dict['source'] = 'PubMed'
    entry_dict['pmid'] = pm_dict['MedlineCitation']['PMID']['#text']
    entry_dict['doi'] = None
    
    if isinstance(pm_dict['MedlineCitation']['Article']['ArticleTitle'], str):
        entry_dict['title'] = pm_dict['MedlineCitation']['Article']['ArticleTitle']
    elif isinstance(pm_dict['MedlineCitation']['Article']['ArticleTitle'], dict):
        entry_dict['title'] = pm_dict['MedlineCitation']['Article']['ArticleTitle']['#text']
    elif pm_dict['MedlineCitation']['Article']['ArticleTitle'] is None:
        entry_dict['title'] = 'No Title'
    
    if isinstance(art_ids, list):
        for x in art_ids:
            if x['@IdType'] == 'doi':
                entry_dict['doi'] = x['#text']
    elif isinstance(art_ids, dict):
        if art_ids['@IdType'] == 'doi':
            entry_dict['doi'] = art_ids['#text']
    try:
        dbs =  pm_dict['MedlineCitation']['Article']['DataBankList']['DataBank']
        accession_nums = []
        if isinstance(dbs, list):
            for x in dbs:
                ans = x['AccessionNumberList']['AccessionNumber']
                if isinstance(ans, list):
                    accession_nums += ans
                else:
                    accession_nums.append(x)
        elif isinstance(dbs, dict):
            x = dbs['AccessionNumberList']['AccessionNumber']
            if isinstance(x, list):
                accession_nums += x
            else:
                accession_nums.append(x)
                
        if accession_nums:
            entry_dict['accession'] = accession_nums
        else:
            entry_dict['accession'] = None
    except KeyError:
        entry_dict['accession'] = None
        
    
    try:
        pub_type_list = []
        pub_types = pm_dict['MedlineCitation']['Article']['PublicationTypeList']['PublicationType']
        if isinstance(pub_types, list):
            for pt in pub_types:
                pub_type_list.append(pt['#text'])
        elif isinstance(pub_types, dict):
            pub_type_list.append(pub_types['#text'])
        entry_dict['pub_types'] = pub_type_list
    except KeyError:
        entry_dict['pub_types'] = None
    
    try:
        entry_dict['pub_types_raw'] = pm_dict['MedlineCitation']['Article']['PublicationTypeList']
    except KeyError:
        entry_dict['pub_types_raw'] = None
    
    
    try:
        entry_dict['abstract'] = str(pm_dict['MedlineCitation']['Article']['Abstract']['AbstractText'])
    except KeyError:
        entry_dict['abstract'] = None

    pubmed_dicts.append(entry_dict)


# +
for d in tqdm(pubmed_dicts):
    d['abst_id_hits'] = search_text(ids_exact, d['abstract'])
    d['reg_prefix_hits'] = search_text(prefixes, d['abstract'])
    d['reg_name_hits'] = search_text(registry_names, d['abstract'])
    if 'review' in d['title'].lower():
        d['review_in_title'] = True
    else:
        d['review_in_title'] = False
    try:
        if 'Review' in d['pub_types']:
            d['review_type'] = True
        else:
            d['review_type'] = False
    except TypeError:
        d['review_type'] = False


# -

pubmed_search_results = pd.DataFrame(pubmed_dicts)
pubmed_search_results.to_csv(parent + '/data/pubmed/pubmed_search_results_jan2021.csv')

del archive_df

# # Searching CORD-19 data

metadata = zip_load(parent + '/data/cord_19/metadata.csv.zip', 'metadata.csv', low_memory = False)
metadata['publish_time'] = pd.to_datetime(metadata['publish_time'])

# +
#Getting a list of all the filenames for the papers that were published in 2020
covid_19_arts = metadata[metadata.publish_time >= pd.Timestamp(2020,1,1)].sha.to_list()
covid_19_pmc = metadata[metadata.publish_time >= pd.Timestamp(2020,1,1)].pmcid.to_list()
recent_articles = []
for c in covid_19_arts:
    recent_articles.append(str(c) + '.json')

recent_pmcs = []
for p in covid_19_pmc:
    recent_pmcs.append(str(p) + '.xml.json')
# -

cord_hit_list = []
with tarfile.open(parent+'/data/cord_19/document_parses.tar.gz', 'r:gz') as tar:
    file_names = tar.getnames()
    files = tar.getmembers()
    for fn, f in zip(file_names, tqdm(files)):
        name = fn.split('/')[-1]
        doc_dict = {}
        if name in recent_articles:
            file = tar.extractfile(f)
            content = file.read()
            stringify = content.decode('utf-8')
            j = json.loads(content)
            doc_dict['file_name'] = j['paper_id']
            doc_dict['source'] = 'cord_pdf'
            doc_dict['id_hits'] = search_text(ids_exact, stringify)
            doc_dict['reg_prefix_hits'] = search_text(prefixes, stringify)
            doc_dict['reg_name_hits'] = search_text(registry_names, stringify)
            doc_dict['title'] = j['metadata']['title']
            if 'review' in doc_dict['title'].lower():
                doc_dict['review_in_title'] = True
            else:
                doc_dict['review_in_title'] = False
        elif name in recent_pmcs:
            file = tar.extractfile(f)
            content = file.read()
            stringify = content.decode('utf-8')
            j = json.loads(content)
            doc_dict['file_name'] = j['paper_id']
            doc_dict['source'] = 'cord_pmc'
            doc_dict['id_hits'] = search_text(ids_exact, stringify)
            doc_dict['reg_prefix_hits'] = search_text(prefixes, stringify)
            doc_dict['reg_name_hits'] = search_text(registry_names, stringify)
            doc_dict['title'] = j['metadata']['title']
            if 'review' in doc_dict['title'].lower():
                doc_dict['review_in_title'] = True
            else:
                doc_dict['review_in_title'] = False
        else:
            continue
        if doc_dict:
            cord_hit_list.append(doc_dict)

cord_df = pd.DataFrame(cord_hit_list)

import pickle
pickle.dump(cord_df, open('cord_df.pkl', 'wb'))

# # Bringing it all together

from lib.id_searches import make_doi_url, trial_pub_type, dedupe_list

# +
cord_pdf_merge = cord_df.merge(metadata[['sha', 'doi', 'pubmed_id', 'cord_uid', 'url']], how='left', left_on='file_name', right_on='sha').drop(['sha'], axis=1)

cord_pmc_merge = cord_df.merge(metadata[['pmcid', 'doi', 'pubmed_id', 'cord_uid', 'url']], how='left', left_on='file_name', right_on='pmcid').drop(['pmcid'], axis=1)

# +
combined = cord_pdf_merge[cord_pdf_merge.doi.notnull()].append(cord_pmc_merge[cord_pmc_merge.doi.notnull()], ignore_index=True)

final_cord = combined.loc[combined.astype(str).drop_duplicates().index].drop(['file_name'], axis=1).reset_index(drop=True)

merged = final_cord.merge(pubmed_search_results, how='outer', left_on='pubmed_id', right_on='pmid').drop(['abstract', 'pub_types_raw'], axis=1)

# +
source_conds = [(merged.source_x.notnull() & merged.source_y.isna()), 
                (merged.source_x.isna() & merged.source_y.notnull()), 
                merged.source_x.notnull() & merged.source_y.notnull()]
source_output = [merged.source_x, merged.source_y, 'mixed']

merged['source'] = np.select(source_conds, source_output, None)
merged.drop(['source_x', 'source_y'], axis=1, inplace=True)

# +
title_conds = [(merged.title_x.notnull() & merged.title_y.isna()), 
                (merged.title_x.isna() & merged.title_y.notnull()), 
                merged.title_x.notnull() & merged.title_y.notnull()]
title_output = [merged.title_x, merged.title_y, merged.title_y]

merged['title'] = np.select(title_conds, title_output, None)
merged.drop(['title_x', 'title_y'], axis=1, inplace=True)

# +
doi_conds = [(merged.doi_x.notnull() & merged.doi_y.isna()), 
                (merged.doi_x.isna() & merged.doi_y.notnull()), 
                merged.doi_x.notnull() & merged.doi_y.notnull()]
doi_output = [merged.doi_x, merged.doi_y, merged.doi_y]

merged['doi'] = np.select(doi_conds, doi_output, None)
merged.drop(['doi_x', 'doi_y'], axis=1, inplace=True)

# +
pmid_conds = [(merged.pubmed_id.notnull() & merged.pmid.isna()), 
                (merged.pubmed_id.isna() & merged.pmid.notnull()), 
                merged.pubmed_id.notnull() & merged.pmid.notnull()]
pmid_output = [merged.pubmed_id, merged.pmid, merged.pmid]

merged['pm_id'] = np.select(pmid_conds, pmid_output, None)
merged.drop(['pubmed_id', 'pmid'], axis=1, inplace=True)

# +
review_title_conds = [(merged.review_in_title_x.notnull() & merged.review_in_title_y.isna()), 
                      (merged.review_in_title_x.isna() & merged.review_in_title_y.notnull()), 
                      (merged.review_in_title_x == True) | (merged.review_in_title_y == True), 
                      (merged.review_in_title_x == False) & (merged.review_in_title_y == False)]
review_title_output = [merged.review_in_title_x, merged.review_in_title_y, True, False]

merged['review_in_title'] = np.select(review_title_conds, review_title_output)
merged.drop(['review_in_title_x', 'review_in_title_y'], axis=1, inplace=True)

# +
id_hits_cond = [merged.id_hits.notnull() & merged.abst_id_hits.isna(), 
                merged.id_hits.isna() & merged.abst_id_hits.notnull(), 
                merged.id_hits.notnull() & merged.abst_id_hits.notnull()]
id_hits_output= [merged.id_hits, merged.abst_id_hits, merged.id_hits + merged.abst_id_hits]
    
    
merged['trial_id_hits'] = np.select(id_hits_cond, id_hits_output, None)
merged['trial_id_hits'] = merged['trial_id_hits'].apply(dedupe_list)
merged.drop(['id_hits', 'abst_id_hits'], axis=1, inplace=True)

# +
prefix_hits_cond = [merged.reg_prefix_hits_x.notnull() & merged.reg_prefix_hits_y.isna(), 
                merged.reg_prefix_hits_x.isna() & merged.reg_prefix_hits_y.notnull(), 
                merged.reg_prefix_hits_x.notnull() & merged.reg_prefix_hits_y.notnull()]
prefix_hits_output= [merged.reg_prefix_hits_x, merged.reg_prefix_hits_y, 
                     merged.reg_prefix_hits_x + merged.reg_prefix_hits_y]
    
    
merged['prefix_hits'] = np.select(prefix_hits_cond, prefix_hits_output, None)
merged['prefix_hits'] = merged['prefix_hits'].apply(dedupe_list)
merged.drop(['reg_prefix_hits_x', 'reg_prefix_hits_y'], axis=1, inplace=True)

# +
reg_name_hits_cond = [merged.reg_name_hits_x.notnull() & merged.reg_name_hits_y.isna(), 
                      merged.reg_name_hits_x.isna() & merged.reg_name_hits_y.notnull(), 
                      merged.reg_name_hits_x.notnull() & merged.reg_name_hits_y.notnull()]
reg_name_hits_output= [merged.reg_name_hits_x, merged.reg_name_hits_y, 
                       merged.reg_name_hits_x + merged.reg_name_hits_y]
    
    
merged['reg_name_hits'] = np.select(reg_name_hits_cond, reg_name_hits_output, None)
merged['reg_name_hits'] = merged['reg_name_hits'].apply(dedupe_list)
merged.drop(['reg_name_hits_x', 'reg_name_hits_y'], axis=1, inplace=True)
# -

merged['id'] = np.where(merged.pm_id.isna(), merged.cord_uid, merged.pm_id)

final_df = merged.fillna(np.nan).groupby('id', as_index=False).first()

# +
final_df = final_df[['id', 'trial_id_hits', 'prefix_hits', 'reg_name_hits', 'pub_types', 'doi', 'pm_id', 
                     'cord_uid', 'url', 'title', 'review_in_title', 'review_type']]

final_df.columns = ['id', 'id_hits', 'prefix_hits', 'reg_name_hits', 'pub_types', 'doi', 'pm_id', 'cord_id', 'url', 
                    'title', 'review_in_title', 'review_type']
# -

final_df['pub_types'] = final_df.pub_types.astype(str).apply(trial_pub_type)
final_df['doi_link'] = final_df.doi.apply(make_doi_url)

final_df[((final_df.id_hits.notnull()) | (final_df.pub_types.notnull())) & 
         ((final_df.review_in_title != True) & (final_df.review_in_title != True))].to_csv(parent + '/data/final_auto_24Feb2021.csv')
