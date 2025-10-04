import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link as RouterLink } from 'react-router-dom';
import UserListPage from './pages/UserListPage';
import UserDetailPage from './pages/UserDetailPage';
import DataIngestionPage from './pages/DataIngestionPage'; // Import the new page
import { 
    ThemeProvider, 
    createTheme, 
    CssBaseline, 
    Container, 
    AppBar, 
    Toolbar, 
    Typography, 
    Link, 
    Box,
    Button // Import Button
} from '@mui/material';
import LanIcon from '@mui/icons-material/Lan';
import CloudUploadIcon from '@mui/icons-material/CloudUpload'; // Import the upload icon

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#90caf9' },
    secondary: { main: '#f48fb1' },
    background: { default: '#121212', paper: '#1e1e1e' },
  },
  typography: { fontFamily: 'Roboto, Arial, sans-serif' },
});

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <AppBar position="static" color="default" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Toolbar>
              <LanIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                <Link component={RouterLink} to="/" sx={{ textDecoration: 'none', color: 'inherit' }}>
                  AI Compliance Simulator
                </Link>
              </Typography>
              
              {/* --- NEW BUTTON ADDED HERE --- */}
              <Button 
                component={RouterLink} 
                to="/ingest" 
                color="inherit" 
                variant="outlined"
                startIcon={<CloudUploadIcon />}
              >
                Ingest Real Data
              </Button>

            </Toolbar>
          </AppBar>
          
          <Container component="main" maxWidth="xl" sx={{ flexGrow: 1, py: 4 }}>
            <Routes>
              <Route path="/" element={<UserListPage />} />
              <Route path="/users/:userId" element={<UserDetailPage />} />
              {/* --- NEW ROUTE ADDED HERE --- */}
              <Route path="/ingest" element={<DataIngestionPage />} />
            </Routes>
          </Container>

          <Box component="footer" sx={{ p: 2, mt: 'auto', backgroundColor: '#121212' }}>
            <Typography variant="body2" color="text.secondary" align="center">
              Compliance Simulator © 2025
            </Typography>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;