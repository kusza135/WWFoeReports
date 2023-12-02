import streamlit_authenticator as stauth
from streamlit_tools import execute_query


def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{login}','{UserName}', '{Password}')", return_type="df")

hashed_passwords  = stauth.Hasher(['123']).generate()


        

# new_user('Adamus', 'Adamus Bóg Krwi',  hashed_passwords[0])
# new_user('Lusi', 'Lusi The Queen', hashed_passwords[0])