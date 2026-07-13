# CUMCM 2025 format baseline

Source: user-supplied `format2025.doc`, titled *全国大学生数学建模竞赛论文格式规范（2025 年修订稿）*.

SHA-256 of the supplied source file:

```text
65974bb5e4f3219e548ac2aeb69c0c21399985c49d541c1d939b1210ef9c2be2
```

The executable requirements used by Shumo are:

1. A4 paper, with each margin at least 2.5 cm.
2. For paper submission, the commitment page and numbering page precede the abstract; for electronic submission they are excluded.
3. The electronic paper begins with the abstract page. The title, abstract and keywords fit on one page.
4. Page numbers begin at 1 on the abstract page and appear in the center footer.
5. The body begins on the next page, contains no table of contents and should normally be controlled within 20 pages.
6. Appendices follow the body and may exceed the body page target.
7. Appendices include the support-material file list and all complete runnable source programs used in modeling.
8. The electronic paper is one PDF or Word file; Shumo standardizes on PDF and enforces a 20 MB limit.
9. No identity, school or region information appears in the abstract, body, appendix or support materials.
10. All external sources are cited according to scientific-paper conventions.
11. The electronic and paper versions must be consistent.
12. More recent official rules and applicable AI-tool rules override older conflicting requirements.

The class `skills/math_modeling/templates/latex/shumo-cumcm2025.cls` implements the page geometry, page numbering, Chinese typography, caption policy and core equation numbering convention used by the Skill.
