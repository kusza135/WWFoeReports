import streamlit as st
from sqlalchemy import text
from PIL import Image
import os

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

def get_guild_name():
    sql = execute_query(
            f'''SELECT name FROM V_all_guilds vag WHERE clanId  = {get_guild_id()} ''', return_type="df",)
    return sql["name"].iloc[0]

def last_refresh_date():
    query = f'SELECT MAX(last_update_date) AS last_update_date FROM t_log'
    text_var = execute_query(query=query, return_type="df")
    st.markdown(f"<h7 style='text-align: center; color: grey;'><center>Świat:<br><b>{get_world_name(get_world_id())}</b></center></h7>", unsafe_allow_html=True) 
    st.markdown(f"<h7 style='text-align: center; color: grey;'><center>Data ostatniego odświeżenia raportu WG/GPCh:<br><b>{str(text_var['last_update_date'].iloc[0])}</b></center></h7>", unsafe_allow_html=True) 
    
    
def page_header():

    colx, coly, colz = st.columns([5, 10, 4])
    image = Image.open(path + '/../.streamlit/Logo.png')
    with colz as x:
        last_refresh_date()
    colx.image(image, width=150)
     
    coly.title(f'{get_guild_name()}  \n\n', anchor='main')
      
    
    

def execute_query(query: str, return_type: str = "df"):
    # st.write(query)
    con= st.connection('my_sql', type='sql')
    if return_type == "df":
        return con.query(query)
    elif return_type == "list":
        return con.query(query).values.tolist()



def create_engine():
    con = st.connection('my_sql', type='sql')
    conx = con.engine
    return conx
    
def runsql(dbconnector, query):
    try:
        with dbconnector.connect() as con:
            rs = con.execute(text(query) )
    except Exception as e:
        st.write(query)
        raise e.with_traceback