import streamlit as st
from sqlalchemy import text
from PIL import Image
import os
import ast
import time

path = os.path.dirname(__file__)


def get_global_params(param_name):
    return st.secrets.get('global')[f'{param_name}']

def get_guild_id():
    return get_global_params('guild_id')
    
def get_world_id():
    return get_global_params('world')

def get_world_name(word_id):
    sql = execute_query(
            f'''SELECT world_name FROM V_worlds WHERE world  = '{get_world_id()}' ''', return_type="df",)
    return sql["world_name"].iloc[0]

def get_worlds():
    sql = execute_query(
            f'''SELECT world, world_name FROM V_worlds  ''', return_type="df",)
    return sql

def get_guild_name():
    sql = execute_query(
            f'''SELECT name FROM V_all_guilds vag WHERE clanId  = {get_guild_id()} ''', return_type="df",)
    return sql["name"].iloc[0]

def last_refresh_date():
    query = f'SELECT MAX(last_update_date) AS last_update_date FROM t_log'
    text_var = execute_query(query=query, return_type="df")
    st.markdown(f"<h7 style='text-align: center; color: grey;'><center>Świat:<br><b>{get_world_name(get_world_id())}</b></center></h7>", unsafe_allow_html=True) 
    st.markdown(f"<h7 style='text-align: center; color: grey;'><center>Data ostatniego odświeżenia raportu WG/GPCh:<br><b>{str(text_var['last_update_date'].iloc[0])}</b></center></h7>", unsafe_allow_html=True) 
    if st.button(label="Refresh", width='stretch'):
        st.cache_data.clear()
        st.rerun()
    
    
def page_header():
    imagelogo = ".streamlit//foe_logo_max.jpg"
    st.set_page_config(
        page_title="WW Stats",
        page_icon=imagelogo,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'http://www.google.com/',
            'Report a Bug' : 'mailto:adamus01@gmail.com', 
            'About': "# This apps may help to monitor guild health."
        }
    )
    colx, coly, colz = st.columns([5, 10, 4])
    image = Image.open(path + '/../.streamlit/Logo.png')

    st.logo(imagelogo, icon_image=imagelogo)

    with colz as x:
        last_refresh_date()
    colx.image(image, width=150)
     
    coly.title(f'{get_guild_name()}  \n\n', anchor='main')
      
    
    

def execute_query(
    query: str,
    return_type: str = "df",
    params: dict | None = None,
    ttl: int = 0,
):
    """
    Wykonuje zapytanie SELECT do bazy danych.

    Parametry
    ---------
    query       : zapytanie SQL; użyj :nazwa jako placeholder,
                  np. WHERE world = :world AND id = :id
    return_type : "df"   → DataFrame
                  "list" → lista krotek
    params      : słownik wartości do podstawienia,
                  np. {"world": get_world_id(), "id": 42}
    ttl         : czas cache'owania w sekundach (0 = bez cache)

    Przykład
    --------
    execute_query(
        "SELECT * FROM V_users WHERE world = :world AND guildid = :guildid",
        params={"world": get_world_id(), "guildid": get_guild_id()},
    )
    """
    con = st.connection("my_sql", type="sql")
    result = con.query(query, params=params or {}, ttl=ttl)
    if return_type == "df":
        return result
    elif return_type == "list":
        return result.values.tolist()
    raise ValueError(f"Nieznany return_type: '{return_type}'. Użyj 'df' lub 'list'.")


def create_engine():
    con = st.connection("my_sql", type="sql")
    return con.engine


def runsql(dbconnector, query: str) -> None:
    """Wykonuje zapytanie mutujące (INSERT/UPDATE/DELETE/CALL) z commitem."""
    try:
        with dbconnector.connect() as con:
            con.execute(text(query))
            con.commit()
    except Exception as e:
        st.error(f"Błąd SQL: {e}")
        raise


def convert_string_to_bool(str_value) -> bool | None:
    """Konwertuje string 'true'/'false' (dowolna wielkość liter) na bool."""
    if isinstance(str_value, bool):
        return str_value
    if isinstance(str_value, str):
        if str_value.lower() == "true":
            return True
        if str_value.lower() == "false":
            return False
    return None