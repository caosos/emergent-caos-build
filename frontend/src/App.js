import "@/App.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { MemoryWorkbench } from "@/components/MemoryWorkbench";

function App() {
  return (
    <div className="App" data-testid="app-root">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MemoryWorkbench />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
