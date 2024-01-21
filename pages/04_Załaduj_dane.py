import streamlit as st
from PIL import Image
from tools.streamlit_tools import execute_query, create_engine
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

if guildPlayers not in st.session_state: st.session_state[guildPlayers] = str(randint(1000, 100000000))
if wg not in st.session_state: st.session_state[wg] = str(randint(1000, 100000000))
if gpch not in st.session_state: st.session_state[gpch] = str(randint(1000, 100000000))

def date_pick(sdate):
    przycisk1 = st.toggle('zmień datę ładowania danych')
    vdate = sdate
    if przycisk1:
        vdate = st.date_input("Wybierz datę", value="today", format='DD-MM-YYYY')
        return vdate
    return vdate

def load_file(File_type, visibility = True):
    uploaded_file = st.file_uploader(f"Wybierz lub przeciągnij plik {File_type}", key= st.session_state[File_type], disabled=not visibility)
    if uploaded_file is not None:
        # To read file as string:
        string_data = json.loads(uploaded_file.getvalue().decode("utf-8"))

        st.write(File_type)
        if File_type == guildPlayers:
            data = pd.DataFrame(string_data)
            
        elif File_type == wg:
            data = pd.json_normalize(string_data)
            data.columns = data.columns.str.lstrip('player.')
        elif File_type == gpch:
            data = pd.json_normalize(string_data)
            data.columns = data.columns.str.lstrip('player\.')
        return data
    else:
        return None


def load_data_intoDB(db_conn, dfName, DfData, vdate=date.today()):
 
    # conn = db_conn.raw_connection()
    match dfName:
        case 'guildPlayers':
            
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
            execute_query(f'DROP TABLE IF EXISTS __{dfName}', return_type=None)
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='replace')
            
            execute_query(f"CALL p_{dfName}('__{dfName}')", return_type="df")
            
            
        case 'ages':
            
            input_data = DfData.loc[:, ['id'
                                        , 'Age_PL'
                                        , 'era'
                                       ]]
            
            execute_query(f'DROP TABLE IF EXISTS __{dfName}', return_type=None)
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='append')

            execute_query(f"CALL p_{dfName}('__{dfName}')", return_type="df")
           
            
        case 'wg':
            input_data = DfData.loc[:, ['_id'
                                        , 'xpeditionPoints'
                                        , 'solvedEncounters'
                                        , 'contributionDifficulty'
                                       ]]
            
            execute_query(f'DROP TABLE IF EXISTS __{dfName}', return_type=None)
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='append')
            
            execute_query(f"CALL p_{dfName}('__{dfName}',{wg_day(vdate)})", return_type=None)
         
            
        case 'gpch':
            input_data = DfData.loc[:, ['_id'
                                        , 'nk'
                                        , 'battlesWon'
                                        , 'negotiationsWon'
                                        , 'ttrition'
                                       ]]
            
            execute_query(f'DROP TABLE IF EXISTS __{dfName}', return_type=None)
            input_data.to_sql(name=f'__{dfName}',con=db_conn,if_exists='append')
            
            execute_query(f"CALL p_{dfName}('__{dfName}',{gpch_day(vdate)})", return_type="df")

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

def run_loads(guildPlayers_data, wg_data, gpch_data):
    with st.status("inicjuję połączenie.", expanded=True) as status:
        con = create_engine()
        if not guildPlayers_data.empty:
            st.write(f"Ładowanie {guildPlayers}...")
            load_data_intoDB(con,'guildPlayers', guildPlayers_data)
            status.update(label=f"Zakończono {guildPlayers}!", state='running', expanded=True)
        if not wg_data.empty:
            st.write(f"Ładowanie {wg}...")
            load_data_intoDB(con,'wg', wg_data)
            status.update(label=f"Zakończono {wg}!", state='running', expanded=True)
        if not gpch_data.empty:
            st.write(f"Ładowanie {gpch}...")
            load_data_intoDB(con,'gpch', gpch_data)
            status.update(label=f"Zakończono {gpch}!", state='running', expanded=True)
        run_last_update_date(con)
        status.update(label="Zakończono ładowanie danych!", state='complete', expanded=True)
        time.sleep(3)
        st.session_state.pop(guildPlayers)
        st.session_state.pop(wg)
        st.session_state.pop(gpch)




def main():    
    # st.empty
    colx, coly = st.columns([5, 10])
    image = Image.open(path + '/../.streamlit/Logo.png')
    colx.image(image, width=150)
    coly.title('Wzgórze Wisielców  \n\n', anchor='main')

    authenticator, users, username  = login()
    if username:
        role = get_user_role_from_db(username)
        if role == 'Admin':
            # guildPlayers_data =pd.DataFrame()
            # st.write(guildPlayers_data.count())
            xcol, xlcol, xxlcol = st.columns(3)
            with xlcol.container(border=True):
                vdate = date_pick(sdate)
            col1, col2, col3 = st.columns(3, gap="small")
            with col1.container() as c:
                guildPlayers_data = load_file(guildPlayers)
            with col2.container() as c:
                wg_data = load_file(wg)
            with col3.container() as c:
                if gpch_day(vdate) == 0: 
                    gpch_data = load_file(gpch, True)
                else:
                    gpch_data = load_file(gpch, False)
            
                # st.write("tutaj będzie funcjonalność ładowania plików")                

            
            if guildPlayers_data is not None or ( gpch_data is not None and gpch_day(vdate) == True ) or wg_data is not None:
                if not guildPlayers_data.empty or wg_data.empty or gpch_data.empty:
                    if guildPlayers_data is None or guildPlayers_data.empty: 
                        guildPlayers_data = pd.DataFrame()
                    if gpch_data is None or gpch_data.empty: 
                        gpch_data = pd.DataFrame()
                    if wg_data is None or wg_data.empty: 
                        wg_data = pd.DataFrame()
                    st.button(label="Załaduj pliki", type='primary', on_click=run_loads, args=(guildPlayers_data, wg_data, gpch_data)) 
                    # \
                    #         and guildPlayers in st.session_state.keys():
                        

                        
            
        else:
            st.markdown('<div style="text-align: center;">Nie masz odpwowiedniej roli by wyświetlić tą zawartość.</div>', unsafe_allow_html=True)
            
main()