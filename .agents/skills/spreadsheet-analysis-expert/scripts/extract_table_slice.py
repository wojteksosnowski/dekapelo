#!/usr/bin/env python3
"""extract_table_slice.py

Narzędzie CLI do precyzyjnego wycinania fragmentu arkusza kalkulacyjnego (.xlsx, .xls, .ods)
z automatycznym rozwiązywaniem scalonych komórek (merged cells).
Zwraca format Markdown, CSV lub JSON gotowy do bezpośredniej analizy przez LLM.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional, List, Any

# Zapewnienie poprawnego kodowania na konsoli Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def extract_slice_xlsx(
    filepath: str,
    sheet_name: Optional[str] = None,
    min_row: int = 1,
    max_row: int = 25,
    min_col: int = 1,
    max_col: int = 15,
    resolve_merged: bool = True
) -> List[List[Any]]:
    import openpyxl

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

    # Budowa mapy scalonych komórek
    merged_map = {}
    if resolve_merged and hasattr(ws, "merged_cells"):
        for rng in ws.merged_cells.ranges:
            top_val = ws.cell(row=rng.min_row, column=rng.min_col).value
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    merged_map[(r, c)] = top_val

    grid = []
    effective_max_r = min(max_row, ws.max_row or max_row)
    effective_max_c = min(max_col, ws.max_column or max_col)

    for r in range(min_row, effective_max_r + 1):
        row_vals = []
        for c in range(min_col, effective_max_c + 1):
            if resolve_merged and (r, c) in merged_map:
                val = merged_map[(r, c)]
            else:
                val = ws.cell(row=r, column=c).value
            row_vals.append(val)
        grid.append(row_vals)

    wb.close()
    return grid


def format_markdown_table(grid: List[List[Any]], min_row: int = 1, min_col: int = 1) -> str:
    if not grid:
        return "*Pusta tabela*"

    lines = []
    # Nagłówek kolumn z indeksami
    col_count = len(grid[0])
    header_cols = ["Wiersz"] + [f"Kol {min_col + i}" for i in range(col_count)]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

    for idx, row in enumerate(grid):
        row_idx = min_row + idx
        formatted_cells = [str(v).replace("\n", " ").replace("|", "\\|").strip() if v is not None else "" for v in row]
        lines.append(f"| {row_idx} | " + " | ".join(formatted_cells) + " |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Precyzyjne wycinanie wycinka tabeli z arkusza kalkulacyjnego")
    parser.add_argument("file", help="Ścieżka do pliku arkusza")
    parser.add_argument("--sheet", help="Nazwa arkusza")
    parser.add_argument("--start-row", type=int, default=1, help="Wiersz początkowy (1-indexed, domyślnie 1)")
    parser.add_argument("--end-row", type=int, default=25, help="Wiersz końcowy (1-indexed, domyślnie 25)")
    parser.add_argument("--start-col", type=int, default=1, help="Kolumna początkowa (1-indexed, domyślnie 1)")
    parser.add_argument("--end-col", type=int, default=15, help="Kolumna końcowa (1-indexed, domyślnie 15)")
    parser.add_argument("--no-resolve-merged", action="store_true", help="Wyłącz rozwiązywanie scalonych komórek")
    parser.add_argument("--json", action="store_true", help="Format JSON")
    parser.add_argument("--csv", action="store_true", help="Format CSV")

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Błąd: Plik {file_path} nie istnieje.", file=sys.stderr)
        sys.exit(1)

    ext = file_path.suffix.lower()
    if ext not in [".xlsx", ".xlsm", ".xltx"]:
        import pandas as pd
        engine = "odf" if ext == ".ods" else None
        df = pd.read_excel(str(file_path), sheet_name=args.sheet or 0, header=None, engine=engine)
        sub_df = df.iloc[args.start_row - 1 : args.end_row, args.start_col - 1 : args.end_col]
        grid = sub_df.values.tolist()
    else:
        grid = extract_slice_xlsx(
            str(file_path),
            sheet_name=args.sheet,
            min_row=args.start_row,
            max_row=args.end_row,
            min_col=args.start_col,
            max_col=args.end_col,
            resolve_merged=not args.no_resolve_merged
        )

    if args.json:
        print(json.dumps(grid, indent=2, ensure_ascii=False, default=str))
    elif args.csv:
        import csv
        writer = csv.writer(sys.stdout)
        for row in grid:
            writer.writerow([str(v) if v is not None else "" for v in row])
    else:
        print(format_markdown_table(grid, min_row=args.start_row, min_col=args.start_col))


if __name__ == "__main__":
    main()
