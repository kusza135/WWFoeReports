import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query, get_guild_name
from tools.login import login, get_user_role_from_db, reset_password, db_change_pwd
import os
import streamlit_authenticator as stauth

path = os.path.dirname(__file__)

def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{login}','{UserName}', '{Password}')", return_type="df")

    
def main():    
    st.set_page_config(
        page_title="WW Stats - Administracja",
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
    coly.title(f'{get_guild_name()}  \n\n', anchor='main')
    authenticator, users, username  = login()
    if username:
        role = get_user_role_from_db(username)
        
        with st.container() as c:
            
            col1, col2, col3 = st.columns([50, 50, 10])
            if role == 'Admin':
                options = col1.radio(label="Wybierz opcję",options=["Change your Password", "Create New User", "Reset User Password"], horizontal=False)
            elif role == 'User':
                options = col1.radio(label="Wybierz opcję",options=["Zmień hasło"], horizontal=False)
            
            if options == "Change your Password" or options == "Zmień hasło":
                with col2.container():
                    new_password, x = reset_password(authenticator)
                    if new_password != None and x == True:
                        db_change_pwd(username, new_password)
                        st.success("Hasło zmienione", icon="✅")
            if options == "Create New User":
                with col2.container():
            # with col1.expander(label="Create New User") as cnu:
                    x = authenticator.register_user('Uzupełnij dane', preauthorization=False)
                    if x == True :
                        # userName = 
                        for names in authenticator.credentials['usernames']:
                            new_user(names, authenticator.credentials['usernames'][names]['name'], authenticator.credentials['usernames'][names]['password'])
                        st.success('User registered successfully')
                        st.cache_data.clear()
                        st.rerun()

            # with col2.expander(label="Reset User Password") as rup:
            if options == "Reset User Password":
                with col2.container():
                    wybor_uzytkownika = st.selectbox(label="Wybierz użytkownika", options=users)
                    new_password = st.text_input(label="Nowe hasło", type='password')
                    rep_new_password = st.text_input(label="Powtórz nowe hasło", type='password')
                    st.session_state['button_disable'] =True
                    if len(new_password) > 0:
                                if new_password == rep_new_password:
                                    hashed_password  = stauth.Hasher([new_password]).generate()
                                    st.session_state['button_disable'] = False
                                    st.button(label="Zresetuj", type='primary', on_click=db_change_pwd, args=(wybor_uzytkownika, hashed_password[0]), disabled=st.session_state['button_disable'])
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.markdown('<div style="text-align: center;">Hasła do siebie nie pasują!</div>', unsafe_allow_html=True)
        


main()
