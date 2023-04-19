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
import pandas as pd
import numpy as np

# + trusted=true
import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# + trusted=true
df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/kaplan-meier-time-to-pub.csv?token=GHSAT0AAAAAAB5S2YBJQ4MQEDBJTJWVKDAAZBFZH4Q')
df.head()

# + trusted=true
randomisation_df = pd.read_csv('https://raw.githubusercontent.com/worcjamessmith/COVID-trial-characteristics/main/data/final_dataset.csv')

# + trusted=true
randomisation_df.head(2)

# + trusted=true
randomisation_df[randomisation_df.TrialID.str.contains('EUCTR')]

# + trusted=true
randomisation_df.columns

# + trusted=true
registrations = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/registrations.csv?token=GHSAT0AAAAAAB5S2YBI65TVQ7I3LA6SRPMMZBFZPRA')

# + trusted=true
registrations.head()

# + trusted=true
test = registrations[['id', 'trn']].merge(randomisation_df[['TrialID', 'randomisation']], left_on='trn', right_on='TrialID', how='left')

# + trusted=true
test.head()

# + trusted=true
test.randomisation.value_counts(dropna=False)

# + trusted=true
test[test.id.isin(df.id.to_list())].randomisation.value_counts(dropna=False)

# + trusted=true

# +



# + trusted=true
#ICTRP
ictrp = pd.read_csv(parent + '/data/ictrp_data/COVID19-web_1July2021.csv', dtype={'Phase': str})

# + trusted=true
ictrp.columns

# + trusted=true
working = ictrp[['TrialID', 'Public title', 'Scientific title', 'Source Register', 'Study design']].reset_index(drop=True)

# + trusted=true
working.columns = ['TrialID', 'Public_title', 'Scientific_title', 'Source_registry', 'Study_design']

# + trusted=true
#Fix EUCTR IDs

# + trusted=true
working['TrialID_fixed'] = np.where(working.TrialID.str.contains('EUCTR'), working.TrialID.str.rsplit('-', 1).str.get(0), working.TrialID)

# +
#Limit only to trials we care about to make life easy:

# + trusted=true
included_studies = registrations[registrations.id.isin(df.id.to_list())].trn.to_list()

# + trusted=true
final_working = working[working.TrialID_fixed.isin(included_studies)].reset_index(drop=True)

# + trusted=true
# # +
#randomisation checks

anzctr_yr = (final_working['Source_registry'] == 'ANZCTR') & (final_working['Study_design'].str.contains('Allocation: Randomised controlled trial'))
anzctr_nr = (final_working['Source_registry'] == 'ANZCTR') & (final_working['Study_design'].str.contains('Allocation: Non-randomised trial'))

#ChiCTR - only titles to be checked below
chictr_yr = (final_working['Source_registry'] == 'ChiCTR') & (final_working['Study_design'].str.contains('Randomized parallel controlled trial|Randomized cross-over control'))
chictr_nr = (final_working['Source_registry'] == 'ChiCTR') & (final_working['Study_design'].str.contains('Non randomized|Quasi-randomized controlled'))

ctg_yr = (final_working['Source_registry'] == 'ClinicalTrials.gov') & (final_working['Study_design'].str.contains('Allocation: Randomized'))
ctg_nr = (final_working['Source_registry'] == 'ClinicalTrials.gov') & (final_working.Study_design.notnull()) & ~(final_working['Study_design'].str.contains('Allocation: Randomized', na=False))

ctri_yr = (final_working['Source_registry'] == 'CTRI') & (final_working['Study_design'].str.contains(r'Randomized|Method of generating randomization sequence:Stratified randomization|Method of generating randomization sequence:Computer generated randomization|Method of generating randomization sequence:Other|Method of generating randomization sequence:Random Number Table'))
ctri_nr = (final_working['Source_registry'] == 'CTRI') & (final_working['Study_design'].str.contains(r'Non-randomized|Single Arm Trial'))

drks_yr = (final_working['Source_registry'] == 'German Clinical Trials Register') & (final_working['Study_design'].str.contains('Allocation: Randomized'))
drks_nr = (final_working['Source_registry'] == 'German Clinical Trials Register') & (final_working.Study_design.notnull()) & ~(final_working['Study_design'].str.contains('Allocation: Randomized', na=False))

euctr_yr = (final_working['Source_registry'] == 'EU Clinical Trials Register') & (final_working['Study_design'].str.contains('Randomised: yes'))
euctr_nr = (final_working['Source_registry'] == 'EU Clinical Trials Register') & (final_working.Study_design.notnull()) & ~(final_working['Study_design'].str.contains('Randomised: yes', na=False))

irct_yr = (final_working['Source_registry'] == 'IRCT') & (final_working['Study_design'].str.contains('Randomization: Randomized'))
irct_nr = (final_working['Source_registry'] == 'IRCT') & ~(final_working['Study_design'].str.contains('Randomization: Randomized') & ~(final_working['Study_design'].str.contains(r'(?i)Randomization: N/A', na=False)))

isrctn_yr = (final_working['Source_registry'] == 'ISRCTN') & (final_working['Study_design'].str.contains(r'(?i)randomi[s,z]ed|cluster-randomised|parallel')) & ~(final_working['Study_design'].str.contains(r'(?i)non-randomi[s,z]ed', na=False))
isrctn_nr = (final_working['Source_registry'] == 'ISRCTN') & (final_working['Study_design'].str.contains(r'(?i)non-randomi[s,z]ed'))

