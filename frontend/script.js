const models = ["message", "emoji", "channel", "guild", "user"];
const templates = { "results": null };

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

function renderModelRow(name, row) {
    return nunjucks.renderString(templates[name], { row });
}

function renderResult(results, fields) {
    $("#error").hide();
    $("#results").html(nunjucks.renderString(templates["results"], {
        fields: fields,
        rows: results,
    }))
}

function renderError(error) {
    $("#error").show().text(error);
}

function handleSearchChange(event) {
    var currentModel = $("#model option:selected").text();
    var query = {
        "query": $(event.target).val(),
        "limit": 1000,
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
        if (data.results && !data.error) {
            renderResult(data.results, data.fields);
        } else if (data.error) {
            renderError(data.error);
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