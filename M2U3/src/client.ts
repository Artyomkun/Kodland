import { corsFetch } from 'corsbridge';
import express from 'express';
import compression from 'compression';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import path from 'path';
import fs from 'fs';

const app = express();
const PORT = 8080;

const sitePath = path.join(process.cwd(), 'site');

console.log('Current directory:', process.cwd());
console.log('Site path:', sitePath);
console.log('Site exists:', fs.existsSync(sitePath));

if (fs.existsSync(sitePath)) {
    console.log('Found site files');
    console.log('Files:', fs.readdirSync(sitePath));
    
    app.use(express.static(sitePath));
    
    app.get('/', (req, res) => {
        const indexPath = path.join(sitePath, 'index.html');
        if (fs.existsSync(indexPath)) {
            res.sendFile(indexPath);
        } else {
            const htmlFiles = fs.readdirSync(sitePath).filter(f => f.toLowerCase().endsWith('.html'));
            if (htmlFiles.length > 0) {
                res.sendFile(path.join(sitePath, htmlFiles[0]));
            } else {
                res.send('No HTML files found');
            }
        }
    });
} else {
    console.log('Site not found at:', sitePath);
    app.get('/', (req, res) => {
        res.send('CORS Proxy running. Site not mounted.');
    });
}

app.use(helmet());
app.use(compression());

const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: 'Too many requests'
});
app.use('/proxy/*', limiter);

app.set('etag', 'strong');

app.get('/proxy/*', async (req, res) => {
  try {
    const urlPath = (req.params as { [key: string]: string })[0];
      if (!urlPath) {
          return res.status(400).json({ error: 'URL is required' });
      }

      // === ИСПРАВЛЕНИЕ: Сохраняем query параметры ===
      const originalUrl = req.originalUrl;
      let queryString = '';
      
      // Извлекаем query параметры из оригинального URL
      if (originalUrl.includes('?')) {
          queryString = originalUrl.substring(originalUrl.indexOf('?'));
      }
      
      const targetUrl = `https://${urlPath}${queryString}`;
      console.log('Proxy fetching:', targetUrl);
      console.log('URL Path:', urlPath);
      console.log('Query String:', queryString);

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
      
  } catch (error: any) {
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