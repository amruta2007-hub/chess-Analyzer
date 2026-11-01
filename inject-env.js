/**
 * inject-env.js
 * Automatically executed during Netlify build to inject API_BASE_URL
 * into frontend/js/env.js.
 */
const fs = require('fs');
const path = require('path');

const apiBaseUrl = (process.env.API_BASE_URL || '').trim();

const targetDir = path.join(__dirname, 'frontend', 'js');
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

const targetFile = path.join(targetDir, 'env.js');

const fileContent = `/**
 * Runtime environment configuration injected at build/deploy time.
 * Configured via Netlify Environment Variable: API_BASE_URL
 */
window.ENV = window.ENV || {};
window.ENV.API_BASE_URL = "${apiBaseUrl.replace(/"/g, '\\"')}";
`;

fs.writeFileSync(targetFile, fileContent, 'utf8');
console.log(`[Netlify Build] Successfully wrote API_BASE_URL="${apiBaseUrl}" to ${targetFile}`);
