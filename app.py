import csv
import io
from datetime import date
from typing import Any

import streamlit as st

from replik_client import ReplikClient


st.set_page_config(page_title="IS REPLIK – konania", page_icon="📄", layout="wide")
st.title("IS REPLIK – vyhľadávanie konaní")
st.write(
    "Vyhľadajte konania podľa dátumu začatia. Kliknite na riadok v tabuľke "
    "a aplikácia načíta detail konania."
)


@st.cache_resource
def get_client() -> ReplikClient:
    return ReplikClient(use_production=True)


if "konania" not in st.session_state:
    st.session_state.konania = []

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
            st.session_state.detail_id = None
            st.session_state.detail = None
        except Exception as exc:
            st.error(f"Nepodarilo sa načítať konania: {exc}")

konania = st.session_state.konania
if konania:
    st.success(f"Načítaných záznamov: {len(konania)}")
    st.caption("Kliknutím na riadok zobrazíte detail konkrétneho konania.")

    # on_select/selection_mode vyžadujú Streamlit 1.35 alebo novší.
    selection = st.dataframe(
        konania,
        key="konania_tabulka",
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = selection.selection.rows
    if selected_rows:
        selected = konania[selected_rows[0]]
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
