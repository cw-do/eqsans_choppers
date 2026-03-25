% !TEX root = chopper_calibration_guide_ornl.tex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% File: ornltm.cls (Minimal version for environments without LaTeX packages)
% Original Authors: Seth R Johnson, Sam Crawford,* and John Batson
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\NeedsTeXFormat{LaTeX2e}[1995/12/01]
\ProvidesClass{ornltm}[2018/10/13 ORNL Technical Memorandum class]

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% OPTIONS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newif\if@tm
\newif\if@spr
\newif\if@ltr

\DeclareOption{tm}{\@tmtrue}
\DeclareOption{spr}{\@sprtrue}
\DeclareOption{ltr}{\@ltrtrue}

\ProcessOptions\relax

\if@tm
\else
  \if@spr
  \else
    \if@ltr
    \else
      \@tmtrue
    \fi
  \fi
\fi

\LoadClass[11pt,letterpaper]{article}

\renewcommand{\today}{\ifcase \month \or January\or February\or March\or %
April\or May \or June\or July\or August\or September\or October\or November\or %
December\fi~\number \year}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% STYLING
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\RequirePackage{fancyhdr}
\RequirePackage[pdfusetitle]{hyperref}
\RequirePackage{longtable}
\RequirePackage{array}
\RequirePackage{color}
\RequirePackage{graphicx}

