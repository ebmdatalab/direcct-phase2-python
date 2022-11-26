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
raw_extract = pd.read_csv(parent + '/data/interventions/2022-10-05_095641-form_7-refset_34-extractions.tsv', sep='\t', encoding="ISO-8859-1")
raw_arms = pd.read_csv(parent + '/data/interventions/2022-10-05_095649-sub_arm-refset_34-sub-extraction.tsv', sep='\t', encoding="ISO-8859-1")
rec_extract = pd.read_csv(parent + '/data/interventions/2022-10-05_095652-form_7-refset_34-final.tsv', sep='\t', encoding="ISO-8859-1")
rec_arms = pd.read_csv(parent + '/data/interventions/2022-10-05_095655-sub_arm-refset_34-sub-final.tsv', sep='\t', encoding="ISO-8859-1")

# + trusted=true
reconciled_ids = rec_arms.db_id.to_list()

# + trusted=true
remove_rec = raw_arms[~raw_arms.db_id.isin(reconciled_ids)]

# + trusted=true
cols = ['db_id', 'trialid', 'type', 'placebo_plus_soc', 'category', 'intervention', 'intervention_plus_soc']

# + trusted=true
final_int = pd.concat([remove_rec[cols], rec_arms[cols]]).reset_index(drop=True)

# + trusted=true
final_exp = final_int[final_int.type == 'experimental'].reset_index(drop=True)

# + trusted=true
final_exp.head()

# + trusted=true
final_exp.to_csv(parent + '/data/interventions/int_norm.csv')
# + trusted=true
exp = final_int[final_int.type == 'experimental']

# + trusted=true
final_int[final_int.intervention.isna()]

# + trusted=true
ints = final_int[final_int.type == 'experimental'].intervention
int_list = ints.to_list()

# + trusted=true
final_int.loc[3916]

# + trusted=true
a = ints.to_frame()
a[a.intervention.isna()]

# + trusted=true
all_ints = []
for i in int_list:
    if ';' in i:
        all_ints = all_ints + i.split(';')
    else:
        all_ints.append(i)

# + trusted=true
c = collections.Counter(x for x in all_ints if x)

# + trusted=true
int_counts = pd.DataFrame.from_dict(dict(c), orient='index').reset_index()
int_counts.columns = ['interventions', 'counts']

# + trusted=true
int_counts.sort_values(by='counts', ascending=False)

# + trusted=true
c2 = collections.Counter(x for x in int_list if x)

# + trusted=true
int_counts2 = pd.DataFrame.from_dict(dict(c2), orient='index').reset_index()
int_counts2.columns = ['interventions', 'counts']

# + trusted=true
int_counts2

# + trusted=true
int_counts2.sort_values(by='counts', ascending=False).to_csv(parent + '/data/interventions/int_to_norm.csv')

# +



# + trusted=true
final_exp['HCQ'] = np.where(final_exp.intervention.str.contains('Hydroxychloroquine'), 1, 0)
final_exp['IVE'] = np.where(final_exp.intervention.str.contains('Ivermectin'), 1, 0)
final_exp['CP'] = np.where(final_exp.intervention.str.contains('Convalescent Plasma'), 1, 0)

# + trusted=true
final_exp[['db_id', 'HCQ', 'IVE', 'CP']].groupby('db_id').sum().to_csv(parent + '/data/interventions/common_ints.csv')
# -








# +



# + trusted=true
ints = final_int[final_int.type == 'experimental'].intervention

# + trusted=true
ints
# +



# + trusted=true
ints_exp = final_int[final_int.type == 'experimental']
# -

ints_exp[ints_exp.

# + trusted=true
final_int[final_int.intervention == 'Dabur chyawanprash']
# -










# +



# + trusted=true
int_list = ints.to_list()

# + trusted=true
all_ints = []
for i in int_list:
    if ';' in i:
        all_ints = all_ints + i.split(';')
    else:
        all_ints.append(i)

# + trusted=true
import collections
c = collections.Counter(x for x in all_ints if x)

# + trusted=true
int_counts = pd.DataFrame.from_dict(dict(c), orient='index').reset_index()
int_counts.columns = ['interventions', 'counts']

# + trusted=true
int_counts.sort_values(by='counts', ascending=False).head(10)

# + trusted=true
int_counts.to_csv(parent + '/data/interventions/unique_ints.csv')
# -








# +


