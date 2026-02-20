/**
 * Main entry point for the Web UI
 * Provides routing, theme (light/dark), and text-size controls.
 */
import React, { useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes, Link } from 'react-router-dom';
import {
  AppBar,
  Box,
  Container,
  CssBaseline,
  IconButton,
  Toolbar,
  Tooltip,
  Typography,
  createTheme,
  ThemeProvider,
} from '@mui/material';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import TextDecreaseIcon from '@mui/icons-material/TextDecrease';
import TextIncreaseIcon from '@mui/icons-material/TextIncrease';
import MainMenu from './MainMenu';
import KeysetsPage from './KeysetsPage';

const App: React.FC = () => {
  const [mode, setMode] = useState<'light' | 'dark'>('light');
  const [textSizeDelta, setTextSizeDelta] = useState<number>(0);

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: { main: '#1976d2' },
          secondary: { main: '#dc004e' },
          background: {
            default: mode === 'dark' ? '#0f172a' : '#f5f5f5',
            paper: mode === 'dark' ? '#1e293b' : '#ffffff',
          },
        },
        typography: {
          fontFamily: ['Roboto', 'Arial', 'sans-serif'].join(','),
          fontSize: 14 + textSizeDelta,
        },
      }),
    [mode, textSizeDelta]
  );

  const handleToggleMode = () => setMode((prev) => (prev === 'light' ? 'dark' : 'light'));
  const handleTextSizeDelta = (delta: number) =>
    setTextSizeDelta((prev) => Math.min(6, Math.max(-2, prev + delta)));

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppBar position="static" color="primary" enableColorOnDark>
          <Toolbar sx={{ display: 'flex', gap: 2 }}>
            <Typography variant="h6" component={Link} to="/" color="inherit" sx={{ textDecoration: 'none' }}>
              AI Typing Trainer
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Tooltip title="Decrease text size">
              <span>
                <IconButton color="inherit" onClick={() => handleTextSizeDelta(-2)} aria-label="decrease text size">
                  <TextDecreaseIcon />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Increase text size">
              <span>
                <IconButton color="inherit" onClick={() => handleTextSizeDelta(2)} aria-label="increase text size">
                  <TextIncreaseIcon />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={mode === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
              <IconButton color="inherit" onClick={handleToggleMode} aria-label="toggle theme">
                {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Routes>
            <Route path="/" element={<MainMenu />} />
            <Route path="/keysets" element={<KeysetsPage />} />
          </Routes>
        </Container>
      </BrowserRouter>
    </ThemeProvider>
  );
};

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found in the document');
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
