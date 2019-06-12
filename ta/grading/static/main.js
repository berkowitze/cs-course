function loadAsgn(x) {
    var sel = $(x);
    $.ajax({url: '/load_asgn',
            success: asgnLoaded,
            data: {asgn: sel.val()}});
}

function asgnLoaded(jProblems) {
    var problems = JSON.parse(jProblems);
    if (problems == "None") {
        $('div#prob-list-div').addClass('hidden');
        $('div#problem-status').addClass('hidden');
        clearSidebar();
        return;
    }
    var sel = $('select#prob-list');
    $('div#prob-list-div').removeClass('hidden');
    sel.find('option').not('#base-prob-opt').remove();
    problems.map(function(a, b) {
        var opt = $('<option>');
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
    var sel = $(x);
    probNumb = sel.val();
    $.ajax({
        url: '/load_prob',
        success: probLoaded,
        data: {prob: probNumb}
    });
}

function probLoaded(x) {
    var data = JSON.parse(x);
    d = data;
    if (data == "None") {
        $('div#problem-status').addClass('hidden');
        clearSidebar();
        $('div#handin-options').addClass('hidden');
        return;
    }
    if (Number(data.handin_count) != 0) {
        $('div#problem-status').removeClass('hidden');
        var frac = data.complete_count / data.handin_count;
        bar.animate(frac);
        $(bar.text).text(`${data.complete_count}/${data.handin_count} graded`);
    }
    try {
        if (data.handin_count == data.complete_count) {
            // don't you dare delete this person reading this code
            confetti.start();
        }
        else {
            stopConfetti();
        }
    }
    catch(err) {
        console.log("Confetti Error, talk to HTA!");
    }
    $('div#handin-options').removeClass('hidden');
    clearSidebar();
    populateSidebar(data.ta_handins);
    $('footer').removeClass('nodisp');
    if (!data.anonymous) {
        populateStudentList(data.unextracted_logins);
    }
}

function populateStudentList(s) {
    var sel = $('#student-select');
    sel.find('option').not('.nodel').remove();
    for (i = 0; i < s.length; i++) {
        opt = $('<option>');
        opt.val(s[i]);
        opt.text(s[i]);
        sel.append(opt);
    }
}

function clearSidebar() {
    $('li.handin-list-item').not('#handin-list-item-template').remove();
    $('button.handin-button').not('.extract-button').prop('disabled', true);
}

function generateSidebarItem(li, handin) {
    var secondary;
    li.prop('id', '');
    li.find('.handin-student-id').text(handin.id);
    li.addClass('nontemp');
    if (JSON.parse(handin.complete)) {
        secondary = 'Complete';
        li.addClass('complete');
    }
    else {
        secondary = 'In progress';
        li.addClass('incomplete');
    }
    if (JSON.parse(handin.flagged)) {
        li.addClass('flagged');
        secondary += ', flagged';
    }
    else {
        li.addClass('unflagged');
    }
    li.data('student-id', handin.id);
    li.find('.handin-status').text(secondary);
    li.removeClass('nodisp');
    if (handin['student-name'] != null) {
        li.find('span.sname').remove();
        var span = $("<span class='sname'>");
        span.text('(' + handin['student-name'] + ')');
        li.append(span);
    }
    return li;
}

function populateSidebar(userHandins) {
    var sidebarItems = [];
    var handin;
    var template;
    for (var i = 0; i < userHandins.length; i++) {
        handin = userHandins[i];
        template = $('#handin-list-item-template');
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
            var pdata = JSON.parse(data);
            if (pdata == "None") {
                toast("No more to grade!", 'success', 3000);
                return;
            }
            populateSidebar([pdata]);
            handinLoaded(data);
        }
    });
}

function toast(msg, type, duration) {
    toastr.options.timeOut = duration;
    toastr[type](msg);
}

function extractByLogin(x) {
    var s = $('#student-select').val();
    if (s == 'NONE') {
        toast('Select a student...', 'failure', 3500);
        return;
    }
    $('.extract-button').prop('disabled', 'true');
    $.ajax({
        url: '/extract_handin',
        data: {handin_login: s},
        success: function(data) {
            var pdata = JSON.parse(data);
            if (pdata == "None") {
                toast('No more to grade!', 'success', '3000');
                return;
            }
            populateSidebar([pdata]);
            handinLoaded(data);
            $.modal.close();
        }
    });
}

function loadHandin(x) {
    $('.active-li').removeClass('active-li');
    $(x).addClass('active-li');
    var sid = $(x).data('student-id');
    $.ajax({
        url: '/load_handin',
        data: {sid: sid},
        success: handinLoaded
    });
}

function resetContainer() {
    $('main .container').html(''); // get rid of container data
    $('#code-content').html(''); // get rid of code viewer content
    $('.active-li').removeClass('active-li'); // deselect selected sidebar items
}

