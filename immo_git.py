from geopy.geocoders import Nominatim
import streamlit as st
import pandas as pd
import requests
import numpy as np
import statistics
import random, string, sys
import altair as alt


st.title('Marché immobilier en France')

st.sidebar.title('Ma recherche')

tooltip_style = """
<style>
div[data-baseweb="tooltip"] {
  width: 350px;
}
</style>
"""
st.markdown(tooltip_style,unsafe_allow_html=True)

codePostal = st.sidebar.text_input('Ville :', help='France entière, Alsace et Moselle exclus')

if codePostal != None:
    codePostalS= str(codePostal)

adresse = st.sidebar.text_input('Adresse :')
if adresse != None:
    adresseS= str(adresse)

dist = st.sidebar.slider('Choisissez un rayon (m) :', 100, 500, 1000) 
dist= str(dist)

if not codePostal:
    st.stop()
    
st.write('Votre recherche : '+adresseS+' à '+codePostal+' dans un rayon de '+dist+'m pour la periode 2014-2019')

def randomword(length):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for i in range(length))

word=randomword(7)
geolocator = Nominatim(user_agent=word)

location = geolocator.geocode(adresseS+' ,France ,'+codePostalS)
my_str = str(location)
 
target = 'Moselle'
target1= '-Rhin'
 
if (my_str.__contains__(target)):
    st.write('Cette zone geographique est indisponible')
    st.stop()
if (my_str.__contains__(target1)):
    st.write('Cette zone geographique est indisponible')
    st.stop()

if location == None:
    st.write('Essayez une adresse à proximité')
    st.stop()

lat=str(location.latitude)
 
lon=str(location.longitude)
 
loc=str(location)

url= 'http://api.cquest.org/dvf?lat='+lat+'&lon='+lon+'&dist='+dist

request= requests.get(url)

dataR = request.json()
 
datacomr1=list(dict.values(dataR))
 
area=datacomr1[4]

df = pd.DataFrame.from_dict(pd.json_normalize(area), orient='columns')

df.columns = df.columns.str.replace('properties.', '')
df.columns = df.columns.str.replace('.', '_')
df['nature_mutation'] = df['nature_mutation'].str.replace("'",'')

df['surface_relle_bati'] = df['surface_relle_bati'].fillna(0)
df['valeur_fonciere'] = df['valeur_fonciere'].fillna(0)
df['surface_terrain'] = df['surface_terrain'].fillna(0)

df = df[df['surface_relle_bati'] > 0]
df = df[df['valeur_fonciere'] > 0]
df = df[df['surface_terrain'] >= 0]

df.loc[df['surface_terrain'] > 1, 'price_m2'] = df['valeur_fonciere']/(df['surface_relle_bati']+ np.log(df.surface_terrain))
df.loc[df['surface_terrain'] <= 1, 'price_m2'] = df['valeur_fonciere']/df['surface_relle_bati']


df['date_mutation']= pd.to_datetime(df['date_mutation'])
df['year'] = df['date_mutation'].dt.year

df=df[df.price_m2 < df.price_m2.quantile(.9)]

df['z_score'] = (df['price_m2'] - df['price_m2'].mean()) / df['price_m2'].std()

df_w_o = df[(df['z_score'] < 1) & (df['z_score'] > -1)]

df_w_o = df_w_o[df_w_o['nature_mutation'].str.contains('Adjudication') == False]
df_w_o = df_w_o[df_w_o['nature_mutation'].str.contains('Echange') == False]
df_w_o = df_w_o[df_w_o['nature_mutation'].str.contains('Vente en létat futur dachèvement') == False]
df_w_o = df_w_o[df_w_o['nature_mutation'].str.contains('Vente terrain à bâtir') == False]

df_w_o = df_w_o[df_w_o['type_local'].str.contains('Local industriel. commercial ou assimilé') == False]
df_w_o = df_w_o[df_w_o['type_local'].str.contains('Dépendance') == False]

median = df_w_o.groupby(['year','nature_mutation','type_local'])['price_m2'].median()
median= median.reset_index(name='price_m2')
median.rename(columns = {'price_m2':'price_m2_median'}, inplace = True)
mean = df_w_o.groupby(['year','nature_mutation','type_local'])['price_m2'].mean()
mean= mean.reset_index(name='price_m2')

medianl = df_w_o.groupby(['year','nature_mutation','type_local'])['price_m2'].size()
medianl= medianl.reset_index(name='obs')

median['obs']= medianl['obs']
median['price_m2_mean']= mean['price_m2']

st.subheader('Type de biens vendus :')

