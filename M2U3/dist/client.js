"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const compression_1 = __importDefault(require("compression"));
const helmet_1 = __importDefault(require("helmet"));
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const app = (0, express_1.default)();
const PORT = 8080;
const sitePath = path_1.default.join(process.cwd(), 'site');
console.log('Current directory:', process.cwd());
console.log('Site path:', sitePath);
console.log('Site exists:', fs_1.default.existsSync(sitePath));
if (fs_1.default.existsSync(sitePath)) {
    console.log('Found site files');
    console.log('Files:', fs_1.default.readdirSync(sitePath));
    app.use(express_1.default.static(sitePath));
    app.get('/', (req, res) => {
        const indexPath = path_1.default.join(sitePath, 'index.html');
        if (fs_1.default.existsSync(indexPath)) {
            res.sendFile(indexPath);
        }
        else {
            const htmlFiles = fs_1.default.readdirSync(sitePath).filter(f => f.toLowerCase().endsWith('.html'));
            if (htmlFiles.length > 0) {
                res.sendFile(path_1.default.join(sitePath, htmlFiles[0]));
            }
            else {
                res.send('No HTML files found');
            }
        }
    });
}
else {
    console.log('Site not found at:', sitePath);
    app.get('/', (req, res) => {
        res.send('CORS Proxy running. Site not mounted.');
    });
}
app.use((0, helmet_1.default)());
app.use((0, compression_1.default)());
const limiter = (0, express_rate_limit_1.default)({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: 'Too many requests'
});
app.use('/proxy/*', limiter);
app.set('etag', 'strong');
app.get('/proxy/*', async (req, res) => {
    try {
        const urlPath = req.params[0];
        if (!urlPath) {
            return res.status(400).json({ error: 'URL is required' });
        }
        const targetUrl = `https://${urlPath}`;
        console.log('Proxy fetching:', targetUrl);
        const response = await fetch(targetUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        // Получаем HTML как текст
        const html = await response.text();
        // Устанавливаем правильные заголовки
        res.set({
            'Content-Type': 'text/html; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        });
        // Отправляем HTML как есть
        res.send(html);
    }
    catch (error) {
        console.error('Proxy error:', error);
        res.status(500).json({
            error: error.message || 'Unknown error',
            timestamp: new Date().toISOString()
        });
    }
});
app.get('/health', (req, res) => {
    res.json({
        status: 'OK',
        timestamp: new Date().toISOString(),
        service: 'cors-proxy'
    });
});
app.listen(PORT, () => {
    console.log(`Server started on port ${PORT}`);
});
