# Markdown Library Guide

## marked (v14+)

- **Install**: `npm install marked` or via CDN `https://cdn.jsdelivr.net/npm/marked/marked.min.js`
- **Size**: ~25 KB minified
- **Output**: HTML string — requires external sanitization (DOMPurify)
- **Config**:
  ```js
  import { marked } from 'marked';
  marked.setOptions({ gfm: true, breaks: false });
  const html = marked.parse('# Hello');
  ```
- **Best for**: lightweight vanilla JS, CDN-only pages, simple static sites

## markdown-it (v14+)

- **Install**: `npm install markdown-it`
- **Size**: ~45 KB; plugin ecosystem adds weight
- **Output**: HTML string — requires sanitization
- **Config**:
  ```js
  import MarkdownIt from 'markdown-it';
  const md = new MarkdownIt({ html: false, linkify: true, typographer: true });
  const html = md.render('# Hello');
  ```
- **Popular plugins**: `markdown-it-footnote`, `markdown-it-task-lists`, `markdown-it-abbr`
- **Best for**: Node.js SSR, plugin-heavy pipelines, Vue

## react-markdown (v9+)

- **Install**: `npm install react-markdown`
- **Output**: React elements — no `dangerouslySetInnerHTML`, XSS-safe by default
- **Pipeline**: remark (AST) → rehype (HAST) → React
- **Basic**:
  ```jsx
  import ReactMarkdown from 'react-markdown';
  <ReactMarkdown>{markdownString}</ReactMarkdown>
  ```
- **With GFM + sanitization**:
  ```jsx
  import remarkGfm from 'remark-gfm';
  import rehypeSanitize from 'rehype-sanitize';
  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
    {content}
  </ReactMarkdown>
  ```
- **Best for**: React apps rendering content (blog posts, docs, READMEs)

## @uiw/react-md-editor

- **Install**: `npm install @uiw/react-md-editor`
- **Features**: split editor/preview pane, toolbar, fullscreen, dark mode
- **Basic**:
  ```jsx
  import MDEditor from '@uiw/react-md-editor';
  import '@uiw/react-md-editor/markdown-editor.css';

  const [value, setValue] = useState('');
  <MDEditor value={value} onChange={setValue} />
  <MDEditor.Markdown source={value} />
  ```
- **Best for**: React CMS interfaces, note-taking apps, comment boxes needing an interactive editor

## vue-markdown-it

- **Install**: `npm install vue-markdown-it`
- **Usage**:
  ```vue
  <script setup>
  import VueMarkdownIt from 'vue-markdown-it';
  </script>
  <template>
    <vue-markdown-it :source="markdownString" />
  </template>
  ```
- **Best for**: Vue 3 apps needing read-only Markdown rendering with minimal setup

## Decision Checklist

1. React app, read-only rendering? → `react-markdown` (+ `rehype-sanitize`)
2. React app, needs an editor UI? → `@uiw/react-md-editor`
3. Vue app? → `vue-markdown-it` or `markdown-it` + manual render
4. Plain HTML/JS or CDN-only? → `marked` + `DOMPurify` via CDN
5. Node.js SSR or needs advanced plugins (math, footnotes, custom tokens)? → `markdown-it`
