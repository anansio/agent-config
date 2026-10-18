---
name: docs-rules
description: Conventions for document files such as Markdown, reStructuredText, and AsciiDoc. Loaded automatically when writing or editing documentation.
paths:
  - "**/*.md"
  - "**/*.mdx"
  - "**/*.rst"
  - "**/*.adoc"
---

# Documentation Rules

Write for a reader who does not have your context and did not follow the
discussion that produced the document.

- Describe the thing as it is now. Avoid words that only fit this moment or this
  conversation, like "new", "old", "currently", "our".
- Do not write context-dependent negatives such as "we no longer use X". Say
  what is true; a later reader will not know what the old thing was.
- Aim for something easy to scan: headings, short paragraphs, lists where they
  help.
