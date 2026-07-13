\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{shumo-cumcm2025}[2026/07/13 Shumo CUMCM 2025 electronic-paper class]
\LoadClass[UTF8,zihao=-4,a4paper]{ctexart}

\RequirePackage[a4paper,top=2.5cm,bottom=2.5cm,left=2.5cm,right=2.5cm,headheight=14pt]{geometry}
\RequirePackage{fontspec}
\RequirePackage{xeCJK}
\RequirePackage{amsmath,amssymb,mathtools,bm}
\RequirePackage{booktabs,tabularx,longtable,array,multirow}
\RequirePackage{graphicx,float,caption,subcaption}
\RequirePackage{tikz}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,calc,fit}
\RequirePackage{enumitem}
\RequirePackage{fancyhdr}
\RequirePackage{hyperref}
\RequirePackage{cleveref}
\RequirePackage{siunitx}
\RequirePackage{xcolor}
\RequirePackage{listings}
\RequirePackage{microtype}
\RequirePackage{setspace}
\RequirePackage{etoolbox}

\setmainfont{Liberation Serif}
\setsansfont{Liberation Sans}
\setmonofont{DejaVu Sans Mono}
\setCJKmainfont{Noto Serif CJK SC}
\setCJKsansfont{Noto Sans CJK SC}
\setCJKmonofont{Noto Sans Mono CJK SC}

\setstretch{1.28}
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt}
\setlength{\abovedisplayskip}{6pt plus 2pt minus 2pt}
\setlength{\belowdisplayskip}{6pt plus 2pt minus 2pt}
\setlength{\textfloatsep}{10pt plus 2pt minus 2pt}
\setlength{\floatsep}{8pt plus 2pt minus 2pt}
\setlength{\intextsep}{8pt plus 2pt minus 2pt}

\ctexset{
  section = {
    name = {,、},
    number = \chinese{section},
    format = \centering\heiti\zihao{3},
    beforeskip = 1.1ex plus .2ex,
    afterskip = .8ex plus .2ex
  },
  subsection = {
    number = \arabic{section}.\arabic{subsection},
    format = \heiti\zihao{4},
    beforeskip = .9ex plus .2ex,
    afterskip = .5ex plus .1ex
  },
  subsubsection = {
    number = \arabic{section}.\arabic{subsection}.\arabic{subsubsection},
    format = \heiti\zihao{-4},
    beforeskip = .7ex plus .2ex,
    afterskip = .3ex plus .1ex
  }
}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\thepage}
\pagenumbering{arabic}

\captionsetup{font=small,labelsep=quad,justification=centering,singlelinecheck=false}
\captionsetup[table]{position=top,skip=4pt}
\captionsetup[figure]{position=bottom,skip=4pt}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}
\crefname{figure}{图}{图}
\crefname{table}{表}{表}
\crefname{equation}{式}{式}
\crefname{section}{节}{节}
\numberwithin{equation}{section}

\sisetup{detect-all,group-separator={,},group-minimum-digits=4,round-mode=places,round-precision=3}
\hypersetup{unicode=true,colorlinks=false,pdfborder={0 0 0}}
\urlstyle{same}

\newcommand{\papertitle}[1]{%
  \begin{center}
    {\heiti\zihao{2}\bfseries #1\par}
  \end{center}
  \vspace{0.8em}
}

\newenvironment{cnabstract}{%
  \begin{center}{\heiti\zihao{3}\bfseries 摘\quad 要}\end{center}
  \vspace{0.2em}
  \zihao{-4}
}{\par}

\newcommand{\keywords}[1]{%
  \par\vspace{0.6em}\noindent\textbf{关键词：}#1
}

\newcommand{\keyequation}[2]{%
  \begin{equation}\label{#1}#2\end{equation}
}

\newcolumntype{Y}{>{\centering\arraybackslash}X}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}

\lstdefinestyle{shumopython}{
  language=Python,
  basicstyle=\ttfamily\zihao{6},
  keywordstyle=\bfseries,
  commentstyle=\itshape,
  numbers=left,
  numberstyle=\tiny,
  numbersep=6pt,
  frame=single,
  breaklines=true,
  columns=fullflexible,
  showstringspaces=false,
  tabsize=4,
  captionpos=b
}
\lstset{style=shumopython}

\AtBeginEnvironment{longtable}{\zihao{5}}
\AtBeginEnvironment{tabular}{\zihao{5}}
\AtBeginEnvironment{tabularx}{\zihao{5}}
