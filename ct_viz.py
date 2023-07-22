#!/usr/bin/env python
# coding: utf-8

# In[1]:
# pip install plost

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plost


# In[17]:


st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title('CT Analysis')


def update_df(text):
    base_url = "https://clinicaltrials.gov/api/query/study_fields?"
    params = {
        "expr": str(st.session_state.text),  # Use st.session_state.text_input here
        "fields": "NCTId,Condition,BriefTitle,Phase,OverallStatus,StartDate,StartDateType,CompletionDate,CompletionDateType,"
                  "StudyType,LocationFacility,LocationCity,LocationState,LocationZip,LocationCountry,LocationStatus",
        "min_rnk": "1",
        "max_rnk": "1000",
        "fmt": "json"
    }

    all_studies = []

    @st.cache_data
    def load_data(base_url,params):

        while True:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                studies = data["StudyFieldsResponse"]["StudyFields"]
                all_studies.extend(studies)

                # Check if there are more studies beyond the current range
                if int(data["StudyFieldsResponse"]["NStudiesFound"]) > int(params["max_rnk"]):
                    min_rank = int(params["max_rnk"]) + 1
                    max_rank = min_rank + 999
                    params["min_rnk"] = str(min_rank)
                    params["max_rnk"] = str(max_rank)
                else:
                    break  # No more studies, exit the loop
            else:
                print(f"Error: {response.status_code}")
                break

        # Create a DataFrame from the retrieved studies
        df = pd.DataFrame(all_studies)
        return df

    df=load_data(base_url,params)

    # Convert the object to date and time
    df["CompletionDate"]=df["CompletionDate"].apply(
        lambda x :pd.to_datetime(
            x[0]) if isinstance(
            x, list) and len(
            x) > 0 else pd.NaT )

    df["StartDate"]=df["StartDate"].apply(
        lambda x :pd.to_datetime(
            x[0]) if isinstance(
            x, list) and len(
            x) > 0 else pd.NaT )

    # Counting the number of trials going on
    df["Nos_location"]=df["LocationCountry"].apply(lambda x: len(x) if isinstance(x,list) else 0)

    return df


if  'text' not in st.session_state:
    st.session_state.CONNECTED =  False
    st.session_state.text = ''
    

def _connect_form_cb(connect_status):
    st.session_state.CONNECTED = connect_status
    

def display_db_connection_menu():
    with st.form(key="connect_form"):
        st.text_input('Enter the condition', help='Click on search, pressing enter will not work', value=st.session_state.text, key='text')
        submit_button = st.form_submit_button(label='Search', on_click=_connect_form_cb, args=(True,))
        if submit_button:
            if st.session_state.text=='':
                st.write("Please enter a condition")
                st.stop()
            
            
            
        
display_db_connection_menu()
    
