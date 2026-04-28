import io

import pandas as pd
import streamlit as st

from x_html_parser import parse_x_profile_html, parse_x_profile_html_file


st.set_page_config(page_title="X HTML Exporter", layout="wide")

st.title("X / Twitter 本地 HTML 解析导出")

mode = st.radio(
    "输入方式",
    options=["粘贴 HTML（推荐）", "上传 HTML 文件", "本地文件路径"],
    horizontal=True,
    index=0,
)

raw_html = ""
input_path = ""
uploaded = None

if mode == "粘贴 HTML（推荐）":
    raw_html = st.text_area(
        "把你复制的 X 页面 HTML 粘贴到这里（支持一次粘贴多条/一整段 Timeline）",
        value="",
        height=260,
        placeholder='例如包含 data-testid="tweet" 的那段 HTML…',
    )
elif mode == "上传 HTML 文件":
    uploaded = st.file_uploader("上传 HTML 文件", type=["html", "htm"])
else:
    input_path = st.text_input("本地 HTML 路径（云端部署时通常用不上）", value="")

export_csv = st.checkbox("导出 CSV", value=True)
export_xlsx = st.checkbox("导出 Excel (XLSX)", value=True)

run = st.button("开始解析", type="primary")

if run:
    if raw_html.strip():
        _, rows = parse_x_profile_html(raw_html)
    elif uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
        _, rows = parse_x_profile_html(raw)
    else:
        if not input_path:
            st.error("请粘贴 HTML、上传 HTML 文件，或填写本地 HTML 路径。")
            st.stop()
        _, rows = parse_x_profile_html_file(input_path)

    df = pd.DataFrame(rows)
    show_cols = [
        "post_url",
        "post_time",
        "account",
        "post_content",
        "like_count",
        "comment_count",
        "repost_count",
        "view_count",
        "tags",
    ]
    for c in show_cols:
        if c not in df.columns:
            df[c] = None
    out_df = df[show_cols].copy()

    st.subheader(f"解析结果（{len(out_df)} 条）")
    st.dataframe(out_df, use_container_width=True, hide_index=True)

    if len(out_df) == 0:
        st.stop()

    if export_csv:
        csv_bytes = out_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "下载 CSV",
            data=csv_bytes,
            file_name="x_export.csv",
            mime="text/csv",
        )

    if export_xlsx:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="posts")
        st.download_button(
            "下载 XLSX",
            data=out.getvalue(),
            file_name="x_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