% Simplified abbreviation support (replaces acro package)
\newcommand{\DeclareAcronym}[2]{}
\newcommand{\ac}[1]{#1}
\newcommand{\Acs}[1]{#1}
\newcommand{\Ac}[1]{#1}
\newcommand{\acl}[1]{#1}
\newcommand{\Acl}[1]{#1}
\newcommand{\acresetall}{}
\newcommand{\printacronyms}{}

% Load document style
\RequirePackage{ornltm-style}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% VARIABLES
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newif\if@divisiondefined
\@divisiondefinedfalse
\def\@division{DIVISION NAME UNDEFINED%
\PackageWarning{ornltm}{No division name has been defined.}}
\newcommand{\division}[1]{\def\@division{#1}\@divisiondefinedtrue}

\newif\if@reportnumdefined
\@reportnumdefinedfalse
\def\@reportnum{ORNL/XX-XXXX/XXX%
\PackageWarning{ornltm}{No report number has been defined.}}
\newcommand{\reportnum}[1]{\def\@reportnum{#1}\@reportnumdefinedtrue}

\newif\if@sponsornumdefined
\@sponsornumdefinedfalse
\def\@sponsornum{}
\newcommand{\sponsornum}[1]{\def\@sponsornum{#1}\@sponsornumdefinedtrue}

\newif\if@reportdraft
\@reportdraftfalse
\newcommand{\reportdraft}{\@reportdrafttrue}

\def\@affiliation{\relax}
\newcommand{\affiliation}[1]{\def\@affiliation{#1}}
\newcommand{\affilnum}[1]{\texorpdfstring{\textsuperscript{#1}}{}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% PRINT AUTHORS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand\printauthors{%
  \begingroup
  \parskip=0pt
  \parindent=0pt
  \leavevmode\noindent
  \newcount\auth@count \auth@count=0
  \def\auth@break{\unskip\hfil\break}%
  \def\auth@do##1\and##2\auth@end{%
    \advance\auth@count by 1\relax
    \ifnum\auth@count<5
      ##1%
      \if\relax\detokenize{##2}\relax
      \else
        \auth@break
        \expandafter\auth@do##2\auth@end
      \fi
    \else
      ##1%
      \if\relax\detokenize{##2}\relax
      \else
        \unskip\space et al.%
      \fi
    \fi
  }%
  \expandafter\auth@do\@author\and\auth@end
  \par\endgroup
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% DEFINE COLORS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand{\textbsf}[1]{{\bfseries\sffamily #1}}
\newcommand{\textbi}[1]{{\bfseries\itshape #1}}
\definecolor{ornlgreen}{RGB}{0,121,52}
\definecolor{ornldarkgreen}{RGB}{52,118,60}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% COVER PAGE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\fancypagestyle{coverpage}{\renewcommand\headrulewidth{0pt}\fancyhf{}}

\newcommand{\@restrictfootwarning}[1]{%
  \vspace{-2\baselineskip}\par
  \makebox[\textwidth][c]{\textbsf{#1}}\par
}

\newsavebox{\titlebox}
\newcommand{\fittitle}[2][\textwidth]{%
  \sbox{\titlebox}{\parbox{#1}{\Huge\textbsf{\@title}}}%
  \ifdim\dimexpr\ht\titlebox+\dp\titlebox\relax>#2\relax
    \makebox[#1][l]{\resizebox{!}{#2}{\usebox{\titlebox}}}%
  \else
    \usebox{\titlebox}%
  \fi
}

\newcommand{\maxsizebox}[4]{#4}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% HEADERS AND FOOTERS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\pagestyle{fancy}
\fancyhead{}
\fancyfoot{}
\cfoot{\thepage{}}

\fancypagestyle{plain}
\fancyhead{}
\fancyfoot{}
\cfoot{\thepage{}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% TECHNICAL MEMO (TM) OPTION
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\if@tm
\def\makecoverpage{%
\newgeometry{top=0.25in,bottom=0.25in,right=1.00in,left=1.00in}

\begin{titlepage}
\thispagestyle{coverpage}

% Green banner at top
\noindent\colorbox{ornlgreen}{\parbox{\dimexpr\textwidth+2\fboxsep}{\vspace{0.3in}\centering\color{white}\Huge\textbsf{OAK RIDGE NATIONAL LABORATORY}\vspace{0.1in}}}

\vspace{0.3in}

%% REPORT NUMBER %%
\begin{minipage}{\textwidth}
\flushleft
\textcolor{ornlgreen}{\large\textbsf{\@reportnum}}
\end{minipage}

%% TITLE %%
\vspace{0.5in}
\begin{minipage}[c][1in][c]{\textwidth}
  \fittitle[\textwidth]{0.60in}
\end{minipage}

\vspace{2in}

%%% AUTHOR AND DATE %%%
\begin{minipage}[c][3in][t]{2.5in}%
\large\sffamily
\printauthors
\vspace*{1\baselineskip \@plus 1\baselineskip \@minus 1\baselineskip}
\large\textbsf{\@date}
\end{minipage}%

\begin{minipage}[c][3.05in][c]{4.00in}%
\if@reportdraft
  \begin{center}
  \textbsf{\normalsize Draft. Document has not been reviewed and approved for public release.}%
  \end{center}
  \vspace{1em}
\fi
\end{minipage}

\vspace{0.60in}
\noindent{\footnotesize\textbsf{ORNL is managed by UT-Battelle LLC for the US~Department of Energy}}

\end{titlepage}
\restoregeometry
}%

\newcommand\backmatter{%
  \clearpage%
  \thispagestyle{plain}%
  \setcounter{page}{0}%
  \renewcommand\thepage{Back cover}%
\begin{titlepage}
\noindent\colorbox{ornlgreen}{\parbox{\dimexpr\textwidth+2\fboxsep}{\vspace{8in}}}
\end{titlepage}
}%

\fi

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% TITLE PAGE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newcommand\maketitlepage{%
\begin{titlepage}
\setcounter{page}{2}%

\raggedleft{\large\textbf{\@reportnum}}
\vspace{1in}

\centering\@division
\vspace{\stretch{1}}

\begin{minipage}{\textwidth}%
\begin{center}
  \Large\textbf{\MakeUppercase{\@title}}
\end{center}
\end{minipage}%

\vspace{\stretch{1}}

\renewcommand{\affilnum}[1]{}%
\def\and{\tabularnewline}%
\begin{tabular}[t]{c}%
  \@author
\end{tabular}%

\vspace{\stretch{.5}}

\@date

\vspace{\stretch{.5}}

Prepared by \\
OAK RIDGE NATIONAL LABORATORY \\
Oak Ridge, TN 37831 \\
managed by \\
UT-BATTELLE LLC \\
for the \\
US DEPARTMENT OF ENERGY \\
under contract DE-AC05-00OR22725

\end{titlepage}%
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% FRONT MATTER
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newif\if@mainmatter
\@mainmattertrue
\def\@cleariffrontmatter{\if@mainmatter\relax\else{\clearpage}\fi}
\def\@cleardbliffrontmatter{\if@mainmatter\relax\else{\cleardoublepage}\fi}

\newcommand\frontmatter{%
  \@mainmatterfalse%
  \renewcommand\and{\\}
  \renewcommand\thepage{Front cover}%
  \makecoverpage%
  \pagenumbering{roman}%
  \setcounter{page}{1}%
  \maketitlepage%
  \cleardoublepage
  \setcounter{page}{3}%
}

\newenvironment{foreword}{%
	\addcontentsline{toc}{section}{FOREWORD}
	\phantomsection
  \section*{FOREWORD}%
}

\renewenvironment{abstract}{%
\if@mainmatter\relax\else
  \cleardoublepage
	\pagenumbering{arabic}
	\setcounter{page}{1}
\fi
	\addcontentsline{toc}{section}{ABSTRACT}
	\phantomsection
  \section*{ABSTRACT}%
}{}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% MAIN MATTER
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand\mainmatter{%
  \cleardoublepage%
  \@mainmattertrue%
  \pagenumbering{arabic}%
  \renewcommand{\sectionbreak}{\renewcommand\sectionbreak\cleardoublepage}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% CAPTION STYLES
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\RequirePackage[font=bf,labelsep=period,justification=centering]{caption}

\newcommand\longcaption[2]{\caption[#1]{#1 \normalfont #2}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\endinput
