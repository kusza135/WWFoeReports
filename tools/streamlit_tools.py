import streamlit as st


def execute_query(query: str, return_type: str = "df"):
    # st.write(query)
    con= st.connection('my_sql', type='sql')
    if return_type == "df":
        return con.query(query)
    elif return_type == "list":
        return con.query(query).values.tolist()



    