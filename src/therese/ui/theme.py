"""
Thème THERESE CLI.

Couleurs :
- THERESE : Bleu Blanc Rouge (drapeau français)
- CLI : Orange (Mistral)
"""

# CSS Textual pour THERESE
THERESE_CSS = """
/* === Thème THERESE === */
/* Bleu Blanc Rouge + Orange Mistral */

Screen {
    background: #0D1117;
}

/* Header avec le logo */
#header {
    dock: top;
    height: 3;
    background: #161B22;
    border-bottom: solid #30363D;
    padding: 0 2;
}

#logo {
    color: #0055A4;  /* Bleu */
    text-style: bold;
}

#logo-t {
    color: #0055A4;  /* Bleu - T */
}

#logo-h {
    color: #0055A4;  /* Bleu - H */
}

#logo-e1 {
    color: #FFFFFF;  /* Blanc - E */
}

#logo-r {
    color: #FFFFFF;  /* Blanc - R */
}

#logo-e2 {
    color: #EF4135;  /* Rouge - E */
}

#logo-s {
    color: #EF4135;  /* Rouge - S */
}

#logo-e3 {
    color: #EF4135;  /* Rouge - E */
}

#logo-cli {
    color: #FF7000;  /* Orange Mistral */
    text-style: bold;
}

/* Zone de conversation */
#conversation {
    height: 1fr;
    background: #0D1117;
    padding: 1 2;
    overflow-y: auto;
}

/* Messages */
.message {
    margin: 1 0;
    padding: 1 2;
    background: #161B22;
    border: solid #30363D;
}

.message-user {
    background: #1C2128;
    border: solid #0055A4;
}

.message-assistant {
    background: #161B22;
    border: solid #FF7000;
    min-height: 5;
}

.message-tool {
    background: #1C2128;
    border: solid #3FB950;
}

.message-header {
    color: #7D8590;
    text-style: bold;
    margin-bottom: 1;
}

.message-content {
    color: #E6EDF3;
    width: 100%;
}

/* Markdown doit wrapper le texte - même les URLs longues */
Markdown {
    width: 100%;
    overflow: hidden;
}

/* Force le wrap des lignes longues (URLs, etc.) */
Markdown Static {
    text-overflow: fold;
}

MarkdownH1, MarkdownH2, MarkdownH3, MarkdownParagraph {
    width: 100%;
    text-overflow: fold;
}

MarkdownBulletList, MarkdownOrderedList {
    width: 100%;
    padding-left: 2;
}

/* Bloc code - aussi fold pour les longues lignes */
MarkdownFence {
    text-overflow: fold;
    overflow-x: hidden;
}

/* Code blocks */
.code-block {
    background: #0D1117;
    border: solid #30363D;
    padding: 1;
    margin: 1 0;
}

/* Zone de saisie expandable */
#input-area {
    dock: bottom;
    height: auto;
    min-height: 5;
    max-height: 14;
    background: #161B22;
    border-top: solid #30363D;
    padding: 1 2;
}

#input {
    background: #0D1117;
    border: solid #30363D;
    padding: 0 1;
    height: auto;
    min-height: 3;
    max-height: 10;
    color: #E6EDF3;
}

#input:focus {
    border: solid #FF7000;
}

/* Status bar */
#status {
    dock: bottom;
    height: 1;
    background: #161B22;
    color: #7D8590;
    padding: 0 2;
}

#model-name {
    color: #FF7000;
}

#working-dir {
    color: #0055A4;
}

/* Spinner / Loading */
.loading {
    color: #FF7000;
}

/* Footer */
#footer {
    dock: bottom;
    height: 1;
    background: #0D1117;
    color: #7D8590;
    text-align: center;
}

/* Message command */
.message-command {
    background: #1C2128;
    border: solid #D29922;
}

/* Grand logo */
#big-logo {
    padding: 1 2;
    margin-bottom: 1;
    text-align: center;
}

/* Chain of Thought (raisonnement Magistral) */
.streaming-cot {
    background: #1a1f29;
    border: dashed #0055A4;
    padding: 1 2;
    margin: 1 0;
    color: #7D8590;
}
"""