if st.session_state.CONNECTED:
    st.write('You are Searching for:',  st.session_state.text)
    df = update_df(st.session_state.text)

     #Heading for sidebar
    st.sidebar.header('CT Dashboard `version 0.1`')
    
    #selecting the study type
    df['StudyType_str']=df.loc[:,'StudyType'].apply( lambda x: 'N/A' if len(x)==0 else ' '.join(map(str,x))) 
    options_st = df['StudyType_str'].unique().tolist()
    options_st.insert(0, "All")
    selected_options_str = st.sidebar.selectbox('What kind of study you want?',options= options_st)
    
    if selected_options_str == 'All':
        filtered_df = df
    else:      
         #Convert selected_options_str back to a list
        selected_options = selected_options_str.split()
        filtered_df= df[df.StudyType_str.isin(selected_options)]
        pass
        if filtered_df.empty:
            st.write("No studies found for the selected options.")
            st.stop()

    # Slider for selecting year
    st.sidebar.subheader('Start Year of CT')
    with st.sidebar.form('ct-year'):
        years = filtered_df['StartDate'].dt.year.unique()
        selected_year_ranges = st.slider('Select Year Range', min_value=int(min(years)), max_value=int(max(years)), value=(int(min(years)), int(max(years))), key='slider_year')

        # Add a submit button to the form
        submit_button = st.form_submit_button("Submit")

        # After the form is submitted, check if the submit button is clicked
        if submit_button:
            # Assign the selected tuples to selected_year_range
            selected_year_range = selected_year_ranges
        else:
            # If the form is not submitted, assign a default value to selected_year_range
            selected_year_range = (int(min(years)), int(max(years)))

    
    # Filter the DataFrame based on the selected dates
    filtered_df = filtered_df[(filtered_df['StartDate'].dt.year >= selected_year_range[0]) & (filtered_df['StartDate'].dt.year <= selected_year_range[1])]
    # filtered_df['StartDate'] = filtered_df['StartDate'].dt.strftime('%Y-%m')
    filtered_df['Phase']=filtered_df['Phase'].fillna('N/A')



    #Data for pie chart
    filtered_df.loc[:,'Phase_str'] = filtered_df.loc[:,'Phase'].apply(lambda x: 'N/A' if len(x) == 0 else ' '.join(map(str, x)))
    filtered_df_pie=filtered_df.groupby("Phase_str")['NCTId'].count().rename('count_phase').reset_index()


    #Select the Phase for pie chart
    options = filtered_df_pie['Phase_str'].unique().tolist()
    selected_options = st.sidebar.multiselect('Which app do you want?',options)



    st.sidebar.markdown('''
    ---
    Created with ❤️ by [Shubhanshu](https://www.linkedin.com/in/shubh789/).
    ''')
    
    #data for side bars
    filtered_df["StartYear"]=filtered_df['StartDate'].dt.year
    if len(selected_options) == 0:
        filtered_df_lc=filtered_df.groupby('StartYear')['NCTId'].count().rename('Nos_CT').reset_index()
        
    else:
        filtered_df_lc_pie = filtered_df[filtered_df.Phase_str.isin(selected_options)]
        filtered_df_lc = filtered_df_lc_pie.groupby('StartYear')['NCTId'].count().rename('Nos_CT').reset_index()
        


    # Row A
    st.markdown('### Metrics')
    col1, col2, col3 = st.columns(3)
    col1.metric("Nos. of studies", filtered_df_lc.Nos_CT.sum())
    
    #Nos. of recruiting studies
    recruiting_count = (
    filtered_df['NCTId'][filtered_df['OverallStatus'].apply(lambda x: x == ['Recruiting'])].count()
    if len(selected_options) == 0
    else filtered_df_lc_pie['NCTId'][filtered_df['OverallStatus'].apply(lambda x: x == ['Recruiting'])].count()
    )

    col2.metric("Nos. Recruiting CT", recruiting_count)
    
    #Nos. of completed studies
    completion_count = (
    filtered_df['NCTId'][filtered_df['CompletionDateType'].apply(lambda x: x == ['Actual'])].count()
    if len(selected_options) == 0
    else filtered_df_lc_pie['NCTId'][filtered_df['CompletionDateType'].apply(lambda x: x == ['Actual'])].count()
    )
    col3.metric("Trials completed", completion_count)

    #row B
    c1,c2=st.columns((7,3))
    
    with c1:
        st.markdown('### Clinical trials per year')
        st.line_chart(filtered_df_lc, x = 'StartYear', y = 'Nos_CT',)

    if len(selected_options) == 0:
        filtered_pie = filtered_df_pie  # No filtering required, keep all data
    else:
        filtered_pie = filtered_df_pie[filtered_df_pie['Phase_str'].isin(selected_options)]


    with c2:
        st.markdown('### Phase distribution')
        plost.donut_chart(
            data=filtered_pie,
            theta='count_phase',
            color='Phase_str',
            legend=None,
            use_container_width=True)

    dataExploration = st.container()

    with dataExploration:
#       st.title('Clinical trials data')
      st.subheader('Sample data')
#       st.header('Dataset: Clinical trials of', st.session_state.text)
      st.markdown('I found this dataset at... https://clinicaltrials.gov')
      st.markdown('**It is a sample of 100 rows from the dataset**')
#       st.text('Below is the sample DataFrame')
      st.dataframe(filtered_df.head(100))