function handinLoaded(jProblemData) {
    var problemData = JSON.parse(jProblemData);
    resetContainer();
    $('#code-content').text(problemData['student-code']); // set code viewer content
    $('#code-link').val(problemData['sfile-link']);
    $('main').data('active-id', problemData.id); // set main data to the student's id
    var sidebarItem = sidebarById(problemData.id); // get sidebar item for this handin
    $(sidebarItem).addClass('active-li'); // select current sidebar item
    $('button.handin-button').prop('disabled', false); // disable handin button
    if (problemData.flagged) {
        $('#handin-flag').text('Unflag');
        $('#handin-flag').data('flag', false);
    }
    else {
        $('#handin-flag').text('Flag');
        $('#handin-flag').data('flag', true);
    }
    $('main .container').load('/render_rubric', function(e) {
        $('.tag-editor').contextmenu(function(e) {
            return tagEditorRightClick(e);
        });
//        $('.tag-editor').attr('oncontextmenu', 'return tagEditorRightClick(this)');
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


function flagToggle(x) {
    var button = $(x);
    var activeId = $('main').data('active-id');
    var flagIt = button.data('flag');
    var msg;
    if (flagIt) {
        msg = prompt('Why are you flagging this?\nOnly HTAs will see this, not the student.');
    }
    else {
        msg = '';
    }
    if (msg === null) {
        return;
    }
    $.ajax({
        url: '/flag_handin',
        data: {
            flag: flagIt,
            id: activeId,
            msg: msg},
        success: toggledFlag
    });
}


function toggledFlag(jdata) {
    var data = JSON.parse(jdata);
    var li = sidebarById(data.idid);
    if (JSON.parse(data.flagged)) {
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
    var handin = data.problemData;
    generateSidebarItem(li, handin);
}

function unextractHandin(x) {
    var button = $(x);
    var activeId = $('main').data('active-id');
    if (!confirm('Confirm Removal')) {
        return;
    }
    $.ajax({
        url: '/unextract_handin',
        data: {id: activeId},
        success: handinUnextracted
    });
}

function handinUnextracted(data) {
    var ident = JSON.parse(data);
    sidebarById(ident).remove();
    $('main .container').html('');
    $('button.handin-button').not('.extract-button').prop('disabled', true);
}

function fetchFormInfo() {
    var rubric = {};
    var cats = $('.container .category-div');
    var cat;
    var cname;
    var fudgePoints;
    var sels;
    for (i = 0; i < cats.length; i++) {
        cat = cats.eq(i);
        cname = cat.data('category');
        fudgePoints = Number(cat.find('input.fudge-points-inp').val());
        rubric[cname] = {
            fudge: fudgePoints,
            options: {}
        };
        sels = cat.find('select.rubric-sel');
        var j;
        for (j = 0; j < sels.length; j++) {
            var sel = sels.eq(j);
            var descr = sel.data('descr');
            var v = sel.val();
            if (v != null) {
                rubric[cname].options[descr] = Number(v);
            }
            else {
                rubric[cname].options[descr] = null;
            }
        }
    }
    return rubric;
}

function getComments() {
    var cat_comments = {};
    $('.category-div input.comments-sel')
    .tagEditor('getTags')
    .map(function(x) {
        cat_comments[x.field.dataset.category] = x.tags;
    });

    var gen_comments = $('input#general-comments').tagEditor('getTags')[0].tags;
    return {
        general: gen_comments,
        categorized: cat_comments
    };
}

function saveHandin(tryComplete) {
    console.log('SAVING with completed = ' + tryComplete);
    formData = fetchFormInfo();
    comments = getComments();
    activeId = $('main').data('active-id');
    emoji = $('#emoji').prop('checked');
    $.ajax({
        url: '/save_handin', // returns false if there was no error
        data:
            {
                'formData': JSON.stringify(formData),
                'id': JSON.stringify(activeId),
                'comments': JSON.stringify(comments),
                'emoji': emoji
            },
        success: function(data) {
            if (tryComplete) {
                handinSaved();
                completeHandin();
            }
            else {
                handinSaved();
            }
        }
    });
}

function handinSaved() {
    toast("Handin saved.", 'success', 2000);
}

function completeHandin() {
    activeId = $('main').data('active-id');
    $.ajax({
        url: '/complete_handin',
        data: {'id': activeId},
        success: handinCompleted
    });
}

function handinCompleted(data) {
    if (JSON.parse(data)) {
        clearMain();
        toast('Handin complete.', 'success', 2000);
        loadProb($('select#prob-list'));
    }
    else {
        toast('Must fill all dropdowns before completion.', 'error', 3500);
    }
}

function clearMain() {
    $('#rubric-div').empty();
    $('.handin-button').not('.extract-button').prop('disabled', true);
}

$(document).ready(function(){
    toastr.options.positionClass = "toast-bottom-right";
    $('select#asgn-list').focus();
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
});

var newPopup = (function() {
    var popups = {};
    var popup_ndx = 0;
    return function(url) {
        if (!(url in popups)) {
            popup_ndx += 1;
            popups[url] = popup_ndx;
        }
        window.open(
            url,
            popups[url],
            'height=800,width=1000,left=10,top=10,resizable=yes,' +
            'scrollbars=yes,toolbar=yes,menubar=no,location=no,status=yes');
    };
})();


function openCode(x) {
    newPopup('/view_code?id=' + $('main').data('activeId'));
}

function runTest(x) {
    newPopup('/run_test?id=' + $('main').data('activeId'));
}

function viewReport(x) {
    newPopup('/preview_report?id=' + $('main').data('activeId'));
}

function preTagSave(field, editor, given, tag, giving) {
    ungiven = field.data('options').autocomplete.source;
    if (given.includes(giving)) {
        // duplicate comment
        return;
    }
    ung_ndx = ungiven.indexOf(giving);
    if (ung_ndx >= 0) {
        // giving suggested comment
        ungiven.splice(ung_ndx, 1); // do not resuggest
        return;
    }
    // giving new unique comment
}

function tagEditorRightClick(e) {
    const elem = $(e.target);
    if (!elem.hasClass('tag-editor-tag')) {
        return false;
    }
    const tag = elem;
    field = tag.parentsUntil('ul.tag-editor').parent().siblings('input');
    category = tag.parents('.category-div').data('category');
    if (confirm('Make comment global?')) {
        $.ajax({
            url: 'add_global_comment',
            data: {
                'category': category,
                'comment': tag.text()
            },
            success: function(resp) {
                if (resp == 'added') {
                    console.log('success');
                }
                else {
                    console.log('failure');
                }
            },
            error: function(err) {
                console.log('err:');
                console.log(err);
            }
        });
    }
    return false;
}
