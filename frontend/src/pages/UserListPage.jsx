import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link as RouterLink } from 'react-router-dom';
import { 
    Grid, 
    Card, 
    CardContent, 
    Typography, 
    Alert, 
    Box, 
    CircularProgress, 
    Link,
    TextField,
    InputAdornment
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

const UserCard = ({ user }) => (
    <Grid item xs={12} sm={6} md={4}>
        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', transition: '0.3s', '&:hover': { transform: 'scale(1.03)', boxShadow: 6 } }}>
            <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" component="h2" gutterBottom>
                    <Link component={RouterLink} to={`/users/${user.id}`} underline="hover" color="inherit">
                        {user.full_name}
                    </Link>
                </Typography>
                <Typography color="text.secondary" sx={{ mb: 1.5 }}>
                    {user.email}
                </Typography>
                <Typography variant="body2">
                    Country: <strong>{user.country}</strong>
                </Typography>
            </CardContent>
        </Card>
    </Grid>
);

const UserListPage = () => {
    const [allUsers, setAllUsers] = useState([]);
    const [filteredUsers, setFilteredUsers] = useState([]);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        axios.get('http://localhost:8000/api/v1/users')
            .then(response => {
                setAllUsers(response.data);
                setFilteredUsers(response.data);
            })
            .catch(err => {
                console.error("Failed to fetch users:", err);
                setError('Failed to load user data from the server.');
            })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        const results = allUsers.filter(user =>
            user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            user.email.toLowerCase().includes(searchTerm.toLowerCase())
        );
        setFilteredUsers(results);
    }, [searchTerm, allUsers]);

    if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}><CircularProgress /></Box>;

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom>User Dashboard</Typography>
            <TextField
                fullWidth
                label="Search Users by Name or Email"
                variant="outlined"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                sx={{ mb: 4 }}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchIcon />
                        </InputAdornment>
                    ),
                }}
            />
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            
            <Grid container spacing={3}>
                {filteredUsers.length > 0 ? (
                    filteredUsers.map(user => <UserCard key={user.id} user={user} />)
                ) : (
                    <Grid item xs={12}>
                        <Typography>No users found matching your search.</Typography>
                    </Grid>
                )}
            </Grid>
        </Box>
    );
};

export default UserListPage;