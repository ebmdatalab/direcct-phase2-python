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

# After running the scrapers in Notebook 3 and manually retrieving additional data from the registries from a small number of trials, we combined this data in an excel sheet `registry_data.xlsx` detailing the data collected and where it came from. This notebook will clean up this data in a way we can use to be merged into the final dataset

import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

import pandas as pd
import re
import numpy as np

# +
reg = pd.read_excel(parent + '/data/registry_data/registry_data.xlsx', sheet_name='Full')

ictrp = pd.read_csv(parent + '/data/cleaned_ictrp_16Dec2020.csv')
# -

reg.columns

ictrp.head()

merged = reg.merge(ictrp[['trialid', 'web_address']], how='left', 
                   left_on='trial_id', right_on='trialid').drop('trialid', axis=1)

merged['pcd'] = pd.to_datetime(merged['pcd'], errors='coerce')
merged['scd'] = pd.to_datetime(merged['scd'], errors='coerce')

# +
conditions = [merged.pcd.notnull(), (merged.pcd.isnull() & merged.scd.notnull()), (merged.pcd.isnull() & merged.scd.isnull())]
choices = [merged.pcd, merged.scd, None]

merged['relevant_comp_date'] = np.select(conditions, choices)
merged['relevant_comp_date'] = pd.to_datetime(merged['relevant_comp_date'], errors='coerce')
# -

merged['tabular_results'] = np.where(merged.reg_results_status.isin(['Study Results', 'View results']), 1, 0)

# +
filt_1 = merged.other_results_1.notnull()

filt_2 = merged.other_results_2.notnull()
# -

merged['potential_other_results'] = np.where((filt_1 | filt_2), 1, 0)

merged.to_csv(parent + '/data/registry_data/registry_data_clean.csv')

merged.head()


