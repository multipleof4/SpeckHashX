// Two pages: the home page and the 404 page that Cloudflare Pages serves for unknown paths.
export default { build: { rolldownOptions: { input: ['index.html', '404.html'] } } }
