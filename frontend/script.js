const models = ["message"];
const templates = {};

nunjucks.configure({ autoescape: true });

for (const model of models) {
    fetch(`/templates/${model}.html`).then((response) => {
        return response.text();
    }).then((body) => {
        templates[model] = body;
        console.log(body);
    });
}

function renderModelRow(name, row) {
    return nunjucks.renderString(templates[name], { row });
}

function handleSearchChange(event) {
    var query = {
        "query": $(event.target).val(),
        "limit": 25,
    };

    fetch('/search/message', {
        method: 'POST',
        body: JSON.stringify(query),
    }).then((response) => {
        return response.json();
    }).then((data) => {
        console.log("[Debug]", data._debug);

        if (data.results) {
            var html = "";

            for (const row of data.results) {
                html = html + renderModelRow('message', row)
            }
            $("#results").html(html);
            // $("#results").text(JSON.stringify(data.results), null, 2);
        } else if (data.error) {
            console.error(data)
        }
    });
}

$(document).ready(function () {
    var val = $("#search").val();
    $("#search").focus().val("").val(val);
    $("#search").keyup((e) => {
        if (e.keyCode == 13) {
            handleSearchChange(e);
        }
    });
});