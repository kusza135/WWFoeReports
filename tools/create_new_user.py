import streamlit_authenticator as stauth
from streamlit_tools import execute_query


def new_user(login, UserName, Password):
    execute_query(f"call p_add_user('{login}','{UserName}', '{Password}')", return_type="df")

hashed_passwords  = stauth.Hasher(['123']).generate()
# print(hashed_passwords)

def db_change_pwd(UserName, Password):
    query = f"call p_modify_user('{UserName}', '{Password}')"
    execute_query(query, return_type="df")
    
# db_change_pwd('xxx', f'{hashed_passwords[0]}')