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
print(sys.version)

# + trusted=true
import schemdraw
from schemdraw import flow

import pandas as pd
import numpy as np

from lifelines import KaplanMeierFitter
#from lifelines_fix import add_at_risk_counts
from lifelines.plotting import add_at_risk_counts
from lifelines import AalenJohansenFitter
import warnings

import matplotlib.pyplot as plt 
from matplotlib_venn import venn3, venn3_circles, venn3_unweighted
# %matplotlib inline
# + trusted=true
from matplotlib.pyplot import Text

# + [markdown]
# # Loading Data


# + trusted=true
df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/main-analyses/kaplan-meier-time-to-pub.csv')
df.head()

# + trusted=true
#Making a copy to mess around with
df_copy = df.copy()

# + trusted=true
results_cutoff = pd.to_datetime('2021-08-15')
# -

# # Making Dates into Dates

# + trusted=true
for x in df_copy.columns:
    if 'date' in x:
        df_copy[x] = pd.to_datetime(df_copy[x])
# -

# # Joining in IDs

# + trusted=true
df_reg = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/registrations.csv?token=GHSAT0AAAAAAB5S2YBJNSWM6KQE5D6TM7RKZBVHJBQ')

# + trusted=true
grouped_reg = df_reg[['id','trn']].groupby('id')['trn'].apply(list).to_frame().reset_index()


# + trusted=true
df2 = df_copy.merge(grouped_reg[['id', 'trn']], on='id', how='left')

# + [markdown] jp-MarkdownHeadingCollapsed=true tags=[]
# # Filtering out post cut-off dates
#
# On checks, there should not be any but this just makes sure.

# + trusted=true
df2['date_publication_preprint_adj'] = np.where(df2.date_publication_preprint > results_cutoff, pd.NaT, df2.date_publication_preprint)
df2['date_publication_preprint_adj'] = pd.to_datetime(df2['date_publication_preprint_adj'])

# + trusted=true
df2['date_publication_article_adj'] = np.where(df2.date_publication_article > results_cutoff, pd.NaT, df2.date_publication_article)
df2['date_publication_article_adj'] = pd.to_datetime(df2['date_publication_article_adj'])

# + trusted=true
df2['date_publication_summary_adj'] = np.where(df2.date_publication_summary > results_cutoff, pd.NaT, df2.date_publication_summary)
df2['date_publication_summary_adj'] = pd.to_datetime(df2['date_publication_summary_adj'])
# -

# # Then we need to re-create the other columns from that adjusted data

# + trusted=true
#Reporting variables
df2['publication_preprint_adj'] = np.where(df2['date_publication_preprint_adj'].notnull(), True, False)
df2['publication_article_adj'] = np.where(df2['date_publication_article_adj'].notnull(), True, False)
df2['publication_summary_adj'] = np.where(df2['date_publication_summary_adj'].notnull(), True, False)
df2['publication_any_adj'] = np.where(df2['publication_preprint_adj'] | df2['publication_article_adj'] | df2['publication_summary_adj'], True, False)

# + trusted=true
#Time to reporting by route
df2['time_publication_preprint_adj'] = np.where(df2.publication_preprint_adj, 
                                                (df2.date_publication_preprint_adj - df2.date_completion) / pd.Timedelta('1 day'),
                                                (results_cutoff - df2.date_completion) / pd.Timedelta('1 day'))

df2['time_publication_article_adj'] = np.where(df2.publication_article_adj, 
                                                (df2.date_publication_article_adj - df2.date_completion) / pd.Timedelta('1 day'),
                                                (results_cutoff - df2.date_completion) / pd.Timedelta('1 day'))

df2['time_publication_summary_adj'] = np.where(df2.publication_summary_adj, 
                                                (df2.date_publication_summary_adj - df2.date_completion) / pd.Timedelta('1 day'),
                                                (results_cutoff - df2.date_completion) / pd.Timedelta('1 day'))

# + trusted=true
#Time to reporting any

df2['time_reporting_any_adj'] = df2[['time_publication_preprint_adj', 'time_publication_article_adj', 'time_publication_summary_adj']].min(axis=1)
# -

# # Overall Reporting Rate

