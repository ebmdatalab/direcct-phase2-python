# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# + trusted=true
import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# + trusted=true
import pandas as pd
import numpy as np
import collections

# + trusted=true
arms = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/arms.csv')

# + trusted=true
len(arms)

# + trusted=true
intervention_arms = arms[arms.type == 'experimental']

# + trusted=true
intervention_arms.head()

# + trusted=true
included_trials = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/main-analyses/kaplan-meier-time-to-pub.csv')

# + trusted=true
included_trials.head()

# + trusted=true
intervention_arms2 = intervention_arms[intervention_arms.id.isin(included_trials.id.to_list())].reset_index(drop=True)

# + trusted=true
len(intervention_arms2)

# + trusted=true
grouped = intervention_arms2[['id', 'intervention']].groupby('id')['intervention'].apply(list)

# + trusted=true
ids = grouped.index.to_list()
ints = grouped.to_list()

# + trusted=true
unique_tx_dict = {}
running_int_list = []

for i, t in zip(ids, ints):
    all_ints = []
    for x in t:
        if ';' in x:
            split_ints = x.split(';')
            all_ints = all_ints + split_ints
        else:
            all_ints.append(x)
    unique_tx_dict[i] = ';'.join(set(all_ints))
    running_int_list = running_int_list + list(set(all_ints))

# + trusted=true
c = collections.Counter(x for x in running_int_list if x)

# + trusted=true
int_counts = pd.DataFrame.from_dict(dict(c), orient='index').reset_index()
int_counts.columns = ['interventions', 'counts']

# + trusted=true
int_counts.sort_values(by='counts', ascending=False).to_csv(parent + '/data/interventions/' + 'top_ints.csv')

# + trusted=true
int_counts.sort_values(by='counts', ascending=False).head(10)

# + trusted=true
pd.DataFrame.from_dict(unique_tx_dict, orient='index').reset_index().rename({'index':'id', 0:'intervention'}, axis=1).to_csv(parent + '/data/interventions/' + 'int_mapping.csv')
# -


# +

# -







