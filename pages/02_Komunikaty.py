import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query, page_header
from tools.login import login, check_user_role_permissions
import os

dump_value = "-1z"
st.session_state['textmsg']= dump_value

path = os.path.dirname(__file__)

def assign_session_p():
    st.markdown(f"*{st.session_state['textmsg']}*")
    st.write(st.session_state['2_key'])
    change_text(st.session_state['textmsg'], st.session_state['2_key'])

  
   
def cheat_sheet():
    
    res = execute_query(f"SELECT msg_type FROM t_tips WHERE valid_to ='3000-12-31'", return_type="df")
    
    editable = st.toggle('Edytuj')
    
    st.markdown(
            """
        <style>
        button {
            height: auto;
            padding-top: 10px !important;
            padding-bottom: 10px !important;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )  
    if not editable:

            col1, col2, col3, col4 = st.columns([ 5, 5, 5, 5 ])
            for i in res.index:
                # st.write(i//4)                
                if i//4==0:
                    with col1.container():
                        if st.button(res.iloc[i]['msg_type'], key=f'P1_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']
                if i//4==1:
                    with col2.container():
                        if st.button(res.iloc[i]['msg_type'], key=f'P1_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']
                if i//4==2:
                    with col3.container():
                        if st.button(res.iloc[i]['msg_type'], key=f'P1_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']
                if i//4==3:
                    with col4.container():
                        if st.button(res.iloc[i]['msg_type'], key=f'P1_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']


            
            st.divider()
            if get_text(st.session_state['textmsg']):
                with stylable_container(
                    "codeblock",
                    """
                    code {
                        white-space: pre-wrap !important;
                    }
                    """,
                ):
                    st.code(get_text(st.session_state['textmsg']), language="markdown") 
                    
            st.divider()
    else:            
        # with tab2:
            col11, col22, col33, col44  = st.columns([5, 5, 5, 5])
            for i in res.index:
                if i//4==0:
                    with col11.container() as x:
                        if st.button(res.iloc[i]['msg_type'], key=f'P2_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']
                if i//4==1:
                    with col22.container() as x:
                        if st.button(res.iloc[i]['msg_type'], key=f'P2_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']
                if i//4==2:
                    with col33.container() as x:
                        if st.button(res.iloc[i]['msg_type'], key=f'P2_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']
                if i//4==3:
                    with col44.container():
                        if st.button(res.iloc[i]['msg_type'], key=f'P1_{i}', help=None, on_click=None, type="secondary", disabled=False, width='stretch'):
                            st.session_state['textmsg'] = res.iloc[i]['msg_type']

            
            if st.session_state['textmsg'] != dump_value:
                with st.container(border=True):
                    p_name = st.session_state['textmsg']
                    st.session_state['2_key'] = get_text(p_name)
                    st.text_area(label="Wprowadź nowy tekst:", value=get_text(p_name), key= '2_key',  height=350, placeholder="Wpisz nowy text", on_change=assign_session_p)
                    
                    st.markdown(''':red[Wciśnij Ctrl+Enter aby zatwierdzić zmiany]''')

            
            st.divider()
            
            col5, col55, col555 = st.columns([5, 5, 5])
            with col5.container() as x:
                new_message()



def get_text(type):
    if type == dump_value:
        results = ""
    else:
        res = execute_query(f"SELECT msg_text FROM t_tips WHERE msg_type = '{type}' AND valid_to ='3000-12-31'", return_type="df")
        results = res.iloc[0]['msg_text']
    return results
    
def change_text(type, msg):
    if type != dump_value:
        sql = f"call p_change_tips('{type}','{msg}')"
        # st.write(sql)
        execute_query(sql, return_type="df")
        st.toast("Dane zapisane", icon="✅")
        st.cache_data.clear()

    
def new_message():
    v_type = st.text_input(label="Krótki opis komunikatu")
    if v_type != None:
        v_msg = st.text_area(label="Opis", placeholder="Uzupełnij opis")
        if v_msg != None  and v_msg != "" and v_type != None and v_type != "":
            st.button(label="Zapisz", on_click=change_text, args= (v_type, v_msg), disabled=False)
        else:
            st.button(label="Zapisz", on_click=change_text, args= (v_type, v_msg), disabled=True)



def run_reports():
    st.subheader(" ##  Ściąga komunikatów  ## ", anchor='komunikaty')
    
    cheat_sheet()

        
if __name__ == '__main__':
    page_header()
    authenticator, users, username  = login()
    if username:
        # st.write(st.session_state['authenticator_status'])
        if st.session_state['authenticator_status']:
            if check_user_role_permissions(username, 'MESSAGES') == True:
                run_reports()   
            else:
                st.warning("Nie masz dostępu do tej zawartości.")  