col1b, col2b = st.columns([5, 6])
df_pie=median.groupby(['type_local'])['obs'].sum()
df_pie=df_pie.reset_index('type_local', inplace=False)
df_pie.rename(columns = {'obs':'Nbr_de_ventes'}, inplace = True)
chartp=alt.Chart(df_pie).mark_arc().encode(theta=alt.Theta(field="Nbr_de_ventes", type="quantitative"), color=alt.Color(field="type_local", type="nominal"),)

with col2b:
    st.altair_chart(chartp)
with col1b:
    st.dataframe(df_pie)

median_ap=median[median['type_local'].str.contains('Maison') == False]
median_ap.drop(columns=['nature_mutation','type_local', 'obs'], inplace=True)

median_ma=median[median['type_local'].str.contains('Appartement') == False]
median_ma.drop(columns=['nature_mutation','type_local', 'obs'], inplace=True)

st.subheader('Choisissez le type de bien que vous souhaitez analyser :')

appartement = st.checkbox('Appartement')
maison=st.checkbox('Maison')

if appartement:
    chart=(alt.Chart(median_ap).transform_fold(['price_m2_median', 'price_m2_mean'], as_=['Stats_Apt', 'Valeur']).mark_bar().encode(x='Stats_Apt:N',y='Valeur:Q',color='Stats_Apt:N',column='year',))
    st.altair_chart(chart)
    
if maison:
    chart=(alt.Chart(median_ma).transform_fold(['price_m2_median', 'price_m2_mean'], as_=['Stats_Mais', 'Valeur']).mark_bar().encode(x='Stats_Mais:N',y='Valeur:Q',color='Stats_Mais:N',column='year',))
    st.altair_chart(chart)
            
df_surf_dist=df_w_o['surface_relle_bati'].value_counts(bins=20, sort=False)
df_surf_dist = df_surf_dist.reset_index(name='surface_relle_bati')
df_surf_dist.rename(columns = {'index':'range'}, inplace = True)
df_surf_dist.rename(columns = {'surface_relle_bati':'Ventes'}, inplace = True)
df_surf_dist['range'] = df_surf_dist['range'].apply(lambda x: pd.Interval(left=int(round(x.left)), right=int(round(x.right))))

def round_interval(i, ndigits=0):
    return pd.Interval(round(i.left, ndigits), round(i.right, ndigits), i.closed)

num_bins = 60
min_val = int(df_w_o['valeur_fonciere'].min())+1
max_val = int(df_w_o['valeur_fonciere'].max())
bin_size = (max_val-min_val)//num_bins
bins = np.arange(min_val,max_val,bin_size)
df_price_dist=df_w_o['valeur_fonciere'].value_counts(bins=bins, sort=False)
df_price_dist = df_price_dist.reset_index(name='surface_relle_bati')
df_price_dist.rename(columns = {'index':'range'}, inplace = True)
df_price_dist.rename(columns = {'surface_relle_bati':'Ventes'}, inplace = True)

df_price_dist.range=df_price_dist['range'].apply(round_interval, ndigits=-3)
df_price_dist['range'] = df_price_dist['range'].apply(lambda x: pd.Interval(left=int(round(x.left)), right=int(round(x.right))))

st.subheader('Etat global du marché :')

col1, col2 = st.columns([5, 6])
col1a, col2a = st.columns([5, 6])

col1.subheader('Nbr Ventes/surface(m2)')

col1.write(df_surf_dist.head(8))

col1a.subheader('Nbr Ventes/prix(€)')

col1a.write(df_price_dist.head(8))

df_surf_dist1= df_surf_dist

df_surf_dist1['left'] = df_surf_dist['range'].array.left

df_surf_dist1.drop ('range', axis=1, inplace=True)
df_surf_dist1 = df_surf_dist1.rename(columns={'left':'index'}).set_index('index')
df_surf_dist1.rename(columns = {'surface_relle_bati':'Ventes'}, inplace = True)

col2.subheader('Distribution Qte/Surf')
col2.bar_chart(df_surf_dist1)

df_price_dist1=df_price_dist
df_price_dist1['left'] = df_price_dist['range'].array.left
df_price_dist1.drop ('range', axis=1, inplace=True)
df_price_dist1 = df_price_dist1.rename(columns={'left':'index'}).set_index('index')
df_price_dist1.rename(columns = {'valeur_fonciere':'Mutations/surface'}, inplace = True)

col2a.subheader('Distribution Qte/Px')
col2a.bar_chart(df_price_dist1)

st.subheader('Carte des ventes :')

df_map = df_w_o.filter(['lat','lon'], axis=1)
st.map(df_map)

st.stop()
