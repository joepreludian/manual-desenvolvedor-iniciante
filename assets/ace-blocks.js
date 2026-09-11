// Converte cada bloco <pre><code class="language-xxx"> em um editor Ace editável,
// com botões "Copiar" e "Restaurar". Se o Ace não carregar (sem internet),
// nada acontece e o <pre> original continua visível.
(function () {
  if (typeof ace === "undefined") return;

  // Tema "vscode_dark": aproximação do Dark+ do VS Code.
  ace.define("ace/theme/vscode_dark", ["require", "exports", "module", "ace/lib/dom"], function (require, exports) {
    exports.isDark = true;
    exports.cssClass = "ace-vscode-dark";
    exports.cssText = [
      ".ace-vscode-dark .ace_gutter { background: #1e1e1e; color: #858585; }",
      ".ace-vscode-dark .ace_print-margin { width: 1px; background: #2b2b2b; }",
      ".ace-vscode-dark { background-color: #1e1e1e; color: #d4d4d4; }",
      ".ace-vscode-dark .ace_cursor { color: #aeafad; }",
      ".ace-vscode-dark .ace_marker-layer .ace_selection { background: #264f78; }",
      ".ace-vscode-dark .ace_marker-layer .ace_active-line { background: #282828; }",
      ".ace-vscode-dark .ace_gutter-active-line { background-color: #282828; }",
      ".ace-vscode-dark .ace_marker-layer .ace_selected-word { border: 1px solid #3a3d41; }",
      ".ace-vscode-dark .ace_marker-layer .ace_bracket { margin: -1px 0 0 -1px; border: 1px solid #888; }",
      ".ace-vscode-dark .ace_invisible { color: #404040; }",
      ".ace-vscode-dark .ace_keyword, .ace-vscode-dark .ace_meta, .ace-vscode-dark .ace_storage, .ace-vscode-dark .ace_storage.ace_type { color: #569cd6; }",
      ".ace-vscode-dark .ace_keyword.ace_control, .ace-vscode-dark .ace_keyword.ace_operator.ace_flow { color: #c586c0; }",
      ".ace-vscode-dark .ace_keyword.ace_operator { color: #d4d4d4; }",
      ".ace-vscode-dark .ace_constant, .ace-vscode-dark .ace_constant.ace_language { color: #569cd6; }",
      ".ace-vscode-dark .ace_constant.ace_numeric { color: #b5cea8; }",
      ".ace-vscode-dark .ace_constant.ace_character, .ace-vscode-dark .ace_constant.ace_other { color: #ce9178; }",
      ".ace-vscode-dark .ace_string, .ace-vscode-dark .ace_string.ace_regexp { color: #ce9178; }",
      ".ace-vscode-dark .ace_comment { color: #6a9955; font-style: italic; }",
      ".ace-vscode-dark .ace_support.ace_function, .ace-vscode-dark .ace_entity.ace_name.ace_function { color: #dcdcaa; }",
      ".ace-vscode-dark .ace_support.ace_type, .ace-vscode-dark .ace_support.ace_class, .ace-vscode-dark .ace_entity.ace_name.ace_type { color: #4ec9b0; }",
      ".ace-vscode-dark .ace_support.ace_constant { color: #569cd6; }",
      ".ace-vscode-dark .ace_variable, .ace-vscode-dark .ace_variable.ace_parameter, .ace-vscode-dark .ace_entity.ace_other.ace_attribute-name { color: #9cdcfe; }",
      ".ace-vscode-dark .ace_variable.ace_language { color: #569cd6; }",
      ".ace-vscode-dark .ace_entity.ace_name.ace_tag { color: #569cd6; }",
      ".ace-vscode-dark .ace_invalid { color: #f44747; background: transparent; }",
      ".ace-vscode-dark .ace_indent-guide { background: linear-gradient(to right, #404040 1px, transparent 1px) left repeat-y; background-size: 1px 100%; }"
    ].join("\n");
    var dom = require("ace/lib/dom");
    dom.importCssString(exports.cssText, exports.cssClass, false);
  });

  var modes = {
    bash: "sh", sh: "sh", zsh: "sh", shell: "sh", console: "sh",
    python: "python", py: "python",
    html: "html", css: "css", javascript: "javascript", js: "javascript",
    json: "json", yaml: "yaml", yml: "yaml", sql: "sql", markdown: "markdown", md: "markdown",
    text: "text", txt: "text", "": "text"
  };

  function langOf(code) {
    var m = (code.className || "").match(/(?:^|\s)(?:language-|sourceCode\s+)?([a-zA-Z0-9]+)/g) || [];
    for (var i = 0; i < m.length; i++) {
      var name = m[i].trim().replace(/^language-/, "").replace(/^sourceCode\s+/, "");
      if (name !== "sourceCode" && modes[name] !== undefined) return name;
    }
    return "";
  }

  var blocks = document.querySelectorAll("pre > code");
  Array.prototype.forEach.call(blocks, function (code) {
    var pre = code.parentNode;
    if (pre.classList.contains("mermaid")) return;
    var lang = langOf(code);
    var original = code.textContent.replace(/\n$/, "");

    var wrap = document.createElement("div");
    wrap.className = "ace-block";

    var bar = document.createElement("div");
    bar.className = "ace-toolbar";
    bar.innerHTML =
      '<span class="lang">' + (lang || "texto") + "</span>" +
      '<span class="spacer"></span>' +
      '<button type="button" data-act="copy">Copiar</button>' +
      '<button type="button" data-act="reset">Restaurar</button>';

    var host = document.createElement("div");
    host.className = "ace-editor";

    wrap.appendChild(bar);
    wrap.appendChild(host);
    pre.parentNode.replaceChild(wrap, pre);

    var editor = ace.edit(host, {
      mode: "ace/mode/" + (modes[lang] || "text"),
      theme: "ace/theme/vscode_dark",
      value: original,
      minLines: 2,
      maxLines: 40,
      showPrintMargin: false,
      highlightActiveLine: false,
      fontSize: 14,
      tabSize: 4,
      useSoftTabs: true
    });
    editor.renderer.setScrollMargin(6, 6, 0, 0);

    bar.addEventListener("click", function (ev) {
      var act = ev.target && ev.target.getAttribute("data-act");
      if (act === "copy") {
        var text = editor.getValue();
        var done = function () { ev.target.textContent = "Copiado!"; setTimeout(function () { ev.target.textContent = "Copiar"; }, 1200); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done);
        else { editor.selectAll(); document.execCommand("copy"); done(); }
      } else if (act === "reset") {
        editor.setValue(original, -1);
      }
    });
  });
})();
