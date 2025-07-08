const isDevelopment = window.location.hostname === 'localhost';

// Replace with your actual Cloud Run service URL after deployment
const GCP_WEBSOCKET_URL = 'wss://oversea-backend-uymqysezzq-uc.a.run.app/ws';

export const WS_URL = isDevelopment 
  ? 'ws://localhost:8000/ws' 
  : GCP_WEBSOCKET_URL;

export const API_URL = isDevelopment 
  ? 'http://localhost:8000' 
  : GCP_WEBSOCKET_URL.replace('wss://', 'https://').replace('/ws', '');