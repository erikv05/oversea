const isDevelopment = window.location.hostname === 'localhost';

export const WS_URL = isDevelopment 
  ? 'ws://localhost:8000/ws' 
  : `wss://${window.location.host}/api/ws`;

export const API_URL = isDevelopment 
  ? 'http://localhost:8000' 
  : '/api';