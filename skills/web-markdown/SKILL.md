---
name: web-markdown
description: Add Markdown parsing and rendering to web applications. Use when the user wants to render Markdown content, build a Markdown editor with live preview, display user-generated Markdown safely, or integrate a Markdown library (marked.js, markdown-it, react-markdown, @uiw/react-md-editor, vue-markdown-it) into a vanilla JS, React, Vue, or other frontend project. Relevant phrases include showing a live preview while typing, rendering README content, adding a rich text editor, sanitizing HTML from Markdown, and preventing XSS in rendered Markdown.
---

# Web Markdown

Guide for adding Markdown parsing and rendering to web apps.

## Library Selection

Choose by environment:

| Context | Recommended | Notes |
|---|---|---|
| Vanilla JS / HTML | `marked` + `DOMPurify` | Lightweight, CDN-friendly |
| React (render) | `react-markdown` + `rehype-sanitize` | React-native, remark/rehype pipeline |
| React (editor) | `@uiw/react-md-editor` | Editor + preview in one component |
| Vue | `vue-markdown-it` or `markdown-it` + manual render | SSR-compatible |
| Node.js (SSR) | `markdown-it` | Most configurable, plugin-rich |

For install commands, config snippets, and a decision checklist, see [references/library-guide.md](references/library-guide.md).

## Security: Always Sanitize

Markdown parsers produce raw HTML. **Never inject unsanitized HTML into the DOM**; it enables XSS.

- Vanilla JS: pipe `marked` output through `DOMPurify.sanitize()` before setting `innerHTML`
- React: `react-markdown` is safe by default; add `rehype-sanitize` if `rehype-raw` is enabled
- Vue: sanitize with `dompurify` before binding to `v-html`

For threat model, DOMPurify config options, Node.js alternative (`sanitize-html`), and CSP headers, see [references/security.md](references/security.md).

## Live Preview Editor Pattern

For any framework:
1. Bind a `<textarea>` (or controlled input) to state
2. On each change, parse the Markdown string to HTML
3. Render the HTML into a preview pane

Debounce the parse call (100–200 ms) to avoid blocking on every keystroke.

### Vanilla JS

```html
<textarea id="src"></textarea>
<div id="preview"></div>
<script type="module">
  import { marked } from 'https://cdn.jsdelivr.net/npm/marked/src/marked.esm.js';
  import DOMPurify from 'https://cdn.jsdelivr.net/npm/dompurify/dist/purify.es.mjs';
  const src = document.getElementById('src');
  const preview = document.getElementById('preview');
  src.addEventListener('input', () => {
    preview.innerHTML = DOMPurify.sanitize(marked.parse(src.value));
  });
</script>
```

### React (read-only render)

```jsx
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

export function MarkdownRenderer({ content }) {
  return <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>;
}
```

### Vue 3 (live preview)

```vue
<script setup>
import { ref, computed } from 'vue';
import MarkdownIt from 'markdown-it';
import DOMPurify from 'dompurify';

const md = new MarkdownIt();
const source = ref('');
const rendered = computed(() => DOMPurify.sanitize(md.render(source.value)));
</script>

<template>
  <textarea v-model="source" />
  <div v-html="rendered" />
</template>
```

## Styling Rendered Markdown

Parsed Markdown is plain semantic HTML. Apply styles via:
- A scoped wrapper class (e.g., `.prose`) with descendant selectors (`h1`, `p`, `code`, etc.)
- **Tailwind CSS**: `@tailwindcss/typography` plugin with the `prose` class
- GitHub-style: `github-markdown-css` on npm/CDN

## Common Enhancements

- **Syntax highlighting**: `highlight.js` or `prism.js`; React uses `react-syntax-highlighter`
- **Math rendering**: `remark-math` + `rehype-katex` (React) or `markdown-it-katex`
- **Mermaid diagrams**: `mermaid.js` post-processes fenced code blocks tagged ` ```mermaid `
- **Tables / footnotes / task lists**: enabled by default in `markdown-it`; opt-in via `marked` extensions or `remark-gfm`
