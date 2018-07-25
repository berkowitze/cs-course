function loadAsgn(x) {
    sel = $(x);
    $.ajax({url: '/load_asgn',
            success: asgnLoaded,
            data: {'asgn': sel.val()}})
}

function asgnLoaded(x) {
    problems = JSON.parse(x);
    if (problems == "None") {
        $('div#prob-list-div').addClass('hidden');
        $('div#problem-status').addClass('hidden');
        clearSidebar();
        return;
    }
    sel = $('select#prob-list');
    $('div#prob-list-div').removeClass('hidden');
    sel.find('option').not('#base-prob-opt').remove();
    problems.map(function(a, b) {
        opt = $('<option>');
        opt.text(a);
        opt.val(b+1);
        sel.append(opt);
    });
}

function loadProb(x) {
    sel = $(x);
    probNumb = sel.val();
    $.ajax({
        url: '/load_prob',
        success: probLoaded,
        data: {'prob': probNumb}
    });
}

function probLoaded(x) {
    data = JSON.parse(x);
    if (data == "None") {
        $('div#problem-status').addClass('hidden');
        clearSidebar();
        $('div#handin-options').addClass('hidden');
        return;
    }
    $('div#problem-status').removeClass('hidden');
    frac = Number(data["completed"]) / Number(data["handins"]);
    bar.animate(frac);
    $(bar.text).text(data['completed'] + '/' + data['handins'] + ' completed.');
    try {
        if (data['completed'] == data['handins']) {
            // don't you dare delete this person reading this code
            confetti.start();
        }
        else {
            cf = $('#confetti').get(0);
            context = cf.getContext('2d');
            context.clearRect(0, 0, cf.width, cf.height);
            confetti.stop();
        }
    }
    catch(err) {

    }
    $('div#handin-options').removeClass('hidden');
    clearSidebar();
    populateSidebar(data['handin_data']);
    $('footer').removeClass('nodisp');
}

function clearSidebar() {
    $('li.handin-list-item').not('#handin-list-item-template').remove();
    $('button.handin-button').not('#extract-handin').prop('disabled', true);
}

function generateSidebarItem(li, handin) {
    li.prop('id', '');
    li.find('.handin-student-id').text(handin['id']);
    li.addClass('nontemp');
    if (JSON.parse(handin['complete'])) {
        secondary = 'Complete'
        li.addClass('complete');
    }
    else {
        secondary = 'In progress'
        li.addClass('incomplete');
    }
    if (JSON.parse(handin['flagged'])) {
        li.addClass('flagged');
        secondary += ', flagged'
    }
    else {
        li.addClass('unflagged');
    }
    li.data('student-id', handin['id']);
    li.find('.handin-status').text(secondary);
    li.removeClass('nodisp');
    return li;
}

function populateSidebar(userHandins) {
    sidebarItems = [];
    for (i = 0; i < userHandins.length; i++) {
        var handin = userHandins[i];
        var template = $('#handin-list-item-template');
        sidebarItems.push(generateSidebarItem(template.clone(), handin));
        
    }
    sidebarItems = sidebarItems.sort(function(a, b) {
        if ($(a).data('studentId') < $(b).data('studentId')) {
            return -1;
        }
        else {
            return 1;
        }
    });
    $('#handin-ul div#sidenav-content').append(sidebarItems);
}

function extract(x) {
    button = $(x);
    button.prop('disabled', true);
    $.ajax({
        url: '/extract_handin',
        success: function(data) {
            pdata = JSON.parse(data)
            if (pdata == "None") {
                M.toast({'html': 'No more to grade!',
                         'displayLength': 3000});
                return;
            }
            populateSidebar([pdata]);
            handinLoaded(data);
        }
    });
}

function loadHandin(x) {
    $('.active-li').removeClass('active-li');
    $(x).addClass('active-li');
    var sid = $(x).data('student-id');
    $.ajax({
        url: '/load_handin',
        data: {'sid': sid},
        success: handinLoaded
    });
}

