import argparse
from pathlib import Path

import pandas as pd

from x_html_parser import parse_x_profile_html_file


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="本地 X 页面保存的 .html 路径")
    ap.add_argument("--out", required=True, help="输出文件路径（.csv 或 .xlsx）")
    args = ap.parse_args()

    _, rows = parse_x_profile_html_file(args.input)
    df = pd.DataFrame(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    suffix = out.suffix.lower()
    if suffix == ".csv":
        df.to_csv(out, index=False, encoding="utf-8-sig")
        return 0
    if suffix in {".xlsx", ".xls"}:
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="tweets")
        return 0

    raise SystemExit("out 只支持 .csv 或 .xlsx")


if __name__ == "__main__":
    raise SystemExit(main())
