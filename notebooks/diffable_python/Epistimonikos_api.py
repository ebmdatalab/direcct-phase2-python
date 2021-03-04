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

from lib.credentials import epistomonikos_api

from requests import get

response = get("https://api.epistemonikos.org/v1/documents/00bffc961ab6f181eca9f2aa184970c3c48a1ff1", headers={'Authorization': epistomonikos_api['access_token']})
response.json()


def get_url(url):
    response = get(url, verify = False)
    html = response.content
    soup = BeautifulSoup(html, "html.parser")
    return soup


