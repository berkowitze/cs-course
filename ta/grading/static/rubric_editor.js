let unsavedChanges = false;

function selectedRubric() {
    const sel = $('#rubric-select');
    const asgn = sel.children(':selected').data('asgn');
    if (asgn === undefined) {
        return null;
    }
    const qn = Number(sel.val());
    return {asgn, qn};
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
        console.log(rubric);
        if (rubric == null) {
            editor.set({"To start": "Click 'Create rubric'"})
            $('#create-button').prop('disabled', false);
        }
        else {
            editor.set(rubric);
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
        editor.set(rubric);
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



let editor;
let container;

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
  }, 300)
});
