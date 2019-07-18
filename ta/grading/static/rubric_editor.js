let unsavedChanges = false;

let editor;
let container;
let codeEditor;

String.prototype.replaceAll = function(search, replacement) {
    var target = this;
    return target.split(search).join(replacement);
};

function selectedRubric() {
    const sel = $('#rubric-select');
    const asgn = sel.children(':selected').data('asgn');
    const full_asgn = sel.children(':selected').data('full_asgn');
    if (asgn === undefined) {
        return null;
    }
    const qn = Number(sel.val());
    return {asgn, qn, full_asgn};
}

function editMode(rubric) {
    $('main').addClass('edit-mode');
    $('main').removeClass('updater-mode');
    $('#mode').text('');
    delete editor.options.onEditable;
    editor.options.modes = ['tree', 'code', 'text'];
    editor.setMode('tree');
    editor.set(rubric);
}

function updaterMode(rubric) {
    $('main').addClass('updater-mode');
    $('main').removeClass('edit-mode');
    $('#mode').text('(Read only - editable only by updater below)');
    editor.options.onEditable = (p) => false;
    editor.options.modes = ['code'];
    editor.setMode('code');
    codeEditor.refresh();
    editor.set(rubric);
}

function selectRubric() {
    $('#editor').html('');
    $('#create-button').prop('disabled', true);
    $('#rubric-info').text('');
    const rubric = selectedRubric();
    if (rubric == null) {
        return;
    }
    fetch(`/load_rubric/${rubric.asgn}/${rubric.qn}`)
    .then(resp => resp.json())
    .then(rubric => {
        if (rubric == null) {
            editor.set({"To start": "Click 'Create rubric'"})
            $('#create-button').prop('disabled', false);
        }
        else {
            if (rubric['started']) {
                updaterMode(rubric['rubric']);
            }
            else {
                editMode(rubric['rubric']);
            }
        }
    });
}


function createRubric(b) {
    const button = $(b);
    button.prop('disabled', true);
    const rubric = selectedRubric();
    if (rubric == null) {
        return;
    }
    fetch(`/create_rubric/${rubric.asgn}/${rubric.qn}`)
    .then(resp => resp.json())
    .then(rubric => {
        editMode(rubric);
        button.prop('disabled', true);
    });
}

function pushUpdate() {
    const rubric = selectedRubric();
    if (rubric == null) {
        return;
    }
    if (editor.errorNodes.length > 0) {
        alert('Cannot save invalid rubric');
        return;
    }
    const data = editor.get();
    opts = {
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
            'Content-Type': 'application/json'
        }
    }
    fetch(`/update_rubric/${rubric.asgn}/${rubric.qn}`, opts)
    .then(resp => resp.text())
    .then(txt => {
        if (txt == 'Success') {
            alert('Updated');
            unsavedChanges = false;
        }
        else {
            alert(`Error updating: ${txt}`);
        }
    });
}


function exiting(e) {
    if (!unsavedChanges) {
        console.log('Not prompting save');
        return undefined;
    }
    var message = "You have unsaved changes. Exit anyway?",
    e = e || window.event;
    if (e) {
        e.returnValue = message;
    }

    // For Safari
    return message;
}

function updated() {
    unsavedChanges = true;
    try {
        const content = editor.get();    
    }
    catch (err) {
        console.log('error parsing json');
        console.error(err);
    }
}

function previewUpdate(x) {
    const rubric = selectedRubric();
    if (rubric == null) {
        return;
    }
    b = $(x);
    b.text('Checking...');
    b.prop('disabled', true);
    fetch(`/check_updater/${rubric.asgn}/${rubric.qn}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(
        {
            code: codeEditor.getValue()
        }
        )
    })
    .then(resp => resp.json())
    .then(json => {
        b.text('Check & Preview updater');
        b.prop('disabled', false);

        text = json.results.replaceAll('\n', '<br/>')
        if (text == 'Good') {
            $('#errors').html('Updater passed checks. Rubric preview loaded into JSON viewer.');
            editor.set(json.preview);
        }
        else {
            $('#errors').html(text);
        }
    })
    .catch(err => {
        console.error(err);
        $('#errors').html(err);
        b.text('Check & Preview updater');
        b.prop('disabled', false);
    });
}

function updateRubrics(x) {
    const rubric = selectedRubric();
    if (rubric == null) {
        return;
    }
    if (!confirm('Confirm rubric update')) {
        return;
    }
    b = $(x);
    b.text('Checking...');
    b.prop('disabled', true);
    fetch('/run_updater', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            full_asgn: rubric.full_asgn,
            qn: rubric.qn,
            code: codeEditor.getValue()
        })
    })
    .then(resp => resp.text())
    .then(text => {
        if (text == 'Success') {
            alert('Rubrics sucessfully updated.');
            b.prop('disabled', false);
            b.text('Update all rubrics');
        }
        else {
            alert(text);
        }
    })
    .catch(err => {
        console.error(err);
        alert(`Error updating rubrics: ${err}`);
        b.prop('disabled', false);
        b.text('Update all rubrics');
    });
}

function setupEditor() {
  var options = {
    schema: rubric,
    schemaRefs: {comments, rubricCategory, rubricItem, rubricOption},
    mode: 'tree',
    modes: ['code', 'text', 'tree'],
    onChange: updated,
    templates: [
    {
      text: 'Rubric Category',
      title: 'Insert a new rubric category',
      className: 'jsoneditor-type-object',
      field: 'CategoryName',
      value: {
        comments: {'given': [], 'un_given': []},
        fudge_points: [0, 5],
        rubric_items: []
    }
},
{
  text: 'Rubric Item',
  title: 'Insert a new rubric item',
  className: 'jsoneditor-type-object',
  value: {
    selected: null,
    descr: 'Item Description',
    options: []
}
},
{
  text: 'Rubric Option',
  title: 'Insert a new rubric option',
  className: 'jsoneditor-type-object',
  value: {
    point_val: 0,
    descr: "option description"
}
}]
};
  // create the editor
  container = document.getElementById('jsoneditor');
  editor = new JSONEditor(container, options, {"To start": "Select a rubric to edit"});
}

$(document).ready(() => {
  window.onbeforeunload = exiting;
  fetch('/rubricSchema')
  .then(resp => resp.json())
  .then(schemas => {
    rubric = schemas['rubric'];
    comments = schemas['comments'];
    rubricCategory = schemas['rubricCategory'];
    rubricItem = schemas['rubricItem'];
    rubricOption = schemas['rubricOption'];
    setupEditor();
});
  setInterval(() => {
    $('#save-button').prop('disabled', !unsavedChanges);
}, 300);
  codeEditor = CodeMirror.fromTextArea(document.getElementById('thingy'), {
    lineNumbers: true,
    mode: "python"
});
});