function resetContainer() {
    $('main .container').html(''); // get rid of container data
    $('#code-content').html(''); // get rid of code viewer content
    $('.active-li').removeClass('active-li'); // deselect selected sidebar items
}

function handinLoaded(problemData) {
    problemData = JSON.parse(problemData);
    resetContainer();
    $('#code-content').html(problemData['student-code']); // set code viewer content
    $('main').data('active-id', problemData['id']); // set main data to the student's id
    var x = sidebarById(problemData['id']); // get sidebar item for this handin
    $(x).addClass('active-li'); // select current sidebar item
    $('button.handin-button').prop('disabled', false); // disable handin button
    if (problemData['flagged']) {
        $('#handin-flag').text('Unflag');
        $('#handin-flag').data('flag', false);
    }
    else {
        $('#handin-flag').text('Flag');
        $('#handin-flag').data('flag', true);
    }
    var gradingForm = rubricToForm(problemData['rubric']);
    var codeButton = $('<button data-target="code-modal" class="btn modal-trigger">')
    codeButton.text('View student code (' + problemData['filename'] + ')');
    gradingForm.prepend(codeButton);
    $('main .container').html(gradingForm);
    $('pre code').each(function(i, block) {
        hljs.highlightBlock(block);
    });
}

function sidebarById(id) {
    var lis = $('li.handin-list-item.nontemp');
    for (i = 0; i < lis.length; i++) {
        if (lis.eq(i).data('student-id') == id) {
            return lis.eq(i);
        }
    }
    return undefined;
}

function rubricToForm(rubric) {
    var container = $('<div class="container">'); // container with entire rubric for student
    var keys = Object.keys(rubric);
    keys.sort();
    for (var i = 0; i < keys.length; i++) {          // **for each category...
        var key = keys[i];
        if (key == '_COMMENTS') {
            continue;
        }
        var catDiv = $('<div class="category-div">'); // div for this category
        var catName = $('<div class="category-name">'); // category div headre
        catName.text(key)
        catDiv.append(catName);
        a = rubric[key];
        var category = rubric[key]['rubric_items']; // list of rubric items
        for (var j = 0; j < category.length; j++) {   // **for each rubric item...
            rubric_item = category[j];
            // generate description of rubric item (left side of HTML)
            var rubric_desc = $('<div class="rubric-desc">');
            rubric_desc.text(rubric_item['name']);
            // just in case text is somehow modified, add the name as data too
            rubric_desc.data('json_key', rubric_item['name']);
            rubric_desc.data('cat_id', i);
            rubric_desc.data('item_id', j);
            catDiv.append(rubric_desc);

            // generate select dropdown for the rubric item options
            var rubric_select = $('<select class="rubric-sel browser-default">');
            for (var k = 0; k < rubric_item['options'].length; k++) { // for each option of each rubric item
                var opt = $('<option>');
                opt.val(rubric_item['options'][k]);
                opt.text(rubric_item['options'][k]);
                opt.data('index', k);
                rubric_select.append(opt);
            }
            if ('value' in rubric_item && rubric_item['value'] != null) {
                rubric_select.val(rubric_item['value']); // set value if it's set
            }
            else if (rubric_item['default'] != null) {
                rubric_select.val(rubric_item['default']); // set default if value not set
            }
            else {
                rubric_select.val(''); // set no value if null default & no value
            }
            rubric_select.data('cat_id', i);
            rubric_select.data('item_id', j);
            catDiv.append(rubric_select);
        }
        // add comment row for this category...
        var commentDivDescription = $('<div class="rubric-desc-column">');
        commentDivDescription.text('Enter comments for ' + key + ': ');

        var commentDiv = generateCommentSection(key, rubric[key]['comments']);
        commentDiv.addClass('rubric-sel-column');

        catDiv.append(commentDivDescription);
        catDiv.append(commentDiv);

        catDiv.append(commentDiv);
        container.append(catDiv);

    }
    a = rubric;
    genCommentSel  = generateCommentSection('General', rubric['_COMMENTS']);
    genCommentHead = $('<div class="general-name">');
    genCommentHead.text('General Comments');
    container.append(genCommentHead);
    container.append(genCommentSel);
    $(document).ready(function(){
        $('select.comment-select').select2({'tags': true, 
                    createTag: function (tag) {
                    return {
                        id: tag.term,
                        text: tag.term,
                        isNew: true
                    }
                 }});
    });
    return container;
}

