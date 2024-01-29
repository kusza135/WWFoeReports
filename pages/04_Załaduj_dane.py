import streamlit as st
from PIL import Image
from tools.streamlit_tools import execute_query, create_engine, runsql
from tools.login import login, get_user_role_from_db
import os
# import streamlit_authenticator as stauth
import json
import pandas as pd
from  datetime import datetime, date, timedelta
from random import randint
import time


path = os.path.dirname(__file__)
sdate = date.today()

guildPlayers = "Gracze Gildii Wzgórze Wisielców"
wg = "Wyprawy Gildyjne"
gpch = "Gildyjne Pola Chwały"

if f"File_{guildPlayers}" not in st.session_state: st.session_state[f"File_{guildPlayers}"] = str(randint(1000, 100000000))
if f"File_{wg}" not in st.session_state: st.session_state[f"File_{wg}"] = str(randint(1000, 100000000))
if f"File_{gpch}" not in st.session_state: st.session_state[f"File_{gpch}"] = str(randint(1000, 100000000))

if f"Clipboard_{guildPlayers}" not in st.session_state: st.session_state[f"Clipboard_{guildPlayers}"] = str(randint(1000, 100000000))
if f"Clipboard_{wg}" not in st.session_state: st.session_state[f"Clipboard_{wg}"] = str(randint(1000, 100000000))
if f"Clipboard_{gpch}" not in st.session_state: st.session_state[f"Clipboard_{gpch}"] = str(randint(1000, 100000000))


def date_pick(sdate):
    przycisk1 = st.toggle('zmień datę ładowania danych')
    vdate = sdate
    if przycisk1:
        vdate = st.date_input("Wybierz datę", value="today", format='DD-MM-YYYY')
        return vdate
    return vdate

def load_file(Load_Method, File_type, visibility = True):
    if Load_Method == "File":
        st.markdown(body=f"Wybierz lub przeciągnij plik :blue[{File_type}]")
        uploaded_file = st.file_uploader(f"Wybierz lub przeciągnij plik {File_type}", key= st.session_state[f"{Load_Method}_{File_type}"], disabled=not visibility, label_visibility="hidden")
    elif Load_Method == "Clipboard":
        st.markdown(body=f"Wklej dane :blue[{File_type}]")
        if visibility == True:
            plholder = "Dane powinny być w formacie JSON"
        else:
            plholder = f"{File_type} w trakcie sezonu! \nOkno nie aktywne."
        uploaded_file = st.text_area(label=f"Wklej dane {File_type}", height=200, placeholder= plholder, key= st.session_state[f"{Load_Method}_{File_type}"], disabled=not visibility, label_visibility="hidden")
    if uploaded_file is not None:
        # To read file as string:
        try:
            if Load_Method == "File":
                string_data = json.loads(uploaded_file.getvalue().decode("utf-8"))
            elif Load_Method == "Clipboard":
                string_data = json.loads(uploaded_file)
            st.markdown(f"{File_type}  - Dane są poprawne :white_check_mark:")
            if File_type == guildPlayers:
                data = pd.DataFrame(string_data)
                
            elif File_type == wg:
                data = pd.json_normalize(string_data)
                data.columns = data.columns.str.lstrip('player.')
            elif File_type == gpch:
                data = pd.json_normalize(string_data)
                data.columns = data.columns.str.lstrip('player\.')
            return data
        except:
            if not uploaded_file == "":
                st.markdown(f"{File_type}  - Dane są błędne :thumbsdown:")
    else:
        return None

