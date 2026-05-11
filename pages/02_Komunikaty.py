import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from tools.streamlit_tools import execute_query, page_header
from tools.login import login, check_user_role_permissions

# ---------------------------------------------------------------------------
# STALE
# ---------------------------------------------------------------------------

DUMP_VALUE = "-1z"

# ---------------------------------------------------------------------------
# WARSTWA DANYCH
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_message_types() -> object:
    """Lista typow komunikatow — cache 5 min."""
    return execute_query(
        "SELECT msg_type FROM t_tips WHERE valid_to = '3000-12-31'",
        return_type="df",
    )


@st.cache_data(ttl=300)
def get_text(msg_type: str) -> str:
    """Tresc komunikatu danego typu — cache 5 min."""
    if msg_type == DUMP_VALUE:
        return ""
    res = execute_query(
        "SELECT msg_text FROM t_tips WHERE msg_type = :msg_type AND valid_to = '3000-12-31'",
        params={"msg_type": msg_type},
        return_type="df",
    )
    if res.empty:
        return ""
    return res.iloc[0]["msg_text"]


def change_text(msg_type: str, msg: str) -> None:
    """Zapisuje zmieniony tekst komunikatu."""
    if msg_type == DUMP_VALUE or not msg_type:
        return
    execute_query(
        "CALL p_change_tips(:msg_type, :msg)",
        params={"msg_type": msg_type, "msg": msg},
        return_type="df",
    )
    get_text.clear()
    get_message_types.clear()
    st.toast("Dane zapisane", icon="✅")


# ---------------------------------------------------------------------------
# HELPERY UI
# ---------------------------------------------------------------------------

def _render_type_buttons(types, key_prefix: str) -> None:
    """
    Renderuje przyciski typow komunikatow w 4 kolumnach.
    Klikniecie zapisuje wybrany typ do session_state['selected_msg_type'].
    """
    cols = st.columns(4)
    for i, msg_type in enumerate(types):
        with cols[i % 4]:
            if st.button(msg_type, key=f"{key_prefix}_{i}", width="stretch"):
                st.session_state["selected_msg_type"] = msg_type


def _on_text_change() -> None:
    """Callback dla text_area w trybie edycji."""
    change_text(
        st.session_state.get("selected_msg_type", DUMP_VALUE),
        st.session_state.get("edit_text_key", ""),
    )


# ---------------------------------------------------------------------------
# GLOWNE SEKCJE
# ---------------------------------------------------------------------------

@st.fragment
def cheat_sheet_view(types) -> None:
    """
    Tryb podgladu — przyciski + wyswietlenie tresci komunikatu.
    Fragment izoluje rerenderowanie od trybu edycji.
    """
    _render_type_buttons(types, key_prefix="view")

    st.divider()

    selected = st.session_state.get("selected_msg_type", DUMP_VALUE)
    text = get_text(selected)
    if text:
        with stylable_container(
            "codeblock",
            "code { white-space: pre-wrap !important; }",
        ):
            st.code(text, language="markdown")

    st.divider()


@st.fragment
def cheat_sheet_edit(types) -> None:
    """
    Tryb edycji — przyciski + edytowalny text_area + formularz nowego komunikatu.
    Fragment izoluje rerenderowanie od trybu podgladu.
    """
    _render_type_buttons(types, key_prefix="edit")

    selected = st.session_state.get("selected_msg_type", DUMP_VALUE)

    if selected != DUMP_VALUE:
        with st.container(border=True):
            current_text = get_text(selected)
            st.text_area(
                label="Wprowadz nowy tekst:",
                value=current_text,
                key="edit_text_key",
                height=350,
                placeholder="Wpisz nowy tekst",
                on_change=_on_text_change,
            )
            st.markdown(":red[Wcisnij Ctrl+Enter aby zatwierdzic zmiany]")

    st.divider()

    # Nowy komunikat
    col1, *_ = st.columns([5, 5, 5])
    with col1:
        new_message()


@st.fragment
def new_message() -> None:
    """Formularz dodawania nowego komunikatu."""
    v_type = st.text_input(label="Krotki opis komunikatu")
    v_msg = st.text_area(label="Opis", placeholder="Uzupelnij opis")
    disabled = not (v_type and v_msg)
    st.button(
        label="Zapisz",
        on_click=change_text,
        args=(v_type, v_msg),
        disabled=disabled,
        type="primary",
    )


# ---------------------------------------------------------------------------
# GLOWNA FUNKCJA
# ---------------------------------------------------------------------------

def run_reports() -> None:
    st.subheader("Sciaga komunikatow", anchor="komunikaty")

    # Inicjalizacja session_state
    if "selected_msg_type" not in st.session_state:
        st.session_state["selected_msg_type"] = DUMP_VALUE

    types = get_message_types()["msg_type"].tolist()

    editable = st.toggle("Edytuj")

    st.markdown(
        """
        <style>
        button { height: auto; padding-top: 10px !important; padding-bottom: 10px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if editable:
        cheat_sheet_edit(types)
    else:
        cheat_sheet_view(types)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    page_header()

    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None

    authenticator, users, username = login()

    if username and st.session_state.get("authentication_status"):
        if check_user_role_permissions(username, "MESSAGES"):
            run_reports()
        else:
            st.warning("Nie masz dostepu do tej zawartosci.")