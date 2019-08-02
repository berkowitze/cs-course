# echo "Enter a branch name to use with git";
#read branchName;
#git checkout -b $branchName;
basepath=$(realpath `dirname $0`/..);

if [ ! -e $basepath/ta/venv/bin ]; then
  read -p "Enter a Python 3.7 path (i.e. /local/bin/python3.7): " PYTHONPATH;
  if [ -x $PYTHONPATH ]; then
      res=`$PYTHONPATH -c "import sys; print('%s.%s' % (sys.version_info.major, sys.version_info.minor))"`
      if [[ $res != "3.7" ]]; then
          echo "invalid python executable (got version $res, needed 3.7)"
          exit 1;
      fi;
  else
      echo "got non-executable path for python installation"
      exit 1;
  fi;
  virtualenv -p $PYTHONPATH "$basepath/ta/venv";
  $basepath/ta/venv/bin/pip install -r $basepath/ta/requirements.txt;
fi
function writeIfNotExists() {
    [ -e $1 ] || echo $2 >> $1;
}
writeIfNotExists $basepath/hta/grading/extensions.json "[]"
writeIfNotExists $basepath/hta/s-t-blocklist.json "{}"
writeIfNotExists $basepath/ta/t-s-blocklist.json "{}"

writeIfNotExists $basepath/ta/assignments.json '{
  "aa_README": [
    "all keys must be the same as the Google Form dropdown option",
    "dates are mm/dd/yyyy HH:MM_M format (i.e. 11/29/2018 05:00PM)",
    "format for each assignment in custom_types.py"
  ],
  "assignments": {}
}'

writeIfNotExists $basepath/hta/handin/submission_log.txt "";

echo '
1. Create handin form (Instructions: <INSERT LINK>)
    a. Get ID of spreadsheet the form dumps into
2. Go into ta/config.py
    a. change __base_path__
    b. change the settings in HandinConfig
    c. Set spreadsheet_id to 1a
    d. Set sheet_name to appropriate sheet name.
    e. Go to the CONFIG class and change email_from and hta_email
3. Contact Eli about getting a client secret setup. eliberkowitz@gmail.com
4. Go to /hta/handin and run `python get_creds.py`.
5. Run cs00-update-password
6. Make regrade forms & update hta/grading/regrading/settings.json
7. Register yagmail:
  /course/csxxxx/ta/venv/bin/python
  import yagmail
  yagmail.register(email, password)
'
function rename-execs() {
    cd $1;
    python -c "import os; [os.rename(f, f.replace('111', '00')) for f in os.listdir('.') if '111' in f]";
    sed 's/111/00/g' .gitignore > ugh;
    mv -f ugh .gitignore;
    cd $basepath;

}

rename-execs $basepath/tabin;
rename-execs $basepath/htabin;

function touch-if-dne() {
    [ -e $1 ] || touch $1;
}

touch-if-dne $basepath/ta/groups/tas.txt
touch-if-dne $basepath/ta/groups/htas.txt
touch-if-dne $basepath/ta/groups/students.txt
touch-if-dne $basepath/ta/groups/students.csv

