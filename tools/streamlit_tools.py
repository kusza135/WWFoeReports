import streamlit as st
from sqlalchemy import text

def get_global_params(param_name):
    return st.secrets.get('global')[f'{param_name}']

def get_guild_id():
    return get_global_params('guild_id')
    
def get_guild_name():
    sql = execute_query(
            f'''SELECT name FROM V_all_guilds vag WHERE clanId  = {get_guild_id()} ''', return_type="df",)
    return sql["name"].iloc[0]
    

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