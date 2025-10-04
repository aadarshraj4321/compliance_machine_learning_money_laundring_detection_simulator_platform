import axios from 'axios';

// Get the API key from the frontend's environment variables.
// In React with Vite, these variables MUST start with VITE_ to be exposed to the browser.
const API_KEY = 'sdfsdfgsdgfsdasfasdasdAAADSDOIUJKJHKJhkjahsdhkjahsdhasdkUYJKJh1232132JKKJhk$$%@!'; 

// Define the base URL for all API calls.
const API_BASE_URL = 'http://localhost:8000';

// Check if the API key is missing. This is a helpful warning during development.
if (!API_KEY) {
  console.error("CRITICAL ERROR: VITE_API_KEY is not defined in your frontend/.env file.");
  alert("Frontend API Key is missing. The application will not work. Please check the console.");
}

// Create a new instance of axios with our custom configuration.
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // This is the most important part.
    // We add the secret API key to a custom header for every single request.
    'X-API-Key': API_KEY 
  }
});

/**
 * This is an "interceptor". It's an advanced feature of axios that lets us
 * "intercept" every response before it goes back to our components.
 * This is a great place to handle errors globally.
 */
apiClient.interceptors.response.use(
  // If the response is successful (e.g., status 200), just return it as is.
  (response) => response,
  
  // If the response has an error...
  (error) => {
    // Log a detailed error message to the developer console.
    console.error(
      'API Call Failed:', 
      error.response?.config?.method.toUpperCase(),
      error.response?.config?.url,
      error.response?.status,
      error.response?.data
    );
    
    // You could add global error handling here, for example:
    // if (error.response?.status === 401) {
    //   alert("Authentication failed. Please check your API Key.");
    // }
    
    // It's crucial to return a rejected promise so that the .catch()
    // block in our components will still work.
    return Promise.reject(error);
  }
);

// Export the configured client so other parts of our app can use it.
export default apiClient;