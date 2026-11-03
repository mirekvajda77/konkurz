import csv
import io
from datetime import date
from typing import Any

import streamlit as st

from replik_client import ReplikClient


st.set_page_config(page_title="IS REPLIK – konania", page_icon="📄", layout="wide")
st.title("IS REPLIK – vyhľadávanie konaní")
st.write(
    "Vyhľadajte konania podľa dátumu začatia. Potom vyberte konkrétne konanie zo zoznamu "
    "a aplikácia načíta jeho detail."
)


@st.cache_resource
def get_client() -> ReplikClient:
    return ReplikClient(use_production=True)


if "konania" not in st.session_state:
    st.session_state.konania = []
if "detail" not in st.session_state:
    st.session_state.detail = None
if "detail_id" not in st.session_state:
    st.session_state.detail_id = None

with st.form("vyhladavanie"):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        datum_od = st.date_input("Dátum od", value=date(date.today().year, 1, 1))
    with col2:
        datum_do = st.date_input("Dátum do", value=date.today())
    with col3:
        max_stranok = st.number_input(
            "Maximálny počet stránok",
            min_value=1,
            max_value=100,
            value=5,
            step=1,
        )
    hladat = st.form_submit_button("Načítať konania", type="primary")

if hladat:
    if datum_od > datum_do:
        st.error("Dátum „od“ nemôže byť neskôr ako dátum „do“.")
    else:
        try:
            with st.spinner("Načítavam údaje z IS REPLIK…"):
                st.session_state.konania = get_client().fetch_konania_pre_obdobie(
                    datum_od=datum_od.isoformat(),
                    datum_do=datum_do.isoformat(),
                    max_stranok=int(max_stranok),
                )
            st.session_state.detail = None
            st.session_state.detail_id = None
        except Exception as exc:
            st.error(f"Nepodarilo sa načítať konania: {exc}")
            st.session_state.konania = []

konania = st.session_state.konania
if konania:
    st.success(f"Načítaných záznamov: {len(konania)}")

    options = [
        f"{row.get('Id') or '-'} | {row.get('Dlznik') or '-'} | {row.get('SpisovaZnackaSudu') or '-'}"
        for row in konania
    ]
    selected_label = st.selectbox("Vyber konanie", options)
    selected_index = options.index(selected_label)
    selected = konania[selected_index]

    konanie_id: Any = selected.get("Id")
    if konanie_id is None or not str(konanie_id).strip():
        st.warning("Vybraný záznam neobsahuje ID potrebné na načítanie detailu.")
    else:
        if st.session_state.get("detail_id") != str(konanie_id):
            try:
                with st.spinner("Načítavam detail konania…"):
                    detail = get_client().get_konanie_detail(str(konanie_id))
                st.session_state.detail_id = str(konanie_id)
                st.session_state.detail = detail
            except Exception as exc:
                st.session_state.detail_id = str(konanie_id)
                st.session_state.detail = None
                st.error(f"Nepodarilo sa načítať detail konania: {exc}")

        detail = st.session_state.get("detail")
        if detail is not None:
            st.subheader("Detail konania")
            st.caption(
                f"{selected.get('Dlznik') or 'Dlžník neuvedený'} · "
                f"{selected.get('SpisovaZnackaSudu') or 'Spisová značka neuvedená'}"
            )
            st.json(detail, expanded=True)

    st.subheader("Výsledky")
    st.dataframe(konania, use_container_width=True, hide_index=True)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=ReplikClient.CSV_FIELDNAMES,
        delimiter=";",
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(konania)
    st.download_button(
        label="Stiahnuť výsledky ako CSV",
        data=output.getvalue().encode("utf-8-sig"),
        file_name="konania_export.csv",
        mime="text/csv",
    )
elif not hladat:
    st.info("Zadajte obdobie a kliknite na „Načítať konania“.")
