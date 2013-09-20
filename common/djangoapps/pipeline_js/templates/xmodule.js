## This file is designed to load all the XModule Javascript files in one wad
## using requirejs. It is passed through the Mako template system, which
## populates the `urls` variable with a list of paths to XModule JS files.
## These files assume that several libraries are available and bound to
## variables in the global context, so we load those libraries with requirejs
## and attach them to the global context manually.
define(["jquery", "youtube", "mathjax", "codemirror", "tinymce", "jquery.tinymce"],
       function($, YT, MathJax, CodeMirror, tinyMCE) {
    window.$ = $;
    window.YT = YT;
    window.MathJax = MathJax;
    window.CodeMirror = CodeMirror;
    window.tinyMCE = tinyMCE;
    window.RequireJS = {
        'requirejs': requirejs,
        'require': require,
        'define': define
    };

    var urls = ${urls};
    var head = $("head");
    $.each(urls, function(i, url) {
        head.append($("<script/>", {src: url}));
    });
    return window.XModule;
});
