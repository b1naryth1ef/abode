const models = ["message", "emoji", "channel", "guild", "user"];
const templates = { "row": null };

const env = nunjucks.configure({ autoescape: true });
env.addFilter("discrim", (str) => {
    return ('0000' + str).slice(-4);
});

for (const model of Object.keys(templates).concat(models)) {
    fetch(`/templates/${model}.html`).then((response) => {
        return response.text();
    }).then((body) => {
        templates[model] = body;
        console.log(body);
    });
}

function split(str, separator, limit) {
    str = str.split(separator);

    if (str.length > limit) {
        var ret = str.splice(0, limit);
        ret.push(str.join(separator));

        return ret;
    }

    return str;
}


function getPath(object, path) {
    if (path.includes(".")) {
        let [field, rest] = split(path, ".", 1);
        return getPath(object[field], rest);
    }
    return object[path];
}

function renderTableRow(fields, rowData) {
    let row = fields.map((field) => {
        return getPath(rowData, field);
    });
    return nunjucks.renderString(templates["row"], { row })
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

                if (data.fields) {
                    html = html + renderTableRow(data.fields, rowData);
                } else {
                    html = html + renderModelRow(currentModel, rowData);
                }

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