#lol JPRN-JapicCTI-184176
jprn_yr = (final_working['Source_registry'] == 'JPRN') & (final_working['Study_design'].str.contains(r'(?i)randomi[s,z]ed')) & ~(final_working['Study_design'].str.contains(r'(?i)non-randomi[s,z]ed', na=False))
jprn_nr = (final_working['Source_registry'] == 'JPRN') & (final_working['Study_design'].str.contains(r'(?i)Non-randomi[s,z]ed|single assignment|single arm'))

kct_yr = (final_working['Source_registry'] == 'KCT') & (final_working['Study_design'].str.contains('Allocation : RCT'))
kct_nr = (final_working['Source_registry'] == 'KCT') & ~(final_working['Study_design'].str.contains('Allocation : RCT', na=False))

lbctr_yr = (final_working['Source_registry'] == 'LBCTR') & (final_working['Study_design'].str.contains('Allocation: Randomized controlled trial'))

ntr_yr = (final_working['Source_registry'] == 'Netherlands Trial Register') & (final_working['Study_design'].str.contains('Randomized: Yes'))
ntr_nr = (final_working['Source_registry'] == 'Netherlands Trial Register') & ~(final_working['Study_design'].str.contains('Randomized: Yes', na=False))

#"Randomised" is not capitalised when the value is "Non-randomised"
pactr_yr = (final_working['Source_registry'] == 'PACTR') & (final_working['Study_design'].str.contains(r'Randomi[s,z]ed'))
pactr_nr = (final_working['Source_registry'] == 'PACTR') & ~(final_working['Study_design'].str.contains(r'Randomi[s,z]ed', na=False))

#PER: Free text so will only do positive case for randomized
per_yr = (final_working['Source_registry'] == 'PER') & (final_working['Study_design'].str.contains(r'(?i)\brandomi[s,z]ed|Randomization'))

#This one is a little hokey...should check or just do manually
rbr_yr = (final_working['Source_registry'] == 'RBR') & (final_working['Study_design'].str.contains(r'(?i)randomi[s,z]ed')) & ~(final_working['Study_design'].str.contains(r'(?i)non-?randomi[s,z]ed|single-group', na=False))
rbr_nr = (final_working['Source_registry'] == 'RBR') & (final_working['Study_design'].str.contains(r'(?i)non-?randomi[s,z]ed|single-group'))

tctr_yr = (final_working['Source_registry'] == 'TCTR') & (final_working['Study_design'].str.contains('Randomized controlled trial'))
tctr_nr = (final_working['Source_registry'] == 'TCTR') & (final_working['Study_design'].notnull()) & ~(final_working['Study_design'].str.contains('Randomized controlled trial', na=False)) & ~(final_working['Study_design'] == 'Not Specified')

rpcec_yr = (final_working['Source_registry'] == 'RPCEC') & (final_working['Study_design'].str.contains('Allocation: Randomized trial|Allocation: Randomized controlled trial'))
rpcec_nr = (final_working['Source_registry'] == 'RPCEC') & ~(final_working['Study_design'].str.contains('Allocation: Randomized trial|Allocation: Randomized controlled trial', na=False))

# # +
conds_r = [anzctr_yr, anzctr_nr, chictr_yr, chictr_nr, ctg_yr, ctg_nr, ctri_yr, ctri_nr, drks_yr, drks_nr, euctr_yr, euctr_nr, 
           irct_yr, irct_nr, jprn_yr, jprn_nr, kct_yr, kct_nr, ntr_yr, ntr_nr, pactr_yr, pactr_nr, rbr_yr, rbr_nr, 
           tctr_yr, tctr_nr, rpcec_yr, rpcec_nr, isrctn_yr, isrctn_nr, lbctr_yr, per_yr]

out_r = ['Yes', 'No'] *  15 + ['Yes'] * 2

final_working['Randomisation'] = np.select(conds_r, out_r, 'Not Assessed')

# # +
randomised_cond = ((final_working.Randomisation != 'Yes') & 
                   ((final_working['Scientific_title'].str.contains(r'(?i)randomi[s,z]ed|stratified-randomized|random controlled')) | 
                    (final_working['Public_title'].str.contains(r'(?i)randomi[s,z]ed|stratified-randomized|random controlled'))) & 
                   ~((final_working['Scientific_title'].str.contains(r'(?i)non-randomi[s,z]ed')) | 
                     (final_working['Public_title'].str.contains(r'(?i)non-randomi[s,z]ed'))))

final_working['Randomisation'] = np.where(randomised_cond, 'Yes', final_working.Randomisation)

final_working['Randomisation'] = np.where((final_working['Source_registry'] == 'IRCT') & 
                                          final_working['Study_design'].str.contains('Randomization: N/A') & 
                                          ~(final_working['Study_design'].str.contains('Assignment: Single', na=False)), 
                                          'Not Assessed', final_working.Randomisation)


final_working['Randomisation'] = np.where((final_working['Source_registry'] == 'ChiCTR') & 
                                          final_working['Study_design'].str.contains('Single arm'), 
                                          'No', final_working.Randomisation)

# + trusted=true
final_working['Randomisation'].value_counts()

# + trusted=true
final_working[(final_working.Randomisation == 'Not Assessed') | (final_working.Randomisation.isna())].Study_design.value_counts()
# +