def load_data_intoDB(db_conn, dfName, DfData, vdate = date.today()):
 
    
    if  dfName == 'guildPlayers':
            
            input_data = DfData.loc[:, ['player_id'
                                        , 'name'
                                        , 'score'
                                        , 'rank'
                                        , 'city_name'
                                        , 'won_battles'
                                        , 'era'
                                        , 'title'
                                        , 'permissions']]
            
            # print(input_data.head(10))
            runsql(db_conn, f'DROP TABLE IF EXISTS __{dfName}')
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='replace')
            try:
                conn = db_conn.raw_connection()
                cur = conn.cursor()
                cur.callproc(f"p_{dfName}", args=[f"__{dfName}", {vdate}])
                cur.close() 
            finally:
                conn.close()
            
            
    elif  dfName == 'ages':
            
            input_data = DfData.loc[:, ['id'
                                        , 'Age_PL'
                                        , 'era'
                                       ]]
            
            runsql(db_conn, f'DROP TABLE IF EXISTS __{dfName}')
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='append')
            try:
                conn = db_conn.raw_connection()
                cur = conn.cursor()
                cur.callproc(f"p_{dfName}", args=[f"__{dfName}"])
                cur.close() 
            finally:
                conn.close()
            
    elif  dfName == 'wg':
            input_data = DfData.loc[:, ['_id'
                                        , 'xpeditionPoints'
                                        , 'solvedEncounters'
                                        , 'contributionDifficulty'
                                       ]]
            
            runsql(db_conn, f'DROP TABLE IF EXISTS __{dfName}')
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='append')
            
            try:
                conn = db_conn.raw_connection()
                cur = conn.cursor()
                cur.callproc(f"p_{dfName}", args=[f"__{dfName}", {vdate}, wg_day(vdate)])
                cur.close() 
            finally:
                conn.close()
            
    elif  dfName == 'gpch':
            input_data = DfData.loc[:, ['_id'
                                        , 'nk'
                                        , 'battlesWon'
                                        , 'negotiationsWon'
                                        , 'ttrition'
                                       ]]
            
            runsql(db_conn, f'DROP TABLE IF EXISTS __{dfName}')
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='append')
            try:
                conn = db_conn.raw_connection()
                cur = conn.cursor()
                cur.callproc(f"p_{dfName}", args=[f"__{dfName}", {vdate}, gpch_day(vdate)])
                cur.close() 
            finally:
                conn.close()

def wg_day(date):
    return date.weekday()

def gpch_day(date):
    start_date_str = '2023-10-25'
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    delta = date - start_date
    date_diff = delta.days
    loop = date_diff//14
    cur_run = date - (start_date + (timedelta(days=loop)*14)  )
    res = cur_run.days
    if res> 11:
        res = 0
    return res

def run_last_update_date(db_conn):
    conn = db_conn.raw_connection()
    cur = conn.cursor()
    cur.callproc(f"p_log")
    cur.close()  

def run_loads(Load_Method, guildPlayers_data, wg_data, gpch_data, vdate):
    with st.status("inicjuję połączenie.", expanded=True) as status:
        con = create_engine()
        statistics = pd.DataFrame(columns=['Source', 'Loaded records'])
        if not guildPlayers_data.empty:
            st.write(f"Ładowanie {guildPlayers}...")
            load_data_intoDB(con,'guildPlayers', guildPlayers_data, vdate)
            status.update(label=f"Zakończono {guildPlayers}!", state='running', expanded=True)
            statistics.loc[len(statistics)] = [ f"{guildPlayers}", len(guildPlayers_data)]
        if not wg_data.empty:
            st.write(f"Ładowanie {wg}...")
            load_data_intoDB(con,'wg', wg_data, vdate)
            status.update(label=f"Zakończono {wg}!", state='running', expanded=True)
            statistics.loc[len(statistics)] = [ f"{wg}", len(wg_data)]
        if not gpch_data.empty:
            st.write(f"Ładowanie {gpch}...")
            load_data_intoDB(con,'gpch', gpch_data, vdate)
            status.update(label=f"Zakończono {gpch}!", state='running', expanded=True)
            statistics.loc[len(statistics)] = [ f"{gpch}", len(gpch_data)]
            
            
        run_last_update_date(con)
        status.update(label="Zakończono ładowanie danych!", state='complete', expanded=True)
        st.dataframe(statistics)
        time.sleep(10)
        status.update(label="Zakończono ładowanie danych!", state='complete', expanded=False)
        st.session_state.pop(f"{Load_Method}_{guildPlayers}")
        st.session_state.pop(f"{Load_Method}_{wg}")
        st.session_state.pop(f"{Load_Method}_{gpch}")

