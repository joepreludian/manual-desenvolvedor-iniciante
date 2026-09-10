// Converte cada bloco <pre><code class="language-xxx"> em um editor Ace editável,
// com botões "Copiar" e "Restaurar". Se o Ace não carregar (sem internet),
// nada acontece e o <pre> original continua visível.
(function () {
  if (typeof ace === "undefined") return;

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
      theme: "ace/theme/tomorrow",
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
