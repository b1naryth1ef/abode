const models = ["message"];
const templates = {};

const env = nunjucks.configure({ autoescape: true });
env.addFilter("discrim", (str) => {
    return ('0000' + str).slice(-4);
});

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

const currentModel = "message";

function handleSearchChange(event) {
    var query = {
        "query": $(event.target).val(),
        "limit": 250,
    };

    fetch(`/search/${currentModel}`, {
        method: 'POST',
        body: JSON.stringify(query),
    }).then((response) => {
        return response.json();
    }).then((data) => {
        console.log("[Debug]", data._debug);

        if (data.results[currentModel]) {
            var html = "";

            for (const idx in data.results[currentModel]) {
                let rowData = data.results[currentModel][idx];

                Object.keys(data.results).map((model) => {
                    if (model == currentModel) {
                        return;
                    }
                    Object.assign(rowData, { [model]: data.results[model][idx] });
                });

                html = html + renderModelRow('message', rowData);
            }
            $("#results").html(html);
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