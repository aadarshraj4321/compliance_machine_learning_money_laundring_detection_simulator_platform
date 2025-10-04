import React, { useState } from 'react';
import axios from 'axios';
import { Box, Paper, Typography, Button, Alert, LinearProgress, Stack, Link, Checkbox, FormControlLabel } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { Link as RouterLink } from 'react-router-dom';

const DataIngestionPage = () => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [jobStatus, setJobStatus] = useState({ message: '', type: '' });
    const [clearData, setClearData] = useState(true);

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
        setJobStatus({ message: '', type: '' });
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            setJobStatus({ message: 'Please select a file first.', type: 'error' });
            return;
        }

        setIsUploading(true);
        
        try {
            if (clearData) {
                setJobStatus({ message: 'Clearing all existing data...', type: 'info' });
                await axios.post('http://localhost:8000/ingest/clear-all-data');
                setJobStatus({ message: 'Data cleared. Now uploading file...', type: 'info' });
            } else {
                setJobStatus({ message: 'Uploading and appending data...', type: 'info' });
            }

            const formData = new FormData();
            formData.append('file', selectedFile);

            const response = await axios.post('http://localhost:8000/ingest/upload-csv', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            
            setJobStatus({ 
                message: `Upload successful! Processing has started in the background. Check the dashboard in a few minutes. (Job ID: ${response.data.job_id})`, 
                type: 'success'
            });
        } catch (error) {
            const errorMessage = error.response?.data?.detail || 'An unknown error occurred.';
            setJobStatus({ message: `An error occurred: ${errorMessage}`, type: 'error' });
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <Paper sx={{ p: 4, maxWidth: '800px', mx: 'auto' }}>
            <Typography variant="h4" gutterBottom>Real Data Ingestion</Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
                Upload a CSV file containing transaction data. The system will create new user entities and run all compliance checks.
            </Typography>

            <Stack spacing={2} alignItems="center">
                <Button
                    component="label"
                    variant="outlined"
                    fullWidth
                    startIcon={<CloudUploadIcon />}
                    sx={{ height: '120px', borderStyle: 'dashed', flexDirection: 'column' }}
                    disabled={isUploading}
                >
                    <Typography variant="h6">{selectedFile ? `File: ${selectedFile.name}` : 'Click to Select a CSV File'}</Typography>
                    <Typography variant="caption">(.csv format required)</Typography>
                    <input type="file" hidden accept=".csv" onChange={handleFileChange} />
                </Button>

                <FormControlLabel
                    control={
                        <Checkbox
                            checked={clearData}
                            onChange={(e) => setClearData(e.target.checked)}
                            name="clearDataCheckbox"
                            color="primary"
                        />
                    }
                    label="Clear all existing investigation data before uploading"
                    sx={{ alignSelf: 'flex-start' }}
                />

                <Button
                    onClick={handleUpload}
                    disabled={!selectedFile || isUploading}
                    variant="contained"
                    size="large"
                    sx={{ width: '100%', py: 1.5 }}
                >
                    {isUploading ? <CircularProgress size={24} /> : 'Upload and Analyze'}
                </Button>

                {jobStatus.message && (
                    <Alert severity={jobStatus.type || 'info'} sx={{ width: '100%' }}>
                        {jobStatus.message}
                        {jobStatus.type === 'success' && 
                            <Link component={RouterLink} to="/" sx={{display: 'block', mt: 1, fontWeight: 'bold'}}>
                                Go to Dashboard to see results
                            </Link>
                        }
                    </Alert>
                )}
            </Stack>
        </Paper>
    );
};

export default DataIngestionPage;