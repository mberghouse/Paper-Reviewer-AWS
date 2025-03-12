import React from 'react';
import { createRoot } from 'react-dom/client';
import App from '../../../react_app.jsx';

const root = createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
); 