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

function stopConfetti() {
    var cf = $('#confetti').get(0);
    var context = cf.getContext('2d');
    context.clearRect(0, 0, cf.width, cf.height);
    confetti.stop();
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
    if (Number(data['handin_count']) != 0) {
        $('div#problem-status').removeClass('hidden');
        frac = data['complete_count'] /data['handin_count'];
        bar.animate(frac);
        $(bar.text).text(`${data['complete_count']}/${data['handin_count']} graded`);
        // $(bar.text).text(data['complete_count'] + '/' + data['handin_count'] + ' completed.');
    }
    try {
        if (data['handin_count'] == data['complete_count']) {
            // don't you dare delete this person reading this code
            confetti.start();
        }
        else {
            stopConfetti();
        }
    }
    catch(err) {
        console.log("Confetti Error, talk to HTA!")
    }
    $('div#handin-options').removeClass('hidden');
    clearSidebar();
    populateSidebar(data['ta_handins']);
    $('footer').removeClass('nodisp');
    if (!data['anonymous']) {
        populateStudentList(data['unextracted_logins']);
    }
}

function populateStudentList(s) {
    sel = $('#student-select');
    sel.find('option').not('.nodel').remove();
    for (var i = 0; i < s.length; i++) {
        opt = $('<option>');
        opt.val(s[i]);
        opt.text(s[i]);
        sel.append(opt);
    }
    sel.select2();
    // $('#student-list-modal').modal('open');
}

function clearSidebar() {
    $('li.handin-list-item').not('#handin-list-item-template').remove();
    $('button.handin-button').not('.extract-button').prop('disabled', true);
}