# + trusted=true
overall_cols = ['id', 'trn', 'date_completion', 'date_publication_preprint_adj', 'date_publication_article_adj', 
                'date_publication_summary_adj', 'publication_preprint_adj', 'publication_article_adj', 
                'publication_summary_adj', 'publication_any_adj', 'time_publication_preprint_adj', 
                'time_publication_article_adj','time_publication_summary_adj', 'time_reporting_any_adj']

# + trusted=true
adjusted_data = df2[overall_cols].reset_index(drop=True)

# + trusted=true
adjusted_data['preprint_to_jounral'] = (adjusted_data.date_publication_article_adj - adjusted_data.date_publication_preprint_adj) / pd.Timedelta('1 day')

# + trusted=true
adjusted_data[(adjusted_data.preprint_to_jounral <= 0)]

# + trusted=true
adjusted_data[(adjusted_data.publication_preprint_adj == True) & 
              (adjusted_data.publication_article_adj == True) & 
              (adjusted_data.preprint_to_jounral >= 0)]['preprint_to_jounral'].describe()

# + [markdown] tags=[]
# # Data Handling for A-J curves for time to preprint with article pub as a competing risk

# + trusted=true
competing_risks = df2[['id', 
                      'date_completion', 
                      'date_publication_article_adj', 
                      'date_publication_preprint_adj', 
                      'time_publication_article_adj', 
                      'time_publication_preprint_adj']].reset_index(drop=True)

# + trusted=true
cr_conds = [
    competing_risks.time_publication_preprint_adj <= competing_risks.time_publication_article_adj,
    (competing_risks.date_publication_article_adj.notnull() & competing_risks.date_publication_preprint_adj.isna())]

cr_out = [competing_risks.time_publication_preprint_adj, competing_risks.time_publication_article_adj]

competing_risks['time_cr'] = np.select(cr_conds, cr_out)

cr_event_conds = [
    competing_risks.date_publication_preprint_adj.notnull(),
    competing_risks.date_publication_preprint_adj.isna() & competing_risks.date_publication_article_adj.notnull(),
    competing_risks.date_publication_preprint_adj.isna() & competing_risks.date_publication_article_adj.isna()]

cr_event_out = [1, 2, 0]

competing_risks['event_cr'] = np.select(cr_event_conds, cr_event_out)
competing_risks['time_cr'] = np.where(competing_risks['time_cr'] < 0, 0, competing_risks['time_cr'])

# + trusted=true
d = competing_risks[['time_cr', 'event_cr']].reset_index(drop=True)
d = d.set_index('time_cr')

# + trusted=true
aj = AalenJohansenFitter(seed=5236)

#This just hides the warning that data is randomly "jiggered" to break ties, which is fine.
#The seed for this is set above
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    aj.fit(competing_risks.time_cr, competing_risks.event_cr, event_of_interest=1)

# + trusted=true
aj_corrected = aj.cumulative_density_.reset_index()
aj_corrected = aj_corrected.set_index(aj_corrected.event_at.apply(round)).drop('event_at', axis=1)

# + trusted=true
aj_corrected.loc[200]

# + trusted=true
d = aj_corrected.merge(d, how='outer', left_index=True, right_index=True)
d = d.loc[d['event_cr'] == 0].copy()

# + [markdown] tags=[]
# # Any Publication

