import io

import pandas as pd
import streamlit as st

from x_html_parser import parse_x_profile_html, parse_x_profile_html_file


st.set_page_config(page_title="X HTML Exporter", layout="wide")

st.title("X / Twitter 本地 HTML 解析导出")

default_path = "/Users/oria/Desktop/(1) MGM Rewards (@MGMRewards) _ X.html"
input_path = st.text_input("本地 HTML 路径", value=default_path)
uploaded = st.file_uploader("或上传 HTML 文件", type=["html", "htm"])

export_csv = st.checkbox("导出 CSV", value=True)
export_xlsx = st.checkbox("导出 Excel (XLSX)", value=True)

run = st.button("开始解析", type="primary")

if run:
    if uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
        _, rows = parse_x_profile_html(raw)
    else:
        _, rows = parse_x_profile_html_file(input_path)

    df = pd.DataFrame(rows)
    st.subheader(f"解析结果（{len(df)} 条）")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if len(df) == 0:
        st.stop()

    if export_csv:
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "下载 CSV",
            data=csv_bytes,
            file_name="x_export.csv",
            mime="text/csv",
        )

    if export_xlsx:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="tweets")
        st.download_button(
            "下载 XLSX",
            data=out.getvalue(),
            file_name="x_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