def main():    
    st.set_page_config(
        page_title="WW Stats - Załaduj dane",
        page_icon=".streamlit//logo.png",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'http://www.google_com/',
            'Report a Bug' : 'mailto:adamus01@gmail.com', 
            'About': "# This apps may help to monitor guild health."
        }
    )  
    colx, coly = st.columns([5, 10])
    image = Image.open(path + '/../.streamlit/Logo.png')
    colx.image(image, width=150)
    coly.title('Wzgórze Wisielców  \n\n', anchor='main')

    authenticator, users, username  = login()
    if username:
        role = get_user_role_from_db(username)
        if role == 'Admin':

            xcol, xlcol, xxlcol = st.columns(3)
            with xcol.container(border=True):
                load_type = st.checkbox(label="Wymagaj ładowania wszystkich ekstraktów", value=True)
                wg_gpch_daily_run = st.checkbox(label="Pozwalaj na ładowanie danych w trakcie WG / GPCh", value=True)
            with xlcol.container(border=True):
                vdate = date_pick(sdate)
            
            tab1, tab2 = st.tabs(["Załaduj ze schowka", "Załaduj z pliku"])

            with tab1:
                Load_Method= "Clipboard"
                col1, col2, col3 = st.columns(3, gap="small")
                with col1.container() as c:
                    guildPlayers_data_cl = load_file(Load_Method, guildPlayers)
                with col2.container() as c:
                    if wg_gpch_daily_run == False and wg_day(vdate) !=0:
                        wg_data_cl = load_file(Load_Method, wg, False)
                    else:
                         wg_data_cl = load_file(Load_Method, wg, True)
                with col3.container() as c:
                    if wg_gpch_daily_run == False and gpch_day(vdate) !=0:
                        gpch_data_cl = load_file(Load_Method, gpch, False)
                    else:  
                        gpch_data_cl = load_file(Load_Method, gpch, True)

                if  ( (load_type == True and ((wg_gpch_daily_run == True and guildPlayers_data_cl is not None and gpch_data_cl is not None and wg_data_cl is not None ) \
                       or (wg_gpch_daily_run == False  and (guildPlayers_data_cl is not None or gpch_data_cl is not None or wg_data_cl is not None ))))) \
                    or ( load_type == False and (guildPlayers_data_cl is not None or gpch_data_cl is not None or wg_data_cl is not None)):
                    if (guildPlayers_data_cl is None or gpch_data_cl is None or wg_data_cl is None)\
                        or (guildPlayers_data_cl.empty or gpch_data_cl.empty or wg_data_cl.empty):
                        if guildPlayers_data_cl is None or guildPlayers_data_cl.empty: 
                            guildPlayers_data_cl = pd.DataFrame()
                        if gpch_data_cl is None or gpch_data_cl.empty: 
                            gpch_data_cl = pd.DataFrame()
                        if wg_data_cl is None or wg_data_cl.empty: 
                            wg_data_cl = pd.DataFrame()


                        st.button(label="Załaduj dane", type='primary', on_click=run_loads, args=(Load_Method, guildPlayers_data_cl, wg_data_cl, gpch_data_cl, vdate)) 
                    else:
                        st.button(label="Załaduj dane", type='primary', on_click=run_loads, args=(Load_Method, guildPlayers_data_cl, wg_data_cl, gpch_data_cl, vdate)) 
                
            with tab2:
                Load_Method= "File"                
                col1, col2, col3 = st.columns(3, gap="small")
                with col1.container() as c:
                    guildPlayers_data = load_file(Load_Method, guildPlayers)
                with col2.container() as c:
                    if wg_gpch_daily_run == False and wg_day(vdate) !=0:
                        wg_data = load_file(Load_Method, wg, False)
                    else:
                        wg_data = load_file(Load_Method, wg, True)
                with col3.container() as c:
                    if wg_gpch_daily_run == False and gpch_day(vdate) !=0:
                        gpch_data = load_file(Load_Method, gpch, False)
                    else:  
                        gpch_data = load_file(Load_Method, gpch, True)


                
                if  ( (load_type == True and ((wg_gpch_daily_run == True and guildPlayers_data is not None and gpch_data is not None and wg_data is not None ) \
                       or (wg_gpch_daily_run == False  and (guildPlayers_data is not None or gpch_data is not None or wg_data is not None ))))) \
                    or ( load_type == False and (guildPlayers_data is not None or gpch_data is not None or wg_data is not None)):
                    if guildPlayers_data is None or gpch_data is None or wg_data is None:
                        if guildPlayers_data is None or guildPlayers_data.empty: 
                            guildPlayers_data = pd.DataFrame()
                        if gpch_data is None or gpch_data.empty: 
                            gpch_data = pd.DataFrame()
                        if wg_data is None or wg_data.empty: 
                            wg_data = pd.DataFrame()
                        st.button(label="Załaduj pliki", type='primary', on_click=run_loads, args=(Load_Method, guildPlayers_data, wg_data, gpch_data, vdate)) 
                    else:
                        st.button(label="Załaduj pliki", type='primary', on_click=run_loads, args=(Load_Method, guildPlayers_data, wg_data, gpch_data, vdate)) 
                        
        else:
            st.markdown('<div style="text-align: center;">Nie masz odpwowiedniej roli by wyświetlić tą zawartość.</div>', unsafe_allow_html=True)
            
main()