function generateSidebarItem(li, handin) {
    h = handin;
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
    if (handin['student-name'] != null) {
        li.find('span.sname').remove();
        span = $("<span class='sname'>");
        span.text('(' + handin['student-name'] + ')');
        li.append(span);
    }
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
    $('.extract-button').prop('disabled', 'true');
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

function extractByLogin(x) {
    s = $('#student-select').val();
    if (s == 'NONE') {
        M.toast({'html': 'Select a student...',
                 'displayLength': 2000})
        return;
    }
    $('.extract-button').prop('disabled', 'true');
    $.ajax({
        'url': '/extract_handin',
        'data': {'handin_login': s},
        success: function(data) {
            pdata = JSON.parse(data)
            if (pdata == "None") {
                M.toast({'html': 'No more to grade!',
                         'displayLength': 3000});
                return;
            }
            populateSidebar([pdata]);
            handinLoaded(data);
            $('#student-list-modal').modal('close');
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

function copyCodeLink(x) {
    button = $(x);
    $('#code-link').select();
    document.execCommand('copy');
    M.toast({html: 'Copied'});
}

function handinLoaded(problemData) {
    var problemData = JSON.parse(problemData);
    resetContainer();
    $('#code-content').text(problemData['student-code']); // set code viewer content
    $('#code-link').val(problemData['sfile-link']);
    $('main').data('active-id', problemData['id']); // set main data to the student's id
    var sidebarItem = sidebarById(problemData['id']); // get sidebar item for this handin
    $(sidebarItem).addClass('active-li'); // select current sidebar item
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
    var codeButton = $('<button onclick="openCode(this)" class="btn">');
    codeButton.text(`View student code (${problemData['filename']})`);
    gradingForm.prepend(codeButton);
    $('main .container').html(gradingForm);
    $('pre code').each(function(i, block) {
        Prism.highlightElement(block);
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
    r = rubric;
    var container = $('<div class="container">'); // container with entire rubric for student
    var keys = Object.keys(rubric['rubric']);
    keys.sort();
    for (var i = 0; i < keys.length; i++) {          // **for each category...
        var cat = keys[i];
        var catDiv = $('<div class="category-div">'); // div for this category
        var catName = $('<div class="category-name">'); // category div headre
        catDiv.data('category', cat);
        catName.text(cat);
        catDiv.append(catName);
        var category = rubric['rubric'][cat]['rubric_items']; // list of rubric items
        for (var j = 0; j < category.length; j++) {   // **for each rubric item...
            rubric_item = category[j];
            // generate description of rubric item (left side of HTML)
            var rubric_desc = $('<div class="rubric-desc">');
            rubric_desc.text(rubric_item['descr']);
            // just in case text is somehow modified, add the name as data too
            catDiv.append(rubric_desc);

            // generate select dropdown for the rubric item options
            var rubric_select = $('<select class="rubric-sel browser-default">');
            rubric_select.data('description', rubric_item['descr']);
            for (var k = 0; k < rubric_item['options'].length; k++) { // for each option of each rubric item
                var opt = $('<option>');
                opt.val(k);
                opt.text(rubric_item['options'][k]['descr']);
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
            catDiv.append(rubric_select);
        }
        // add comment row for this category...
        var commentDivDescription = $('<div class="rubric-desc-column">');
        commentDivDescription.text('Enter comments for ' + cat + ': ');

        var commentDiv = generateCommentSection(cat, rubric['rubric'][cat]['comments'], cat);
        commentDiv.addClass('rubric-sel-column');

        catDiv.append(commentDivDescription);
        catDiv.append(commentDiv);

        catDiv.append(commentDiv);
        container.append(catDiv);

    }
    a = rubric;
    genCommentSel  = generateCommentSection('General', rubric['comments'], null);
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

function generateCommentSection(category, comments, send_cat) {
    var sel = $('<select multiple="multiple" class="form-control">');
    sel.addClass('comment-select');
    var data = [];
    for (var i = 0; i < comments['given'].length; i++) {
        var comment = comments['given'][i];
        var new_comment = {'id': comment,
                           'text': comment,
                           'selected': true};
        data.push(new_comment);
    }
    for (var i = 0; i < comments['un_given'].length; i++) {
        var comment = comments['un_given'][i];
        var new_comment = {'id': comment,
                           'text': comment,
                           'selected': false};
    }
    sel.prop('id', category);
    sel.data('category', category);
    sel.select2({data: data,
                 tags: true
                 }).on('select2:select',
                        function(e) {
                            console.log(e);
                            if (e.params.data.isNew) {
                                term = e.params.data.text;
                                CommentDialog("Make comment useable by all TA's?", send_cat, term);
                            }
                        });
    return sel;
}

function CommentDialog(message, category, comment) {
    $('<div></div>').appendTo('body')
    .html('<div><h6>'+message+'?</h6></div>')
    .dialog({
        modal: true, title: 'Make comment global?', zIndex: 10000, autoOpen: true,
        width: 'auto', resizable: false,
        open: function() {
              $(this).parents('.ui-dialog-buttonpane button:eq(1)').focus(); 
            },
        buttons: {
            No: function () {
                $(this).dialog("close");
            },
            Yes: function () {
                addGlobalComment(category, comment);
                $(this).dialog("close");
            }
        },
        close: function (event, ui) {
            // $(this).remove();
        }
    });
};

function addGlobalComment(category, comment) {
    c = category;
    $.ajax({
        url: '/add_global_comment',
        data:
        {
            'id': $('main').data('active-id'),
            'category': category,
            'comment': comment,
        },
        success: function() {
            M.toast({'html': 'Global comment added.',
                     'displayLength': 2000});
            $('#handin-save').click();
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
    $('button.handin-button').not('.extract-button').prop('disabled', true);
}

function fetchFormInfo() {
    var rubric = {};
    r = rubric;
    var cats = $('.container .category-div');
    for (var i = 0; i < cats.length; i++) {
        var cat = cats.eq(i);
        var cname = cat.data('category');

        rubric[cname] = {}
        var sels = cat.find('select.rubric-sel');
        for (var j = 0; j < sels.length; j++) {
            var sel = sels.eq(j);
            var descr = sel.data('description');
            var v = sel.val();
            if (v != null) {
                rubric[cname][descr] = Number(v);
            }
            else {
                rubric[cname][descr] = null;
            }
            
        }
    }
    return rubric;
}

function getComments() {
    data = [];
    commentDivs = $('.category-div .comment-select');
    data.push($('#General').val());
    data.push({});
    for (i = 0; i < commentDivs.length; i++) {
        commentDiv = commentDivs.eq(i);
        data[1][commentDiv.data('category')] = commentDiv.val();
    }
    return data;
}

function saveHandin(x, complete=false) {
    formData = fetchFormInfo();
    comments = getComments();
    activeId = $('main').data('active-id');
    $.ajax({
        url: '/save_handin', // returns false if there was no error
        data:
            {
                'formData': JSON.stringify(formData),
                'id': JSON.stringify(activeId),
                'completed': JSON.stringify(complete),
                'comments': JSON.stringify(comments)
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
    $('.handin-button').not('.extract-button').prop('disabled', true);
}

function viewReport(x) {
    $('#report-modal').modal('open');
    cid = $('main').data('active-id');
    button = $(x);
    // reportLoaded("Hello");
    $.ajax({
        url: '/preview_report',
        data: {'id': cid},
        success: reportLoaded
    })
}

function reportLoaded(data) {
    $('#report-contents').html(JSON.parse(data));
}

function runTest(x) {
    button = $(x);
    button.prop('disabled', true);
    button.text('Running... do not do anything!')
    cid = $('main').data('active-id');
    $.ajax({
        url: '/run_test',
        data: {'id': cid},
        success: testsRun,
        error: testsFailed
    });
}

function testsRun(data) {
    var b = $('#run-test-button')
    b.prop('disabled', false);
    b.text('Run tests');

    res = JSON.parse(data);
    $('#test-content').text(res);
    $('#test-modal').modal('open');
}

function testsFailed(data) {
    console.log(data);
    M.toast({'html': 'Test run failed: contact HTA (console)',
             'displayLength': 3000});
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
    $('#report-modal').modal();
    $('#test-modal').modal();
    $('#student-list-modal').modal();
    $('#student-list-modal').removeAttr('tabindex');

    // initialize all selects
    $('.select2-multiple').select2();
    $('#student-select').select2();
});

function newPopup(url) {
	popupWindow = window.open(
		url,'popUpWindow','height=800,width=1000,left=10,top=10,resizable=yes,scrollbars=yes,toolbar=yes,menubar=no,location=no,directories=no,status=yes')
}


function openCode(x) {
    newPopup('/view_code?id=' + $('main').data('activeId'));
}
