# 本地材料结构

将用户提供的二进制材料按以下结构放置，目录整体由 `.gitignore` 排除：

```text
tests/case002/local/problem/
├── official/
│   ├── A题.pdf
│   └── attachments/
│       ├── result1.xlsx
│       ├── result2.xlsx
│       └── result3.xlsx
└── guidance/
    ├── 完整过程.docx
    ├── 建模过程.docx
    ├── 论文撰写.docx
    └── 论文模板.docx
```

文件身份以 `source_manifest.yaml` 中的 SHA-256 为准。Office 自动生成的临时锁文件不纳入材料。
