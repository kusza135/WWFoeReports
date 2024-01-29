import streamlit as st
from sqlalchemy import text

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