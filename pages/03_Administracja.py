import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from PIL import Image
from tools.streamlit_tools import execute_query
from tools.login import login, get_user_role_from_db
import os
import streamlit_authenticator as stauth

path = os.path.dirname(__file__)

def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{login}','{UserName}', '{Password}')", return_type="df")

def db_change_pwd(UserName, Password):
    query = f"call p_modify_user('{UserName}', '{Password}')"
    st.write(query)
    execute_query(query, return_type="df")
    
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
            with st.container() as c:
                
                col1, col2, col3 = st.columns([50, 50, 10])
                options = col1.radio(label="Wybierz opcję",options=["Create New User", "Reset User Password"], horizontal=False)
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
        else:
            st.markdown('<div style="text-align: center;">Nie masz odpwowiedniej roli by wyświetlić tą zawartość.</div>', unsafe_allow_html=True)


main()