function generateCommentSection(category, comments) {
    var sel = $('<select multiple="multiple" class="form-control">');
    sel.addClass('comment-select');
    var data = [];
    for (var i = 0; i < comments.length; i++) {
        var comment = comments[i];
        var new_comment = {'id': comment['comment'],
                           'text': comment['comment'],
                           'selected': comment['value']};
        data.push(new_comment);
    }
    sel.prop('id', category);
    sel.select2({data: data,
                 tags: true
                 }).on('select2:select',
                        function(e) {
                            console.log(e);
                            if (e.params.data.isNew) {
                                term = e.params.data.text;
                                CommentDialog("Make comment useable by all TA's?", category, term);
                            }
                        });
    return sel;
}

function CommentDialog(message, category, comment) {
    $('<div></div>').appendTo('body')
    .html('<div><h6>'+message+'?</h6></div>')
    .dialog({
        modal: true, title: 'Delete message', zIndex: 10000, autoOpen: true,
        width: 'auto', resizable: false,
        buttons: {
            Yes: function () {
                console.log('Global Comment');
                addGlobalComment(category, comment, false);
                $(this).dialog("close");
            },
            No: function () {
                console.log('Local comment');
                addGlobalComment(category, comment, true);
                $(this).dialog("close");
            }
        },
        close: function (event, ui) {
            // $(this).remove();
        }
    });
};

function addGlobalComment(category, comment, global) {
    $.ajax({
        url: '/add_comment',
        data:
        {
            'id': $('main').data('active-id'),
            'category': category,
            'comment': comment,
            'student-only': global,
        },
        success: function() {
            M.toast({'html': 'Comment added; save handin',
                     'displayLength': 2000});
            $('#new-comment-inp').val('');
        }
    });
}


function flagToggle(x) {
    button = $(x);
    activeId = $('main').data('active-id');
    flagIt = button.data('flag');
    if (flagIt) {
        msg = prompt('Why are you flagging this?\nOnly HTAs will see this, not the student.')
    }
    else {
        msg = ''
    }
    $.ajax({
        url: '/flag_handin',
        data: {'flag': flagIt, 'id': activeId, 'msg': msg},
        success: toggledFlag
    });
}


function toggledFlag(data) {
    data = JSON.parse(data);
    li = sidebarById(data['id']);
    if (JSON.parse(data['flagged'])) {
        $('#handin-flag').text('Unflag');
        $('#handin-flag').data('flag', false);
        li.removeClass('unflagged');
        li.addClass('flagged');
    }
    else {
        $('#handin-flag').text('Flag');
        $('#handin-flag').data('flag', true);
        li.removeClass('flagged');
        li.addClass('unflagged');
    }
    handin = data['problemData'];
    generateSidebarItem(li, handin);
}

function unextractHandin(x) {
    button = $(x);
    activeId = $('main').data('active-id');
    if (!confirm('Confirm Removal')) {
        return;
    }
    $.ajax({
        url: '/unextract_handin',
        data: {'id': activeId},
        success: handinUnextracted
    });
}

function handinUnextracted(data) {
    ident = JSON.parse(data);
    sidebarById(ident).remove();
    $('main .container').html('');
    $('button.handin-button:not(#extract-handin)').prop('disabled', true);
}

