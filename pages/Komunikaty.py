import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query
from tools.login import login
import os


path = os.path.dirname(__file__)
   
def cheat_sheet():
    tab1, tab2 = st.tabs(["Wyśwletl", "Zmień"])
    
    res = execute_query(f"SELECT msg_type FROM t_tips WHERE valid_to ='3000-12-31'", return_type="df")
    
    
    
    with tab1:
        col1, col2, col3 = st.columns([5, 5, 5])
        for i in res.index:
            if i//3==0:
                with col1.container():
                    container_tab1(res.iloc[i]['msg_type'])
            if i//3==1:
                with col2.container():
                    container_tab1(res.iloc[i]['msg_type'])
            if i//3==2:
                with col3.container():
                    container_tab1(res.iloc[i]['msg_type'])

    with tab2:
        col11, col22, col33 = st.columns([5, 5, 5])
        for i in res.index:
            if i//3==0:
                with col11.container() as x:
                    container_tab2(res.iloc[i]['msg_type'])
            if i//3==1:
                with col22.container() as x:
                    container_tab2(res.iloc[i]['msg_type'])
            if i//3==2:
                with col33.container() as x:
                    container_tab2(res.iloc[i]['msg_type'])
        
        st.divider()
        
        col4, col44, col444 = st.columns([5, 5, 5])
        with col4.container() as x:
            new_message()

def container_tab1(p_name):
    with st.expander(p_name):
        if f'{p_name}1_key' not in st.session_state:
            st.session_state[f'{p_name}1_key'] = get_text(p_name)
        with stylable_container(
            "codeblock",
            """
            code {
                white-space: pre-wrap !important;
            }
            """,
        ):
            st.code(st.session_state[f'{p_name}1_key'], language="markdown")
        
def container_tab2(p_name):
    def assign_session_p():
        st.write(st.session_state[f'{p_name}2_key'])
        st.warning('Dane nie zostały jeszcze zapisane \n Wróć i kliknij "Zapisz".', icon="⚠️")
        # change_text(p_type, st.session_state.ur_key)
        
    with st.expander(p_name):
        if f'{p_name}2_key' not in st.session_state:
            
            st.session_state[f'{p_name}2_key'] = get_text(p_name)
            st.text_area(label="Wprowadź nowy tekst:", value=get_text(p_name), key=f'{p_name}2_key', placeholder="Wpisz nowy text", on_change=assign_session_p)
        if get_text(p_name) != st.session_state[f'{p_name}2_key']:
            st.button(label=f"Zapisz_{p_name}", on_click=change_text, args=(p_name, st.session_state[f'{p_name}2_key']), disabled=False)
        else:
            st.button(label=f"Zapisz_{p_name}", on_click=change_text, args=(p_name, st.session_state[f'{p_name}2_key']), disabled=True)
 

def get_text(type):
    res = execute_query(f"SELECT msg_text FROM t_tips WHERE msg_type = '{type}' AND valid_to ='3000-12-31'", return_type="df")
    return res.iloc[0]['msg_text']
    
def change_text(type, msg):
    execute_query(f"call p_change_tips('{type}','{msg}')", return_type="df")
    st.cache_data.clear()
    st.cache_resource.clear()
    
def new_message():
    v_type = st.text_input(label="Krótki opis komunikatu")
    if v_type != None:
        v_msg = st.text_area(label="Opis", placeholder="Uzupełnij opis")
        if v_msg != None  and v_msg != "" and v_type != None and v_type != "":
            st.button(label="Zapisz", on_click=change_text, args= (v_type, v_msg), disabled=False)
        else:
            st.button(label="Zapisz", on_click=change_text, args= (v_type, v_msg), disabled=True)



def run_reports():
    # st.empty
    colx, coly = st.columns([5, 10])
    image = Image.open(path + '/../.streamlit/Logo.png')
    colx.image(image, width=150)
    coly.title('Wzgórze Wisielców  \n\n', anchor='main')
    
    st.subheader(" ##  Ściąga komunikatów  ## ", anchor='komunikaty')
    
    cheat_sheet()

        
if __name__ == '__main__':    
    if 'authenticator_status' not in st.session_state:
        st.session_state.authenticator_status = None
    login()
    if st.session_state['authenticator_status']:
        run_reports()

