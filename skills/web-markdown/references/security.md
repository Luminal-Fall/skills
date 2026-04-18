# Markdown Security Reference

## Threat Model

Markdown parsers convert Markdown to HTML. If that HTML is injected into the DOM without sanitization:

- An attacker-controlled Markdown string (e.g., user comments, form inputs) can embed `<script>`, event handlers (`onload=`, `onerror=`), `javascript:` hrefs, or `data:` URIs
- This results in stored or reflected XSS, capable of stealing session cookies or hijacking the page

**Always sanitize HTML output before setting `innerHTML`**, unless using a library that renders to React/virtual DOM elements.

## DOMPurify (Browser)

The standard sanitizer for browser environments.

```js
import DOMPurify from 'dompurify';

// Default: strips scripts, event handlers, dangerous URIs
const clean = DOMPurify.sanitize(dirtyHtml);
element.innerHTML = clean;
```

**Restrict to a safe tag allowlist**:

```js
const clean = DOMPurify.sanitize(dirtyHtml, {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'a', 'blockquote', 'h1', 'h2', 'h3'],
  ALLOWED_ATTR: ['href', 'title'],
  ALLOW_DATA_ATTR: false,
});
```

**Force safe external links** (open in new tab, add rel):

```js
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});
```

## sanitize-html (Node.js / SSR)

For server-side rendering where DOMPurify is unavailable:

```js
import sanitizeHtml from 'sanitize-html';

const clean = sanitizeHtml(dirtyHtml, {
  allowedTags: sanitizeHtml.defaults.allowedTags.concat(['img']),
  allowedAttributes: {
    a: ['href', 'title', 'target'],
    img: ['src', 'alt'],
  },
});
```

## rehype-sanitize (React / remark pipeline)

When using `react-markdown`, add as a rehype plugin:

```jsx
import rehypeSanitize from 'rehype-sanitize';

// GitHub-equivalent default schema
<ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
```

Only required when `rehype-raw` is also enabled (which allows raw HTML passthrough). Without `rehype-raw`, `react-markdown` is safe by default.

## Content Security Policy (CSP)

Add a CSP header to limit damage even if a sanitizer is bypassed:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;
```

- Omit `unsafe-inline` for `script-src` entirely — Markdown content should never inject `<script>` tags
- For inline styles from syntax highlighters (e.g., highlight.js), use a nonce or hash instead of `unsafe-inline` in `style-src`

## Quick Checklist

- [ ] Using `marked` or `markdown-it` output? → Pipe through DOMPurify or sanitize-html before setting `innerHTML`
- [ ] Using Vue `v-html`? → Sanitize before binding
- [ ] Using `react-markdown` with `rehype-raw`? → Add `rehype-sanitize`
- [ ] External links in Markdown? → Add `rel="noopener noreferrer"` and `target="_blank"`
- [ ] Serving user-generated Markdown? → Add a CSP header
