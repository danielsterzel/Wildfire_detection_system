import { useState, useEffect } from "react";

interface Cell {
  row: number;
  col: number;
  symbol_type: string;
}

interface GridData {
  cells: Cell[];
}

const GRID_SIZE = 20;
const CELL_SIZE = 30; // pixels

const getColorForSymbol = (symbolType: string): string => {
  switch (symbolType) {
    case "TREE":
      return "bg-green-600 hover:bg-green-700";
    case "FIRE":
      return "bg-red-600 hover:bg-red-700 animate-pulse";
    case "BURNED":
      return "bg-gray-700 hover:bg-gray-800";
    case "WATER":
      return "bg-blue-500 hover:bg-blue-600";
    default:
      return "bg-gray-300";
  }
};

export function Grid() {
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    const fetchGrid = async () => {
      try {
        const response = await fetch("http://localhost:8000/grid");
        const data = await response.json();
        setGridData(data);
        setLoading(false);
      } catch (error) {
        console.error("Failed to fetch grid:", error);
        setLoading(false);
      }
    };

    fetchGrid();
    if (!isPaused) {
      const interval = setInterval(fetchGrid, 200); // Fetch every 200ms
      return () => clearInterval(interval);
    }
  }, [isPaused]);

  if (loading) {
    return <div className="text-white text-center py-8">Loading simulation...</div>;
  }

  if (!gridData) {
    return <div className="text-white text-center py-8">Failed to load grid</div>;
  }

  // Create a 2D array from the flat cells array
  const grid: (Cell | null)[][] = Array(GRID_SIZE)
    .fill(null)
    .map(() => Array(GRID_SIZE).fill(null));

  gridData.cells.forEach((cell) => {
    if (cell.row < GRID_SIZE && cell.col < GRID_SIZE) {
      grid[cell.row][cell.col] = cell;
    }
  });

  return (
    <div className="flex flex-col items-center justify-start gap-3 p-4 bg-gray-900 rounded-xl w-full h-full overflow-hidden">
      <h2 className="text-xl font-bold text-white">Forest Fire Simulation</h2>

      <div className="flex gap-2">
        <button
          onClick={() => setIsPaused(!isPaused)}
          className="px-4 py-1 bg-yellow-600 hover:bg-yellow-700 text-white font-bold rounded-lg transition text-sm"
        >
          {isPaused ? "▶ Resume" : "⏸ Pause"}
        </button>
      </div>

      <div
        className="border-2 border-yellow-500 bg-black p-1 flex-shrink-0"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${GRID_SIZE}, ${CELL_SIZE}px)`,
          gap: "1px",
          backgroundColor: "#000",
        }}
      >
        {grid.map((row, rowIdx) =>
          row.map((cell, colIdx) => (
            <div
              key={`${rowIdx}-${colIdx}`}
              className={`${
                cell ? getColorForSymbol(cell.symbol_type) : "bg-gray-400"
              } border border-gray-800 transition-colors duration-100`}
              style={{
                width: `${CELL_SIZE}px`,
                height: `${CELL_SIZE}px`,
              }}
              title={`(${rowIdx}, ${colIdx}) - ${cell?.symbol_type || "EMPTY"}`}
            />
          ))
        )}
      </div>

      <div className="grid grid-cols-4 gap-2 text-white text-xs">
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-green-600"></div>
          <span>Trees</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-red-600 animate-pulse"></div>
          <span>Fire</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-gray-700"></div>
          <span>Burned</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 bg-blue-500"></div>
          <span>Water</span>
        </div>
      </div>
    </div>
  );
}
