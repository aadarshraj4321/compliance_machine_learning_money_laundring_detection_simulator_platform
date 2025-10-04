import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { 
    Box, 
    Card, 
    CardContent, 
    Typography, 
    Grid, 
    Paper, 
    Table, 
    TableBody, 
    TableCell, 
    TableContainer, 
    TableHead, 
    TableRow, 
    Alert as MuiAlert, 
    CircularProgress, 
    Divider, 
    Button, 
    Stack, 
    Chip,
    TextField,
    Snackbar,
    Modal,
    Fade,
    Backdrop,
    IconButton
} from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LanIcon from '@mui/icons-material/Lan';
import GavelIcon from '@mui/icons-material/Gavel';
import CloseIcon from '@mui/icons-material/Close';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AssessmentIcon from '@mui/icons-material/Assessment';

// AlertCard Component - Displays a single alert
const AlertCard = ({ alert }) => (
    <Paper elevation={2} sx={{ p: 2, mb: 2, borderLeft: 5, borderColor: alert.alert_type.includes('GRAPH') ? 'error.main' : 'warning.main' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="h6" component="div">{alert.alert_type}</Typography>
            <Chip label={alert.status} color={alert.status === 'OPEN' ? 'error' : 'success'} size="small" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, wordBreak: 'break-word' }}>
            <strong>Finding:</strong> {alert.message}
        </Typography>
        <Divider sx={{ my: 1.5, borderColor: 'rgba(255, 255, 255, 0.2)' }} />
        <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
            <strong>AI Summary:</strong> {alert.ai_summary || "Not available."}
        </Typography>
        <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1, textAlign: 'right' }}>
            {new Date(alert.created_at).toLocaleString()}
        </Typography>
    </Paper>
);

