import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const embeddedStaticRoots = {
  '/ppt/': path.resolve(__dirname, '../img/ppt'),
  '/mind-map-wizard/': path.resolve(__dirname, '../img/mind-map-wizard'),
  '/video-search/': path.resolve(__dirname, '../img/video-search'),
  '/vendor/': path.resolve(__dirname, 'public/vendor'),
}

const vendoredAssetsDir = path.resolve(__dirname, 'public/vendor')

function vendoredAssets(dir = vendoredAssetsDir) {
  if (!fs.existsSync(dir)) return []
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = path.join(dir, entry.name)
    return entry.isDirectory() ? vendoredAssets(absolutePath) : [absolutePath]
  })
}

const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.otf': 'font/otf',
  '.png': 'image/png',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.ttf': 'font/ttf',
  '.webp': 'image/webp',
}

function createJsonResponse(res, statusCode, payload) {
  res.statusCode = statusCode
  res.setHeader('Content-Type', 'application/json')
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.end(typeof payload === 'string' ? payload : JSON.stringify(payload))
}

function readBackendEnv() {
  const envPath = path.resolve(__dirname, '../backend/.env')
  try {
    const content = fs.readFileSync(envPath, 'utf8')
    return Object.fromEntries(
      content
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line && !line.startsWith('#') && line.includes('='))
        .map((line) => {
          const separatorIndex = line.indexOf('=')
          return [line.slice(0, separatorIndex).trim(), line.slice(separatorIndex + 1).trim()]
        }),
    )
  } catch {
    return {}
  }
}

function createEmbeddedStaticPlugin() {
  let isBuild = false

  return {
    name: 'embedded-static-pages',
    configResolved(config) {
      isBuild = config.command === 'build'
    },
    buildStart() {
      if (!isBuild) return
      [
        ['vendor', vendoredAssetsDir],
      ].forEach(([outputDirectory, sourceDirectory]) => {
        vendoredAssets(sourceDirectory).forEach((absolutePath) => {
          const relativePath = path.relative(sourceDirectory, absolutePath).split(path.sep).join('/')
          this.emitFile({
            type: 'asset',
            fileName: `${outputDirectory}/${relativePath}`,
            source: fs.readFileSync(absolutePath),
          })
        })
      })
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const requestUrl = new URL(req.url || '/', 'http://localhost')
        const match = Object.entries(embeddedStaticRoots).find(([prefix]) => requestUrl.pathname.startsWith(prefix))
        if (!match) {
          next()
          return
        }

        const [prefix, rootDir] = match
        const relativePath = decodeURIComponent(requestUrl.pathname.slice(prefix.length)) || 'index.html'
        const requestedPath = relativePath.endsWith('/') ? `${relativePath}index.html` : relativePath
        const filePath = path.resolve(rootDir, requestedPath)

        if (!filePath.startsWith(rootDir)) {
          res.statusCode = 403
          res.end('Forbidden')
          return
        }

        fs.stat(filePath, (statError, stats) => {
          if (statError || !stats.isFile()) {
            res.statusCode = 404
            res.end('Not Found')
            return
          }

          res.setHeader('Content-Type', mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream')
          fs.createReadStream(filePath).pipe(res)
        })
      })
    },
  }
}

function createVideoSearchProxy() {
  return {
    name: 'video-search-proxy',
    configureServer(server) {
      server.middlewares.use('/api-cover', async (req, res) => {
        try {
          const requestUrl = new URL(req.url || '', 'http://localhost')
          const rawUrl = requestUrl.searchParams.get('url')
          if (!rawUrl) {
            res.statusCode = 400
            res.end('Missing url')
            return
          }

          const imageUrl = new URL(rawUrl)
          const allowedHosts = ['hdslb.com', 'bilibili.com', 'biliimg.com']
          if (!allowedHosts.some((host) => imageUrl.hostname === host || imageUrl.hostname.endsWith(`.${host}`))) {
            res.statusCode = 400
            res.end('Unsupported image host')
            return
          }

          const proxyRes = await fetch(imageUrl, {
            headers: {
              Referer: 'https://www.bilibili.com/',
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
              Accept: 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            },
          })
          const arrayBuffer = await proxyRes.arrayBuffer()
          res.statusCode = proxyRes.status
          res.setHeader('Content-Type', proxyRes.headers.get('content-type') || 'image/jpeg')
          res.setHeader('Cache-Control', 'public, max-age=86400')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.end(Buffer.from(arrayBuffer))
        } catch (error) {
          res.statusCode = 500
          res.end(error.message)
        }
      })

      server.middlewares.use('/api-bili', async (req, res) => {
        const targetUrl = `https://api.bilibili.com${req.url}`
        try {
          const proxyRes = await fetch(targetUrl, {
            headers: {
              Referer: 'https://search.bilibili.com',
              Origin: 'https://search.bilibili.com',
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
              Accept: 'application/json',
              Cookie: 'buvid3=infoc',
            },
          })
          createJsonResponse(res, proxyRes.status, await proxyRes.text())
        } catch (error) {
          createJsonResponse(res, 500, { error: error.message })
        }
      })

    },
  }
}

export default defineConfig({
  plugins: [
    createEmbeddedStaticPlugin(),
    vue({
      template: {
        compilerOptions: {
          isCustomElement: tag => tag.startsWith('wokwi-'),
        },
      },
    }),
    createVideoSearchProxy(),
  ],
  publicDir: '../img',
  server: {
    host: '0.0.0.0',
    port: 5088,
    strictPort: true,
    proxy: {
      '/ppt-api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
        rewrite: requestPath => requestPath.replace(/^\/ppt-api/, '/api'),
      },
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
    fs: {
      allow: ['..'],
    },
  },
})
