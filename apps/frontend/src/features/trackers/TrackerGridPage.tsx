import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { CellValueChangedEvent, ColDef, ICellRendererParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { useTracker, useEditCell, type TrackerCellData } from "./useTrackers";

/**
 * Phase 0 grid dimensions are a fixed 15x8 window, not driven by
 * Tracker.schema_definition (which holds column name/type/formula-flag
 * per the model docstring) -- that schema-driven column rendering is
 * real remaining scope, not built in this slice. Every cell coordinate
 * in this fixed window is addressable and persists via the same sparse
 * tracker_cells rows regardless, so nothing here blocks adding
 * schema-driven columns later.
 */
const GRID_ROWS = 15;
const COL_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];

interface GridRow {
  rowIdx: number;
  [colLetter: string]: number | string;
}

function cellsByCoord(cells: TrackerCellData[]): Map<string, TrackerCellData> {
  const map = new Map<string, TrackerCellData>();
  for (const cell of cells) map.set(`${cell.row_idx}-${cell.col_idx}`, cell);
  return map;
}

export function TrackerGridPage() {
  const { trackerId } = useParams<{ trackerId: string }>();
  const { data: tracker, isLoading, isError, error } = useTracker(trackerId);
  const editCell = useEditCell(trackerId ?? "");

  const cellMap = useMemo(() => cellsByCoord(tracker?.cells ?? []), [tracker]);

  const rowData: GridRow[] = useMemo(
    () =>
      Array.from({ length: GRID_ROWS }, (_, i) => {
        const rowIdx = i + 1; // A1 is row_idx=1, per formula_parser's convention
        const row: GridRow = { rowIdx };
        COL_LETTERS.forEach((letter, colIdx) => {
          const cell = cellMap.get(`${rowIdx}-${colIdx}`);
          // Editable value is always the *stored* text -- formula if
          // set, else raw_value -- never the computed result. Showing
          // the computed value alongside is the renderer's job below,
          // so editing a formula shows you the formula, not its last
          // answer.
          row[letter] = cell ? (cell.formula ?? cell.raw_value ?? "") : "";
        });
        return row;
      }),
    [cellMap],
  );

  const columnDefs: ColDef<GridRow>[] = useMemo(
    () => [
      {
        field: "rowIdx",
        headerName: "",
        width: 56,
        editable: false,
        pinned: "left",
        cellClass: "data-value",
      },
      ...COL_LETTERS.map(
        (letter, colIdx): ColDef<GridRow> => ({
          field: letter,
          headerName: letter,
          editable: true,
          cellRenderer: (params: ICellRendererParams<GridRow>) => {
            const cell = cellMap.get(`${params.data?.rowIdx}-${colIdx}`);
            if (!cell) return "";
            if (cell.error_state !== "none") {
              return `#${cell.error_state.toUpperCase()}`;
            }
            if (cell.formula) {
              return cell.computed_value ?? "";
            }
            return cell.raw_value ?? "";
          },
        }),
      ),
    ],
    [cellMap],
  );

  function handleCellValueChanged(event: CellValueChangedEvent<GridRow>) {
    const letter = event.colDef.field;
    if (!letter || letter === "rowIdx") return;
    const colIdx = COL_LETTERS.indexOf(letter);
    const rowIdx = event.data.rowIdx;
    const typed = String(event.newValue ?? "");

    const isFormula = typed.startsWith("=");
    editCell.mutate({
      row_idx: rowIdx,
      col_idx: colIdx,
      formula: isFormula ? typed : null,
      raw_value: isFormula ? null : typed || null,
    });
  }

  if (isLoading) {
    return <div style={{ padding: "32px", color: "var(--color-text-muted)" }}>Loading tracker…</div>;
  }
  if (isError || !tracker) {
    return (
      <div style={{ padding: "32px", color: "var(--color-negative)" }}>
        Couldn't load this tracker: {(error as Error)?.message ?? "not found"}
      </div>
    );
  }

  return (
    <div style={{ padding: "32px", height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ marginBottom: "16px" }}>
        <Link to="/app/trackers" style={{ color: "var(--color-text-muted)", fontSize: "13px" }}>
          ← Trackers
        </Link>
        <h1 style={{ fontSize: "20px", fontWeight: 600, marginTop: "4px" }}>{tracker.name}</h1>
      </div>

      <div className="ag-theme-alpine" style={{ flex: 1, minHeight: 0 }}>
        <AgGridReact<GridRow>
          rowData={rowData}
          columnDefs={columnDefs}
          onCellValueChanged={handleCellValueChanged}
          suppressMovableColumns
          stopEditingWhenCellsLoseFocus
        />
      </div>
    </div>
  );
}