// Main Page Component
const UserDetailPage = () => {
    const { userId } = useParams();
    const [dossier, setDossier] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [actionStates, setActionStates] = useState({ kyc: false, graph: false, advising: false });
    const [graphOpen, setGraphOpen] = useState(false);
    const [graphData, setGraphData] = useState(null);
    const [isPolling, setIsPolling] = useState(false);
    const [advisorModalOpen, setAdvisorModalOpen] = useState(false);
    const [advisorResponse, setAdvisorResponse] = useState('');
    const [advisorTitle, setAdvisorTitle] = useState('');
    const [newTxAmount, setNewTxAmount] = useState('');
    const [newTxDesc, setNewTxDesc] = useState('Manual Deposit');
    const [snackbarOpen, setSnackbarOpen] = useState(false);
    const [snackbarMessage, setSnackbarMessage] = useState('');

    const showSnackbar = (message) => { setSnackbarMessage(message); setSnackbarOpen(true); };

    const fetchDossier = useCallback(async (showLoading = true) => {
        if(showLoading) setLoading(true);
        try {
            const [userRes, alertsRes, txsRes] = await Promise.all([
                axios.get(`http://localhost:8000/api/v1/users/${userId}`),
                axios.get(`http://localhost:8000/api/v1/users/${userId}/alerts`),
                axios.get(`http://localhost:8000/api/v1/users/${userId}/transactions`),
            ]);
            setDossier({ profile: userRes.data, alerts: alertsRes.data, transactions: txsRes.data });
        } catch (err) { setError(`Failed to load data for user ${userId}.`); } 
        finally { if(showLoading) setLoading(false); }
    }, [userId]);

    useEffect(() => { fetchDossier(); }, [fetchDossier]);

    // --- ALL HANDLER FUNCTIONS ARE NOW PRESENT ---

    const handleRunKyc = async () => {
        setActionStates(prev => ({ ...prev, kyc: true }));
        showSnackbar('KYC check initiated...');
        try {
            await axios.post(`http://localhost:8000/api/v1/users/${userId}/run-kyc-check`);
            setTimeout(() => { fetchDossier(false); showSnackbar('KYC check complete.'); }, 3000);
        } catch (err) { showSnackbar('KYC check failed.'); } 
        finally { setTimeout(() => setActionStates(prev => ({ ...prev, kyc: false })), 3000); }
    };


    const handleRunGraphAnalysis = async () => {
    setActionStates(prev => ({ ...prev, graph: true }));
    setIsPolling(true);
    setGraphData(null);
    setGraphOpen(true);
    
    try {
        // Step 1: Start the job (THIS WAS MISSING!)
        const startRes = await axios.post(`http://localhost:8000/api/v1/users/${userId}/run-graph-analysis`);
        // Wait 2 seconds before polling to allow DB entry to be created
        await new Promise(resolve => setTimeout(resolve, 2000));

        const { job_id } = startRes.data;

        // Step 2: Start polling for the result
        const poll = (retries = 20) => {
            // Stop trying after 40 seconds (20 retries * 2 seconds)
            if (retries === 0) {
                setIsPolling(false);
                setActionStates(prev => ({...prev, graph: false}));
                setGraphData({ error: "Analysis timed out. The task is taking too long." });
                return;
            }
            
            // Poll the unified results endpoint
            axios.get(`http://localhost:8000/api/v1/results/${job_id}`)
                .then(res => {
                    // Check if the task is complete
                    if (res.data.status === 'SUCCESS' || res.data.status === 'COMPLETED' || res.data.status === 'FAILED') {
                        // Check if the result is for a graph
                        if (res.data.result_type === 'graph') {
                            setGraphData(res.data.result);
                        } else {
                            // Handle cases where the result is not a graph (e.g., an error)
                            setGraphData({ error: "Received an unexpected result type from the server." });
                        }
                        setIsPolling(false);
                        setActionStates(prev => ({ ...prev, graph: false }));
                        fetchDossier(false); // Refresh alerts on the main page in the background
                    } else {
                        // If status is PENDING or RUNNING, wait and poll again
                        setTimeout(() => poll(retries - 1), 2000);
                    }
                })
                .catch(() => {
                    // If there's a network error or 404, just try again
                    setTimeout(() => poll(retries - 1), 2000);
                });
        };

        // Start the first poll
        poll();

    } catch (err) {
        console.error("Failed to start graph analysis task:", err);
        setIsPolling(false);
        setActionStates(prev => ({ ...prev, graph: false }));
        setGraphData({ error: "Could not start the analysis job." });
    }
};

    const handleAdvisorAction = async (actionType) => {
        setActionStates(prev => ({ ...prev, advising: true }));
        setAdvisorResponse('');
        setAdvisorTitle(actionType === 'explain' ? 'AI Risk Profile Analysis' : 'DRAFT: Suspicious Activity Report');
        setAdvisorModalOpen(true);
        const endpoint = actionType === 'explain' ? `/api/v1/advisor/explain-risk/${userId}` : `/api/v1/advisor/generate-sar/${userId}`;
        try {
            const res = await axios.get(`http://localhost:8000${endpoint}`);
            setAdvisorResponse(actionType === 'explain' ? res.data.explanation : res.data.sar_draft);
        } catch (err) { setAdvisorResponse(`Error generating response.`); } 
        finally { setActionStates(prev => ({ ...prev, advising: false })); }
    };

    const handleAddTransaction = async (e) => {
        e.preventDefault();
        if (!newTxAmount || isNaN(parseFloat(newTxAmount))) { showSnackbar('Please enter a valid amount.'); return; }
        try {
            await axios.post(`http://localhost:8000/api/v1/users/${userId}/transactions`, { amount: parseFloat(newTxAmount), description: newTxDesc });
            setNewTxAmount('');
            showSnackbar('Transaction added! Analyzing patterns...');
            setTimeout(() => fetchDossier(false), 2000);
        } catch (err) { showSnackbar('Error adding transaction.'); }
    };

    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>;
    if (error) return <MuiAlert severity="error">{error}</MuiAlert>;
    if (!dossier) return <MuiAlert severity="warning">No user data found.</MuiAlert>;

    const { profile, alerts, transactions } = dossier;

    return (
        <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
                <AccountCircleIcon sx={{ fontSize: '4rem', mr: 2, color: 'primary.light' }} />
                <Box>
                    <Typography variant="h3" component="h1" fontWeight="bold">{profile.full_name}</Typography>
                    <Typography variant="h6" color="text.secondary">{profile.email}</Typography>
                </Box>
            </Box>

            <Grid container spacing={4}>
                <Grid item xs={12} lg={4}>
                    <Stack spacing={3}>
                        <Paper elevation={3} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>Identity Details</Typography><Divider sx={{ mb: 2 }} /><Typography><strong>Country:</strong> {profile.country}</Typography><Typography><strong>Member Since:</strong> {new Date(profile.created_at).toLocaleDateString()}</Typography></Paper>
                        <Paper elevation={3} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>Compliance Actions</Typography><Divider sx={{ mb: 2 }} /><Stack spacing={2}><Button size="large" startIcon={<GavelIcon />} onClick={handleRunKyc} disabled={actionStates.kyc}>{actionStates.kyc ? 'Processing...' : 'Run KYC Check'}</Button><Button size="large" startIcon={<LanIcon />} onClick={handleRunGraphAnalysis} disabled={actionStates.graph} variant="outlined" color="warning">{actionStates.graph ? 'Analyzing...' : 'Analyze Network'}</Button></Stack></Paper>
                        <Paper elevation={3} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>AI Advisor</Typography><Divider sx={{ mb: 2 }} /><Stack spacing={2}><Button size="large" startIcon={<SmartToyIcon />} onClick={() => handleAdvisorAction('explain')} disabled={actionStates.advising}>Explain Risk Profile</Button><Button size="large" startIcon={<AssessmentIcon />} onClick={() => handleAdvisorAction('sar')} variant="outlined" color="error" disabled={actionStates.advising}>Draft SAR</Button></Stack></Paper>
                        <Paper elevation={3} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>Add Manual Transaction</Typography><Divider sx={{ mb: 2 }} /><Box component="form" onSubmit={handleAddTransaction}><TextField label="Amount (INR)" type="number" value={newTxAmount} onChange={(e) => setNewTxAmount(e.target.value)} fullWidth margin="normal" required /><TextField label="Description" type="text" value={newTxDesc} onChange={(e) => setNewTxDesc(e.target.value)} fullWidth margin="normal" required /><Button type="submit" variant="contained" color="primary" fullWidth sx={{ mt: 1 }}>Add Transaction</Button></Box></Paper>
                    </Stack>
                </Grid>
                <Grid item xs={12} lg={8}>
                    <Stack spacing={3}>
                        <Paper elevation={3} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>Active Alerts ({alerts.length})</Typography><Divider sx={{ mb: 2 }} />{alerts.length > 0 ? (<Box sx={{ maxHeight: '40vh', overflowY: 'auto', pr: 1 }}>{alerts.map(alert => <AlertCard key={alert.id} alert={alert} />)}</Box>) : (<Typography color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>No active alerts for this user.</Typography>)}</Paper>
                        <Paper elevation={3} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>Transaction History ({transactions.length})</Typography><Divider sx={{ mb: 2 }} /><TableContainer sx={{ maxHeight: '40vh', overflowY: 'auto' }}><Table stickyHeader size="small"><TableHead><TableRow><TableCell>Date</TableCell><TableCell>Description</TableCell><TableCell align="right">Amount (INR)</TableCell></TableRow></TableHead><TableBody>{transactions.map(tx => (<TableRow key={tx.id} hover><TableCell>{new Date(tx.timestamp).toLocaleString()}</TableCell><TableCell>{tx.description}</TableCell><TableCell align="right">{tx.amount.toFixed(2)}</TableCell></TableRow>))}</TableBody></Table></TableContainer></Paper>
                    </Stack>
                </Grid>
            </Grid>
            
            <Snackbar open={snackbarOpen} autoHideDuration={4000} onClose={() => setSnackbarOpen(false)} message={snackbarMessage} />

            <Modal open={graphOpen} onClose={() => setGraphOpen(false)} closeAfterTransition slots={{ backdrop: Backdrop }} slotProps={{ backdrop: { timeout: 500 } }}>
                <Fade in={graphOpen}>
                    <Paper sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '90vw', height: '90vh', bgcolor: 'background.paper', p: 3, display: 'flex', flexDirection: 'column', borderRadius: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><Typography variant="h5">Transaction Network Analysis</Typography><IconButton onClick={() => setGraphOpen(false)}><CloseIcon /></IconButton></Box>
                        <Divider sx={{ my: 2 }} />
                        {isPolling && (<Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><CircularProgress /><Typography sx={{ ml: 2 }}>Analyzing...</Typography></Box>)}
                        {graphData && !isPolling && (
                            <Grid container spacing={2} sx={{ flexGrow: 1, height: 'calc(100% - 60px)' }}>
                                <Grid item xs={12} md={9} sx={{ height: '100%' }}>
                                    {graphData.plot_data ? (<Plot data={graphData.plot_data.data} layout={{...graphData.plot_data.layout, autosize: true, paper_bgcolor: '#1e1e1e', font: { color: 'white' } }} style={{ width: '100%', height: '100%' }} useResizeHandler config={{ responsive: true, displaylogo: false }} />) : (<Typography>Could not render graph. {graphData.error}</Typography>)}
                                </Grid>
                                <Grid item xs={12} md={3} sx={{ height: '100%', overflowY: 'auto' }}>
                                    <Typography variant="h6">AI Investigator's Report</Typography>
                                    <Paper sx={{ p: 2, mt: 1, backgroundColor: '#333' }}><Typography>{graphData.ai_explanation || "No AI explanation."}</Typography></Paper>
                                </Grid>
                            </Grid>
                        )}
                    </Paper>
                </Fade>
            </Modal>
            
            <Modal open={advisorModalOpen} onClose={() => setAdvisorModalOpen(false)}>
                <Fade in={advisorModalOpen}>
                    <Paper sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '60vw', maxWidth: '800px', maxHeight: '80vh', p: 4, display: 'flex', flexDirection: 'column' }}>
                        <Typography variant="h5" component="h2" gutterBottom>{advisorTitle}</Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Box sx={{ overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                            {actionStates.advising ? <Box sx={{ display: 'flex', alignItems: 'center' }}><CircularProgress size={24} sx={{ mr: 2 }} /><Typography>Generating response...</Typography></Box> : <Typography variant="body1" component="div">{advisorResponse}</Typography>}
                        </Box>
                    </Paper>
                </Fade>
            </Modal>
        </Box>
    );
};

export default UserDetailPage;