# + trusted=true
any_pub = df2[['publication_any_adj', 'time_reporting_any_adj']].reset_index(drop=True)
any_pub['publication_any_adj'] = any_pub['publication_any_adj'].astype(int)
any_pub['time_reporting_any_adj'] = np.where(any_pub['time_reporting_any_adj'] < 0, 0, any_pub['time_reporting_any_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(figsize = (10,10), dpi=300)
ax = plt.subplot()

T = any_pub.time_reporting_any_adj
E = any_pub.publication_any_adj

kmf_any = KaplanMeierFitter()
kmf_any.fit(T, E)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')

ax.set_ylim([0, 1])

#plt.title("Time To Results Dissemination From Trial Completion", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date', labelpad=10, fontsize=14)

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(kmf_any, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#These are the KM values
any_df = kmf_any.survival_function_
any_df['ci_values'] = 1-any_df.KM_estimate
any_df.loc[100]

# + trusted=true
#fig.savefig('Figures/time_any_pub.png')
# -

# # Article Publication

# + trusted=true
article_pub = df2[['publication_article_adj', 'time_publication_article_adj']].reset_index(drop=True)
article_pub['publication_article_adj'] = article_pub['publication_article_adj'].astype(int)
article_pub['time_publication_article_adj'] = np.where(article_pub['time_publication_article_adj'] < 0, 0, article_pub['time_publication_article_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_art = article_pub.time_publication_article_adj
E_art = article_pub.publication_article_adj

kmf_article = KaplanMeierFitter()
kmf_article.fit(T_art, E_art)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_article.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')

ax.set_ylim([0, 1])

#plt.title("Time To Journal Publication From Trial Completion", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Journal Publication from Registered Completion Date', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_article, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#These are the KM values
j_df = kmf_article.survival_function_
j_df['ci_values'] = 1-j_df.KM_estimate
j_df.loc[299]

# + trusted=true
#fig.savefig('Figures/time_to_journal.png')
# -

# # Time to Preprint Publication (with article pub as competing risk)

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

aj = AalenJohansenFitter(seed=10)

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    aj.fit(competing_risks.time_cr, competing_risks.event_cr, event_of_interest=1)
aj.plot(yticks=yticks, figsize=(15,10), lw=3, legend=None, grid=True, ci_show=False, color= '#377eb8')
plt.plot(d.index, d['CIF_1'], '|', markersize=10, color='C0')

#plt.title('Time to Preprint Publication from Trial Completion', pad=15, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=15)
plt.xlabel('Days to Preprint Publication from Registered Completion Date', labelpad=10, fontsize=12)

ax.set_ylim([0, 1])

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(aj, rows_to_show = ['At risk'])
plt.tight_layout()
plt.show()

# + trusted=true
#fig.savefig('Figures/time_to_preprint_aj.png')
# -

# # Registrations with only mature results registries

# + trusted=true
reg_pub2 = df2[['id', 'trn', 'publication_summary_adj', 'time_publication_summary_adj']][(df2.trn.astype(str).str.contains('NCT')) | (df2.trn.astype(str).str.contains('EUCTR')) | (df2.trn.astype(str).str.contains('ISRCTN'))].reset_index(drop=True)
reg_pub2['publication_summary_adj'] = reg_pub2['publication_summary_adj'].astype(int)
reg_pub2['time_publication_summary_adj'] = np.where(reg_pub2['time_publication_summary_adj'] < 0, 0, reg_pub2['time_publication_summary_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_mag_reg = reg_pub2.time_publication_summary_adj
E_mag_reg = reg_pub2.publication_summary_adj

kmf_reg2 = KaplanMeierFitter()
kmf_reg2.fit(T_mag_reg, E_mag_reg)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_reg2.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')

ax.set_ylim([0, 1])

#plt.title("Time To Registry Results From Trial Completion (EUCTR, CTG, ISRCTN)", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Registry Results from Registered Completion Date', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_reg2, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#These are the KM values
reg2_df = kmf_reg2.survival_function_
reg2_df['ci_values'] = 1-reg2_df.KM_estimate
reg2_df.loc[365]

# + trusted=true
#fig.savefig('Figures/registry_eu_ctg_isrctn_reporting.png')
# -

# # Registry results (All Registries)
# -We restrict this only to registrations on registries that can accept registry results

# + trusted=true
reg_pub = df2[['publication_summary_adj', 'time_publication_summary_adj']].reset_index(drop=True)
reg_pub['publication_summary_adj'] = reg_pub['publication_summary_adj'].astype(int)
reg_pub['time_publication_summary_adj'] = np.where(reg_pub['time_publication_summary_adj'] < 0, 0, reg_pub['time_publication_summary_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_reg = reg_pub.time_publication_summary_adj
E_reg = reg_pub.publication_summary_adj

kmf_article = KaplanMeierFitter()
kmf_article.fit(T_reg, E_reg)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_article.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')

ax.set_ylim([0, 1])

#plt.title("Time To Registry Results From Trial Completion", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Registry Results from Registered Completion Date', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_article, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/all_registries.png')
# -

# # Venn

# + trusted=true
venn_data = df2[['publication_preprint_adj', 'publication_article_adj', 'publication_summary_adj']].reset_index(drop=True)

# + trusted=true
prep = venn_data.publication_preprint_adj == True
art = venn_data.publication_article_adj == True
reg = venn_data.publication_summary_adj == True

# + trusted=true
colors = ['#377eb8', '#ff7f00', '#4daf4a','#f781bf', '#a65628', '#984ea3', '#999999', '#e41a1c', '#dede00']
labels = ['Journal Articles', 'Registry Results', 'Preprints']

#Order of values: J, R, J+R, P, P+J, R+P, J+R+P

values = (len(venn_data[art & ~prep & ~reg]), 
          len(venn_data[~art & ~prep & reg]), 
          len(venn_data[art & ~prep & reg]), 
          len(venn_data[~art & prep & ~reg]), 
          len(venn_data[art & prep & ~reg]), 
          len(venn_data[~art & prep & reg]), 
          len(venn_data[art & prep & reg]))


# + trusted=true
plt.figure(figsize=(8,8), dpi=300)
v1 = venn3(
    subsets = values, 
    set_labels = labels,
    set_colors = colors, 
    subset_label_formatter = lambda x: str(x) + "\n(" + f"{(x/sum(values)):1.2%}" + ")", 
    alpha = .6)

for text in v1.set_labels:
    text.set_fontsize(10)

for text in v1.subset_labels:
    if text == v1.subset_labels[-2]:
        text.set_fontsize(5)
    else:
        text.set_fontsize(8)

#Journal Only
v1.get_label_by_id("100").set_x(-0.2)
#All
v1.get_label_by_id("111").set_x(.2)
v1.get_label_by_id("111").set_y(.05)
#Registry + preprint
v1.get_label_by_id("011").set_y(-.02)
v1.get_label_by_id("011").set_x(.36)
#Registry Only
v1.get_label_by_id("010").set_x(.43)
v1.get_label_by_id("010").set_y(.18)

venn3_circles(values)
#plt.title('COVID-19 Clinical Trial Results by Dissemination Route', fontweight='bold')
#plt.savefig('Figures/reporting_venn.png')
plt.show()
# + [markdown] tags=[]
# # Breaking Pandemic into Phases

# + trusted=true
phase_1 = pd.to_datetime('2020-06-30')
phase_2 = pd.to_datetime('2020-12-31')
phase_3 = pd.to_datetime('2021-06-30')


date_conds = [(df2.date_completion <= phase_1), 
              (df2.date_completion > phase_1) & (df2.date_completion <= phase_2),
              (df2.date_completion > phase_2) & (df2.date_completion <= phase_3)]

date_out = [1,2,3]

df2['pandemic_phase'] = np.select(date_conds, date_out)

# + trusted=true
phase_pub = df2[['publication_any_adj', 'time_reporting_any_adj', 'pandemic_phase']].reset_index(drop=True)
phase_pub['publication_any_adj'] = phase_pub['publication_any_adj'].astype(int)
phase_pub['time_reporting_any_adj'] = np.where(phase_pub['time_reporting_any_adj'] < 0, 0, phase_pub['time_reporting_any_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T1 = phase_pub[phase_pub.pandemic_phase == 1].time_reporting_any_adj
E1 = phase_pub[phase_pub.pandemic_phase == 1].publication_any_adj

kmf_1 = KaplanMeierFitter()
kmf_1.fit(T1, E1, label='1-6 Months')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_1.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#377eb8')

T2 = phase_pub[phase_pub.pandemic_phase == 2].time_reporting_any_adj
E2 = phase_pub[phase_pub.pandemic_phase == 2].publication_any_adj

kmf_2 = KaplanMeierFitter()
kmf_2.fit(T2, E2, label='7-12 Months')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_2.plot_cumulative_density(ci_show=False, show_censors=False, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#ff7f00')


T3 = phase_pub[phase_pub.pandemic_phase == 3].time_reporting_any_adj
E3 = phase_pub[phase_pub.pandemic_phase == 3].publication_any_adj

kmf_3 = KaplanMeierFitter()
kmf_3.fit(T3, E3, label='13-18 Months')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_3.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#4daf4a')

ax.set_ylim([0, 1])

#plt.title("Time To Results Dissemination by Timing of Completion", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date', labelpad=10, fontsize=14)
ax.legend(fontsize = 18)

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(kmf_1, kmf_2, kmf_3, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/pandemic_phase_reporting.png')

# + trusted=true
#These are the KM values
fu1_df = kmf_1.survival_function_
fu1_df['ci_values'] = 1-fu1_df['1-6 Months']
fu1_df.loc[195]

# + trusted=true
#These are the KM values
fu2_df = kmf_2.survival_function_
fu2_df['ci_values'] = 1-fu2_df['7-12 Months']
fu2_df.loc[200]

# + trusted=true
#These are the KM values
fu3_df = kmf_3.survival_function_
fu3_df['ci_values'] = 1-fu3_df['13-18 Months']
fu3_df.loc[200]

# + [markdown] tags=[]
# # Interventions

# + trusted=true
df_int = df2.copy()

# + trusted=true
top_ints = pd.read_csv(parent + '/data/interventions/top_ints.csv')
int_mapping = pd.read_csv(parent + '/data/interventions/int_mapping.csv')

# + trusted=true
top_ints.head(12)

# + trusted=true
int_merge = df_int.merge(int_mapping, how='left', left_on='id', right_on='id').drop('Unnamed: 0', axis=1)

# + trusted=true
int_merge.head()

# + trusted=true
#Create dummies for the most common therapies

common_therapies = ['Hydroxychloroquine', 'Convalescent Plasma', 'Stem Cells (Mesenchymal)', 'Ivermectin', 'Azithromycin']

for ct in common_therapies:
    int_merge[ct] = np.where(int_merge.intervention.str.contains(ct, regex=False), 1, 0)

# + trusted=true
int_merge['publication_any_adj'] = int_merge['publication_any_adj'].astype(int)
int_merge['time_reporting_any_adj'] = np.where(int_merge['time_reporting_any_adj'] < 0, 0, int_merge['time_reporting_any_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_hcq = int_merge[int_merge[common_therapies[0]] == 1].time_reporting_any_adj
E_hcq = int_merge[int_merge[common_therapies[0]] == 1].publication_any_adj

kmf_hcq = KaplanMeierFitter()
kmf_hcq.fit(T_hcq, E_hcq, label='HCQ')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_hcq.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#377eb8')

T_cp = int_merge[int_merge[common_therapies[1]] == 1].time_reporting_any_adj
E_cp = int_merge[int_merge[common_therapies[1]] == 1].publication_any_adj

kmf_cp = KaplanMeierFitter()
kmf_cp.fit(T_cp, E_cp, label='Con. Plasma')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_cp.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#ff7f00')

T_scm = int_merge[int_merge[common_therapies[2]] == 1].time_reporting_any_adj
E_scm = int_merge[int_merge[common_therapies[2]] == 1].publication_any_adj

kmf_scm = KaplanMeierFitter()
kmf_scm.fit(T_scm, E_scm, label='Stem Cells')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_scm.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#4daf4a')


T_ive = int_merge[int_merge[common_therapies[3]] == 1].time_reporting_any_adj
E_ive = int_merge[int_merge[common_therapies[3]] == 1].publication_any_adj

kmf_ive = KaplanMeierFitter()
kmf_ive.fit(T_ive, E_ive, label='Ivermectin')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_ive.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#f781bf')

T_azm = int_merge[int_merge[common_therapies[4]] == 1].time_reporting_any_adj
E_azm = int_merge[int_merge[common_therapies[4]] == 1].publication_any_adj

kmf_azm = KaplanMeierFitter()
kmf_azm.fit(T_azm, E_azm, label='Azithromycin')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_azm.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=True, ax=ax, lw=2.5, 
                                   color='#a65628')


T_other = int_merge[int_merge[common_therapies].sum(axis=1) == 0].time_reporting_any_adj
E_other = int_merge[int_merge[common_therapies].sum(axis=1) == 0].publication_any_adj

kmf_any_comp = KaplanMeierFitter()
kmf_any_comp.fit(T_other, E_other, label='All Other Trials')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any_comp.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|', 'alpha':.4}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=4, 
                                     color='lightsteelblue', alpha=.4)

ax.set_ylim([0, 1])

#plt.title("Time To Results Dissemination From Registered Completion Date (Common Interventions)", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date', labelpad=10, fontsize=14)
ax.legend(fontsize = 18)

#from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(kmf_hcq, kmf_cp, kmf_scm, kmf_ive, kmf_azm, kmf_any_comp, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/intervention_reporting.png')
# -

# # Trial Design Characteristics

# + trusted=true
hq_df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/subgroup-analyses/kaplan-meier-minimum-standards.csv')

# + trusted=true
hq_df.columns

# + trusted=true
hq_df['publication_any_adj'] = hq_df['publication_any'].astype(int)
hq_df['time_publication_any_adj'] = np.where(hq_df['time_publication_any'] < 0, 0, hq_df['time_publication_any'])

# + trusted=true
hq_ids = hq_df.id.to_list()

# + trusted=true
nhq = df2[~df2.id.isin(hq_ids)][['publication_any_adj', 'time_reporting_any_adj']].reset_index(drop=True)
nhq['publication_any_adj'] = nhq['publication_any_adj'].astype(int)
nhq['time_reporting_any_adj'] = np.where(nhq['time_reporting_any_adj'] < 0, 0, nhq['time_reporting_any_adj'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(figsize = (10,10), dpi=300)
ax = plt.subplot()

T_hq = hq_df.time_publication_any_adj
E_hq = hq_df.publication_any_adj

kmf_hq = KaplanMeierFitter()
kmf_hq.fit(T_hq, E_hq, label='Meets Design Standard')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_hq.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')


T_nhq = nhq.time_reporting_any_adj
E_nhq = nhq.publication_any_adj

kmf_nhq = KaplanMeierFitter()
kmf_nhq.fit(T_nhq, E_nhq, label="Doesn't Meet Design Standard")
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_nhq.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#ff7f00')

ax.set_ylim([0, 1])
ax.legend(fontsize = 18)

#plt.title("Time To Results Dissemination From Registered Completion Date Based on Trial Characteristics", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date', labelpad=10, fontsize=14)

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(kmf_hq, kmf_nhq, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/design_char_reporting.png')
# -

# # Pub to Preprint

# + trusted=true
pp_df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/main-analyses/kaplan-meier-preprint-to-article.csv')

# + trusted=true
pp_df.head()

# + trusted=true
pp_df.time_preprint_article.max()

# + trusted=true
pp_df.time_preprint_article.describe()

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_pub_preprint = pp_df.time_preprint_article
E_pub_prepint = pp_df.publication_article.astype(int)

kmf_pre_pub = KaplanMeierFitter()
kmf_pre_pub.fit(T_pub_preprint, E_pub_prepint)
ax = kmf_pre_pub.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')

ax.set_ylim([0, 1])

#plt.title("Time From Preprint to Journal Publication", pad=20, fontsize=20)
plt.ylabel('Proportion Converting', labelpad=10, fontsize=14)
plt.xlabel('Days to Journal Publication from Preprint Publication', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_pre_pub, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/preprint_article_pub.png')
# + trusted=true
#These are the KM values
pre_pub_df = kmf_pre_pub.survival_function_
pre_pub_df['ci_values'] = 1-pre_pub_df.KM_estimate
pre_pub_df.loc[198]

# + [markdown] tags=[]
# # Sensitivity Analysis - Only Completed Trials

# + trusted=true
completed = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/sensitivity-analyses/kaplan-meier-time-to-pub_latest_completion_status.csv')

# + trusted=true
completed2 = completed[['id', 'publication_any', 'time_publication_any']].reset_index(drop=True)
completed2['publication_any'] = completed2['publication_any'].astype(int)
completed2['time_publication_any'] = np.where(completed2['time_publication_any'] < 0, 0, completed2['time_publication_any'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_comp2 = completed2.time_publication_any
E_comp2 = completed2.publication_any

kmf_comp = KaplanMeierFitter()
kmf_comp.fit(T_comp2, E_comp2, label='Only Completed')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_comp.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')


T = any_pub.time_reporting_any_adj
E = any_pub.publication_any_adj

kmf_any2 = KaplanMeierFitter()
kmf_any2.fit(T, E, label='Main Analysis')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any2.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|', 'alpha':.4}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='lightsteelblue', alpha=.4)



ax.set_ylim([0, 1])
ax.legend(fontsize = 18)

#plt.title("Time to Any Publication for Completed Status Trials", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_comp, kmf_any2, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()
# + trusted=true
#fig.savefig('Figures/completed_trials_sens.png')
# -
# # Sensitivity Analysis - Full Completion Date

# + trusted=true
full_comp_df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/sensitivity-analyses/kaplan-meier-time-to-pub_scd.csv')

# + trusted=true
full_comp = full_comp_df[['id', 'publication_any', 'time_publication_any']].reset_index(drop=True)
full_comp['publication_any'] = full_comp['publication_any'].astype(int)
full_comp['time_publication_any'] = np.where(full_comp['time_publication_any'] < 0, 0, full_comp['time_publication_any'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_fc = full_comp.time_publication_any
E_fc = full_comp.publication_any

kmf_fc = KaplanMeierFitter()
kmf_fc.fit(T_fc, E_fc, label='Full Completion')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_fc.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')


T = any_pub.time_reporting_any_adj
E = any_pub.publication_any_adj

kmf_any2 = KaplanMeierFitter()
kmf_any2.fit(T, E, label='Main Analysis')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any2.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|', 'alpha':.4}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='lightsteelblue', alpha=.4)



ax.set_ylim([0, 1])
ax.legend(fontsize = 18)

#plt.title("Time to Any Publication for Only Full Study Completion Dates", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Full Completion Date', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_fc, kmf_any2, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/full_complete_sens.png')

# + [markdown] tags=[]
# # Sensitivity Analysis - Interim Results
# + trusted=true
interim_df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/main-analyses/kaplan-meier-time-to-pub.csv')

# + trusted=true
interim_df.columns

# + trusted=true
interim = interim_df[['id', 'publication_interim_any', 'time_publication_interim_any']].reset_index(drop=True)
interim['publication_interim_any'] = interim['publication_interim_any'].astype(int)
interim['time_publication_interim_any'] = np.where(interim['time_publication_interim_any'] < 0, 0, interim['time_publication_interim_any'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_in = interim.time_publication_interim_any
E_in = interim.publication_interim_any

kmf_in = KaplanMeierFitter()
kmf_in.fit(T_in, E_in, label='First Result with Interim')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_in.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')


T = any_pub.time_reporting_any_adj
E = any_pub.publication_any_adj

kmf_any2 = KaplanMeierFitter()
kmf_any2.fit(T, E, label='Main Analysis')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any2.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|', 'alpha':.4}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='lightsteelblue', alpha=.4)



ax.set_ylim([0, 1])
ax.legend(fontsize = 18)

#plt.title("Time to Any Publication Inclusive of Interim Results", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_in, kmf_any2, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# + trusted=true
#fig.savefig('Figures/interim_sens.png')
# -


# # Sensitivity Analysis - April 2022 Update

# + trusted=true
apr22_df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct-analysis/main/data/reporting/sensitivity-analyses/kaplan-meier-time-to-pub_22.csv')

# + trusted=true
updated = apr22_df[['id', 'publication_any', 'time_publication_any']].reset_index(drop=True)
updated['publication_any'] = updated['publication_any'].astype(int)
updated['time_publication_any'] = np.where(updated['time_publication_any'] < 0, 0, updated['time_publication_any'])

# + trusted=true
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T_updated = updated.time_publication_any
E_updated = updated.publication_any

kmf_up = KaplanMeierFitter()
kmf_up.fit(T_updated, E_updated, label='April 22 Update')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_up.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='#377eb8')


T = any_pub.time_reporting_any_adj
E = any_pub.publication_any_adj

kmf_any2 = KaplanMeierFitter()
kmf_any2.fit(T, E, label='Main Analysis')
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any2.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|', 'alpha':.4}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=3, color='lightsteelblue', alpha=.4)



ax.set_ylim([0, 1])
ax.legend(fontsize = 18)

#plt.title("Time to Any Publication (April 2022 Data Refresh)", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion Date as of April 2022', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_up, kmf_any2, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()
# + trusted=true
#fig.savefig('Figures/apr22_sens.png')
# -










# +

# -