function fetchFormInfo() {
    // helper to get all the description/option pairs since i was too
    // lazy to fix the html (css grid was messing it up :( )
    // is this awful? well... yes it's awful. but... like..... ya know...
    // go nested functions! im gonna shut up hi future hta
    getPairs = function() {
        selects = $('.rubric-sel');
        descs  = $('.rubric-desc');
        pairs = [];
        for (i = 0; i < selects.length; i++) {
            sel = selects.eq(i);
            for (j = 0; j < descs.length; j++) {
                desc = descs.eq(j);
                if ((sel.data('item_id') == desc.data('item_id')) &&
                    (sel.data('cat_id') == desc.data('cat_id'))) {
                    cat = sel.siblings('.category-name').text();
                    pairs.push({'select': sel, 'description': desc, 'category': cat});
                    break;
                }
            }
        }
        return pairs;
    }
    pairs = getPairs();
    data = {};
    for (i = 0; i < pairs.length; i++) {
        pair = pairs[i];
        keyval = pair['select'].val();
        key = pair['description'].data('json_key');
        data[key] = [keyval, pair['category']];
    }
    return data;
}

function getComments() {
    data = {};
    commentDivs = $('.category-div .comment-select, #General');
    for (i = 0; i < commentDivs.length; i++) {
        commentDiv = commentDivs.eq(i);
        data[commentDiv.prop('id')] = commentDiv.val();
    }
    return data;
}

function saveHandin(x, complete=false) {
    formData = fetchFormInfo();
    activeId = $('main').data('active-id');
    $.ajax({
        url: '/save_handin', // returns false if there was no error
        data:
            {
                'formData': JSON.stringify(formData),
                'id': JSON.stringify(activeId),
                'completed': JSON.stringify(complete),
                'comments': JSON.stringify(getComments())
            },
        success: function(data) {
            if (!JSON.parse(data)) {
                M.toast({
                    'html': 'Must fill all dropdowns before completing.',
                    'displayLength': 3000
                });
                return;
            }
            if (!complete) {
                handinSaved(data);
            }
            else {
                $.ajax({
                    url: '/complete_handin',
                    data: {'id': activeId},
                    success: handinCompleted
                });
            }
        }
    })
}

function handinSaved(data) {
    a = JSON.parse(data);
    M.toast({
        'html': 'Handin saved.',
        'displayLength': 2500
    });
}

function completeHandin(x) {
    saveHandin(x, complete=true);
}

function handinCompleted(data) {
    M.toast({
        'html': 'Handin completed',
        'displayLength': 2500
    });
    clearMain();
    loadProb($('select#prob-list'));
}

function clearMain() {
    $('#rubric-div').empty();
    $('.handin-button').not('#extract-handin').prop('disabled', true);
}

$(document).ready(function(){
    $('select#asgn-list').focus();
    x = 3;
    // the colorful status bar in the top left (super neccessary do not delete)
    bar = new ProgressBar.Line($('#status-slider').get(0), {
        strokeWidth: 4,
        easing: 'easeInOut',
        duration: 1400,
        trailColor: 'white',
        trailWidth: 1,
        svgStyle: {width: '100%', height: '100%'},
        from: {color: '#f45738'},
        to: {color: '#4BB543'},
        text: {
            value: '',
            color: 'black'
        },
        step: (state, bar) => {
          bar.path.setAttribute('stroke', state.color);
        }
    });

    // select all code on doubleclick
    // from S.O. https://stackoverflow.com/questions/35297919/
    $('pre').dblclick(function() {
        $(this).select();

        var text = this,
            range, selection;

        if (document.body.createTextRange) {
            range = document.body.createTextRange();
            range.moveToElementText(text);
            range.select();
        } else if (window.getSelection) {
            selection = window.getSelection();
            range = document.createRange();
            range.selectNodeContents(text);
            selection.removeAllRanges();
            selection.addRange(range);
        }
    });

    // initialize code viewer
    $('#code-modal').modal();

    // initialize all selects
    $('.select2-multiple').select2()
});
