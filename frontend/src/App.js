import "@/App.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { CaosShell } from "@/components/caos/CaosShell";

function App() {
  return (
    <div className="App" data-testid="app-root">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<CaosShell />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" theme="dark" richColors closeButton />
    </div>
  );
}

export default App;
