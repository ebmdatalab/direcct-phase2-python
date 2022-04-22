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

# https://api.epistemonikos.org
#
# https://app.iloveevidence.com/loves/5e6fdb9669c00e4ac072701d
#
# https://api.iloveevidence.com/pub/v2.alpha/references/search
#
# https://docs.google.com/document/d/1r6R2odna0QllscYmpQLlG8megu0qEW4qzsmQq930UG0/edit#

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

from lib.credentials import epistemonikos_api

from requests import get
from requests import post

from math import ceil
from tqdm.auto import tqdm

# +
search_api = "https://api.iloveevidence.com/pub/v2.alpha/references/search"

headers = {'Authorization': f"Token token={epistemonikos_api['access_token']}"}
# -

get("https://api.epistemonikos.org/v1/documents/00bffc961ab6f181eca9f2aa184970c3c48a1ff1").json()

response = get("https://api.epistemonikos.org/v1/documents/00bffc961ab6f181eca9f2aa184970c3c48a1ff1", headers={'Authorization': f"Token token={epistemonikos_api['access_token']}"})
response.json()

response = get("https://api.epistemonikos.org/v1/documents/00bffc961ab6f181eca9f2aa184970c3c48a1ff1", headers={'Authorization': epistemonikos_api['access_token']})
response.json()

# +
payload = {"categories": "5e7fce7e3d05156b5f5e032a", 
           "article_type": "primary-study",
           #"study_design": "rct",
           "sort_by": "year",
           "order_by": "asc",
           "page": 1,
           "size": 2}

pre_response = post(search_api, headers={'Authorization': f"Token token={epistemonikos_api['access_token']}"}, data=payload)
# -

from time import sleep

pre_response.json()

max_page = ceil(pre_response.json()['info']['total_items'] / 50)
print(max_page)

# +
records = []

for x in tqdm(range(1,max_page+1)[0:10]):
    payload = {"categories": "5e7fce7e3d05156b5f5e032a", 
           "article_type": "primary-study",
           #"study_design": "rct",
           "sort_by": "year",
           "order_by": "asc",
           "page": x,
           "size": 50}
    response = post(search_api, headers=headers, data=payload).json()
    records = records + response['items']
    sleep(1)
    
# -

import pandas as pd

ids = []
for x in records:
    external = x['publication_info']['external_ids']
    for i in external:
        ids.append(i)

pd.DataFrame(ids).source.value_counts()


