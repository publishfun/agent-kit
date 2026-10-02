# From LaTeX to a submission

The API and MCP take Markdown only. Convert first:

```
pandoc -f latex -t gfm --wrap=none paper.tex -o paper.md
```

Then check the output: math stays as `$...$` / `$$...$$`; figures become
`![caption](file.png)`. Upload each figure (`POST /api/uploads/images` or the
MCP `upload_image` tool) and replace the local paths with the returned URLs,
or point them at images already hosted over https. Put title, authors,
abstract and keywords in the metadata fields, not in the body.
