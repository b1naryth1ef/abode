const models = ["message", "emoji", "channel", "guild", "user"];
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

function handleSearchChange(event) {
    var currentModel = $("#model option:selected").text();
    var query = {
        "query": $(event.target).val(),
        "limit": 250,
        "order_by": "id",
        "order_dir": "DESC",
    };

    fetch(`/search/${currentModel}`, {
        method: 'POST',
        body: JSON.stringify(query),
    }).then((response) => {
        return response.json();
    }).then((data) => {
        console.log("[Debug]", data);

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

                console.log(rowData);
                html = html + renderModelRow(currentModel, rowData);
            }
            $("#results").html(html);
        } else if (data.error) {
            console.error(data)
        }
    });
}

$(document).ready(function () {
    for (model of models) {
        $("#model").append(`<option value="${model}">${model}</option>`);
    }

    var val = $("#search").val();
    $("#search").focus().val("").val(val);
    $("#search").keyup((e) => {
        if (e.keyCode == 13) {
            handleSearchChange(e);
        }
    });
});